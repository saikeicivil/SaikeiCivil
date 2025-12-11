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
Lane Component
Travel lanes, passing lanes, and parking lanes
"""

import math
from typing import List, Tuple
from .base_component import AssemblyComponent


class LaneComponent(AssemblyComponent):
    """
    Lane component for travel lanes, passing lanes, turn lanes, and parking.
    
    Standard widths (AASHTO):
    - Travel lane: 3.6m (12 ft)
    - Narrow lane: 3.0m (10 ft)
    - Wide lane: 3.9m (13 ft)
    - Parking lane: 2.4m (8 ft)
    
    Typical cross slopes:
    - Tangent sections: -2% (crowned pavement)
    - Curves: -2% to -8% (superelevation)
    """
    
    def __init__(self, name: str = "Travel Lane", width: float = 3.6, side: str = "RIGHT"):
        """
        Initialize lane component.
        
        Args:
            name: Lane name (e.g., "Right Travel Lane", "Left Turn Lane")
            width: Lane width in meters (default 3.6m = 12 ft)
            side: "LEFT" or "RIGHT" of centerline
        """
        super().__init__(name, "LANE")
        
        self.width = width
        self.cross_slope = -0.02  # -2% default
        self.side = side
        
        # Lane-specific properties
        self.lane_type = "TRAVEL"  # "TRAVEL", "PASSING", "TURN", "PARKING"
        self.direction = "FORWARD"  # "FORWARD", "BACKWARD", "BOTH"
        
        # Superelevation properties
        self.superelevation = 0.0  # Applied superelevation (overrides cross_slope in curves)
        self.is_superelevated = False
        
        # Pavement structure (typical flexible pavement)
        self.add_material_layer("HMA Surface Course", 0.05)  # 50mm
        self.add_material_layer("HMA Intermediate Course", 0.075)  # 75mm
        self.add_material_layer("Aggregate Base", 0.20)  # 200mm
        self.add_material_layer("Subbase", 0.30)  # 300mm
    
    def calculate_points(self, station: float = 0.0) -> List[Tuple[float, float]]:
        """
        Calculate lane profile points.
        
        A lane is a simple rectangular section with a constant cross slope:
        - Inside edge at offset 0, elevation 0
        - Outside edge at offset = width, elevation = width * cross_slope
        
        Args:
            station: Station along alignment
            
        Returns:
            List of (offset, elevation) points
        """
        # Determine which slope to use
        slope = self.superelevation if self.is_superelevated else self.cross_slope
        
        # Sign convention: 
        # - Positive offset = right of attachment point
        # - Negative slope = down to the right
        # - For LEFT side, flip the signs
        
        if self.side == "RIGHT":
            # Right side: offset increases to the right
            inside_offset = self.offset
            outside_offset = self.offset + self.width
            
            inside_elevation = 0.0
            outside_elevation = self.width * slope
            
        else:  # LEFT
            # Left side: offset increases to the left (negative direction)
            inside_offset = -self.offset
            outside_offset = -(self.offset + self.width)
            
            inside_elevation = 0.0
            outside_elevation = self.width * (-slope)  # Flip slope for left side
        
        # Return points from inside to outside
        return [
            (inside_offset, inside_elevation),
            (outside_offset, outside_elevation)
        ]
    
    def set_superelevation(self, rate: float):
        """
        Set superelevation rate for this lane.
        
        Superelevation is the banking of the roadway in curves to help
        vehicles resist centrifugal force. It overrides the normal cross slope.
        
        Args:
            rate: Superelevation rate (e.g., -0.06 = -6%)
        """
        self.superelevation = rate
        self.is_superelevated = True
    
    def remove_superelevation(self):
        """Remove superelevation and return to normal cross slope."""
        self.is_superelevated = False
        self.superelevation = 0.0
    
    @staticmethod
    def create_standard_travel_lane(side: str = "RIGHT") -> 'LaneComponent':
        """
        Create a standard travel lane (3.6m width, -2% cross slope).
        
        Args:
            side: "LEFT" or "RIGHT"
            
        Returns:
            Configured LaneComponent
        """
        name = f"{side.capitalize()} Travel Lane"
        lane = LaneComponent(name, width=3.6, side=side)
        lane.lane_type = "TRAVEL"
        return lane
    
    @staticmethod
    def create_parking_lane(side: str = "RIGHT") -> 'LaneComponent':
        """
        Create a parking lane (2.4m width, -2% cross slope).
        
        Args:
            side: "LEFT" or "RIGHT"
            
        Returns:
            Configured LaneComponent
        """
        name = f"{side.capitalize()} Parking Lane"
        lane = LaneComponent(name, width=2.4, side=side)
        lane.lane_type = "PARKING"
        
        # Parking lanes typically have thinner pavement
        lane.material_layers = []
        lane.add_material_layer("HMA Surface Course", 0.05)  # 50mm
        lane.add_material_layer("Aggregate Base", 0.15)  # 150mm
        lane.add_material_layer("Subbase", 0.20)  # 200mm
        
        return lane
    
    @staticmethod
    def create_turn_lane(side: str = "RIGHT", width: float = 3.6) -> 'LaneComponent':
        """
        Create a turn lane (typically 3.0-3.6m width).
        
        Args:
            side: "LEFT" or "RIGHT"
            width: Lane width in meters
            
        Returns:
            Configured LaneComponent
        """
        name = f"{side.capitalize()} Turn Lane"
        lane = LaneComponent(name, width=width, side=side)
        lane.lane_type = "TURN"
        return lane
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate lane parameters.
        
        Returns:
            (is_valid, error_messages) tuple
        """
        is_valid, errors = super().validate()
        
        # Check lane width against AASHTO standards
        if self.lane_type == "TRAVEL":
            if self.width < 3.0:
                errors.append(f"{self.name}: Travel lane width {self.width:.2f}m is below minimum (3.0m)")
            elif self.width < 3.3:
                errors.append(f"{self.name}: Travel lane width {self.width:.2f}m is narrow (recommend 3.6m)")
        
        # Check superelevation rate
        if self.is_superelevated:
            if abs(self.superelevation) > 0.12:
                errors.append(f"{self.name}: Superelevation {self.superelevation*100:.1f}% exceeds typical maximum (12%)")
        
        # Check cross slope
        if not self.is_superelevated and abs(self.cross_slope) > 0.04:
            errors.append(f"{self.name}: Cross slope {self.cross_slope*100:.1f}% is steep for normal crown (typical 2%)")
        
        return (len(errors) == 0, errors)
    
    def __repr__(self) -> str:
        slope_type = "superelevation" if self.is_superelevated else "cross_slope"
        slope_value = self.superelevation if self.is_superelevated else self.cross_slope
        return f"LaneComponent(name='{self.name}', type='{self.lane_type}', width={self.width:.2f}m, {slope_type}={slope_value*100:.1f}%)"
