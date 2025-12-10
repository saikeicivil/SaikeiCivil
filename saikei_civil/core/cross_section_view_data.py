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
Saikei Civil - Cross-Section View Data Model (Core)
=====================================================

Data structures for cross-section view visualization.
Following the OpenRoads approach where cross-sections are visualized
in a dedicated viewer, not in the 3D model space.

This follows Saikei Civil's architecture pattern:
- Pure Python data structures
- No Blender dependencies
- Easy to test independently

Author: Saikei Civil Development Team
Date: December 2025
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import Enum


class ComponentType(Enum):
    """Types of cross-section components"""
    LANE = "LANE"
    SHOULDER = "SHOULDER"
    CURB = "CURB"
    DITCH = "DITCH"
    MEDIAN = "MEDIAN"
    SIDEWALK = "SIDEWALK"
    CUSTOM = "CUSTOM"


@dataclass
class CrossSectionPoint:
    """A single point in the cross-section"""
    offset: float  # Horizontal offset from centerline (meters)
    elevation: float  # Elevation relative to centerline (meters)
    tag: str = ""  # Optional tag for IFC interpolation


@dataclass
class CrossSectionSegment:
    """A segment of the cross-section (between two points)"""
    start_point: CrossSectionPoint
    end_point: CrossSectionPoint
    component_type: ComponentType
    component_name: str
    side: str  # "LEFT" or "RIGHT"
    material: str = ""


@dataclass
class CrossSectionComponent:
    """A complete component in the cross-section view"""
    name: str
    component_type: ComponentType
    side: str  # "LEFT" or "RIGHT"
    points: List[CrossSectionPoint] = field(default_factory=list)
    width: float = 0.0
    cross_slope: float = 0.0
    thickness: float = 0.15  # Surface thickness in meters (default 150mm / 6")
    is_selected: bool = False
    material: str = ""

    # Visual properties
    color: Tuple[float, float, float, float] = (0.5, 0.5, 0.5, 1.0)


