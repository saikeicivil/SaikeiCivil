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
Corridor core module - Pure Python business logic.

This module provides corridor generation functions using dependency injection.
NO Blender imports allowed - all platform-specific code is in the tool layer.

Following the three-layer architecture:
    Layer 1: Core (this module) - Pure Python business logic
    Layer 2: Tool (saikei_civil.tool) - Blender-specific implementations
    Layer 3: BIM Modules - UI, operators, and properties

Usage:
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        import saikei_civil.tool as tool

    def generate_corridor(
        ifc: type[tool.Ifc],
        corridor_tool: type[tool.Corridor],
        blender: type[tool.Blender],
        ...
    ):
        # Core business logic using injected tools
        pass
"""
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

# Import from native_ifc_corridor for IFC-specific logic
from .native_ifc_corridor import (
    StationPoint,
    StationManager,
    CorridorModeler,
)

if TYPE_CHECKING:
    import saikei_civil.tool as tool


# =============================================================================
# Data Classes (Pure Python, no platform dependencies)
# =============================================================================

@dataclass
class CorridorParams:
    """Parameters for corridor generation."""
    name: str
    start_station: float
    end_station: float
    interval: float = 10.0
    curve_densification: float = 1.5
    lod: str = 'medium'  # 'low', 'medium', 'high'


@dataclass
class MeshStats:
    """Statistics from mesh generation."""
    vertex_count: int
    face_count: int
    generation_time: float
    station_count: int


# =============================================================================
# Core Functions with Dependency Injection
# =============================================================================

def generate_corridor(
    ifc: "type[tool.Ifc]",
    corridor_tool: "type[tool.Corridor]",
    blender: "type[tool.Blender]",
    spatial: "type[tool.Spatial]",
    alignment_index: int,
    assembly_data: Any,
    params: CorridorParams,
) -> Tuple[Any, MeshStats]:
    """
    Generate a 3D corridor mesh from alignment and cross-section assembly.

    This is the main entry point for corridor generation. It:
    1. Gets alignment data from IFC
    2. Creates station points along the alignment
    3. Generates mesh geometry (via corridor_tool)
    4. Links to IFC entities
    5. Organizes in spatial hierarchy

    Args:
        ifc: IFC tool class (dependency injection)
        corridor_tool: Corridor tool class (dependency injection)
        blender: Blender tool class (dependency injection)
        spatial: Spatial tool class (dependency injection)
        alignment_index: Index of alignment in IFC file
        assembly_data: Cross-section assembly data
        params: Corridor generation parameters

    Returns:
        Tuple of (mesh_object, MeshStats)

    Raises:
        ValueError: If alignment or assembly is invalid
    """
    # Get IFC file
    ifc_file = ifc.get()
    if ifc_file is None:
        raise ValueError("No IFC file loaded")

    # Get alignments
    alignments = ifc.by_type("IfcAlignment")
    if alignment_index < 0 or alignment_index >= len(alignments):
        raise ValueError(f"Invalid alignment index: {alignment_index}")

    alignment = alignments[alignment_index]

    # Create alignment wrapper for position queries
    alignment_3d = create_alignment_wrapper(
        alignment,
        params.start_station,
        params.end_station
    )

    # Create assembly wrapper
    assembly_wrapper = create_assembly_wrapper(assembly_data)

    # Generate stations using StationManager
    station_manager = StationManager(alignment_3d, params.interval)
    stations = station_manager.calculate_stations(
        curve_densification_factor=params.curve_densification
    )

    if len(stations) < 2:
        raise ValueError("Need at least 2 stations to create corridor")

    # Generate mesh using corridor tool (Blender-specific)
    mesh_obj, stats = corridor_tool.generate_corridor_mesh(
        stations=stations,
        assembly=assembly_wrapper,
        name=params.name,
        lod=params.lod
    )

    # Create IFC entity and link
    corridor_entity = _create_corridor_ifc_entity(ifc, params.name)

    if corridor_entity and mesh_obj:
        ifc.link(corridor_entity, mesh_obj)

        # Assign to road container
        road = spatial.get_road()
        if road:
            spatial.assign_to_road(corridor_entity)

    # Add to project collection
    project_collection = blender.get_collection("Saikei Civil Project", create=False)
    if project_collection and mesh_obj:
        blender.link_to_collection(mesh_obj, project_collection)

        # Parent to Road empty
        road_empty = _find_road_empty(blender)
        if road_empty and mesh_obj:
            _parent_object(mesh_obj, road_empty)

    return mesh_obj, stats


def _create_corridor_ifc_entity(
    ifc: "type[tool.Ifc]",
    name: str
) -> Optional[Any]:
    """Create IFC entity for the corridor."""
    try:
        import ifcopenshell.guid

        ifc_file = ifc.get()
        if ifc_file is None:
            return None

        # Per OJT001: Use standard PredefinedType to avoid ObjectType requirement
        # PAVEMENT is the standard IfcCourseTypeEnum value for road surfaces
        entity = ifc_file.create_entity(
            "IfcCourse",
            GlobalId=ifcopenshell.guid.new(),
            Name=name,
            Description="Corridor solid generated from cross-section assembly",
            ObjectType="CORRIDOR_SURFACE",  # Descriptive, not required with standard type
            PredefinedType="PAVEMENT"
        )
        return entity
    except Exception:
        return None


def _find_road_empty(blender: "type[tool.Blender]") -> Optional[Any]:
    """Find the Road empty object using the Blender tool."""
    from .ifc_manager.blender_hierarchy import ROAD_EMPTY_NAME
    # Use the Blender tool's get_object method instead of direct bpy access
    return blender.get_object_by_name(ROAD_EMPTY_NAME)


def _parent_object(child: Any, parent: Any) -> None:
    """Parent one object to another."""
    if child and parent:
        child.parent = parent


# =============================================================================
# Alignment Wrapper (Pure Python)
# =============================================================================

class AlignmentWrapper:
    """
    Wrapper for IFC alignment that provides 3D position sampling.

    This is pure Python - it queries IFC data but doesn't use Blender APIs.
    """

    def __init__(self, ifc_alignment: Any, start_sta: float, end_sta: float):
        """
        Initialize alignment wrapper.

        Args:
            ifc_alignment: IfcAlignment entity
            start_sta: Starting station (user-specified, may be offset from 0)
            end_sta: Ending station (user-specified)
        """
        import math
        self._math = math

        self.ifc_alignment = ifc_alignment
        self._start = start_sta
        self._end = end_sta
        self.horizontal = None
        self.vertical = None
        self.segments = []
        # This will be set from alignment data - the station value at distance=0
        self.starting_station = 0.0
        self._load_alignment_data()

        # After loading, determine the alignment's starting station
        # The starting_station is the station value at distance 0 along the alignment
        self._determine_starting_station()

    def _determine_starting_station(self):
        """
        Determine the alignment's starting station value.

        The starting_station is the station offset - i.e., what station value
        corresponds to distance=0 along the alignment geometry.

        This is determined from:
        1. The vertical alignment's first segment's StartDistAlong
        2. Or falls back to 0.0 if no vertical data available
        """
        from .logging_config import get_logger
        logger = get_logger(__name__)

        # Try to get starting station from vertical alignment
        if self.vertical:
            v_segments = []
            for rel in self.vertical.IsNestedBy or []:
                for obj in rel.RelatedObjects:
                    if obj.is_a("IfcAlignmentSegment"):
                        if hasattr(obj, 'DesignParameters') and obj.DesignParameters:
                            if obj.DesignParameters.is_a("IfcAlignmentVerticalSegment"):
                                v_segments.append(obj.DesignParameters)

            if v_segments:
                v_segments.sort(key=lambda s: s.StartDistAlong)
                # The first vertical segment's StartDistAlong tells us what station
                # corresponds to the start of the vertical alignment
                self.starting_station = v_segments[0].StartDistAlong
                logger.info(f"Starting station from vertical alignment: {self.starting_station:.2f}")
                return

        # If no vertical alignment, try to infer from horizontal alignment extent
        # The user's start station (e.g., 10000) maps to geometry distance 0
        # This assumes the horizontal geometry starts at the user's start station
        if self.segments:
            # Calculate total horizontal length
            total_h_length = sum(
                seg.DesignParameters.SegmentLength
                for seg in self.segments
                if seg.DesignParameters
            )
            # If user station range matches horizontal length, use user's start
            user_length = self._end - self._start
            if abs(total_h_length - user_length) < 10.0:  # Within 10m tolerance
                self.starting_station = self._start
                logger.info(f"Starting station inferred from user input: {self.starting_station:.2f}")
                return
            else:
                logger.info(f"Horizontal length ({total_h_length:.2f}m) doesn't match user range ({user_length:.2f}m)")

        # Default: assume the user's start station corresponds to distance 0
        self.starting_station = self._start
        logger.info(f"Starting station defaulting to user start: {self.starting_station:.2f}")

    def _load_alignment_data(self):
        """Load horizontal segments and vertical data from IFC alignment."""
        from .logging_config import get_logger
        logger = get_logger(__name__)

        logger.info(f"Loading alignment data from: {self.ifc_alignment.Name if hasattr(self.ifc_alignment, 'Name') else 'Unknown'}")
        logger.info(f"  Alignment type: {self.ifc_alignment.is_a()}")

        nested_rels = self.ifc_alignment.IsNestedBy or []
        logger.info(f"  Found {len(nested_rels)} IsNestedBy relationships")

        for rel in nested_rels:
            related_objs = rel.RelatedObjects or []
            logger.info(f"    Relationship has {len(related_objs)} related objects")
            for obj in related_objs:
                logger.info(f"      Found: {obj.is_a()} - {obj.Name if hasattr(obj, 'Name') else 'no name'}")
                if obj.is_a("IfcAlignmentHorizontal"):
                    self.horizontal = obj
                    self._load_horizontal_segments(obj)
                elif obj.is_a("IfcAlignmentVertical"):
                    self.vertical = obj

        logger.info(f"  Horizontal alignment: {'Found' if self.horizontal else 'NOT FOUND'}")
        logger.info(f"  Vertical alignment: {'Found' if self.vertical else 'NOT FOUND'}")
        logger.info(f"  Loaded {len(self.segments)} horizontal segments")

    def _load_horizontal_segments(self, horizontal):
        """Load segment data from IfcAlignmentHorizontal."""
        from .logging_config import get_logger
        logger = get_logger(__name__)

        self.segments = []
        nested_rels = horizontal.IsNestedBy or []
        logger.info(f"  Loading horizontal segments from {len(nested_rels)} nested relationships")

        for rel in nested_rels:
            for obj in rel.RelatedObjects or []:
                logger.info(f"    Checking: {obj.is_a()}")
                if obj.is_a("IfcAlignmentSegment"):
                    self.segments.append(obj)
                    # Log segment details
                    params = obj.DesignParameters
                    if params:
                        logger.info(f"      Segment DesignParameters type: {params.is_a()}")
                        if hasattr(params, 'PredefinedType'):
                            logger.info(f"      PredefinedType: {params.PredefinedType}")
                        if hasattr(params, 'SegmentLength'):
                            logger.info(f"      SegmentLength: {params.SegmentLength}")
                        if hasattr(params, 'StartPoint'):
                            sp = params.StartPoint
                            if sp:
                                logger.info(f"      StartPoint: {sp.Coordinates if hasattr(sp, 'Coordinates') else sp}")
                    else:
                        logger.warning(f"      Segment has no DesignParameters!")

    def get_start_station(self) -> float:
        """Get starting station."""
        return self._start

    def get_end_station(self) -> float:
        """Get ending station."""
        return self._end

    def _station_to_distance(self, station: float) -> float:
        """Convert station value to distance along alignment."""
        return station - self.starting_station

    def get_3d_position(self, station: float) -> Tuple[float, float, float]:
        """Get 3D position (x, y, z) at a given station."""
        from .logging_config import get_logger
        logger = get_logger(__name__)

        math = self._math
        distance_along = self._station_to_distance(station)

        x, y = 0.0, 0.0
        cumulative_distance = 0.0
        found_segment = False

        # Log only for first few stations to avoid spam
        debug_this_call = (station == self._start)
        if debug_this_call:
            logger.info(f"get_3d_position(station={station:.2f})")
            logger.info(f"  distance_along={distance_along:.2f}, segments={len(self.segments)}")

        for segment in self.segments:
            params = segment.DesignParameters
            if not params:
                if debug_this_call:
                    logger.warning(f"  Segment has no DesignParameters, skipping")
                continue

            segment_length = params.SegmentLength
            if debug_this_call:
                logger.info(f"  Segment: type={params.PredefinedType}, length={segment_length:.2f}")
                logger.info(f"    cumulative={cumulative_distance:.2f}, target={distance_along:.2f}")

            if cumulative_distance + segment_length >= distance_along:
                local_distance = distance_along - cumulative_distance

                if params.PredefinedType == "LINE":
                    start_point = params.StartPoint.Coordinates
                    direction_angle = params.StartDirection

                    x = start_point[0] + local_distance * math.cos(direction_angle)
                    y = start_point[1] + local_distance * math.sin(direction_angle)
                    found_segment = True
                    if debug_this_call:
                        logger.info(f"    LINE: start={start_point}, dir={direction_angle:.4f}")
                        logger.info(f"    Result: x={x:.2f}, y={y:.2f}")
                    break

                elif params.PredefinedType == "CIRCULARARC":
                    start_point = params.StartPoint.Coordinates
                    radius = abs(params.StartRadiusOfCurvature)
                    start_direction = params.StartDirection
                    signed_radius = params.StartRadiusOfCurvature

                    if signed_radius > 0:
                        center_angle = start_direction + math.pi / 2
                    else:
                        center_angle = start_direction - math.pi / 2

                    center_x = start_point[0] + radius * math.cos(center_angle)
                    center_y = start_point[1] + radius * math.sin(center_angle)

                    arc_angle = local_distance / radius
                    if signed_radius < 0:
                        arc_angle = -arc_angle

                    current_angle = start_direction + arc_angle
                    if signed_radius > 0:
                        current_angle -= math.pi / 2
                    else:
                        current_angle += math.pi / 2

                    x = center_x + radius * math.cos(current_angle)
                    y = center_y + radius * math.sin(current_angle)
                    found_segment = True
                    if debug_this_call:
                        logger.info(f"    ARC: start={start_point}, radius={radius:.2f}")
                        logger.info(f"    Result: x={x:.2f}, y={y:.2f}")
                    break

                else:
                    if debug_this_call:
                        logger.warning(f"    Unknown segment type: {params.PredefinedType}")

            cumulative_distance += segment_length

        if not found_segment and debug_this_call:
            logger.error(f"  NO SEGMENT FOUND for station {station:.2f}!")
            logger.error(f"  Total cumulative distance: {cumulative_distance:.2f}")

        z = self._get_elevation(station)
        if debug_this_call:
            logger.info(f"  Final position: ({x:.2f}, {y:.2f}, {z:.2f})")
        return x, y, z

    def _get_elevation(self, station: float) -> float:
        """Get elevation at station from vertical alignment."""
        if not self.vertical:
            return 0.0

        v_segments = []
        for rel in self.vertical.IsNestedBy or []:
            for obj in rel.RelatedObjects:
                if obj.is_a("IfcAlignmentSegment"):
                    if hasattr(obj, 'DesignParameters') and obj.DesignParameters:
                        if obj.DesignParameters.is_a("IfcAlignmentVerticalSegment"):
                            v_segments.append(obj.DesignParameters)

        if not v_segments:
            return 0.0

        v_segments.sort(key=lambda s: s.StartDistAlong)

        for seg in v_segments:
            start_sta = seg.StartDistAlong
            end_sta = start_sta + seg.HorizontalLength

            if start_sta <= station <= end_sta:
                local_dist = station - start_sta

                if seg.PredefinedType == "CONSTANTGRADIENT":
                    return seg.StartHeight + seg.StartGradient * local_dist

                elif seg.PredefinedType == "PARABOLICARC":
                    g1 = seg.StartGradient
                    g2 = seg.EndGradient
                    L = seg.HorizontalLength
                    A = (g2 - g1) / (2.0 * L)
                    return seg.StartHeight + g1 * local_dist + A * (local_dist ** 2)

        if v_segments:
            return v_segments[0].StartHeight
        return 0.0

    def get_direction(self, station: float) -> float:
        """Get direction (bearing) at station."""
        math = self._math
        distance_along = self._station_to_distance(station)
        cumulative_distance = 0.0

        for segment in self.segments:
            params = segment.DesignParameters
            if not params:
                continue

            segment_length = params.SegmentLength

            if cumulative_distance + segment_length >= distance_along:
                local_distance = distance_along - cumulative_distance

                if params.PredefinedType == "LINE":
                    return params.StartDirection

                elif params.PredefinedType == "CIRCULARARC":
                    radius = abs(params.StartRadiusOfCurvature)
                    signed_radius = params.StartRadiusOfCurvature
                    start_direction = params.StartDirection

                    arc_angle = local_distance / radius
                    if signed_radius < 0:
                        arc_angle = -arc_angle

                    return start_direction + arc_angle

            cumulative_distance += segment_length

        return 0.0

    def get_grade(self, station: float) -> float:
        """Get grade at station from vertical alignment."""
        if not self.vertical:
            return 0.0

        v_segments = []
        for rel in self.vertical.IsNestedBy or []:
            for obj in rel.RelatedObjects:
                if obj.is_a("IfcAlignmentSegment"):
                    if hasattr(obj, 'DesignParameters') and obj.DesignParameters:
                        if obj.DesignParameters.is_a("IfcAlignmentVerticalSegment"):
                            v_segments.append(obj.DesignParameters)

        if not v_segments:
            return 0.0

        v_segments.sort(key=lambda s: s.StartDistAlong)

        for seg in v_segments:
            start_sta = seg.StartDistAlong
            end_sta = start_sta + seg.HorizontalLength

            if start_sta <= station <= end_sta:
                if seg.PredefinedType == "CONSTANTGRADIENT":
                    return seg.StartGradient

                elif seg.PredefinedType == "PARABOLICARC":
                    local_dist = station - start_sta
                    g1 = seg.StartGradient
                    g2 = seg.EndGradient
                    L = seg.HorizontalLength
                    return g1 + (g2 - g1) * (local_dist / L)

        return 0.0


def create_alignment_wrapper(
    ifc_alignment: Any,
    start_station: float,
    end_station: float
) -> AlignmentWrapper:
    """
    Create an alignment wrapper for position queries.

    Args:
        ifc_alignment: IfcAlignment entity
        start_station: Starting station
        end_station: Ending station

    Returns:
        AlignmentWrapper instance
    """
    return AlignmentWrapper(ifc_alignment, start_station, end_station)


# =============================================================================
# Assembly Wrapper (Pure Python)
# =============================================================================

@dataclass
class ComponentData:
    """Cross-section component data."""
    name: str
    component_type: str
    width: float
    slope: float
    offset: float
    elevation: float
    material: str = "Asphalt"
    thickness: float = 0.15  # Surface thickness in meters


@dataclass
class AssemblyWrapper:
    """Wrapper for cross-section assembly data."""
    name: str
    components: List[ComponentData]
    constraint_manager: Optional[Any] = None  # ConstraintManager from parametric_constraints

    def get_component_value(
        self,
        component_name: str,
        parameter: str,
        station: float,
        default_value: float
    ) -> float:
        """
        Get effective parameter value at a station, applying constraints.

        Args:
            component_name: Name of component (e.g., "Right Travel Lane")
            parameter: Parameter name (e.g., "width", "cross_slope", "offset")
            station: Station along alignment (meters)
            default_value: Value to use if no constraint applies

        Returns:
            Effective parameter value at this station
        """
        if self.constraint_manager is None:
            return default_value

        return self.constraint_manager.get_effective_value(
            component_name=component_name,
            parameter_name=parameter,
            station=station,
            default_value=default_value
        )


def create_assembly_wrapper(assembly_props: Any) -> AssemblyWrapper:
    """
    Create an assembly wrapper from Blender PropertyGroup.

    This converts Blender-specific PropertyGroup data to a pure Python
    dataclass that can be used in core business logic.

    Args:
        assembly_props: BC_AssemblyProperties instance

    Returns:
        AssemblyWrapper instance with components and optional constraint_manager
    """
    from .logging_config import get_logger
    logger = get_logger(__name__)

    components = []

    # Track cumulative offset for each side
    left_offset = 0.0
    left_elev = 0.0
    right_offset = 0.0
    right_elev = 0.0

    for comp in assembly_props.components:
        side = comp.side
        width = comp.width
        slope = comp.cross_slope

        if side == "LEFT":
            comp_offset = -(left_offset + width)
            comp_elev = left_elev
            left_offset += width
            left_elev = left_elev - (width * slope)
        else:
            comp_offset = right_offset
            comp_elev = right_elev
            right_offset += width
            right_elev = right_elev - (width * slope)

        # Get thickness: use surface_thickness for most components, depth for ditches
        if comp.component_type == 'DITCH':
            thickness = getattr(comp, 'depth', 0.45)
        else:
            thickness = getattr(comp, 'surface_thickness', 0.15)

        components.append(ComponentData(
            name=comp.name,
            component_type=comp.component_type,
            width=width,
            slope=slope,
            offset=comp_offset,
            elevation=comp_elev,
            material=getattr(comp, 'surface_material', 'Asphalt'),
            thickness=thickness
        ))

    # Convert UI constraints to ConstraintManager (if any)
    constraint_manager = None
    if hasattr(assembly_props, 'constraints') and len(assembly_props.constraints) > 0:
        try:
            # Import here to avoid circular dependencies
            from .parametric_constraints import ConstraintManager, ParametricConstraint, ConstraintType, InterpolationType
            import uuid

            constraint_manager = ConstraintManager()
            enabled_count = 0

            for props in assembly_props.constraints:
                if not props.enabled:
                    continue

                # Generate ID if not set
                constraint_id = props.constraint_id if props.constraint_id else str(uuid.uuid4())

                constraint = ParametricConstraint(
                    id=constraint_id,
                    component_name=props.component_name,
                    parameter_name=props.parameter,
                    constraint_type=ConstraintType(props.constraint_type),
                    start_station=props.start_station,
                    end_station=props.end_station,
                    start_value=props.start_value,
                    end_value=props.end_value,
                    interpolation=InterpolationType(props.interpolation),
                    description=props.description,
                    enabled=props.enabled
                )
                constraint_manager.add_constraint(constraint)
                enabled_count += 1

            if enabled_count > 0:
                logger.info(f"Loaded {enabled_count} parametric constraints for assembly '{assembly_props.name}'")
            else:
                constraint_manager = None  # No enabled constraints

        except Exception as e:
            logger.warning(f"Failed to load constraints: {e}")
            constraint_manager = None

    return AssemblyWrapper(
        name=assembly_props.name,
        components=components,
        constraint_manager=constraint_manager
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Data classes
    "CorridorParams",
    "MeshStats",
    "ComponentData",
    "AssemblyWrapper",
    "AlignmentWrapper",
    # Functions
    "generate_corridor",
    "create_alignment_wrapper",
    "create_assembly_wrapper",
    # Re-exports from native_ifc_corridor
    "StationPoint",
    "StationManager",
    "CorridorModeler",
]
