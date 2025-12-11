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
Shoulder Component
Paved and gravel shoulders for roadways
"""

import math
from typing import List, Tuple
from .base_component import AssemblyComponent


class ShoulderComponent(AssemblyComponent):
    """
    Shoulder component for paved and unpaved shoulders.
    
    Standard widths (AASHTO):
    - Interstate/Freeway: 3.0m (10 ft) paved
    - Arterial: 1.8-2.4m (6-8 ft) paved
    - Rural highway: 2.4m (8 ft) gravel
    - Local road: 0.6-1.2m (2-4 ft) gravel
    
    Typical cross slopes:
    - Paved shoulder: -4% to -6%
    - Gravel shoulder: -6% to -8%
    """
    
    def __init__(self, name: str = "Shoulder", width: float = 2.4, side: str = "RIGHT"):
        """
        Initialize shoulder component.
        
        Args:
            name: Shoulder name (e.g., "Right Paved Shoulder")
            width: Shoulder width in meters (default 2.4m = 8 ft)
            side: "LEFT" or "RIGHT" of attachment point
        """
        super().__init__(name, "SHOULDER")
        
        self.width = width
        self.cross_slope = -0.04  # -4% default (steeper than lane)
        self.side = side
        
        # Shoulder-specific properties
        self.shoulder_type = "PAVED"  # "PAVED" or "GRAVEL"
        self.is_stabilized = True  # Whether shoulder is stabilized (affects materials)
        
        # Paved shoulder structure (thinner than lane)
        self.add_material_layer("HMA Surface Course", 0.04)  # 40mm
        self.add_material_layer("Aggregate Base", 0.15)  # 150mm
        self.add_material_layer("Subbase", 0.20)  # 200mm
    
    def calculate_points(self, station: float = 0.0) -> List[Tuple[float, float]]:
        """
        Calculate shoulder profile points.
        
        Similar to lane but typically with steeper cross slope.
        
        Args:
            station: Station along alignment
            
        Returns:
            List of (offset, elevation) points
        """
        slope = self.cross_slope
        
        if self.side == "RIGHT":
            inside_offset = self.offset
            outside_offset = self.offset + self.width
            
            inside_elevation = 0.0
            outside_elevation = self.width * slope
            
        else:  # LEFT
            inside_offset = -self.offset
            outside_offset = -(self.offset + self.width)
            
            inside_elevation = 0.0
            outside_elevation = self.width * (-slope)
        
        return [
            (inside_offset, inside_elevation),
            (outside_offset, outside_elevation)
        ]
    
    def set_type(self, shoulder_type: str):
        """
        Set shoulder type and update materials accordingly.
        
        Args:
            shoulder_type: "PAVED" or "GRAVEL"
        """
        self.shoulder_type = shoulder_type.upper()
        
        # Update materials based on type
        self.material_layers = []
        
        if self.shoulder_type == "PAVED":
            self.add_material_layer("HMA Surface Course", 0.04)  # 40mm
            self.add_material_layer("Aggregate Base", 0.15)  # 150mm
            self.add_material_layer("Subbase", 0.20)  # 200mm
            self.cross_slope = -0.04  # -4%
            
        else:  # GRAVEL
            self.add_material_layer("Aggregate Surface", 0.10)  # 100mm
            self.add_material_layer("Subbase", 0.20)  # 200mm
            self.cross_slope = -0.06  # -6% (steeper for drainage)
    
    @staticmethod
    def create_paved_shoulder(side: str = "RIGHT", width: float = 2.4) -> 'ShoulderComponent':
        """
        Create a standard paved shoulder.
        
        Args:
            side: "LEFT" or "RIGHT"
            width: Shoulder width in meters (default 2.4m = 8 ft)
            
        Returns:
            Configured ShoulderComponent
        """
        name = f"{side.capitalize()} Paved Shoulder"
        shoulder = ShoulderComponent(name, width, side)
        shoulder.set_type("PAVED")
        return shoulder
    
    @staticmethod
    def create_gravel_shoulder(side: str = "RIGHT", width: float = 1.8) -> 'ShoulderComponent':
        """
        Create a gravel shoulder.
        
        Args:
            side: "LEFT" or "RIGHT"
            width: Shoulder width in meters (default 1.8m = 6 ft)
            
        Returns:
            Configured ShoulderComponent
        """
        name = f"{side.capitalize()} Gravel Shoulder"
        shoulder = ShoulderComponent(name, width, side)
        shoulder.set_type("GRAVEL")
        return shoulder
    
    @staticmethod
    def create_interstate_shoulder(side: str = "RIGHT") -> 'ShoulderComponent':
        """
        Create an interstate/freeway shoulder (3.0m paved).
        
        Args:
            side: "LEFT" or "RIGHT"
            
        Returns:
            Configured ShoulderComponent
        """
        name = f"{side.capitalize()} Interstate Shoulder"
        shoulder = ShoulderComponent(name, 3.0, side)
        shoulder.set_type("PAVED")
        
        # Interstate shoulders are more heavily constructed
        shoulder.material_layers = []
        shoulder.add_material_layer("HMA Surface Course", 0.05)  # 50mm
        shoulder.add_material_layer("HMA Intermediate Course", 0.05)  # 50mm
        shoulder.add_material_layer("Aggregate Base", 0.20)  # 200mm
        shoulder.add_material_layer("Subbase", 0.30)  # 300mm
        
        return shoulder
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate shoulder parameters.
        
        Returns:
            (is_valid, error_messages) tuple
        """
        is_valid, errors = super().validate()
        
        # Check shoulder width
        if self.width < 0.6:
            errors.append(f"{self.name}: Shoulder width {self.width:.2f}m is very narrow (minimum 0.6m)")
        
        # Check cross slope
        if abs(self.cross_slope) < 0.02:
            errors.append(f"{self.name}: Cross slope {self.cross_slope*100:.1f}% may not provide adequate drainage (recommend 4-6%)")
        
        if abs(self.cross_slope) > 0.08:
            errors.append(f"{self.name}: Cross slope {self.cross_slope*100:.1f}% is very steep (typical maximum 8%)")
        
        # Check that shoulder slope is steeper than typical lane slope
        if abs(self.cross_slope) < 0.03:
            errors.append(f"{self.name}: Shoulder cross slope should typically be steeper than lane slope (recommend 4-6%)")
        
        return (len(errors) == 0, errors)
    
    def __repr__(self) -> str:
        return f"ShoulderComponent(name='{self.name}', type='{self.shoulder_type}', width={self.width:.2f}m, slope={self.cross_slope*100:.1f}%)"