class CrossSectionViewData:
    """
    Data container for cross-section view visualization.

    Stores:
        - Cross-section components
        - View extents
        - Selection state
        - Display settings

    This is the data source for the CrossSectionViewRenderer.
    """

    def __init__(self):
        """Initialize cross-section view data"""
        # Component storage
        self.components: List[CrossSectionComponent] = []
        self.centerline_elevation: float = 0.0

        # View extents (will be auto-calculated)
        self.offset_min: float = -15.0
        self.offset_max: float = 15.0
        self.elevation_min: float = -2.0
        self.elevation_max: float = 2.0

        # Grid settings
        self.show_grid: bool = True
        self.offset_grid_spacing: float = 2.0  # meters
        self.elevation_grid_spacing: float = 0.5  # meters

        # Display settings
        self.show_centerline: bool = True
        self.show_labels: bool = True
        self.show_dimensions: bool = True
        self.show_materials: bool = False

        # Selection state
        self.selected_component_index: int = -1
        self.hover_component_index: int = -1

        # Assembly info
        self.assembly_name: str = ""
        self.station: float = 0.0  # Station being viewed
        self.total_width: float = 0.0

        # Component colors by type
        self.component_colors: Dict[ComponentType, Tuple[float, float, float, float]] = {
            ComponentType.LANE: (0.35, 0.35, 0.35, 1.0),      # Dark gray
            ComponentType.SHOULDER: (0.5, 0.5, 0.45, 1.0),    # Light gray/tan
            ComponentType.CURB: (0.7, 0.7, 0.7, 1.0),         # Light gray
            ComponentType.DITCH: (0.4, 0.35, 0.25, 1.0),      # Brown
            ComponentType.MEDIAN: (0.25, 0.5, 0.25, 1.0),     # Green
            ComponentType.SIDEWALK: (0.6, 0.6, 0.6, 1.0),     # Medium gray
            ComponentType.CUSTOM: (0.5, 0.5, 0.5, 1.0),       # Gray
        }

    def clear(self):
        """Clear all cross-section data"""
        self.components.clear()
        self.selected_component_index = -1
        self.hover_component_index = -1
        self.assembly_name = ""
        self.total_width = 0.0

    def add_component(self, name: str, component_type: ComponentType,
                      side: str, points: List[Tuple[float, float]],
                      width: float = 0.0, cross_slope: float = 0.0,
                      thickness: float = 0.15, material: str = "") -> int:
        """
        Add a component to the cross-section view.

        Args:
            name: Component name
            component_type: Type of component
            side: "LEFT" or "RIGHT"
            points: List of (offset, elevation) tuples
            width: Component width
            cross_slope: Cross slope value
            thickness: Surface thickness in meters (default 150mm / 6")
            material: Material name

        Returns:
            Index of added component
        """
        # Convert tuples to CrossSectionPoint objects
        cs_points = [
            CrossSectionPoint(offset=p[0], elevation=p[1])
            for p in points
        ]

        # Get color for component type
        color = self.component_colors.get(
            component_type,
            (0.5, 0.5, 0.5, 1.0)
        )

        component = CrossSectionComponent(
            name=name,
            component_type=component_type,
            side=side,
            points=cs_points,
            width=width,
            cross_slope=cross_slope,
            thickness=thickness,
            material=material,
            color=color
        )

        self.components.append(component)
        return len(self.components) - 1

    def load_from_assembly(self, assembly_props) -> bool:
        """
        Load cross-section data from Blender assembly properties.

        Components are connected by tracking the current offset and elevation
        for each side. Each component starts where the previous one ended,
        ensuring shared vertices at connection points.

        Args:
            assembly_props: BC_AssemblyProperties from Blender

        Returns:
            True if loaded successfully
        """
        self.clear()

        if not assembly_props:
            return False

        self.assembly_name = assembly_props.name

        # Track attachment point for each side (offset, elevation)
        # Components connect at these points - they share vertices
        left_attachment = (0.0, 0.0)   # (offset, elevation)
        right_attachment = (0.0, 0.0)  # (offset, elevation)

        # Process components
        for comp_prop in assembly_props.components:
            # Determine component type
            try:
                comp_type = ComponentType[comp_prop.component_type]
            except KeyError:
                comp_type = ComponentType.CUSTOM

            side = comp_prop.side
            width = comp_prop.width
            cross_slope = comp_prop.cross_slope

            # Get current attachment point for this side
            if side == "LEFT":
                start_offset, start_elev = left_attachment
                direction = -1
            else:  # RIGHT or CENTER
                start_offset, start_elev = right_attachment
                direction = 1

            # Generate points based on component type, starting from attachment point
            points, end_point = self._generate_component_points(
                comp_type, comp_prop, start_offset, start_elev, direction
            )

            # Update attachment point for next component on this side
            if side == "LEFT":
                left_attachment = end_point
            else:
                right_attachment = end_point

            # Get surface thickness (default 150mm / 6")
            thickness = getattr(comp_prop, 'surface_thickness', 0.15)

            self.add_component(
                name=comp_prop.name,
                component_type=comp_type,
                side=side,
                points=points,
                width=width,
                cross_slope=cross_slope,
                thickness=thickness,
                material=getattr(comp_prop, 'surface_material', '')
            )

        # Calculate total width from attachment points
        self.total_width = abs(left_attachment[0]) + abs(right_attachment[0])

        # Update view extents
        self.update_view_extents()

        return True

    def _generate_component_points(self, comp_type: ComponentType,
                                    comp_prop, start_offset: float,
                                    start_elev: float,
                                    direction: int) -> Tuple[List[Tuple[float, float]], Tuple[float, float]]:
        """
        Generate profile points for a component, starting from attachment point.

        Components connect to each other at shared vertices. The start point
        is provided (from previous component's end), and this method returns
        the end point for the next component to attach to.

        Args:
            comp_type: Component type
            comp_prop: Component properties
            start_offset: Starting offset (from previous component)
            start_elev: Starting elevation (from previous component)
            direction: 1 for right, -1 for left

        Returns:
            Tuple of:
                - List of (offset, elevation) tuples for this component
                - End point (offset, elevation) for next component attachment
        """
        points = []
        width = comp_prop.width

        if comp_type == ComponentType.LANE:
            # Simple sloped surface - starts at attachment point
            end_offset = start_offset + (width * direction)
            # Cross slope causes elevation change across the width
            elev_change = width * comp_prop.cross_slope * direction
            end_elev = start_elev + elev_change
            points = [
                (start_offset, start_elev),
                (end_offset, end_elev)
            ]
            end_point = (end_offset, end_elev)

        elif comp_type == ComponentType.SHOULDER:
            # Similar to lane - continues from attachment point
            end_offset = start_offset + (width * direction)
            elev_change = width * comp_prop.cross_slope * direction
            end_elev = start_elev + elev_change
            points = [
                (start_offset, start_elev),
                (end_offset, end_elev)
            ]
            end_point = (end_offset, end_elev)

        elif comp_type == ComponentType.CURB:
            # Curb with vertical face - starts at attachment point
            curb_height = getattr(comp_prop, 'curb_height', 0.15)
            end_offset = start_offset + (width * direction)
            points = [
                (start_offset, start_elev),
                (start_offset, start_elev + curb_height),
                (end_offset, start_elev + curb_height),
                (end_offset, start_elev)
            ]
            # Next component attaches at end, same elevation as start
            end_point = (end_offset, start_elev)

        elif comp_type == ComponentType.DITCH:
            # Trapezoidal ditch - starts at attachment point
            foreslope = getattr(comp_prop, 'foreslope', 4.0)
            backslope = getattr(comp_prop, 'backslope', 3.0)
            bottom_width = getattr(comp_prop, 'bottom_width', 1.2)
            depth = getattr(comp_prop, 'depth', 0.45)

            # Calculate horizontal distances
            fore_dist = depth * foreslope
            back_dist = depth * backslope

            if direction == 1:  # Right side
                p1 = (start_offset, start_elev)
                p2 = (start_offset + fore_dist, start_elev - depth)
                p3 = (start_offset + fore_dist + bottom_width, start_elev - depth)
                p4 = (start_offset + fore_dist + bottom_width + back_dist, start_elev)
                points = [p1, p2, p3, p4]
                end_point = p4
            else:  # Left side
                p1 = (start_offset, start_elev)
                p2 = (start_offset - fore_dist, start_elev - depth)
                p3 = (start_offset - fore_dist - bottom_width, start_elev - depth)
                p4 = (start_offset - fore_dist - bottom_width - back_dist, start_elev)
                points = [p1, p2, p3, p4]
                end_point = p4

        elif comp_type == ComponentType.MEDIAN:
            # Raised median - starts at attachment point
            end_offset = start_offset + (width * direction)
            points = [
                (start_offset, start_elev),
                (start_offset, start_elev + 0.15),
                (end_offset, start_elev + 0.15),
                (end_offset, start_elev)
            ]
            end_point = (end_offset, start_elev)

        elif comp_type == ComponentType.SIDEWALK:
            # Flat sidewalk with slight slope
            end_offset = start_offset + (width * direction)
            elev_change = width * comp_prop.cross_slope * direction
            end_elev = start_elev + elev_change
            points = [
                (start_offset, start_elev),
                (end_offset, end_elev)
            ]
            end_point = (end_offset, end_elev)

        else:
            # Generic flat component
            end_offset = start_offset + (width * direction)
            points = [
                (start_offset, start_elev),
                (end_offset, start_elev)
            ]
            end_point = (end_offset, start_elev)

        return points, end_point

    def update_view_extents(self, padding: float = 2.0):
        """
        Update view extents to fit all components.

        Args:
            padding: Extra space around extents (meters)
        """
        if not self.components:
            # Default extents
            self.offset_min = -15.0
            self.offset_max = 15.0
            self.elevation_min = -2.0
            self.elevation_max = 2.0
            return

        # Find min/max from all component points
        all_offsets = []
        all_elevations = []

        for comp in self.components:
            for pt in comp.points:
                all_offsets.append(pt.offset)
                all_elevations.append(pt.elevation)

        if all_offsets and all_elevations:
            self.offset_min = min(all_offsets) - padding
            self.offset_max = max(all_offsets) + padding
            self.elevation_min = min(all_elevations) - padding
            self.elevation_max = max(all_elevations) + padding

            # Ensure reasonable minimums
            if self.offset_max - self.offset_min < 10.0:
                center = (self.offset_max + self.offset_min) / 2
                self.offset_min = center - 5.0
                self.offset_max = center + 5.0

            if self.elevation_max - self.elevation_min < 2.0:
                center = (self.elevation_max + self.elevation_min) / 2
                self.elevation_min = center - 1.0
                self.elevation_max = center + 1.0

    def select_component(self, index: int):
        """Select a component by index"""
        # Deselect all
        for comp in self.components:
            comp.is_selected = False

        # Select new
        if 0 <= index < len(self.components):
            self.components[index].is_selected = True
            self.selected_component_index = index
        else:
            self.selected_component_index = -1

    def get_component_at_point(self, offset: float, elevation: float,
                                tolerance: float = 0.5) -> int:
        """
        Find component at given point.

        Args:
            offset: Offset coordinate
            elevation: Elevation coordinate
            tolerance: Search tolerance (meters)

        Returns:
            Component index, or -1 if none found
        """
        for i, comp in enumerate(self.components):
            # Simple bounding box check
            offsets = [pt.offset for pt in comp.points]
            elevations = [pt.elevation for pt in comp.points]

            if not offsets or not elevations:
                continue

            min_off = min(offsets) - tolerance
            max_off = max(offsets) + tolerance
            min_elev = min(elevations) - tolerance
            max_elev = max(elevations) + tolerance

            if min_off <= offset <= max_off and min_elev <= elevation <= max_elev:
                return i

        return -1

    def get_status_text(self) -> str:
        """Get status text for display"""
        if not self.assembly_name:
            return "No assembly loaded"

        return f"{self.assembly_name} | {len(self.components)} components | Width: {self.total_width:.2f}m"


