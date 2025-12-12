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

        entity = ifc_file.create_entity(
            "IfcCourse",
            GlobalId=ifcopenshell.guid.new(),
            Name=name,
            Description="Corridor solid generated from cross-section assembly",
            ObjectType="CORRIDOR",
            PredefinedType="USERDEFINED"
        )
        return entity
    except Exception:
        return None


def _find_road_empty(blender: "type[tool.Blender]") -> Optional[Any]:
    """Find the Road empty object."""
    # This is a simple lookup - could be enhanced
    import bpy
    from .ifc_manager.blender_hierarchy import ROAD_EMPTY_NAME
    return bpy.data.objects.get(ROAD_EMPTY_NAME)


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
            start_sta: Starting station
            end_sta: Ending station
        """
        import math
        self._math = math

        self.ifc_alignment = ifc_alignment
        self._start = start_sta
        self._end = end_sta
        self.horizontal = None
        self.vertical = None
        self.segments = []
        self.starting_station = 0.0
        self._load_alignment_data()

    def _load_alignment_data(self):
        """Load horizontal segments and vertical data from IFC alignment."""
        for rel in self.ifc_alignment.IsNestedBy or []:
            for obj in rel.RelatedObjects:
                if obj.is_a("IfcAlignmentHorizontal"):
                    self.horizontal = obj
                    self._load_horizontal_segments(obj)
                elif obj.is_a("IfcAlignmentVertical"):
                    self.vertical = obj

    def _load_horizontal_segments(self, horizontal):
        """Load segment data from IfcAlignmentHorizontal."""
        self.segments = []
        for rel in horizontal.IsNestedBy or []:
            for obj in rel.RelatedObjects:
                if obj.is_a("IfcAlignmentSegment"):
                    self.segments.append(obj)

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
        math = self._math
        distance_along = self._station_to_distance(station)

        x, y = 0.0, 0.0
        cumulative_distance = 0.0

        for segment in self.segments:
            params = segment.DesignParameters
            if not params:
                continue

            segment_length = params.SegmentLength

            if cumulative_distance + segment_length >= distance_along:
                local_distance = distance_along - cumulative_distance

                if params.PredefinedType == "LINE":
                    start_point = params.StartPoint.Coordinates
                    direction_angle = params.StartDirection

                    x = start_point[0] + local_distance * math.cos(direction_angle)
                    y = start_point[1] + local_distance * math.sin(direction_angle)
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
                    break

            cumulative_distance += segment_length

        z = self._get_elevation(station)
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


@dataclass
class AssemblyWrapper:
    """Wrapper for cross-section assembly data."""
    name: str
    components: List[ComponentData]


def create_assembly_wrapper(assembly_props: Any) -> AssemblyWrapper:
    """
    Create an assembly wrapper from Blender PropertyGroup.

    This converts Blender-specific PropertyGroup data to a pure Python
    dataclass that can be used in core business logic.

    Args:
        assembly_props: BC_AssemblyProperties instance

    Returns:
        AssemblyWrapper instance
    """
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

        components.append(ComponentData(
            name=comp.name,
            component_type=comp.component_type,
            width=width,
            slope=slope,
            offset=comp_offset,
            elevation=comp_elev,
            material=getattr(comp, 'surface_material', 'Asphalt')
        ))

    return AssemblyWrapper(
        name=assembly_props.name,
        components=components
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
