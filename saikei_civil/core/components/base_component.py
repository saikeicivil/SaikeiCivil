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
Base Component for Cross-Section Assembly
Foundation class for all cross-section components (lanes, shoulders, curbs, etc.)

IFC 4.3 Compliance:
- Uses IfcOpenCrossProfileDef with HorizontalWidths, Widths, Slopes, Tags
- Tags enable interpolation between cross-sections at different stations
- IfcMaterialProfileSet for associating materials with profiles
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
    - IFC 4.3 export capability (IfcOpenCrossProfileDef)

    IFC Export Pattern:
        IfcOpenCrossProfileDef uses widths/slopes format, NOT explicit point coordinates.
        This allows proper interpolation between cross-sections at different stations.

        Example for a lane (single segment):
            HorizontalWidths=True
            Widths=[3.6]          # 3.6m wide
            Slopes=[-0.02]        # -2% cross slope
            Tags=['LANE_IN', 'LANE_OUT']  # 2 tags for 1 segment
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

        # Tag prefix for IFC interpolation - override in subclasses for custom naming
        self._tag_prefix = component_type[:3].upper()  # e.g., "LAN", "SHO", "CUR"

        # IFC properties
        self.ifc_profile = None  # IfcOpenCrossProfileDef
        self.ifc_material_profile = None  # IfcMaterialProfile
        self.ifc_material_profile_set = None  # IfcMaterialProfileSet
        
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

    def get_widths_slopes_tags(self, station: float = 0.0) -> Tuple[List[float], List[float], List[str]]:
        """
        Calculate widths, slopes, and tags for IfcOpenCrossProfileDef export.

        Converts the point-based geometry from calculate_points() into the
        widths/slopes format required by IFC 4.3 IfcOpenCrossProfileDef.

        Per IFC 4.3 specification:
        - HorizontalWidths=True means widths are measured horizontally
        - Slopes are dimensionless ratios (rise/run, e.g., -0.02 = -2%)
        - Tags identify each point for interpolation (N+1 tags for N segments)

        Args:
            station: Station along alignment

        Returns:
            Tuple of (widths, slopes, tags):
            - widths: List of horizontal segment widths
            - slopes: List of segment slopes as dimensionless ratios
            - tags: List of point identifiers (len = len(widths) + 1)
        """
        points = self.calculate_points(station)

        if len(points) < 2:
            return [], [], []

        widths = []
        slopes = []
        tags = []

        # Generate unique tags for each point
        side_prefix = "L" if self.side == "LEFT" else "R"

        for i, (offset, elevation) in enumerate(points):
            # Create tag for this point
            tag = f"{side_prefix}_{self._tag_prefix}_{i}"
            tags.append(tag)

            # Calculate width and slope for segment to next point
            if i < len(points) - 1:
                next_offset, next_elevation = points[i + 1]

                # Width is horizontal distance (always positive)
                segment_width = abs(next_offset - offset)
                widths.append(segment_width)

                # Slope is rise/run (dimensionless ratio)
                if segment_width > 0.0001:  # Avoid division by zero
                    slope = (next_elevation - elevation) / segment_width
                else:
                    # Vertical segment - use large slope value
                    slope = 1000.0 if (next_elevation - elevation) > 0 else -1000.0
                slopes.append(slope)

        return widths, slopes, tags

    def to_ifc(self, ifc_file) -> Dict[str, Any]:
        """
        Export this component to IFC 4.3 entities.

        Creates:
        - IfcOpenCrossProfileDef for geometry (using Widths/Slopes/Tags format)
        - IfcMaterialProfileSet for material associations

        Per IFC 4.3 specification, IfcOpenCrossProfileDef uses:
        - HorizontalWidths: True (widths measured horizontally)
        - Widths: List of segment widths
        - Slopes: List of segment slopes (dimensionless ratios)
        - Tags: List of point identifiers for interpolation

        Args:
            ifc_file: IfcOpenShell file object

        Returns:
            Dictionary with 'profile', 'material_profile_set' keys
        """
        # Get widths, slopes, and tags from geometry
        widths, slopes, tags = self.get_widths_slopes_tags()

        if not widths:
            # Fallback for components with no valid geometry
            return {
                'profile': None,
                'material_profile_set': None
            }

        # Create IfcOpenCrossProfileDef (IFC 4.3 compliant)
        self.ifc_profile = ifc_file.create_entity(
            "IfcOpenCrossProfileDef",
            ProfileType="CURVE",
            ProfileName=self.name,
            HorizontalWidths=True,
            Widths=widths,
            Slopes=slopes,
            Tags=tags
        )

        # Create material profile set if materials are defined
        if self.material_layers:
            self.ifc_material_profile_set = self._create_material_profile_set(ifc_file)

        return {
            'profile': self.ifc_profile,
            'material_profile_set': self.ifc_material_profile_set
        }

    def _create_material_profile_set(self, ifc_file) -> Any:
        """
        Create IfcMaterialProfileSet for this component's materials.

        Args:
            ifc_file: IfcOpenShell file object

        Returns:
            IfcMaterialProfileSet entity
        """
        material_profiles = []

        for material_name, thickness in self.material_layers:
            # Create IfcMaterial for each layer
            material = ifc_file.create_entity(
                "IfcMaterial",
                Name=material_name
            )

            # Create IfcMaterialProfile linking material to profile
            # Note: Each layer could have its own profile, but for simplicity
            # we link all to the main component profile
            mat_profile = ifc_file.create_entity(
                "IfcMaterialProfile",
                Name=f"{self.name} - {material_name}",
                Material=material,
                Profile=self.ifc_profile
            )
            material_profiles.append(mat_profile)

        # Create IfcMaterialProfileSet containing all material profiles
        profile_set = ifc_file.create_entity(
            "IfcMaterialProfileSet",
            Name=f"{self.name} Materials",
            MaterialProfiles=material_profiles
        )

        return profile_set

    def to_ifc_with_arbitrary_profile(self, ifc_file) -> Dict[str, Any]:
        """
        Alternative IFC export using IfcArbitraryClosedProfileDef.

        This method creates closed profiles suitable for solid geometry.
        Use this when you need to create IfcSectionedSolidHorizontal with
        closed cross-sections.

        Args:
            ifc_file: IfcOpenShell file object

        Returns:
            Dictionary with 'profile', 'material_profile_set' keys
        """
        # Calculate geometry points
        points = self.calculate_points()

        if len(points) < 2:
            return {'profile': None, 'material_profile_set': None}

        # Get total thickness for creating closed profile
        thickness = self.get_total_thickness()
        if thickness <= 0:
            thickness = 0.1  # Default 100mm if no materials defined

        # Create closed profile by adding bottom points
        closed_points = list(points)

        # Add bottom points in reverse order
        for offset, elevation in reversed(points):
            closed_points.append((offset, elevation - thickness))

        # Close the loop
        closed_points.append(closed_points[0])

        # Create tags for closed profile
        widths, slopes, tags = self.get_widths_slopes_tags()
        closed_tags = tags + [f"{t}_BTM" for t in reversed(tags)] + [tags[0]]

        # Create point list
        point_list = ifc_file.create_entity(
            "IfcCartesianPointList2D",
            CoordList=closed_points,
            TagList=closed_tags
        )

        # Create indexed polycurve
        curve = ifc_file.create_entity(
            "IfcIndexedPolyCurve",
            Points=point_list
        )

        # Create arbitrary closed profile
        profile = ifc_file.create_entity(
            "IfcArbitraryClosedProfileDef",
            ProfileType="AREA",
            ProfileName=self.name,
            OuterCurve=curve
        )

        # Create material profile set
        material_profile_set = None
        if self.material_layers:
            material_profile_set = self._create_material_profile_set(ifc_file)

        return {
            'profile': profile,
            'material_profile_set': material_profile_set
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