if __name__ == "__main__":
    # Test the data model with connected components
    data = CrossSectionViewData()

    # Add test components that connect to each other
    # Lane 1 starts at centerline (0, 0)
    data.add_component(
        name="Right Lane 1",
        component_type=ComponentType.LANE,
        side="RIGHT",
        points=[(0, 0), (3.6, -0.072)],  # 2% slope over 3.6m
        width=3.6,
        cross_slope=0.02
    )

    # Lane 2 CONNECTS at (3.6, -0.072) - shared vertex!
    data.add_component(
        name="Right Lane 2",
        component_type=ComponentType.LANE,
        side="RIGHT",
        points=[(3.6, -0.072), (7.2, -0.144)],  # Continues from Lane 1's end
        width=3.6,
        cross_slope=0.02
    )

    # Shoulder CONNECTS at (7.2, -0.144)
    data.add_component(
        name="Right Shoulder",
        component_type=ComponentType.SHOULDER,
        side="RIGHT",
        points=[(7.2, -0.144), (9.6, -0.240)],  # 4% slope
        width=2.4,
        cross_slope=0.04
    )

    data.update_view_extents()

    print("CrossSectionViewData Test - Connected Components")
    print(f"Components: {len(data.components)}")
    print(f"View extents: {data.offset_min:.1f} to {data.offset_max:.1f}")
    print(f"Status: {data.get_status_text()}")

    # Verify components connect
    print("\nComponent connection points:")
    for i, comp in enumerate(data.components):
        start = comp.points[0]
        end = comp.points[-1]
        print(f"  {comp.name}: ({start.offset:.2f}, {start.elevation:.3f}) -> ({end.offset:.2f}, {end.elevation:.3f})")