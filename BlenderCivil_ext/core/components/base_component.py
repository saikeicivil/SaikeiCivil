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
Base Component for Cross-Section Assembly
Foundation class for all cross-section components (lanes, shoulders, curbs, etc.)
"""

import math
from typing import List, Tuple, Optional, Dict, Any


class AssemblyComponent:
    """
    Base class for all cross-section assembly components.
    
    A component represents a single element of a road cross-section (lane, shoulder, curb, etc.)
    Each component has:
    - Geometry (width, slopes, offsets)
    - Materials (pavement layers, soil, etc.)
    - Constraints (how it varies along the alignment)
    - IFC export capability
    """
    
    def __init__(self, name: str, component_type: str):
        """
        Initialize base component.
        
        Args:
            name: Human-readable name (e.g., "Right Travel Lane")
            component_type: Component type identifier (e.g., "LANE", "SHOULDER")
        """
        self.name = name
        self.component_type = component_type
        
        # Geometry properties
        self.width = 3.6  # meters (default lane width)
        self.cross_slope = -0.02  # dimensionless (default -2%)
        self.offset = 0.0  # offset from attachment point
        self.side = "RIGHT"  # "LEFT" or "RIGHT"
        
        # Material properties
        self.material_layers = []  # List of (material_name, thickness) tuples
        
        # Attachment properties
        self.attach_to = None  # Component this attaches to (None = centerline)
        self.attach_point = "OUTSIDE"  # "INSIDE" or "OUTSIDE" edge
        
        # IFC properties
        self.ifc_profile = None  # IfcOpenCrossProfileDef
        self.ifc_material_profile = None  # IfcMaterialProfile
        
    def calculate_points(self, station: float = 0.0) -> List[Tuple[float, float]]:
        """
        Calculate cross-section points for this component at a given station.
        
        This is the core geometry calculation method. Each component type
        implements this to generate its specific geometry.
        
        Args:
            station: Station along alignment (for parametric constraints)
            
        Returns:
            List of (offset, elevation) tuples defining the component profile
        """
        raise NotImplementedError("Subclasses must implement calculate_points()")
    
    def get_start_point(self, station: float = 0.0) -> Tuple[float, float]:
        """
        Get the starting point (inside edge) of this component.
        
        Returns:
            (offset, elevation) tuple
        """
        points = self.calculate_points(station)
        return points[0] if points else (0.0, 0.0)
    
    def get_end_point(self, station: float = 0.0) -> Tuple[float, float]:
        """
        Get the ending point (outside edge) of this component.
        
        Returns:
            (offset, elevation) tuple
        """
        points = self.calculate_points(station)
        return points[-1] if points else (0.0, 0.0)
    
    def add_material_layer(self, material_name: str, thickness: float):
        """
        Add a material layer to this component.
        
        Args:
            material_name: Name of the material (e.g., "HMA Surface Course")
            thickness: Layer thickness in meters
        """
        self.material_layers.append((material_name, thickness))
    
    def get_total_thickness(self) -> float:
        """
        Calculate total thickness of all material layers.
        
        Returns:
            Total thickness in meters
        """
        return sum(thickness for _, thickness in self.material_layers)
    
    def to_ifc(self, ifc_file) -> Dict[str, Any]:
        """
        Export this component to IFC entities.
        
        Creates:
        - IfcOpenCrossProfileDef for geometry
        - IfcMaterialProfile for materials
        
        Args:
            ifc_file: IfcOpenShell file object
            
        Returns:
            Dictionary with 'profile' and 'material_profile' keys
        """
        # Calculate geometry points
        points = self.calculate_points()
        
        # Create IfcCartesianPointList2D for the profile curve
        point_list = ifc_file.create_entity(
            "IfcCartesianPointList2D",
            CoordList=points
        )
        
        # Create IfcIndexedPolyCurve for the profile shape
        indexed_curve = ifc_file.create_entity(
            "IfcIndexedPolyCurve",
            Points=point_list
        )
        
        # Create IfcOpenCrossProfileDef
        self.ifc_profile = ifc_file.create_entity(
            "IfcOpenCrossProfileDef",
            ProfileType="CURVE",
            ProfileName=self.name,
            Curve=indexed_curve,
            # Tags=self.component_type  # Optional: for filtering
        )
        
        # Create material profile if materials are defined
        if self.material_layers:
            # TODO: Create IfcMaterialProfileSet with layers
            # This will be implemented when material system is added
            pass
        
        return {
            'profile': self.ifc_profile,
            'material_profile': self.ifc_material_profile
        }
    
    def apply_constraint(self, station: float, parameter: str, value: float):
        """
        Apply a parametric constraint at a specific station.
        
        This allows components to vary along the alignment (e.g., widening,
        superelevation, different slopes).
        
        Args:
            station: Station where constraint applies
            parameter: Parameter name (e.g., "width", "cross_slope")
            value: New value at this station
        """
        # This will be enhanced with ConstraintManager in the main module
        if hasattr(self, parameter):
            setattr(self, parameter, value)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate component geometry and properties.
        
        Returns:
            (is_valid, error_messages) tuple
        """
        errors = []
        
        # Check width
        if self.width <= 0:
            errors.append(f"{self.name}: Width must be positive")
        
        # Check cross slope
        if abs(self.cross_slope) > 0.15:  # 15% is very steep
            errors.append(f"{self.name}: Cross slope {self.cross_slope*100:.1f}% is very steep")
        
        # Check material layers
        total_thickness = self.get_total_thickness()
        if total_thickness <= 0 and self.material_layers:
            errors.append(f"{self.name}: Material layer thickness must be positive")
        
        return (len(errors) == 0, errors)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', width={self.width:.2f}m, slope={self.cross_slope*100:.1f}%)"
