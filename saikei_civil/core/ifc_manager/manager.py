# ==============================================================================
# Saikei Civil - Civil Engineering Tools for Blender
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================

"""
Native IFC Manager
===================

Central manager for IFC file lifecycle and Blender visualization.
Creates and manages the IFC spatial hierarchy:

    IfcProject
    └── IfcSite
        └── IfcRoad

And visualizes it in Blender with organizational empties.

This module now uses ifc_api wrappers where possible for consistent
patterns and better API compatibility.
"""

import logging
from typing import Dict, List, Optional, Tuple

import bpy
import ifcopenshell
import ifcopenshell.guid

from .ifc_entities import (
    create_units,
    create_geometric_context,
    create_local_placement,
    find_geometric_context,
    find_axis_subcontext,
)
from .. import ifc_api
from .blender_hierarchy import (
    create_blender_hierarchy,
    clear_blender_hierarchy,
    get_or_find_collection,
    get_or_find_object,
    PROJECT_COLLECTION_NAME,
    ALIGNMENTS_EMPTY_NAME,
    GEOMODELS_EMPTY_NAME,
)
from .validation import validate_for_external_viewers, validate_and_report

logger = logging.getLogger(__name__)


class NativeIfcManager:
    """Manages IFC file lifecycle and Blender visualization.

    Creates proper spatial structure per IFC 4.3 standards and
    visualizes it in Blender's outliner for user clarity.

    This is a singleton-style class using class-level state.
    """

    # Class-level state
    file: Optional[ifcopenshell.file] = None
    filepath: Optional[str] = None
    project: Optional[ifcopenshell.entity_instance] = None
    site: Optional[ifcopenshell.entity_instance] = None
    road: Optional[ifcopenshell.entity_instance] = None

    # IFC core entities
    unit_assignment: Optional[ifcopenshell.entity_instance] = None
    geometric_context: Optional[ifcopenshell.entity_instance] = None
    axis_subcontext: Optional[ifcopenshell.entity_instance] = None

    # Blender references
    project_collection: Optional[bpy.types.Collection] = None
    alignments_collection: Optional[bpy.types.Object] = None
    geomodels_collection: Optional[bpy.types.Object] = None

    # Loaded vertical alignments
    vertical_alignments: List = []

    # Road parts by type (IfcRoadPartTypeEnum -> IfcRoadPart)
    road_parts: Dict[str, ifcopenshell.entity_instance] = {}

    # Blender empties for road parts
    road_part_empties: Dict[str, bpy.types.Object] = {}

    @classmethod
    def new_file(cls, schema: str = "IFC4X3") -> Dict:
        """Create new IFC file with complete spatial hierarchy.

        Creates IFC structure:
            IfcProject → IfcSite → IfcRoad

        And Blender visualization:
            Project (Empty) → Site (Empty) → Road (Empty)
            + Alignments, Geomodels empties

        Uses ifc_api wrappers for consistent patterns and API compatibility.

        Args:
            schema: IFC schema version (default: IFC4X3)

        Returns:
            dict with 'ifc_file', 'project_collection', entity references
        """
        cls.clear()

        # Create IFC file and core entities (units/context need manual handling)
        cls.file = ifcopenshell.file(schema=schema)
        cls.unit_assignment = create_units(cls.file)
        cls.geometric_context, cls.axis_subcontext = create_geometric_context(cls.file)

        # Create IfcProject (manual - needs UnitsInContext and RepresentationContexts)
        cls.project = cls.file.create_entity(
            "IfcProject",
            GlobalId=ifcopenshell.guid.new(),
            Name="Saikei Civil Project",
            Description="Civil engineering project",
            UnitsInContext=cls.unit_assignment,
            RepresentationContexts=[cls.geometric_context]
        )

        # Create IfcSite and IfcRoad using ifc_api wrappers
        # These handle placement and aggregation relationships automatically
        cls.site = ifc_api.create_site(
            cls.file,
            cls.project,
            name="Site",
            description="Project site"
        )

        cls.road = ifc_api.create_road(
            cls.file,
            cls.site,
            name="Road",
            description="Road facility"
        )

        # Create Blender visualization
        cls._create_blender_hierarchy()

        logger.info(
            f"Created IFC spatial hierarchy with {len(cls.file.by_type('IfcRoot'))} entities"
        )

        return {
            'ifc_file': cls.file,
            'project_collection': cls.project_collection,
            'project': cls.project,
            'site': cls.site,
            'road': cls.road
        }

    @classmethod
    def _create_blender_hierarchy(cls) -> None:
        """Create Blender visualization of IFC hierarchy."""
        result = create_blender_hierarchy(
            cls.project, cls.site, cls.road, cls.link_object
        )
        cls.project_collection = result[0]
        cls.alignments_collection = result[1]
        cls.geomodels_collection = result[2]

    @classmethod
    def open_file(cls, filepath: str) -> ifcopenshell.file:
        """Load existing IFC file and create Blender visualization.

        Args:
            filepath: Path to IFC file

        Returns:
            Loaded IFC file
        """
        cls.clear()
        cls.file = ifcopenshell.open(filepath)
        cls.filepath = filepath

        # Find key entities
        cls._load_entities_from_file()

        # Create Blender visualization
        cls._create_blender_hierarchy()

        # Load alignments
        cls._load_alignments()

        # Load vertical alignments
        cls._load_vertical_alignments()

        logger.info(
            f"Loaded IFC file: {filepath} "
            f"({len(cls.file.by_type('IfcRoot'))} entities, "
            f"{len(cls.file.by_type('IfcAlignment'))} alignments)"
        )

        return cls.file

    @classmethod
    def _load_entities_from_file(cls) -> None:
        """Load IFC entities from opened file."""
        projects = cls.file.by_type("IfcProject")
        if projects:
            cls.project = projects[0]
            cls.unit_assignment = cls.project.UnitsInContext
            if cls.project.RepresentationContexts:
                cls.geometric_context = find_geometric_context(cls.file)
            cls.axis_subcontext = find_axis_subcontext(cls.file)

        sites = cls.file.by_type("IfcSite")
        if sites:
            cls.site = sites[0]

        roads = cls.file.by_type("IfcRoad")
        if roads:
            cls.road = roads[0]

    @classmethod
    def _load_alignments(cls) -> None:
        """Load horizontal alignments from file."""
        from ..native_ifc_alignment import NativeIfcAlignment
        from ..alignment_visualizer import AlignmentVisualizer
        from ..alignment_registry import register_alignment, register_visualizer

        alignments = cls.file.by_type("IfcAlignment")
        for alignment_entity in alignments:
            try:
                alignment_obj = NativeIfcAlignment(
                    cls.file,
                    alignment_entity=alignment_entity
                )
                register_alignment(alignment_obj)

                visualizer = AlignmentVisualizer(alignment_obj)
                register_visualizer(visualizer, alignment_entity.GlobalId)
                alignment_obj.visualizer = visualizer
                visualizer.update_visualizations()

                logger.info(
                    f"Loaded alignment: {alignment_entity.Name} "
                    f"({len(alignment_obj.pis)} PIs)"
                )

            except Exception as e:
                logger.warning(
                    f"Failed to load alignment {alignment_entity.Name}: {e}"
                )

        # Set first alignment as active
        if alignments:
            from ...ui.alignment_properties import (
                set_active_alignment,
                refresh_alignment_list
            )
            if hasattr(bpy.context, 'scene'):
                refresh_alignment_list(bpy.context)
                set_active_alignment(bpy.context, alignments[0])

    @classmethod
    def _load_vertical_alignments(cls) -> None:
        """Load vertical alignments from file."""
        from ..native_ifc_vertical_alignment import load_vertical_alignments_from_ifc

        try:
            cls.vertical_alignments = load_vertical_alignments_from_ifc(cls.file)
            if cls.vertical_alignments:
                logger.info(
                    f"Loaded {len(cls.vertical_alignments)} vertical alignment(s)"
                )
                cls._integrate_vertical_alignments_with_profile_view()
        except Exception as e:
            logger.warning(f"Failed to load vertical alignments: {e}")
            cls.vertical_alignments = []

    @classmethod
    def _integrate_vertical_alignments_with_profile_view(cls) -> None:
        """Add loaded vertical alignments to profile view if open."""
        if not cls.vertical_alignments:
            return

        try:
            from ..profile_view_overlay import get_profile_overlay
            overlay = get_profile_overlay()

            if overlay:
                overlay.data.clear_vertical_alignments()
                for valign in cls.vertical_alignments:
                    overlay.data.add_vertical_alignment(valign)

                if cls.vertical_alignments:
                    overlay.data.select_vertical_alignment(0)
                overlay.data.update_view_extents()

                logger.debug("Profile view updated with vertical alignments")
        except Exception as e:
            logger.debug(f"Could not integrate with profile view: {e}")

    @classmethod
    def save_file(cls, filepath: Optional[str] = None, validate: bool = True) -> None:
        """Write IFC file to disk.

        Args:
            filepath: Path to save (uses stored filepath if None)
            validate: If True, validates before saving

        Raises:
            ValueError: If no filepath or file to save
        """
        if filepath:
            cls.filepath = filepath

        if not cls.filepath:
            raise ValueError("No filepath specified")
        if not cls.file:
            raise ValueError("No IFC file to save")

        if validate:
            validate_and_report(cls.file)

        cls.file.write(cls.filepath)
        bpy.context.scene["ifc_filepath"] = cls.filepath

        logger.info(f"Saved IFC file: {cls.filepath}")

    @classmethod
    def get_file(cls) -> ifcopenshell.file:
        """Get active IFC file, creating one if needed."""
        if cls.file is None:
            cls.new_file()
        return cls.file

    @classmethod
    def get_project(cls) -> Optional[ifcopenshell.entity_instance]:
        """Get IfcProject entity."""
        if cls.project is None and cls.file:
            projects = cls.file.by_type("IfcProject")
            if projects:
                cls.project = projects[0]
        return cls.project

    @classmethod
    def get_site(cls) -> Optional[ifcopenshell.entity_instance]:
        """Get IfcSite entity."""
        if cls.site is None and cls.file:
            sites = cls.file.by_type("IfcSite")
            if sites:
                cls.site = sites[0]
        return cls.site

    @classmethod
    def get_road(cls) -> Optional[ifcopenshell.entity_instance]:
        """Get IfcRoad entity."""
        if cls.road is None and cls.file:
            roads = cls.file.by_type("IfcRoad")
            if roads:
                cls.road = roads[0]
        return cls.road

    @classmethod
    def get_geometric_context(cls) -> Optional[ifcopenshell.entity_instance]:
        """Get geometric representation context."""
        if cls.geometric_context:
            return cls.geometric_context
        if cls.file:
            cls.geometric_context = find_geometric_context(cls.file)
        return cls.geometric_context

    @classmethod
    def get_axis_subcontext(cls) -> Optional[ifcopenshell.entity_instance]:
        """Get Axis sub-context for alignment curves."""
        if cls.axis_subcontext:
            return cls.axis_subcontext
        if cls.file:
            cls.axis_subcontext = find_axis_subcontext(cls.file)
            if not cls.axis_subcontext:
                return cls.get_geometric_context()
        return cls.axis_subcontext

    @classmethod
    def get_project_collection(cls) -> Optional[bpy.types.Collection]:
        """Get Blender collection for the project."""
        cls.project_collection = get_or_find_collection(
            cls.project_collection, PROJECT_COLLECTION_NAME
        )
        if cls.project_collection is None and cls.file is not None:
            logger.debug("Project collection was deleted, recreating...")
            cls._create_blender_hierarchy()
        return cls.project_collection

    @classmethod
    def get_alignments_collection(cls) -> Optional[bpy.types.Object]:
        """Get Blender empty for alignments."""
        cls.alignments_collection = get_or_find_object(
            cls.alignments_collection, ALIGNMENTS_EMPTY_NAME
        )
        if cls.alignments_collection is None and cls.file is not None:
            logger.debug("Alignments object was deleted, recreating...")
            cls._create_blender_hierarchy()
        return cls.alignments_collection

    @classmethod
    def get_geomodels_collection(cls) -> Optional[bpy.types.Object]:
        """Get Blender empty for geomodels."""
        cls.geomodels_collection = get_or_find_object(
            cls.geomodels_collection, GEOMODELS_EMPTY_NAME
        )
        if cls.geomodels_collection is None and cls.file is not None:
            logger.debug("Geomodels object was deleted, recreating...")
            cls._create_blender_hierarchy()
        return cls.geomodels_collection

    @classmethod
    def contain_alignment_in_road(
        cls,
        alignment: ifcopenshell.entity_instance
    ) -> Optional[ifcopenshell.entity_instance]:
        """Add spatial containment for alignment within road.

        Uses ifc_api.contain_in_spatial() for consistent relationship handling.

        Args:
            alignment: IfcAlignment entity to contain

        Returns:
            IfcRelContainedInSpatialStructure entity or None
        """
        if not cls.road:
            logger.warning("No road entity to contain alignment in")
            return None

        if not cls.file:
            logger.warning("No IFC file loaded")
            return None

        return ifc_api.contain_in_spatial(cls.file, alignment, cls.road)

    @classmethod
    def create_alignment_placement(cls) -> ifcopenshell.entity_instance:
        """Create IfcLocalPlacement for a new alignment."""
        road_placement = None
        if cls.road and hasattr(cls.road, 'ObjectPlacement'):
            road_placement = cls.road.ObjectPlacement
        return create_local_placement(cls.file, relative_to=road_placement)

    @classmethod
    def link_object(
        cls,
        blender_obj: bpy.types.Object,
        ifc_entity: ifcopenshell.entity_instance
    ) -> None:
        """Link Blender object to IFC entity.

        Args:
            blender_obj: Blender object
            ifc_entity: IFC entity to link
        """
        blender_obj["ifc_definition_id"] = ifc_entity.id()
        blender_obj["ifc_class"] = ifc_entity.is_a()
        blender_obj["GlobalId"] = ifc_entity.GlobalId

    @classmethod
    def get_entity(
        cls,
        blender_obj: bpy.types.Object
    ) -> Optional[ifcopenshell.entity_instance]:
        """Retrieve IFC entity from Blender object.

        Args:
            blender_obj: Blender object with IFC link

        Returns:
            IFC entity or None
        """
        if "ifc_definition_id" in blender_obj:
            return cls.file.by_id(blender_obj["ifc_definition_id"])
        return None

    # =========================================================================
    # IfcRoadPart Management (IFC 4.3 Spatial Hierarchy)
    # =========================================================================

    # Mapping from component types to IfcRoadPartTypeEnum values
    COMPONENT_TO_ROAD_PART_TYPE = {
        'LANE': 'TRAFFICLANE',
        'SHOULDER': 'SHOULDER',
        'CURB': 'ROADSIDE',  # Curbs are part of roadside
        'DITCH': 'ROADSIDE',  # Ditches are roadside elements
        'MEDIAN': 'CENTRALRESERVE',
        'SIDEWALK': 'SIDEWALK',
        'CUSTOM': 'ROADSEGMENT',
    }

    # Display names for road parts in Blender
    ROAD_PART_DISPLAY_NAMES = {
        'TRAFFICLANE': '🚗 Traffic Lanes',
        'SHOULDER': '🛤️ Shoulders',
        'ROADSIDE': '🌿 Roadside',
        'CENTRALRESERVE': '🚧 Central Reserve',
        'SIDEWALK': '🚶 Sidewalks',
        'CARRIAGEWAY': '🛣️ Carriageway',
        'ROADSEGMENT': '📐 Road Segment',
    }

    @classmethod
    def get_or_create_road_part(
        cls,
        road_part_type: str,
        name: Optional[str] = None
    ) -> Optional[ifcopenshell.entity_instance]:
        """
        Get or create an IfcRoadPart entity for the specified type.

        Args:
            road_part_type: IfcRoadPartTypeEnum value (e.g., 'TRAFFICLANE', 'SHOULDER')
            name: Optional custom name (defaults to type-based name)

        Returns:
            IfcRoadPart entity or None if no road exists
        """
        if not cls.file or not cls.road:
            logger.warning("Cannot create IfcRoadPart - no file or road entity")
            return None

        # Check if already exists
        if road_part_type in cls.road_parts:
            return cls.road_parts[road_part_type]

        # Create new IfcRoadPart
        road_part_name = name or f"{road_part_type.replace('_', ' ').title()}"

        # Get road placement for relative positioning
        road_placement = None
        if hasattr(cls.road, 'ObjectPlacement') and cls.road.ObjectPlacement:
            road_placement = cls.road.ObjectPlacement

        part_placement = create_local_placement(cls.file, relative_to=road_placement)

        road_part = cls.file.create_entity(
            "IfcRoadPart",
            GlobalId=ifcopenshell.guid.new(),
            Name=road_part_name,
            Description=f"Road part of type {road_part_type}",
            ObjectPlacement=part_placement,
            PredefinedType=road_part_type
        )

        # Create aggregation relationship (Road contains RoadPart) using ifc_api
        ifc_api.aggregate_objects(
            cls.file,
            parent=cls.road,
            children=[road_part],
            name=f"RoadContains{road_part_type}"
        )

        # Store reference
        cls.road_parts[road_part_type] = road_part

        # Create Blender hierarchy visualization
        cls._create_road_part_empty(road_part_type, road_part)

        logger.info(f"Created IfcRoadPart: {road_part_name} ({road_part_type})")

        return road_part

    @classmethod
    def _create_road_part_empty(
        cls,
        road_part_type: str,
        road_part: ifcopenshell.entity_instance
    ) -> Optional[bpy.types.Object]:
        """
        Create Blender empty for a road part in the hierarchy.

        Args:
            road_part_type: Type of road part
            road_part: IfcRoadPart entity

        Returns:
            Created empty object or None
        """
        from .blender_hierarchy import ROAD_EMPTY_NAME, get_or_find_object

        # Find the road empty to parent to
        road_empty = get_or_find_object(None, ROAD_EMPTY_NAME)
        if not road_empty:
            logger.warning("Cannot create road part empty - road empty not found")
            return None

        # Get display name
        display_name = cls.ROAD_PART_DISPLAY_NAMES.get(
            road_part_type, f"🔹 {road_part_type}"
        )

        # Create empty
        part_empty = bpy.data.objects.new(display_name, None)
        part_empty.empty_display_type = 'PLAIN_AXES'
        part_empty.empty_display_size = 2.0
        part_empty.parent = road_empty

        # Link to collection
        collection = cls.get_project_collection()
        if collection:
            collection.objects.link(part_empty)

        # Link to IFC entity
        cls.link_object(part_empty, road_part)

        # Store reference
        cls.road_part_empties[road_part_type] = part_empty

        return part_empty

    @classmethod
    def get_road_part_for_component(
        cls,
        component_type: str
    ) -> Optional[ifcopenshell.entity_instance]:
        """
        Get the appropriate IfcRoadPart for a component type.

        Args:
            component_type: Component type (e.g., 'LANE', 'SHOULDER')

        Returns:
            IfcRoadPart entity or None
        """
        road_part_type = cls.COMPONENT_TO_ROAD_PART_TYPE.get(
            component_type, 'ROADSEGMENT'
        )
        return cls.get_or_create_road_part(road_part_type)

    @classmethod
    def contain_in_road_part(
        cls,
        element: ifcopenshell.entity_instance,
        road_part: ifcopenshell.entity_instance
    ) -> Optional[ifcopenshell.entity_instance]:
        """
        Add spatial containment for an element within a road part.

        Uses ifc_api.contain_in_spatial() for consistent relationship handling.

        Args:
            element: IFC element to contain
            road_part: IfcRoadPart to contain it in

        Returns:
            IfcRelContainedInSpatialStructure entity or None
        """
        if not cls.file or not road_part:
            return None

        return ifc_api.contain_in_spatial(cls.file, element, road_part)

    @classmethod
    def get_road_part_empty(
        cls,
        road_part_type: str
    ) -> Optional[bpy.types.Object]:
        """
        Get the Blender empty for a road part type.

        Args:
            road_part_type: IfcRoadPartTypeEnum value

        Returns:
            Blender empty object or None
        """
        return cls.road_part_empties.get(road_part_type)

    # =========================================================================
    # Cross-Section Component Management (IFC 4.3 Native)
    # =========================================================================

    # Component type to IFC entity type mapping
    COMPONENT_TO_IFC_CLASS = {
        'LANE': 'IfcPavement',           # Pavement for lanes
        'SHOULDER': 'IfcPavement',        # Pavement for shoulders
        'CURB': 'IfcKerb',                # IFC 4.3 has specific kerb entity
        'DITCH': 'IfcBuildingElementProxy',  # No specific ditch entity
        'MEDIAN': 'IfcBuildingElementProxy',
        'SIDEWALK': 'IfcPavement',
        'CUSTOM': 'IfcBuildingElementProxy',
    }

    # Display icons for component types in Blender
    COMPONENT_ICONS = {
        'LANE': '🛣️',
        'SHOULDER': '🛤️',
        'CURB': '🧱',
        'DITCH': '🌊',
        'MEDIAN': '🚧',
        'SIDEWALK': '🚶',
        'CUSTOM': '📐',
    }

    @classmethod
    def create_cross_section_component(
        cls,
        name: str,
        component_type: str,
        side: str,
        width: float,
        cross_slope: float = 0.0,
        offset: float = 0.0,
        assembly_name: str = None
    ) -> Optional[Tuple[ifcopenshell.entity_instance, bpy.types.Object]]:
        """
        Create an IFC entity and Blender object for a cross-section component.

        This implements the Native IFC pattern: component data lives in IFC,
        Blender object is just visualization linked via ifc_definition_id.

        Args:
            name: Component name (e.g., "Right Travel Lane")
            component_type: Type of component (LANE, SHOULDER, CURB, etc.)
            side: Side of alignment (LEFT, RIGHT)
            width: Component width in meters
            cross_slope: Cross slope as decimal (e.g., 0.02 for 2%)
            offset: Offset from centerline in meters
            assembly_name: Optional parent assembly name

        Returns:
            Tuple of (IFC entity, Blender object) or None if no file loaded
        """
        if not cls.file or not cls.road:
            logger.warning("Cannot create component - no IFC file or road loaded")
            return None

        # Get or create the appropriate IfcRoadPart for this component type
        road_part = cls.get_road_part_for_component(component_type)
        if not road_part:
            logger.error(f"Failed to get/create road part for {component_type}")
            return None

        # Determine IFC class for this component type
        ifc_class = cls.COMPONENT_TO_IFC_CLASS.get(component_type, 'IfcBuildingElementProxy')

        # Create placement relative to road part
        road_part_placement = None
        if hasattr(road_part, 'ObjectPlacement') and road_part.ObjectPlacement:
            road_part_placement = road_part.ObjectPlacement
        component_placement = create_local_placement(cls.file, relative_to=road_part_placement)

        # Create the IFC entity
        global_id = ifcopenshell.guid.new()

        # Build description with metadata
        description = f"{component_type} component | Side: {side} | Width: {width:.2f}m | Slope: {cross_slope*100:.1f}%"
        if assembly_name:
            description = f"[{assembly_name}] {description}"

        try:
            if ifc_class == 'IfcKerb':
                # IfcKerb is specific to IFC 4.3
                component_entity = cls.file.create_entity(
                    ifc_class,
                    GlobalId=global_id,
                    Name=name,
                    Description=description,
                    ObjectPlacement=component_placement,
                )
            elif ifc_class == 'IfcPavement':
                # IfcPavement for lanes, shoulders, sidewalks
                component_entity = cls.file.create_entity(
                    ifc_class,
                    GlobalId=global_id,
                    Name=name,
                    Description=description,
                    ObjectPlacement=component_placement,
                )
            else:
                # Fallback to IfcBuildingElementProxy
                component_entity = cls.file.create_entity(
                    "IfcBuildingElementProxy",
                    GlobalId=global_id,
                    Name=name,
                    Description=description,
                    ObjectPlacement=component_placement,
                    PredefinedType="USERDEFINED",
                    ObjectType=f"CrossSection_{component_type}"
                )
        except Exception as e:
            # Fallback if IFC 4.3 entities aren't available
            logger.warning(f"Failed to create {ifc_class}, falling back to proxy: {e}")
            component_entity = cls.file.create_entity(
                "IfcBuildingElementProxy",
                GlobalId=global_id,
                Name=name,
                Description=description,
                ObjectPlacement=component_placement,
                PredefinedType="USERDEFINED",
                ObjectType=f"CrossSection_{component_type}"
            )

        # Create spatial containment in the road part
        cls.contain_in_road_part(component_entity, road_part)

        # Store component properties as property set
        cls._create_component_property_set(
            component_entity, component_type, side, width, cross_slope, offset
        )

        # Create Blender visualization object
        blender_obj = cls._create_component_blender_object(
            name, component_type, side, road_part
        )

        # Link Blender object to IFC entity
        if blender_obj:
            cls.link_object(blender_obj, component_entity)

        logger.info(f"Created cross-section component: {name} ({component_type}, {side})")

        return (component_entity, blender_obj)

    @classmethod
    def _create_component_property_set(
        cls,
        component_entity: ifcopenshell.entity_instance,
        component_type: str,
        side: str,
        width: float,
        cross_slope: float,
        offset: float
    ) -> Optional[ifcopenshell.entity_instance]:
        """
        Create an IfcPropertySet with component properties.

        Args:
            component_entity: The IFC component entity
            component_type: Type of component
            side: LEFT or RIGHT
            width: Width in meters
            cross_slope: Cross slope as decimal
            offset: Offset from centerline

        Returns:
            IfcPropertySet entity or None
        """
        if not cls.file:
            return None

        # Create property values
        props = []

        # Component type
        props.append(cls.file.create_entity(
            "IfcPropertySingleValue",
            Name="ComponentType",
            NominalValue=cls.file.create_entity("IfcLabel", component_type)
        ))

        # Side
        props.append(cls.file.create_entity(
            "IfcPropertySingleValue",
            Name="Side",
            NominalValue=cls.file.create_entity("IfcLabel", side)
        ))

        # Width
        props.append(cls.file.create_entity(
            "IfcPropertySingleValue",
            Name="Width",
            NominalValue=cls.file.create_entity("IfcLengthMeasure", width)
        ))

        # Cross slope (as percentage for clarity)
        props.append(cls.file.create_entity(
            "IfcPropertySingleValue",
            Name="CrossSlope",
            NominalValue=cls.file.create_entity("IfcRatioMeasure", cross_slope)
        ))

        # Offset
        props.append(cls.file.create_entity(
            "IfcPropertySingleValue",
            Name="Offset",
            NominalValue=cls.file.create_entity("IfcLengthMeasure", offset)
        ))

        # Create property set
        pset = cls.file.create_entity(
            "IfcPropertySet",
            GlobalId=ifcopenshell.guid.new(),
            Name="Pset_SaikeiCrossSection",
            HasProperties=props
        )

        # Create relationship
        cls.file.create_entity(
            "IfcRelDefinesByProperties",
            GlobalId=ifcopenshell.guid.new(),
            RelatedObjects=[component_entity],
            RelatingPropertyDefinition=pset
        )

        return pset

    @classmethod
    def _create_component_blender_object(
        cls,
        name: str,
        component_type: str,
        side: str,
        road_part: ifcopenshell.entity_instance
    ) -> Optional[bpy.types.Object]:
        """
        Create a Blender empty to represent the component in the outliner.

        Args:
            name: Component name
            component_type: Type of component
            side: LEFT or RIGHT
            road_part: Parent road part entity

        Returns:
            Created Blender object or None
        """
        # Get the road part empty to parent to
        road_part_type = cls.COMPONENT_TO_ROAD_PART_TYPE.get(component_type, 'ROADSEGMENT')
        parent_empty = cls.get_road_part_empty(road_part_type)

        if not parent_empty:
            logger.warning(f"No parent empty found for {road_part_type}")
            # Try to create it
            cls._create_road_part_empty(road_part_type, road_part)
            parent_empty = cls.get_road_part_empty(road_part_type)

        # Create display name with icon and side indicator
        icon = cls.COMPONENT_ICONS.get(component_type, '📐')
        side_indicator = "◀" if side == "LEFT" else "▶"
        display_name = f"{icon} {name} {side_indicator}"

        # Create empty
        component_empty = bpy.data.objects.new(display_name, None)
        component_empty.empty_display_type = 'PLAIN_AXES'
        component_empty.empty_display_size = 1.0

        # Parent to road part empty
        if parent_empty:
            component_empty.parent = parent_empty

        # Link to project collection
        collection = cls.get_project_collection()
        if collection:
            collection.objects.link(component_empty)

        return component_empty

    @classmethod
    def delete_cross_section_component(
        cls,
        ifc_id: int,
        blender_obj: bpy.types.Object = None
    ) -> bool:
        """
        Delete a cross-section component from IFC and Blender.

        Args:
            ifc_id: ID of the IFC entity to delete
            blender_obj: Optional Blender object to delete

        Returns:
            True if successful
        """
        if not cls.file:
            return False

        try:
            # Delete IFC entity
            if ifc_id > 0:
                entity = cls.file.by_id(ifc_id)
                if entity:
                    # Remove from spatial containment
                    for rel in cls.file.by_type("IfcRelContainedInSpatialStructure"):
                        if entity in (rel.RelatedElements or []):
                            elements = list(rel.RelatedElements)
                            elements.remove(entity)
                            if elements:
                                rel.RelatedElements = elements
                            else:
                                cls.file.remove(rel)
                            break

                    # Remove property set relationships
                    for rel in cls.file.by_type("IfcRelDefinesByProperties"):
                        if entity in (rel.RelatedObjects or []):
                            cls.file.remove(rel)
                            break

                    # Remove the entity
                    cls.file.remove(entity)
                    logger.info(f"Deleted IFC entity #{ifc_id}")

            # Delete Blender object
            if blender_obj:
                bpy.data.objects.remove(blender_obj, do_unlink=True)
                logger.info(f"Deleted Blender object")

            return True

        except Exception as e:
            logger.error(f"Error deleting component: {e}")
            return False

    @classmethod
    def get_component_from_ifc(
        cls,
        ifc_id: int
    ) -> Optional[Dict]:
        """
        Retrieve component properties from IFC entity.

        Args:
            ifc_id: ID of the IFC entity

        Returns:
            Dictionary with component properties or None
        """
        if not cls.file or ifc_id <= 0:
            return None

        try:
            entity = cls.file.by_id(ifc_id)
            if not entity:
                return None

            result = {
                'name': entity.Name,
                'global_id': entity.GlobalId,
                'ifc_class': entity.is_a(),
            }

            # Find property set
            for rel in cls.file.by_type("IfcRelDefinesByProperties"):
                if entity in (rel.RelatedObjects or []):
                    pset = rel.RelatingPropertyDefinition
                    if hasattr(pset, 'Name') and pset.Name == "Pset_SaikeiCrossSection":
                        for prop in pset.HasProperties:
                            if prop.Name == "ComponentType":
                                result['component_type'] = prop.NominalValue.wrappedValue
                            elif prop.Name == "Side":
                                result['side'] = prop.NominalValue.wrappedValue
                            elif prop.Name == "Width":
                                result['width'] = prop.NominalValue.wrappedValue
                            elif prop.Name == "CrossSlope":
                                result['cross_slope'] = prop.NominalValue.wrappedValue
                            elif prop.Name == "Offset":
                                result['offset'] = prop.NominalValue.wrappedValue
                        break

            return result

        except Exception as e:
            logger.error(f"Error retrieving component from IFC: {e}")
            return None

    # =========================================================================
    # Cleanup
    # =========================================================================

    @classmethod
    def clear(cls) -> None:
        """Clear all IFC data and Blender collections."""
        cls.file = None
        cls.filepath = None
        cls.project = None
        cls.site = None
        cls.road = None
        cls.unit_assignment = None
        cls.geometric_context = None
        cls.axis_subcontext = None
        cls.vertical_alignments = []
        cls.road_parts = {}
        cls.road_part_empties = {}

        clear_blender_hierarchy()

        cls.project_collection = None
        cls.alignments_collection = None
        cls.geomodels_collection = None

        # Clear alignment registry
        from .. import alignment_registry
        alignment_registry.clear_registry()

        logger.info("Cleared IFC data and Blender hierarchy")

    @classmethod
    def get_info(cls) -> Dict:
        """Get information about current IFC file."""
        if cls.file is None:
            return {'loaded': False, 'message': 'No IFC file loaded'}

        return {
            'loaded': True,
            'filepath': cls.filepath,
            'schema': cls.file.schema,
            'entities': len(cls.file.by_type("IfcRoot")),
            'project': cls.project.Name if cls.project else None,
            'site': cls.site.Name if cls.site else None,
            'road': cls.road.Name if cls.road else None,
            'alignments': len(cls.file.by_type("IfcAlignment")),
            'geomodels': len(cls.file.by_type("IfcGeomodel"))
        }

    @classmethod
    def validate_for_external_viewers(cls) -> List[str]:
        """Validate IFC file for external viewers."""
        return validate_for_external_viewers(cls.file)

    @classmethod
    def validate_and_report(cls) -> bool:
        """Validate and print report."""
        return validate_and_report(cls.file)


__all__ = ["NativeIfcManager"]
