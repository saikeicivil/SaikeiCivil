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
Native IFC Cross-Section System
Professional road assembly management with IFC 4.3 export
"""

import bpy
import ifcopenshell
import ifcopenshell.guid
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
import math

# Import components (these will be in components/ subdirectory)
# from .components import AssemblyComponent, LaneComponent, ShoulderComponent, CurbComponent, DitchComponent


@dataclass
class ParametricConstraint:
    """
    Parametric constraint for varying component properties along alignment.
    
    Example: Widening a lane from 3.0m to 3.6m between stations 100-200
    """
    station: float  # Station where constraint applies
    component_name: str  # Name of component to modify
    parameter: str  # Parameter name (e.g., "width", "cross_slope")
    value: float  # New value at this station
    
    def __repr__(self) -> str:
        return f"Constraint(sta={self.station:.2f}, {self.component_name}.{self.parameter}={self.value})"


class ConstraintManager:
    """
    Manages parametric constraints for an assembly.
    
    Constraints allow components to vary along the alignment (widening,
    superelevation transitions, etc.)
    """
    
    def __init__(self):
        self.constraints: List[ParametricConstraint] = []
    
    def add_constraint(self, station: float, component_name: str, 
                      parameter: str, value: float):
        """Add a parametric constraint."""
        constraint = ParametricConstraint(station, component_name, parameter, value)
        self.constraints.append(constraint)
        # Keep constraints sorted by station
        self.constraints.sort(key=lambda c: c.station)
    
    def get_constraints_at_station(self, station: float) -> List[ParametricConstraint]:
        """Get all constraints that apply at a specific station."""
        # In a full implementation, this would interpolate between constraints
        # For now, return exact matches
        return [c for c in self.constraints if abs(c.station - station) < 0.01]
    
    def get_value_at_station(self, component_name: str, parameter: str, 
                            station: float, default_value: float) -> float:
        """
        Get the interpolated value of a parameter at a station.
        
        Args:
            component_name: Name of component
            parameter: Parameter name
            station: Query station
            default_value: Default value if no constraints
            
        Returns:
            Interpolated value
        """
        # Find constraints for this component and parameter
        relevant = [c for c in self.constraints 
                   if c.component_name == component_name and c.parameter == parameter]
        
        if not relevant:
            return default_value
        
        # Find bounding constraints
        before = [c for c in relevant if c.station <= station]
        after = [c for c in relevant if c.station > station]
        
        if not before:
            # Before first constraint, use default
            return default_value
        elif not after:
            # After last constraint, use last value
            return before[-1].value
        else:
            # Interpolate between constraints
            c1 = before[-1]
            c2 = after[0]
            
            if abs(c2.station - c1.station) < 0.01:
                return c1.value
            
            # Linear interpolation
            ratio = (station - c1.station) / (c2.station - c1.station)
            return c1.value + ratio * (c2.value - c1.value)


class RoadAssembly:
    """
    Complete road cross-section assembly.
    
    An assembly is a collection of components (lanes, shoulders, etc.) that
    together define the complete roadway cross-section. The assembly can
    vary along the alignment using parametric constraints.
    """
    
    def __init__(self, name: str = "Road Assembly"):
        """
        Initialize road assembly.
        
        Args:
            name: Assembly name (e.g., "Urban Arterial", "Rural Highway")
        """
        self.name = name
        self.components: List[Any] = []  # List of AssemblyComponents
        self.constraint_manager = ConstraintManager()
        
        # IFC properties
        self.ifc_profiles: List[Any] = []  # IfcOpenCrossProfileDef entities
        self.ifc_material_profile_set = None  # IfcMaterialProfileSet
        
    def add_component(self, component: Any, attach_to: Optional[Any] = None):
        """
        Add a component to the assembly.
        
        Args:
            component: AssemblyComponent to add
            attach_to: Component to attach to (None = centerline)
        """
        if attach_to is not None:
            component.attach_to = attach_to
            # Set offset based on attachment point
            if attach_to.side == "RIGHT":
                component.offset = attach_to.offset + attach_to.width
            else:
                component.offset = attach_to.offset + attach_to.width
        
        self.components.append(component)
    
    def remove_component(self, component: Any):
        """Remove a component from the assembly."""
        if component in self.components:
            self.components.remove(component)
    
    def get_component_by_name(self, name: str) -> Optional[Any]:
        """Find a component by name."""
        for component in self.components:
            if component.name == name:
                return component
        return None
    
    def calculate_section_points(self, station: float = 0.0) -> Dict[str, List[Tuple[float, float]]]:
        """
        Calculate all component points at a given station.
        
        Args:
            station: Station along alignment
            
        Returns:
            Dictionary mapping component names to their point lists
        """
        # Apply constraints at this station
        for component in self.components:
            # Check for constraints that affect this component
            for param in ['width', 'cross_slope', 'offset']:
                constrained_value = self.constraint_manager.get_value_at_station(
                    component.name, param, station, getattr(component, param, None)
                )
                if constrained_value is not None:
                    setattr(component, param, constrained_value)
        
        # Calculate points for each component
        result = {}
        for component in self.components:
            result[component.name] = component.calculate_points(station)
        
        return result
    
    def get_total_width(self, station: float = 0.0) -> float:
        """
        Calculate total width of assembly at a station.
        
        Returns:
            Total width in meters
        """
        if not self.components:
            return 0.0
        
        # Calculate all points
        all_points = self.calculate_section_points(station)
        
        # Find min and max offsets
        offsets = []
        for points in all_points.values():
            offsets.extend([p[0] for p in points])
        
        if offsets:
            return max(offsets) - min(offsets)
        return 0.0
    
    def add_constraint(self, station: float, component_name: str, 
                      parameter: str, value: float):
        """
        Add a parametric constraint to the assembly.
        
        Args:
            station: Station where constraint applies
            component_name: Name of component to modify
            parameter: Parameter name (e.g., "width", "cross_slope")
            value: New value at this station
        """
        self.constraint_manager.add_constraint(station, component_name, parameter, value)
    
    def to_ifc(self, ifc_file) -> Dict[str, Any]:
        """
        Export assembly to IFC entities.
        
        Creates:
        - IfcOpenCrossProfileDef for each component
        - IfcCompositeProfileDef to combine them
        - IfcMaterialProfileSet for materials
        
        Args:
            ifc_file: IfcOpenShell file object
            
        Returns:
            Dictionary with IFC entities
        """
        # Export each component
        self.ifc_profiles = []
        for component in self.components:
            component_ifc = component.to_ifc(ifc_file)
            self.ifc_profiles.append(component_ifc['profile'])
        
        # Create composite profile
        composite_profile = ifc_file.create_entity(
            "IfcCompositeProfileDef",
            ProfileType="AREA",
            ProfileName=self.name,
            Profiles=self.ifc_profiles
        )
        
        # TODO: Create IfcMaterialProfileSet with material layers
        # This will be implemented when material system is added
        
        return {
            'composite_profile': composite_profile,
            'profiles': self.ifc_profiles,
            'material_profile_set': self.ifc_material_profile_set
        }
    
    def validate(self, station: float = 0.0) -> Tuple[bool, List[str]]:
        """
        Validate the assembly.

        Checks:
        1. Individual component validation
        2. Component overlap detection (same offset range)
        3. Gap detection (missing coverage between components)

        Args:
            station: Station to validate at (for parametric assemblies)

        Returns:
            (is_valid, error_messages) tuple
        """
        errors = []

        # Validate each component
        for component in self.components:
            is_valid, component_errors = component.validate()
            errors.extend(component_errors)

        # Separate components by side
        left_components = [c for c in self.components if c.side == "LEFT"]
        right_components = [c for c in self.components if c.side == "RIGHT"]

        # Check overlaps and gaps for each side
        overlap_errors, gap_warnings = self._check_component_coverage(
            right_components, station, "RIGHT"
        )
        errors.extend(overlap_errors)

        overlap_errors, gap_warnings = self._check_component_coverage(
            left_components, station, "LEFT"
        )
        errors.extend(overlap_errors)

        return (len(errors) == 0, errors)

    def _check_component_coverage(
        self,
        components: List[Any],
        station: float,
        side: str
    ) -> Tuple[List[str], List[str]]:
        """
        Check for overlaps and gaps in component coverage.

        Args:
            components: List of components on one side
            station: Station to check at
            side: "LEFT" or "RIGHT"

        Returns:
            Tuple of (overlap_errors, gap_warnings)
        """
        errors = []
        warnings = []

        if len(components) < 2:
            return errors, warnings

        # Get extent (min/max offset) for each component
        extents = []
        for component in components:
            points = component.calculate_points(station)
            if points:
                offsets = [abs(p[0]) for p in points]  # Use absolute offset
                extents.append({
                    'name': component.name,
                    'min_offset': min(offsets),
                    'max_offset': max(offsets),
                    'component': component
                })

        # Sort by minimum offset
        extents.sort(key=lambda e: e['min_offset'])

        # Check for overlaps
        for i in range(len(extents) - 1):
            current = extents[i]
            next_ext = extents[i + 1]

            # Overlap: current max > next min (with small tolerance)
            overlap = current['max_offset'] - next_ext['min_offset']
            if overlap > 0.01:  # 1cm tolerance
                errors.append(
                    f"Component overlap on {side}: '{current['name']}' "
                    f"(offset {current['max_offset']:.3f}m) overlaps with "
                    f"'{next_ext['name']}' (starts at {next_ext['min_offset']:.3f}m) "
                    f"by {overlap:.3f}m"
                )

            # Gap: next min > current max (with tolerance)
            gap = next_ext['min_offset'] - current['max_offset']
            if gap > 0.05:  # 5cm tolerance for gaps
                warnings.append(
                    f"Gap on {side}: {gap:.3f}m gap between '{current['name']}' "
                    f"(ends at {current['max_offset']:.3f}m) and '{next_ext['name']}' "
                    f"(starts at {next_ext['min_offset']:.3f}m)"
                )

        return errors, warnings

    def validate_with_warnings(self, station: float = 0.0) -> Tuple[bool, List[str], List[str]]:
        """
        Validate the assembly with separate errors and warnings.

        Args:
            station: Station to validate at

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        is_valid, errors = self.validate(station)

        # Collect warnings from gap detection
        warnings = []
        left_components = [c for c in self.components if c.side == "LEFT"]
        right_components = [c for c in self.components if c.side == "RIGHT"]

        _, right_warnings = self._check_component_coverage(
            right_components, station, "RIGHT"
        )
        warnings.extend(right_warnings)

        _, left_warnings = self._check_component_coverage(
            left_components, station, "LEFT"
        )
        warnings.extend(left_warnings)

        return (is_valid, errors, warnings)
    
    def __repr__(self) -> str:
        return f"RoadAssembly(name='{self.name}', components={len(self.components)})"


