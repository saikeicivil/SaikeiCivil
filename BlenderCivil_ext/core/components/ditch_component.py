# ==============================================================================
# BlenderCivil - Civil Engineering Tools for Blender
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
Ditch Component
Drainage ditches with foreslopes, bottoms, and backslopes
"""

import math
from typing import List, Tuple
from .base_component import AssemblyComponent


class DitchComponent(AssemblyComponent):
    """
    Ditch component for roadside drainage ditches.
    
    A typical ditch consists of:
    - Foreslope: From shoulder down to ditch bottom (e.g., 2:1, 3:1, 4:1)
    - Ditch bottom: Flat or slightly sloped section (0.6-1.5m wide)
    - Backslope: From ditch bottom up to cut slope (e.g., 2:1, 3:1, 4:1)
    
    Standard dimensions (AASHTO):
    - Foreslope: 4:1 to 6:1 (preferred for safety)
    - Bottom width: 1.2m (4 ft) typical
    - Bottom slope: 2-4% longitudinal
    - Depth: 0.3-0.6m below shoulder
    - Backslope: 2:1 to 4:1 (depends on soil)
    """
    
    def __init__(self, name: str = "Ditch", side: str = "RIGHT"):
        """
        Initialize ditch component.
        
        Args:
            name: Ditch name (e.g., "Right Roadside Ditch")
            side: "LEFT" or "RIGHT" of attachment point
        """
        super().__init__(name, "DITCH")
        
        self.side = side
        
        # Ditch geometry properties
        self.foreslope = 4.0  # 4:1 (horizontal:vertical)
        self.bottom_width = 1.2  # 1.2m wide
        self.bottom_slope = -0.02  # -2% cross slope
        self.depth = 0.45  # 0.45m deep from attachment point
        self.backslope = 3.0  # 3:1 (horizontal:vertical)
        self.backslope_height = 0.60  # 0.60m up from ditch bottom
        
        # Material properties
        self.is_lined = False  # Whether ditch is lined (concrete/riprap)
        self.lining_material = None
        
        # Add typical ditch materials (topsoil/grass)
        self.add_material_layer("Topsoil/Grass", 0.15)  # 150mm
    
    def calculate_points(self, station: float = 0.0) -> List[Tuple[float, float]]:
        """
        Calculate ditch profile points.
        
        A ditch profile consists of 4 points:
        1. Top of foreslope (attachment point)
        2. Bottom of foreslope (start of ditch bottom)
        3. End of ditch bottom (start of backslope)
        4. Top of backslope
        
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
        
        # Point 1: Top of foreslope (attachment point)
        p1_offset = sign * self.offset
        p1_elevation = 0.0
        points.append((p1_offset, p1_elevation))
        
        # Point 2: Bottom of foreslope
        # Foreslope is expressed as H:V (e.g., 4:1 = 4 horizontal per 1 vertical)
        foreslope_horizontal = self.depth * self.foreslope
        p2_offset = p1_offset + sign * foreslope_horizontal
        p2_elevation = p1_elevation - self.depth
        points.append((p2_offset, p2_elevation))
        
        # Point 3: End of ditch bottom
        # Bottom may have a slight cross slope
        p3_offset = p2_offset + sign * self.bottom_width
        p3_elevation = p2_elevation + (self.bottom_width * self.bottom_slope)
        points.append((p3_offset, p3_elevation))
        
        # Point 4: Top of backslope
        # Backslope is also expressed as H:V
        backslope_horizontal = self.backslope_height * self.backslope
        p4_offset = p3_offset + sign * backslope_horizontal
        p4_elevation = p3_elevation + self.backslope_height
        points.append((p4_offset, p4_elevation))
        
        return points
    
    def set_lined(self, is_lined: bool, material: str = "Concrete"):
        """
        Set whether ditch is lined (for erosion control in steep ditches).
        
        Args:
            is_lined: Whether ditch has erosion protection lining
            material: Lining material ("Concrete", "Riprap", "Geotextile")
        """
        self.is_lined = is_lined
        self.lining_material = material
        
        if is_lined:
            # Add lining material layer
            if material == "Concrete":
                self.material_layers.insert(0, ("Concrete Lining", 0.10))  # 100mm
            elif material == "Riprap":
                self.material_layers.insert(0, ("Riprap", 0.20))  # 200mm
            elif material == "Geotextile":
                self.material_layers.insert(0, ("Geotextile Fabric", 0.01))  # 10mm
    
    @staticmethod
    def create_standard_ditch(side: str = "RIGHT") -> 'DitchComponent':
        """
        Create a standard roadside ditch (4:1 foreslope, 1.2m bottom, 3:1 backslope).
        
        Args:
            side: "LEFT" or "RIGHT"
            
        Returns:
            Configured DitchComponent
        """
        name = f"{side.capitalize()} Roadside Ditch"
        ditch = DitchComponent(name, side)
        return ditch
    
    @staticmethod
    def create_shallow_ditch(side: str = "RIGHT") -> 'DitchComponent':
        """
        Create a shallow swale/ditch (6:1 foreslope, minimal depth).
        
        Args:
            side: "LEFT" or "RIGHT"
            
        Returns:
            Configured DitchComponent
        """
        name = f"{side.capitalize()} Shallow Swale"
        ditch = DitchComponent(name, side)
        ditch.foreslope = 6.0  # Flatter foreslope
        ditch.depth = 0.30  # Shallower
        ditch.backslope = 6.0  # Flatter backslope
        ditch.backslope_height = 0.30
        return ditch
    
    @staticmethod
    def create_steep_ditch(side: str = "RIGHT") -> 'DitchComponent':
        """
        Create a steep rock-lined ditch (2:1 slopes, concrete lined).
        
        Args:
            side: "LEFT" or "RIGHT"
            
        Returns:
            Configured DitchComponent
        """
        name = f"{side.capitalize()} Steep Ditch"
        ditch = DitchComponent(name, side)
        ditch.foreslope = 2.0  # Steeper
        ditch.depth = 0.60  # Deeper
        ditch.backslope = 2.0  # Steeper
        ditch.backslope_height = 0.90
        ditch.set_lined(True, "Concrete")
        return ditch
    
    def get_total_width(self) -> float:
        """
        Calculate total horizontal width of ditch.
        
        Returns:
            Total width in meters
        """
        foreslope_width = self.depth * self.foreslope
        backslope_width = self.backslope_height * self.backslope
        return foreslope_width + self.bottom_width + backslope_width
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate ditch parameters.
        
        Returns:
            (is_valid, error_messages) tuple
        """
        is_valid, errors = super().validate()
        
        # Check foreslope for safety
        if self.foreslope < 3.0:
            errors.append(f"{self.name}: Foreslope {self.foreslope:.1f}:1 is steep (safety concern, prefer 4:1 or flatter)")
        
        if self.foreslope < 2.0:
            errors.append(f"{self.name}: Foreslope {self.foreslope:.1f}:1 is very steep (clear zone violation)")
        
        # Check backslope stability
        if self.backslope < 1.5:
            errors.append(f"{self.name}: Backslope {self.backslope:.1f}:1 may be unstable (typically 2:1 minimum)")
        
        # Check ditch depth
        if self.depth < 0.15:
            errors.append(f"{self.name}: Ditch depth {self.depth:.2f}m is shallow (may not provide adequate drainage)")
        
        if self.depth > 1.0:
            errors.append(f"{self.name}: Ditch depth {self.depth:.2f}m is very deep (consider piped drainage)")
        
        # Check bottom width
        if self.bottom_width < 0.60:
            errors.append(f"{self.name}: Bottom width {self.bottom_width:.2f}m is narrow (maintenance difficulty)")
        
        # Steep ditches should be lined
        if self.foreslope < 3.0 and not self.is_lined:
            errors.append(f"{self.name}: Steep ditch (foreslope {self.foreslope:.1f}:1) should be lined for erosion control")
        
        return (len(errors) == 0, errors)
    
    def __repr__(self) -> str:
        lined_str = f", lined({self.lining_material})" if self.is_lined else ""
        return f"DitchComponent(name='{self.name}', foreslope={self.foreslope:.1f}:1, bottom={self.bottom_width:.2f}m, backslope={self.backslope:.1f}:1{lined_str})"
