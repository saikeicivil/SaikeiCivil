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
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================

"""
Median Component
Central dividing strips for divided highways and roads
"""

import math
from typing import List, Tuple
from .base_component import AssemblyComponent


class MedianComponent(AssemblyComponent):
    """
    Median component for dividing roadways.

    Standard types (AASHTO):
    - Flush median: Painted or slightly raised, no barrier
    - Raised median: Curbed, may include landscaping
    - Depressed median: Lower than pavement, allows drainage
    - Barrier median: Includes concrete barrier or guardrail

    Standard widths:
    - Minimum (urban): 1.2m (4 ft) - painted only
    - Narrow: 3.0m (10 ft) - allows left turn lanes
    - Standard: 6.0-12.0m (20-40 ft) - landscaping, drainage
    - Wide: 15.0m+ (50 ft+) - full separation with drainage
    """

    def __init__(self, name: str = "Median", width: float = 3.0, side: str = "LEFT"):
        """
        Initialize median component.

        Args:
            name: Median name (e.g., "Center Median")
            width: Median width in meters (default 3.0m = 10 ft)
            side: "LEFT" or "RIGHT" - typically "LEFT" (inside of roadway)
        """
        super().__init__(name, "MEDIAN")

        self.width = width
        self.cross_slope = 0.0  # Flat by default, or crowned
        self.side = side

        # Tag prefix for IFC interpolation
        self._tag_prefix = "MED"

        # Median-specific properties
        self.median_type = "RAISED"  # "FLUSH", "RAISED", "DEPRESSED", "BARRIER"
        self.has_barrier = False
        self.barrier_type = None  # "CONCRETE", "GUARDRAIL", "CABLE"
        self.barrier_offset = 0.0  # Offset from edge

        # Raised median properties
        self.curb_height = 0.15  # 150mm curb if raised
        self.curb_width = 0.15  # 150mm curb width

        # Depressed median properties
        self.depression_depth = 0.0  # Depth below pavement

        # Landscaping flag
        self.has_landscaping = False

        # Default materials for paved median
        self.add_material_layer("Concrete/Pavement", 0.10)  # 100mm
        self.add_material_layer("Aggregate Base", 0.15)  # 150mm

    def calculate_points(self, station: float = 0.0) -> List[Tuple[float, float]]:
        """
        Calculate median profile points.

        Profile varies by median type:
        - FLUSH: Simple sloped or flat surface
        - RAISED: Includes curbs on both sides
        - DEPRESSED: V-shaped or trapezoidal depression
        - BARRIER: Includes barrier wall profile

        Args:
            station: Station along alignment

        Returns:
            List of (offset, elevation) points
        """
        points = []

        if self.side == "RIGHT":
            sign = 1.0
        else:  # LEFT (typical for medians)
            sign = -1.0

        # Start at attachment point
        current_offset = sign * self.offset
        current_elevation = 0.0

        if self.median_type == "FLUSH":
            # Simple flat or crowned surface
            points.append((current_offset, current_elevation))

            # End of median (may have cross slope for drainage)
            end_offset = current_offset + sign * self.width
            end_elevation = current_elevation + (self.width * self.cross_slope)
            points.append((end_offset, end_elevation))

        elif self.median_type == "RAISED":
            # Start with inside curb
            points.append((current_offset, current_elevation))

            # Top of inside curb
            curb_top_elevation = current_elevation + self.curb_height
            points.append((current_offset, curb_top_elevation))

            # Across curb top
            curb_inner_offset = current_offset + sign * self.curb_width
            points.append((curb_inner_offset, curb_top_elevation))

            # Median surface (flat or sloped)
            surface_width = self.width - (2 * self.curb_width)
            surface_end_offset = curb_inner_offset + sign * surface_width
            surface_end_elevation = curb_top_elevation + (surface_width * self.cross_slope)
            points.append((surface_end_offset, surface_end_elevation))

            # Outside curb inner edge
            curb_outer_offset = surface_end_offset + sign * self.curb_width
            points.append((curb_outer_offset, surface_end_elevation))

            # Back down to grade
            end_offset = curb_outer_offset
            end_elevation = surface_end_elevation - self.curb_height
            points.append((end_offset, end_elevation))

        elif self.median_type == "DEPRESSED":
            # Start at grade
            points.append((current_offset, current_elevation))

            # Slope down to depression
            slope_width = self.width * 0.3  # 30% for each slope
            bottom_width = self.width * 0.4  # 40% for bottom

            # Bottom of inside slope
            slope_end_offset = current_offset + sign * slope_width
            slope_end_elevation = current_elevation - self.depression_depth
            points.append((slope_end_offset, slope_end_elevation))

            # End of bottom
            bottom_end_offset = slope_end_offset + sign * bottom_width
            points.append((bottom_end_offset, slope_end_elevation))

            # Top of outside slope
            end_offset = current_offset + sign * self.width
            points.append((end_offset, current_elevation))

        elif self.median_type == "BARRIER":
            # Similar to raised, but with barrier profile
            points.append((current_offset, current_elevation))

            # Barrier base
            barrier_base_elevation = current_elevation
            points.append((current_offset + sign * self.barrier_offset, barrier_base_elevation))

            # Barrier top (simplified rectangular barrier)
            barrier_height = 0.80  # 800mm typical barrier height
            barrier_width = 0.30  # 300mm barrier width
            points.append((current_offset + sign * self.barrier_offset,
                          barrier_base_elevation + barrier_height))
            points.append((current_offset + sign * (self.barrier_offset + barrier_width),
                          barrier_base_elevation + barrier_height))
            points.append((current_offset + sign * (self.barrier_offset + barrier_width),
                          barrier_base_elevation))

            # Continue to end
            end_offset = current_offset + sign * self.width
            points.append((end_offset, current_elevation))

        return points

    def set_type(self, median_type: str):
        """
        Set median type and update geometry/materials accordingly.

        Args:
            median_type: "FLUSH", "RAISED", "DEPRESSED", or "BARRIER"
        """
        self.median_type = median_type.upper()

        # Update materials based on type
        self.material_layers = []

        if self.median_type == "FLUSH":
            self.add_material_layer("Concrete/Pavement", 0.10)
            self.add_material_layer("Aggregate Base", 0.15)
            self.curb_height = 0.0

        elif self.median_type == "RAISED":
            self.add_material_layer("Concrete Curb", 0.15)
            self.add_material_layer("Topsoil/Landscaping", 0.15)
            self.curb_height = 0.15

        elif self.median_type == "DEPRESSED":
            self.add_material_layer("Topsoil/Grass", 0.15)
            self.add_material_layer("Drainage Layer", 0.20)
            self.depression_depth = 0.30  # Default 300mm depression

        elif self.median_type == "BARRIER":
            self.add_material_layer("Concrete Barrier", 0.80)
            self.add_material_layer("Concrete Base", 0.20)
            self.has_barrier = True
            self.barrier_type = "CONCRETE"

    def add_barrier(self, barrier_type: str = "CONCRETE", offset: float = 0.0):
        """
        Add a barrier to the median.

        Args:
            barrier_type: "CONCRETE", "GUARDRAIL", or "CABLE"
            offset: Offset from inside edge
        """
        self.has_barrier = True
        self.barrier_type = barrier_type.upper()
        self.barrier_offset = offset

        if self.median_type != "BARRIER":
            self.median_type = "BARRIER"

    @staticmethod
    def create_flush_median(width: float = 1.2) -> 'MedianComponent':
        """
        Create a flush (painted) median.

        Args:
            width: Median width in meters (default 1.2m = 4 ft)

        Returns:
            Configured MedianComponent
        """
        median = MedianComponent("Flush Median", width, "LEFT")
        median.set_type("FLUSH")
        return median

    @staticmethod
    def create_raised_median(width: float = 3.0) -> 'MedianComponent':
        """
        Create a raised median with curbs.

        Args:
            width: Median width in meters (default 3.0m = 10 ft)

        Returns:
            Configured MedianComponent
        """
        median = MedianComponent("Raised Median", width, "LEFT")
        median.set_type("RAISED")
        return median

    @staticmethod
    def create_depressed_median(width: float = 6.0, depth: float = 0.45) -> 'MedianComponent':
        """
        Create a depressed median for drainage.

        Args:
            width: Median width in meters (default 6.0m = 20 ft)
            depth: Depression depth in meters (default 0.45m)

        Returns:
            Configured MedianComponent
        """
        median = MedianComponent("Depressed Median", width, "LEFT")
        median.set_type("DEPRESSED")
        median.depression_depth = depth
        return median

    @staticmethod
    def create_barrier_median(width: float = 3.0,
                               barrier_type: str = "CONCRETE") -> 'MedianComponent':
        """
        Create a median with barrier.

        Args:
            width: Median width in meters (default 3.0m = 10 ft)
            barrier_type: "CONCRETE", "GUARDRAIL", or "CABLE"

        Returns:
            Configured MedianComponent
        """
        median = MedianComponent("Barrier Median", width, "LEFT")
        median.set_type("BARRIER")
        median.barrier_type = barrier_type.upper()
        return median

    @staticmethod
    def create_wide_landscaped_median(width: float = 12.0) -> 'MedianComponent':
        """
        Create a wide landscaped median.

        Args:
            width: Median width in meters (default 12.0m = 40 ft)

        Returns:
            Configured MedianComponent with landscaping
        """
        median = MedianComponent("Landscaped Median", width, "LEFT")
        median.set_type("RAISED")
        median.has_landscaping = True
        # Replace materials for landscaping
        median.material_layers = []
        median.add_material_layer("Topsoil", 0.30)  # 300mm for plantings
        median.add_material_layer("Subgrade", 0.15)
        return median

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate median parameters.

        Returns:
            (is_valid, error_messages) tuple
        """
        is_valid, errors = super().validate()

        # Check minimum width for type
        if self.median_type == "RAISED" and self.width < 1.2:
            errors.append(f"{self.name}: Raised median width {self.width:.2f}m is too narrow (min 1.2m)")

        if self.median_type == "DEPRESSED" and self.width < 3.0:
            errors.append(f"{self.name}: Depressed median width {self.width:.2f}m is narrow for drainage")

        if self.median_type == "BARRIER":
            if self.width < 0.6:
                errors.append(f"{self.name}: Barrier median width {self.width:.2f}m is too narrow")
            if not self.has_barrier:
                errors.append(f"{self.name}: Barrier median type but no barrier defined")

        # Check depression depth
        if self.median_type == "DEPRESSED":
            if self.depression_depth < 0.15:
                errors.append(f"{self.name}: Depression depth {self.depression_depth:.2f}m may be too shallow for drainage")
            if self.depression_depth > 1.0:
                errors.append(f"{self.name}: Depression depth {self.depression_depth:.2f}m is very deep")

        # Check curb height for raised median
        if self.median_type == "RAISED":
            if self.curb_height < 0.05:
                errors.append(f"{self.name}: Curb height {self.curb_height*1000:.0f}mm is very low")
            if self.curb_height > 0.30:
                errors.append(f"{self.name}: Curb height {self.curb_height*1000:.0f}mm is very high")

        return (len(errors) == 0, errors)

    def __repr__(self) -> str:
        barrier_str = f", barrier={self.barrier_type}" if self.has_barrier else ""
        return f"MedianComponent(name='{self.name}', type='{self.median_type}', width={self.width:.2f}m{barrier_str})"