class CrossSectionManager:
    """
    Main interface to the cross-section system.
    
    This class coordinates all cross-section operations:
    - Creating and managing assemblies
    - Template library
    - Station-based section queries
    - IFC export
    - Integration with alignment system
    """
    
    # Class variable for singleton instance
    _instance = None
    
    def __init__(self):
        """Initialize the cross-section manager."""
        self.assemblies: Dict[str, RoadAssembly] = {}
        self.active_assembly: Optional[RoadAssembly] = None
        
        # Station-based section assignments
        # Maps station ranges to assemblies (for varying sections along alignment)
        self.section_assignments: List[Tuple[float, float, str]] = []  # (start_sta, end_sta, assembly_name)
    
    @classmethod
    def get_instance(cls) -> 'CrossSectionManager':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = CrossSectionManager()
        return cls._instance
    
    def create_assembly(self, name: str) -> RoadAssembly:
        """
        Create a new assembly.
        
        Args:
            name: Assembly name
            
        Returns:
            New RoadAssembly instance
        """
        assembly = RoadAssembly(name)
        self.assemblies[name] = assembly
        
        if self.active_assembly is None:
            self.active_assembly = assembly
        
        return assembly
    
    def get_assembly(self, name: str) -> Optional[RoadAssembly]:
        """Get an assembly by name."""
        return self.assemblies.get(name)
    
    def delete_assembly(self, name: str):
        """Delete an assembly."""
        if name in self.assemblies:
            del self.assemblies[name]
            if self.active_assembly and self.active_assembly.name == name:
                self.active_assembly = None
    
    def set_active_assembly(self, name: str):
        """Set the active assembly."""
        assembly = self.get_assembly(name)
        if assembly:
            self.active_assembly = assembly
    
    def assign_section_to_range(self, start_station: float, end_station: float, assembly_name: str):
        """
        Assign an assembly to a station range.
        
        Args:
            start_station: Start station
            end_station: End station
            assembly_name: Name of assembly to use in this range
        """
        self.section_assignments.append((start_station, end_station, assembly_name))
        # Keep sorted by start station
        self.section_assignments.sort(key=lambda x: x[0])
    
    def get_assembly_at_station(self, station: float) -> Optional[RoadAssembly]:
        """
        Get the assembly that applies at a given station.
        
        Args:
            station: Query station
            
        Returns:
            RoadAssembly or None
        """
        # Check station assignments
        for start_sta, end_sta, assembly_name in self.section_assignments:
            if start_sta <= station <= end_sta:
                return self.get_assembly(assembly_name)
        
        # Default to active assembly
        return self.active_assembly
    
    def get_section_points_at_station(self, station: float) -> Optional[Dict[str, List[Tuple[float, float]]]]:
        """
        Get cross-section points at a station.
        
        Args:
            station: Query station
            
        Returns:
            Dictionary of component points or None
        """
        assembly = self.get_assembly_at_station(station)
        if assembly:
            return assembly.calculate_section_points(station)
        return None
    
    def export_to_ifc(self, ifc_file, alignment=None) -> List[Any]:
        """
        Export all assemblies to IFC.
        
        Args:
            ifc_file: IfcOpenShell file object
            alignment: Optional alignment to associate sections with
            
        Returns:
            List of IFC entities
        """
        ifc_entities = []
        
        for assembly in self.assemblies.values():
            assembly_ifc = assembly.to_ifc(ifc_file)
            ifc_entities.append(assembly_ifc['composite_profile'])
        
        return ifc_entities
    
    def __repr__(self) -> str:
        active_name = self.active_assembly.name if self.active_assembly else "None"
        return f"CrossSectionManager(assemblies={len(self.assemblies)}, active='{active_name}')"


