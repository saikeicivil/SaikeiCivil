# ==============================================================================
# Saikei Civil - Civil Engineering Tools for Blender
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================
"""
Corridor tool implementation - Blender-specific corridor operations.

This module implements the corridor interface from core.tool and provides
all Blender-specific functionality for corridor mesh generation.

Following the three-layer architecture:
    Layer 1: Core (saikei_civil.core) - Pure Python business logic
    Layer 2: Tool (this module) - Blender-specific implementations
    Layer 3: BIM Modules - UI, operators, and properties

This is where ALL Blender imports (bpy, bmesh) should be.

Usage:
    from saikei_civil.tool import Corridor

    # Generate corridor mesh
    mesh_obj, stats = Corridor.generate_corridor_mesh(
        stations=station_list,
        assembly=assembly_wrapper,
        name="Corridor_0_1000",
        lod='medium'
    )
"""
from typing import TYPE_CHECKING, Optional, List, Any, Dict, Tuple
from dataclasses import dataclass
import math
import time

import bpy
import bmesh

if TYPE_CHECKING:
    import ifcopenshell
    from ..core.corridor import AssemblyWrapper, MeshStats
    from ..core.native_ifc_corridor import StationPoint

from ..core import tool as core_tool
from ..core.logging_config import get_logger

logger = get_logger(__name__)


# =============================================================================
# LOD Settings
# =============================================================================

@dataclass
class LODSettings:
    """Level of Detail settings for corridor mesh generation."""
    name: str
    station_interval: float
    curve_densification: float
    smooth_shading: bool
    subdivisions: int

    @classmethod
    def high(cls) -> 'LODSettings':
        """High detail - Best quality, slower generation."""
        return cls(
            name="High",
            station_interval=1.0,
            curve_densification=2.0,
            smooth_shading=True,
            subdivisions=2
        )

    @classmethod
    def medium(cls) -> 'LODSettings':
        """Medium detail - Balanced quality and performance."""
        return cls(
            name="Medium",
            station_interval=1.5,
            curve_densification=1.5,
            smooth_shading=True,
            subdivisions=1
        )

    @classmethod
    def low(cls) -> 'LODSettings':
        """Low detail - Fast preview, lower quality."""
        return cls(
            name="Low",
            station_interval=2.0,
            curve_densification=1.0,
            smooth_shading=False,
            subdivisions=0
        )

    @classmethod
    def from_string(cls, lod: str) -> 'LODSettings':
        """Get LOD settings from string."""
        lod_map = {
            'high': cls.high(),
            'medium': cls.medium(),
            'low': cls.low()
        }
        return lod_map.get(lod, cls.medium())


# =============================================================================
# Corridor Tool Implementation
# =============================================================================

