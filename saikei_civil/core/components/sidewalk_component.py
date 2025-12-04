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
Sidewalk Component
Pedestrian walkways and paths for roadways
"""

import math
from typing import List, Tuple
from .base_component import AssemblyComponent


class SidewalkComponent(AssemblyComponent):
    """
    Sidewalk component for pedestrian walkways.

    Standard dimensions (ADA/AASHTO):
    - Minimum width: 1.2m (4 ft) - ADA minimum for wheelchair passing
    - Typical width: 1.5-1.8m (5-6 ft) - comfortable pedestrian use
    - Wide sidewalk: 2.4m+ (8 ft+) - high pedestrian volume areas
    - Cross slope: 2% maximum (ADA requirement)
    - Running slope: Match adjacent roadway or 5% max

    Configuration:
    - Buffer strip (optional): Grass/planting strip between curb and sidewalk
    - Sidewalk surface: Concrete, pavers, or asphalt
    - Back slope: Transition to adjacent property
    """

    def __init__(self, name: str = "Sidewalk", width: float = 1.5, side: str = "RIGHT"):
        """
        Initialize sidewalk component.

        Args:
            name: Sidewalk name (e.g., "Right Sidewalk")
            width: Sidewalk width in meters (default 1.5m = 5 ft)
            side: "LEFT" or "RIGHT" of attachment point
        """
        super().__init__(name, "SIDEWALK")

        self.width = width
        self.cross_slope = -0.02  # -2% (ADA maximum)
        self.side = side

        # Tag prefix for IFC interpolation
        self._tag_prefix = "SWK"

        # Sidewalk-specific properties
        self.surface_type = "CONCRETE"  # "CONCRETE", "PAVERS", "ASPHALT"
        self.has_buffer_strip = False  # Grass/planting strip between curb and sidewalk
        self.buffer_width = 0.0  # Width of buffer strip
        self.buffer_slope = -0.04  # Buffer strip cross slope (-4%)

        # Elevation above adjacent surface (if raised)
        self.elevation_offset = 0.0  # Typically 0 if adjacent to curb, or raised

        # Standard concrete sidewalk construction
        self.add_material_layer("Concrete", 0.10)  # 100mm (4 inches)
        self.add_material_layer("Compacted Subgrade", 0.10)  # 100mm

    def calculate_points(self, station: float = 0.0) -> List[Tuple[float, float]]:
        """
        Calculate sidewalk profile points.

        Sidewalk profile includes:
        1. Buffer strip (if present): sloped grass/planting area
        2. Sidewalk surface: nearly flat with slight cross slope

        Args:
            station: Station along alignment

        Returns:
            List of (offset, elevation) points
        """
        points = []

        if self.side == "RIGHT":
            sign = 1.0
        else:  # LEFT
            sign = -1.0

        # Start at attachment point
        current_offset = sign * self.offset
        current_elevation = self.elevation_offset

        # Point 1: Start of component
        points.append((current_offset, current_elevation))

        # Buffer strip (if present)
        if self.has_buffer_strip and self.buffer_width > 0:
            # End of buffer strip
            buffer_end_offset = current_offset + sign * self.buffer_width
            buffer_end_elevation = current_elevation + (self.buffer_width * self.buffer_slope)
            points.append((buffer_end_offset, buffer_end_elevation))
            current_offset = buffer_end_offset
            current_elevation = buffer_end_elevation

        # Sidewalk surface
        sidewalk_end_offset = current_offset + sign * self.width
        sidewalk_end_elevation = current_elevation + (self.width * self.cross_slope)
        points.append((sidewalk_end_offset, sidewalk_end_elevation))

        return points

    def set_surface_type(self, surface_type: str):
        """
        Set sidewalk surface type and update materials.

        Args:
            surface_type: "CONCRETE", "PAVERS", or "ASPHALT"
        """
        self.surface_type = surface_type.upper()

        # Update materials based on surface type
        self.material_layers = []

        if self.surface_type == "CONCRETE":
            self.add_material_layer("Concrete", 0.10)  # 100mm
            self.add_material_layer("Compacted Subgrade", 0.10)

        elif self.surface_type == "PAVERS":
            self.add_material_layer("Concrete Pavers", 0.06)  # 60mm pavers
            self.add_material_layer("Bedding Sand", 0.025)  # 25mm sand
            self.add_material_layer("Aggregate Base", 0.10)  # 100mm

        elif self.surface_type == "ASPHALT":
            self.add_material_layer("Asphalt Surface", 0.05)  # 50mm
            self.add_material_layer("Aggregate Base", 0.10)  # 100mm

    def add_buffer_strip(self, width: float = 0.6, slope: float = -0.04):
        """
        Add a buffer strip (grass/planting area) between curb and sidewalk.

        Args:
            width: Buffer strip width in meters (default 0.6m = 2 ft)
            slope: Cross slope (default -4%)
        """
        self.has_buffer_strip = True
        self.buffer_width = width
        self.buffer_slope = slope

    def remove_buffer_strip(self):
        """Remove the buffer strip."""
        self.has_buffer_strip = False
        self.buffer_width = 0.0

    @staticmethod
    def create_standard_sidewalk(side: str = "RIGHT", width: float = 1.5) -> 'SidewalkComponent':
        """
        Create a standard concrete sidewalk.

        Args:
            side: "LEFT" or "RIGHT"
            width: Sidewalk width in meters (default 1.5m = 5 ft)

        Returns:
            Configured SidewalkComponent
        """
        name = f"{side.capitalize()} Sidewalk"
        sidewalk = SidewalkComponent(name, width, side)
        return sidewalk

    @staticmethod
    def create_wide_sidewalk(side: str = "RIGHT") -> 'SidewalkComponent':
        """
        Create a wide sidewalk for high pedestrian traffic.

        Args:
            side: "LEFT" or "RIGHT"

        Returns:
            Configured SidewalkComponent with 2.4m width
        """
        name = f"{side.capitalize()} Wide Sidewalk"
        sidewalk = SidewalkComponent(name, 2.4, side)
        return sidewalk

    @staticmethod
    def create_sidewalk_with_buffer(side: str = "RIGHT", width: float = 1.5,
                                    buffer_width: float = 0.6) -> 'SidewalkComponent':
        """
        Create a sidewalk with buffer strip (planting area).

        Args:
            side: "LEFT" or "RIGHT"
            width: Sidewalk width in meters
            buffer_width: Buffer strip width in meters

        Returns:
            Configured SidewalkComponent with buffer strip
        """
        name = f"{side.capitalize()} Sidewalk w/ Buffer"
        sidewalk = SidewalkComponent(name, width, side)
        sidewalk.add_buffer_strip(buffer_width)
        return sidewalk

    @staticmethod
    def create_minimum_ada_sidewalk(side: str = "RIGHT") -> 'SidewalkComponent':
        """
        Create minimum ADA-compliant sidewalk (1.2m width).

        Args:
            side: "LEFT" or "RIGHT"

        Returns:
            Configured SidewalkComponent with minimum ADA width
        """
        name = f"{side.capitalize()} ADA Sidewalk"
        sidewalk = SidewalkComponent(name, 1.2, side)
        sidewalk.cross_slope = -0.02  # ADA maximum
        return sidewalk

    def get_total_width(self) -> float:
        """
        Calculate total horizontal width including buffer strip.

        Returns:
            Total width in meters
        """
        total = self.width
        if self.has_buffer_strip:
            total += self.buffer_width
        return total

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate sidewalk parameters against ADA/AASHTO requirements.

        Returns:
            (is_valid, error_messages) tuple
        """
        is_valid, errors = super().validate()

        # Check width against ADA minimum
        if self.width < 1.2:
            errors.append(f"{self.name}: Width {self.width:.2f}m is below ADA minimum (1.2m)")
        elif self.width < 1.5:
            errors.append(f"{self.name}: Width {self.width:.2f}m may be narrow for comfortable use")

        # Check cross slope against ADA maximum (2%)
        if abs(self.cross_slope) > 0.02:
            errors.append(f"{self.name}: Cross slope {self.cross_slope*100:.1f}% exceeds ADA maximum (2%)")

        # Check buffer strip if present
        if self.has_buffer_strip:
            if self.buffer_width < 0.3:
                errors.append(f"{self.name}: Buffer strip width {self.buffer_width:.2f}m is very narrow")
            if abs(self.buffer_slope) > 0.10:
                errors.append(f"{self.name}: Buffer slope {self.buffer_slope*100:.1f}% is very steep")

        return (len(errors) == 0, errors)

    def __repr__(self) -> str:
        buffer_str = f", buffer={self.buffer_width:.2f}m" if self.has_buffer_strip else ""
        return f"SidewalkComponent(name='{self.name}', width={self.width:.2f}m, surface='{self.surface_type}'{buffer_str})"