# ==================== TEMPLATE LIBRARY ====================

class TemplateLibrary:
    """
    Standard road assembly templates based on AASHTO and common practice.
    """
    
    @staticmethod
    def create_two_lane_rural(name: str = "Two-Lane Rural Highway") -> RoadAssembly:
        """
        Create a standard two-lane rural highway assembly.
        
        Configuration:
        - Left shoulder: 1.8m paved
        - Left lane: 3.6m
        - Right lane: 3.6m
        - Right shoulder: 2.4m paved
        - Right ditch: 4:1 foreslope
        
        Returns:
            Configured RoadAssembly
        """
        from components import LaneComponent, ShoulderComponent, DitchComponent
        
        assembly = RoadAssembly(name)
        
        # Right side (build outward from centerline)
        right_lane = LaneComponent.create_standard_travel_lane("RIGHT")
        right_shoulder = ShoulderComponent.create_paved_shoulder("RIGHT", 2.4)
        right_ditch = DitchComponent.create_standard_ditch("RIGHT")
        
        assembly.add_component(right_lane)
        assembly.add_component(right_shoulder, attach_to=right_lane)
        assembly.add_component(right_ditch, attach_to=right_shoulder)
        
        # Left side
        left_lane = LaneComponent.create_standard_travel_lane("LEFT")
        left_shoulder = ShoulderComponent.create_paved_shoulder("LEFT", 1.8)
        left_ditch = DitchComponent.create_standard_ditch("LEFT")
        
        assembly.add_component(left_lane)
        assembly.add_component(left_shoulder, attach_to=left_lane)
        assembly.add_component(left_ditch, attach_to=left_shoulder)
        
        return assembly
    
    @staticmethod
    def create_four_lane_divided(name: str = "Four-Lane Divided Highway") -> RoadAssembly:
        """
        Create a four-lane divided highway assembly (one direction).
        
        Configuration:
        - Inside shoulder: 1.2m paved
        - Lane 1: 3.6m (inside)
        - Lane 2: 3.6m (outside)
        - Outside shoulder: 3.0m paved
        - Outside ditch: 4:1 foreslope
        
        Returns:
            Configured RoadAssembly
        """
        from components import LaneComponent, ShoulderComponent, DitchComponent
        
        assembly = RoadAssembly(name)
        
        # Inside (left) to outside (right)
        inside_shoulder = ShoulderComponent.create_paved_shoulder("LEFT", 1.2)
        lane1 = LaneComponent.create_standard_travel_lane("RIGHT")
        lane2 = LaneComponent.create_standard_travel_lane("RIGHT")
        outside_shoulder = ShoulderComponent.create_interstate_shoulder("RIGHT")
        outside_ditch = DitchComponent.create_standard_ditch("RIGHT")
        
        # Build from inside out
        assembly.add_component(inside_shoulder)
        assembly.add_component(lane1, attach_to=inside_shoulder)
        assembly.add_component(lane2, attach_to=lane1)
        assembly.add_component(outside_shoulder, attach_to=lane2)
        assembly.add_component(outside_ditch, attach_to=outside_shoulder)
        
        return assembly


# Module-level convenience functions
def get_manager() -> CrossSectionManager:
    """Get the CrossSectionManager singleton instance."""
    return CrossSectionManager.get_instance()
