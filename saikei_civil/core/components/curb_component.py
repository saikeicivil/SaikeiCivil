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
Curb Component
Vertical and sloped curbs for roadways
"""

import math
from typing import List, Tuple
from .base_component import AssemblyComponent


class CurbComponent(AssemblyComponent):
    """
    Curb component for vertical and sloped curbs.
    
    Standard dimensions (AASHTO):
    - Height: 150mm (6 inches) typical
    - Face batter: vertical or 1:1 slope
    - Top width: 150mm typical
    - Gutter width (if included): 600mm typical
    
    Types:
    - Vertical curb: 90° face (urban areas, parking lots)
    - Sloped curb: 1:1 or 2:1 face (mountable, suburban)
    - Curb and gutter: Combined element
    """
    
    def __init__(self, name: str = "Curb", side: str = "RIGHT"):
        """
        Initialize curb component.
        
        Args:
            name: Curb name (e.g., "Right Vertical Curb")
            side: "LEFT" or "RIGHT" of attachment point
        """
        super().__init__(name, "CURB")
        
        self.width = 0.15  # 150mm wide at top
        self.side = side
        
        # Curb-specific properties
        self.curb_type = "VERTICAL"  # "VERTICAL", "SLOPED", "GUTTER"
        self.height = 0.15  # 150mm high (6 inches)
        self.face_slope = float('inf')  # Vertical face (infinite slope)
        self.has_gutter = False
        self.gutter_width = 0.60  # 600mm gutter if present
        
        # Curb material (concrete)
        self.add_material_layer("Concrete Curb", 0.15)
    
    def calculate_points(self, station: float = 0.0) -> List[Tuple[float, float]]:
        """
        Calculate curb profile points.
        
        Curbs are more complex than lanes because they have vertical sections.
        Profile typically consists of:
        - Base point at attachment
        - Vertical or sloped face
        - Top surface
        - Optional gutter section
        
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
        
        # Start at attachment point (bottom of curb)
        base_offset = sign * self.offset
        base_elevation = 0.0
        points.append((base_offset, base_elevation))
        
        # Curb face
        if self.curb_type == "VERTICAL":
            # Vertical face: go straight up
            face_offset = base_offset
            face_elevation = base_elevation + self.height
            points.append((face_offset, face_elevation))
            
        elif self.curb_type == "SLOPED":
            # Sloped face: typically 1:1 (45°) or 2:1
            face_width = self.height / self.face_slope if self.face_slope > 0 else self.height
            face_offset = base_offset + sign * face_width
            face_elevation = base_elevation + self.height
            points.append((face_offset, face_elevation))
        
        # Top of curb
        top_offset = points[-1][0] + sign * self.width
        top_elevation = self.height
        points.append((top_offset, top_elevation))
        
        # Gutter section (if present)
        if self.has_gutter:
            # Gutter slopes down from curb top
            gutter_slope = -0.04  # -4% typical
            gutter_end_offset = top_offset + sign * self.gutter_width
            gutter_end_elevation = top_elevation + (self.gutter_width * gutter_slope)
            points.append((gutter_end_offset, gutter_end_elevation))
        
        return points
    
    def set_type(self, curb_type: str):
        """
        Set curb type and update geometry.
        
        Args:
            curb_type: "VERTICAL", "SLOPED", or "GUTTER"
        """
        self.curb_type = curb_type.upper()
        
        if self.curb_type == "VERTICAL":
            self.face_slope = float('inf')  # Vertical
            self.has_gutter = False
            
        elif self.curb_type == "SLOPED":
            self.face_slope = 1.0  # 1:1 slope (45°)
            self.has_gutter = False
            
        elif self.curb_type == "GUTTER":
            self.face_slope = float('inf')  # Vertical face
            self.has_gutter = True
            
            # Add gutter material
            if len(self.material_layers) == 1:  # Only has curb material
                self.add_material_layer("Concrete Gutter", 0.15)
    
    @staticmethod
    def create_vertical_curb(side: str = "RIGHT", height: float = 0.15) -> 'CurbComponent':
        """
        Create a standard vertical curb.
        
        Args:
            side: "LEFT" or "RIGHT"
            height: Curb height in meters (default 0.15m = 6 inches)
            
        Returns:
            Configured CurbComponent
        """
        name = f"{side.capitalize()} Vertical Curb"
        curb = CurbComponent(name, side)
        curb.height = height
        curb.set_type("VERTICAL")
        return curb
    
    @staticmethod
    def create_mountable_curb(side: str = "RIGHT", height: float = 0.10) -> 'CurbComponent':
        """
        Create a mountable (sloped) curb.
        
        Args:
            side: "LEFT" or "RIGHT"
            height: Curb height in meters (default 0.10m = 4 inches)
            
        Returns:
            Configured CurbComponent
        """
        name = f"{side.capitalize()} Mountable Curb"
        curb = CurbComponent(name, side)
        curb.height = height
        curb.set_type("SLOPED")
        curb.face_slope = 2.0  # 2:1 slope (more gradual)
        return curb
    
    @staticmethod
    def create_curb_and_gutter(side: str = "RIGHT") -> 'CurbComponent':
        """
        Create a curb and gutter combination.
        
        Args:
            side: "LEFT" or "RIGHT"
            
        Returns:
            Configured CurbComponent
        """
        name = f"{side.capitalize()} Curb & Gutter"
        curb = CurbComponent(name, side)
        curb.set_type("GUTTER")
        return curb
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate curb parameters.
        
        Returns:
            (is_valid, error_messages) tuple
        """
        is_valid, errors = super().validate()
        
        # Check curb height
        if self.height < 0.05:
            errors.append(f"{self.name}: Curb height {self.height*1000:.0f}mm is very low (minimum 50mm)")
        
        if self.height > 0.30:
            errors.append(f"{self.name}: Curb height {self.height*1000:.0f}mm is very high (typical maximum 300mm)")
        
        # Check face slope for mountability
        if self.curb_type == "SLOPED":
            if self.face_slope < 1.0:
                errors.append(f"{self.name}: Face slope {self.face_slope:.1f}:1 is too steep to be mountable")
        
        # Check gutter width
        if self.has_gutter:
            if self.gutter_width < 0.30:
                errors.append(f"{self.name}: Gutter width {self.gutter_width:.2f}m is too narrow (minimum 0.30m)")
            if self.gutter_width > 1.20:
                errors.append(f"{self.name}: Gutter width {self.gutter_width:.2f}m is very wide (typical maximum 1.20m)")
        
        return (len(errors) == 0, errors)
    
    def __repr__(self) -> str:
        gutter_str = f", gutter={self.gutter_width:.2f}m" if self.has_gutter else ""
        return f"CurbComponent(name='{self.name}', type='{self.curb_type}', height={self.height*1000:.0f}mm{gutter_str})"