class Corridor(core_tool.Corridor):
    """
    Blender-specific corridor operations.

    This class implements the Corridor interface from core.tool and provides
    all Blender-specific functionality for corridor mesh generation.

    All bpy/bmesh operations are contained in this class.
    """

    # In-memory storage for corridors
    _corridors: dict = {}

    @classmethod
    def create(
        cls,
        name: str,
        alignment: "ifcopenshell.entity_instance",
        assembly: Any,
        start_station: float,
        end_station: float,
        interval: float = 10.0
    ) -> Any:
        """Create a corridor from alignment and assembly."""
        from ..core.native_ifc_corridor import CorridorModeler

        # Create alignment wrapper
        from ..core.corridor import AlignmentWrapper
        alignment_3d = AlignmentWrapper(alignment, start_station, end_station)

        corridor = CorridorModeler(
            alignment_3d=alignment_3d,
            assembly=assembly,
            name=name
        )

        cls._corridors[name] = corridor
        return corridor

    @classmethod
    def get_corridor(cls, name: str) -> Optional[Any]:
        """Get a corridor by name."""
        return cls._corridors.get(name)

    @classmethod
    def list_corridors(cls) -> List[str]:
        """List all corridor names."""
        return list(cls._corridors.keys())

    @classmethod
    def get_stations(cls, corridor: Any) -> List[float]:
        """Get list of stations where cross-sections are placed."""
        if hasattr(corridor, 'stations'):
            return [s.station for s in corridor.stations]
        return []

    @classmethod
    def add_station(cls, corridor: Any, station: float) -> None:
        """Add a cross-section at a specific station."""
        # Implementation would add station to corridor
        pass

    @classmethod
    def remove_station(cls, corridor: Any, station: float) -> None:
        """Remove a cross-section at a specific station."""
        # Implementation would remove station from corridor
        pass

    @classmethod
    def generate_corridor_mesh(
        cls,
        stations: List["StationPoint"],
        assembly: "AssemblyWrapper",
        name: str = "Corridor",
        lod: str = 'medium'
    ) -> Tuple[Optional[bpy.types.Object], "MeshStats"]:
        """
        Generate Blender mesh geometry from corridor data.

        This is the main mesh generation method. It:
        1. Creates vertices at each station
        2. Connects stations with quad strips
        3. Applies smooth shading based on LOD
        4. Creates and applies materials

        Args:
            stations: List of StationPoint objects from core
            assembly: AssemblyWrapper with component data
            name: Name for the mesh object
            lod: Level of detail ('low', 'medium', 'high')

        Returns:
            Tuple of (mesh_object, MeshStats)
        """
        from ..core.corridor import MeshStats

        start_time = time.time()
        lod_settings = LODSettings.from_string(lod)

        if not stations or len(stations) < 2:
            raise ValueError("Need at least 2 stations to generate mesh")

        # Create new mesh
        mesh = bpy.data.meshes.new(name)
        mesh_obj = bpy.data.objects.new(name, mesh)

        # Generate geometry using BMesh
        bm = bmesh.new()

        try:
            # Get profile points from assembly
            profile_points = cls._get_profile_points(assembly)

            # Generate vertices for each station
            all_vertices = []
            for station in stations:
                station_vertices = cls._create_station_vertices(
                    station, profile_points, bm
                )
                all_vertices.append(station_vertices)

            # Connect adjacent stations with quad strips
            cls._create_quad_strips(bm, all_vertices)

            # Add end caps
            cls._create_end_caps(bm, all_vertices)

            # Convert BMesh to mesh
            bm.to_mesh(mesh)

            # Apply smooth shading if requested
            if lod_settings.smooth_shading:
                for poly in mesh.polygons:
                    poly.use_smooth = True

            # Apply materials
            cls._apply_materials(mesh_obj, assembly)

            # Update statistics
            vertex_count = len(mesh.vertices)
            face_count = len(mesh.polygons)
            generation_time = time.time() - start_time

            stats = MeshStats(
                vertex_count=vertex_count,
                face_count=face_count,
                generation_time=generation_time,
                station_count=len(stations)
            )

            logger.info("Corridor mesh generated:")
            logger.info("  LOD: %s", lod_settings.name)
            logger.info("  Vertices: %s", f"{vertex_count:,}")
            logger.info("  Faces: %s", f"{face_count:,}")
            logger.info("  Time: %.2fs", generation_time)

            return mesh_obj, stats

        finally:
            bm.free()

    @classmethod
    def generate_mesh(cls, corridor: Any, lod: int = 1) -> Optional[bpy.types.Object]:
        """
        Generate Blender mesh for corridor (legacy interface).

        Args:
            corridor: The corridor object (CorridorModeler)
            lod: Level of detail (0=low, 1=medium, 2=high)

        Returns:
            The mesh object
        """
        if corridor is None:
            return None

        lod_map = {0: 'low', 1: 'medium', 2: 'high'}
        lod_str = lod_map.get(lod, 'medium')

        # Get stations and assembly from corridor
        stations = corridor.stations if hasattr(corridor, 'stations') else []
        assembly = corridor.assembly if hasattr(corridor, 'assembly') else None

        if not stations or not assembly:
            return None

        # Create assembly wrapper if needed
        from ..core.corridor import AssemblyWrapper, ComponentData

        if not isinstance(assembly, AssemblyWrapper):
            # Convert to wrapper
            components = []
            for comp in getattr(assembly, 'components', []):
                components.append(ComponentData(
                    name=getattr(comp, 'name', 'Component'),
                    component_type=getattr(comp, 'component_type', 'LANE'),
                    width=getattr(comp, 'width', 3.6),
                    slope=getattr(comp, 'slope', 0.02),
                    offset=getattr(comp, 'offset', 0.0),
                    elevation=getattr(comp, 'elevation', 0.0),
                    material=getattr(comp, 'material', 'Asphalt')
                ))
            assembly = AssemblyWrapper(
                name=getattr(assembly, 'name', 'Assembly'),
                components=components
            )

        mesh_obj, stats = cls.generate_corridor_mesh(
            stations=stations,
            assembly=assembly,
            name=corridor.name if hasattr(corridor, 'name') else 'Corridor',
            lod=lod_str
        )

        return mesh_obj

    @classmethod
    def update_mesh(cls, corridor: Any) -> None:
        """Update existing mesh after corridor changes."""
        if hasattr(corridor, 'update_mesh'):
            corridor.update_mesh()

    @classmethod
    def export_to_ifc(cls, corridor: Any) -> Optional["ifcopenshell.entity_instance"]:
        """Export corridor to IFC entities."""
        try:
            import ifcopenshell
        except ImportError:
            return None

        from .ifc import Ifc

        ifc_file = Ifc.get()
        if ifc_file is None:
            return None

        if hasattr(corridor, 'to_ifc'):
            return corridor.to_ifc(ifc_file)

        return None

    @classmethod
    def create_ifc_corridor_solid(
        cls,
        stations: List["StationPoint"],
        assembly: "AssemblyWrapper",
        name: str = "Corridor",
        interval: float = 10.0
    ) -> Tuple[Optional[Any], Dict[str, Any]]:
        """
        Create an IFC IfcSectionedSolidHorizontal corridor solid.

        This is the proper IFC 4.3 method for creating corridors - it creates
        native IFC geometry instead of converting Blender mesh to IFC.

        Args:
            stations: List of StationPoint objects from core
            assembly: AssemblyWrapper with component data
            name: Name for the corridor
            interval: Station interval (for metadata)

        Returns:
            Tuple of (IfcSectionedSolidHorizontal entity, summary dict)
        """
        from .ifc import Ifc
        from ..core.native_ifc_corridor import (
            CorridorModeler,
            create_profile_from_assembly,
            create_tagged_cross_section_profile,
            PointTags
        )
        from ..core.corridor import AlignmentWrapper

        ifc_file = Ifc.get()
        if ifc_file is None:
            logger.error("No IFC file loaded")
            return None, {"error": "No IFC file loaded"}

        if len(stations) < 2:
            logger.error("Need at least 2 stations to create corridor")
            return None, {"error": "Need at least 2 stations"}

        try:
            # Create directrix (3D alignment curve) from stations
            points = []
            for station_point in stations:
                point = ifc_file.create_entity(
                    "IfcCartesianPoint",
                    Coordinates=(station_point.x, station_point.y, station_point.z)
                )
                points.append(point)

            directrix = ifc_file.create_entity(
                "IfcPolyline",
                Points=points
            )

            logger.info(f"Created directrix with {len(points)} points")

            # Create cross-section profiles for each station
            cross_sections = []
            for station_point in stations:
                profile = create_profile_from_assembly(
                    ifc_file=ifc_file,
                    assembly=assembly,
                    station=station_point.station,
                    pavement_thickness=0.3
                )
                cross_sections.append(profile)

            logger.info(f"Created {len(cross_sections)} cross-section profiles")

            # Create positions for each cross-section
            positions = []
            for station_point in stations:
                distance_expr = ifc_file.create_entity(
                    "IfcDistanceExpression",
                    DistanceAlong=station_point.station,
                    OffsetLateral=0.0,
                    OffsetVertical=0.0
                )

                placement = ifc_file.create_entity(
                    "IfcAxis2PlacementLinear",
                    Location=distance_expr,
                    Axis=None,
                    RefDirection=None
                )
                positions.append(placement)

            logger.info(f"Created {len(positions)} cross-section positions")

            # Create the IfcSectionedSolidHorizontal
            corridor_solid = ifc_file.create_entity(
                "IfcSectionedSolidHorizontal",
                Directrix=directrix,
                CrossSections=cross_sections,
                CrossSectionPositions=positions
            )

            logger.info(f"Created IfcSectionedSolidHorizontal: #{corridor_solid.id()}")

            # Summary
            summary = {
                "name": name,
                "station_count": len(stations),
                "start_station": stations[0].station,
                "end_station": stations[-1].station,
                "length": stations[-1].station - stations[0].station,
                "profile_count": len(cross_sections),
                "corridor_solid_id": corridor_solid.id(),
                "ifc_type": "IfcSectionedSolidHorizontal"
            }

            return corridor_solid, summary

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Failed to create IFC corridor solid: {e}")
            return None, {"error": str(e)}

    # =========================================================================
    # Internal Mesh Generation Methods
    # =========================================================================

    @classmethod
    def _get_profile_points(cls, assembly: "AssemblyWrapper") -> List[Dict[str, Any]]:
        """
        Extract cross-section profile points from assembly.

        Args:
            assembly: AssemblyWrapper instance

        Returns:
            List of component profile data dictionaries
        """
        profile_points = []

        for component in assembly.components:
            points = []
            is_left_side = component.offset < 0

            if is_left_side:
                start_offset = component.offset + component.width
                start_elev = component.elevation - component.slope * component.width
                end_offset = component.offset
                end_elev = component.elevation
                points.append((start_offset, start_elev))
                points.append((end_offset, end_elev))
            else:
                start_offset = component.offset
                start_elev = component.elevation
                end_offset = component.offset + component.width
                end_elev = component.elevation - component.slope * component.width
                points.append((start_offset, start_elev))
                points.append((end_offset, end_elev))

            profile_points.append({
                'name': component.name,
                'type': component.component_type,
                'points': points,
                'material': component.material
            })

        return profile_points

    @classmethod
    def _create_station_vertices(
        cls,
        station: "StationPoint",
        profile_points: List[Dict[str, Any]],
        bm: bmesh.types.BMesh
    ) -> List[bmesh.types.BMVert]:
        """
        Create vertices at a specific station.

        Transforms 2D cross-section points to 3D space based on
        station position and bearing.

        Args:
            station: StationPoint with position and bearing
            profile_points: Cross-section profile definition
            bm: BMesh to add vertices to

        Returns:
            List of created BMesh vertices
        """
        vertices = []

        x, y, z = station.x, station.y, station.z
        bearing = station.direction

        cos_bearing = math.cos(bearing)
        sin_bearing = math.sin(bearing)

        for component in profile_points:
            for offset, elevation in component['points']:
                vert_x = x - offset * sin_bearing
                vert_y = y + offset * cos_bearing
                vert_z = z + elevation

                vert = bm.verts.new((vert_x, vert_y, vert_z))
                vertices.append(vert)

        return vertices

    @classmethod
    def _create_quad_strips(
        cls,
        bm: bmesh.types.BMesh,
        all_vertices: List[List[bmesh.types.BMVert]]
    ):
        """
        Connect adjacent stations with quad faces.

        Args:
            bm: BMesh to add faces to
            all_vertices: List of vertex lists (one per station)
        """
        for i in range(len(all_vertices) - 1):
            station_verts_1 = all_vertices[i]
            station_verts_2 = all_vertices[i + 1]

            for j in range(len(station_verts_1) - 1):
                v1 = station_verts_1[j]
                v2 = station_verts_1[j + 1]
                v3 = station_verts_2[j + 1]
                v4 = station_verts_2[j]

                try:
                    bm.faces.new([v1, v2, v3, v4])
                except ValueError:
                    pass

        bm.verts.index_update()
        bm.faces.index_update()

    @classmethod
    def _create_end_caps(
        cls,
        bm: bmesh.types.BMesh,
        all_vertices: List[List[bmesh.types.BMVert]]
    ):
        """
        Create end cap faces at corridor start and end.

        Args:
            bm: BMesh to add faces to
            all_vertices: List of vertex lists
        """
        if len(all_vertices) < 2:
            return

        start_verts = all_vertices[0]
        if len(start_verts) > 2:
            try:
                bm.faces.new(start_verts)
            except ValueError:
                pass

        end_verts = all_vertices[-1]
        if len(end_verts) > 2:
            try:
                bm.faces.new(list(reversed(end_verts)))
            except ValueError:
                pass

        bm.faces.index_update()

    @classmethod
    def _apply_materials(cls, mesh_obj: bpy.types.Object, assembly: "AssemblyWrapper"):
        """
        Create and apply materials to corridor mesh.

        Args:
            mesh_obj: Blender mesh object
            assembly: AssemblyWrapper with component definitions
        """
        component_colors = {
            'LANE': (0.3, 0.3, 0.3, 1.0),
            'SHOULDER': (0.5, 0.5, 0.45, 1.0),
            'CURB': (0.8, 0.8, 0.8, 1.0),
            'DITCH': (0.4, 0.3, 0.2, 1.0),
            'SIDEWALK': (0.7, 0.7, 0.7, 1.0),
            'MEDIAN': (0.2, 0.6, 0.2, 1.0),
        }

        created_materials = {}

        for component in assembly.components:
            comp_type = component.component_type

            if comp_type not in created_materials:
                mat = cls._create_material(
                    name=f"Corridor_{comp_type}",
                    color=component_colors.get(comp_type, (0.5, 0.5, 0.5, 1.0))
                )
                created_materials[comp_type] = mat
                mesh_obj.data.materials.append(mat)

        logger.info("Created %s materials for corridor", len(created_materials))

    @classmethod
    def _create_material(
        cls,
        name: str,
        color: Tuple[float, float, float, float]
    ) -> bpy.types.Material:
        """
        Create a Blender material with Principled BSDF.

        Args:
            name: Material name
            color: RGBA color tuple

        Returns:
            Blender material
        """
        if name in bpy.data.materials:
            return bpy.data.materials[name]

        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True

        nodes = mat.node_tree.nodes
        principled = nodes.get("Principled BSDF")

        if principled:
            principled.inputs["Base Color"].default_value = color
            principled.inputs["Roughness"].default_value = 0.7
            principled.inputs["Metallic"].default_value = 0.0

        return mat

    @classmethod
    def add_to_collection(
        cls,
        mesh_obj: bpy.types.Object,
        collection_name: str = "Saikei Civil Project"
    ) -> None:
        """
        Add mesh object to a collection.

        Args:
            mesh_obj: The mesh object to add
            collection_name: Name of the collection
        """
        if collection_name in bpy.data.collections:
            collection = bpy.data.collections[collection_name]
            if mesh_obj.name not in collection.objects:
                collection.objects.link(mesh_obj)
        else:
            bpy.context.scene.collection.objects.link(mesh_obj)


__all__ = ["Corridor"]
