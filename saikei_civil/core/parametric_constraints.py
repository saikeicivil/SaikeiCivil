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
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================

"""
Parametric Constraints Module
=============================

OpenRoads-style parametric constraints for cross-section variation along alignments.

This module is part of the CORE layer - pure Python with NO Blender dependencies.
It can be tested without Blender running using pytest.

Constraint Types:
    POINT: Single station override (e.g., width = 4.0m at station 500)
    RANGE: Station range with interpolation (e.g., width transitions from 3.6m to 4.2m
           between stations 100-200)

Interpolation Types:
    LINEAR: Linear interpolation between start and end values
    SMOOTH: Smooth transition using smoothstep function
    STEP: Instant change at end station (no interpolation)

Example Usage:
    >>> from saikei_civil.core.parametric_constraints import (
    ...     ParametricConstraint, ConstraintManager, ConstraintType, InterpolationType
    ... )
    >>>
    >>> # Create a range constraint for lane widening
    >>> constraint = ParametricConstraint(
    ...     id="lane_widening_001",
    ...     component_name="Right Travel Lane",
    ...     parameter_name="width",
    ...     constraint_type=ConstraintType.RANGE,
    ...     start_station=100.0,
    ...     end_station=200.0,
    ...     start_value=3.6,
    ...     end_value=4.2,
    ...     interpolation=InterpolationType.LINEAR,
    ...     description="Turn lane widening"
    ... )
    >>>
    >>> # Create manager and add constraint
    >>> manager = ConstraintManager()
    >>> manager.add_constraint(constraint)
    >>>
    >>> # Query value at station 150 (midpoint)
    >>> value = manager.get_effective_value("Right Travel Lane", "width", 150.0, 3.6)
    >>> print(f"Width at sta 150: {value}")  # 3.9m (midpoint)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum
import uuid


class ConstraintType(Enum):
    """Type of parametric constraint."""
    POINT = "POINT"   # Single station override
    RANGE = "RANGE"   # Station range with interpolation


class InterpolationType(Enum):
    """Interpolation method for range constraints."""
    LINEAR = "LINEAR"   # Linear interpolation (default)
    SMOOTH = "SMOOTH"   # Smooth transition using smoothstep
    STEP = "STEP"       # Instant change at end station


@dataclass
class ParametricConstraint:
    """
    Parametric constraint for cross-section parameter variation.

    Allows overriding any component parameter at specific stations
    or across station ranges with interpolation.

    This is a CORE layer class - no Blender dependencies.

    Attributes:
        id: Unique identifier for this constraint
        component_name: Name of component to modify (e.g., "Right Travel Lane")
        parameter_name: Parameter to modify (e.g., "width", "cross_slope", "offset")
        constraint_type: POINT for single station, RANGE for interpolated range
        start_station: Station where constraint begins
        end_station: Station where constraint ends (same as start for POINT)
        start_value: Parameter value at start station
        end_value: Parameter value at end station (same as start for POINT)
        interpolation: Interpolation method (LINEAR, SMOOTH, STEP)
        description: Optional user notes about this constraint
        enabled: Whether constraint is active (can be disabled without deleting)
    """
    id: str
    component_name: str
    parameter_name: str
    constraint_type: ConstraintType
    start_station: float
    end_station: float
    start_value: float
    end_value: float
    interpolation: InterpolationType = InterpolationType.LINEAR
    description: str = ""
    enabled: bool = True

    def __post_init__(self):
        """Validate and normalize constraint after initialization."""
        # For POINT constraints, ensure end values match start values
        if self.constraint_type == ConstraintType.POINT:
            self.end_station = self.start_station
            self.end_value = self.start_value

        # Ensure start_station <= end_station for RANGE
        if self.start_station > self.end_station:
            self.start_station, self.end_station = self.end_station, self.start_station
            self.start_value, self.end_value = self.end_value, self.start_value

    def applies_to_station(self, station: float) -> bool:
        """
        Check if this constraint is active at the given station.

        Args:
            station: Query station in meters

        Returns:
            True if constraint applies at this station
        """
        if not self.enabled:
            return False
        return self.start_station <= station <= self.end_station

    def get_value_at_station(self, station: float) -> Optional[float]:
        """
        Get the interpolated parameter value at a station.

        Args:
            station: Query station in meters

        Returns:
            Interpolated value, or None if constraint doesn't apply
        """
        if not self.applies_to_station(station):
            return None

        # POINT constraint - return the value
        if self.constraint_type == ConstraintType.POINT:
            return self.start_value

        # RANGE constraint - interpolate
        # Handle case where start == end (point-like range)
        station_range = self.end_station - self.start_station
        if station_range < 0.001:  # Less than 1mm
            return self.start_value

        # Calculate interpolation parameter t (0 to 1)
        t = (station - self.start_station) / station_range
        t = max(0.0, min(1.0, t))  # Clamp to [0, 1]

        if self.interpolation == InterpolationType.STEP:
            # Instant change at end station
            return self.start_value if t < 1.0 else self.end_value

        elif self.interpolation == InterpolationType.SMOOTH:
            # Smoothstep interpolation: t = t * t * (3 - 2 * t)
            t = t * t * (3.0 - 2.0 * t)

        # LINEAR is default (no t modification needed)

        # Lerp between start and end values
        return self.start_value + t * (self.end_value - self.start_value)

    def to_dict(self) -> dict:
        """
        Serialize constraint to dictionary for IFC storage.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            'id': self.id,
            'component_name': self.component_name,
            'parameter_name': self.parameter_name,
            'constraint_type': self.constraint_type.value,
            'start_station': self.start_station,
            'end_station': self.end_station,
            'start_value': self.start_value,
            'end_value': self.end_value,
            'interpolation': self.interpolation.value,
            'description': self.description,
            'enabled': self.enabled
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ParametricConstraint':
        """
        Deserialize constraint from dictionary.

        Args:
            data: Dictionary from to_dict() or IFC property set

        Returns:
            New ParametricConstraint instance
        """
        return cls(
            id=data['id'],
            component_name=data['component_name'],
            parameter_name=data['parameter_name'],
            constraint_type=ConstraintType(data['constraint_type']),
            start_station=float(data['start_station']),
            end_station=float(data['end_station']),
            start_value=float(data['start_value']),
            end_value=float(data['end_value']),
            interpolation=InterpolationType(data.get('interpolation', 'LINEAR')),
            description=data.get('description', ''),
            enabled=data.get('enabled', True)
        )

    @classmethod
    def create_point_constraint(
        cls,
        component_name: str,
        parameter_name: str,
        station: float,
        value: float,
        description: str = "",
        constraint_id: Optional[str] = None
    ) -> 'ParametricConstraint':
        """
        Factory method to create a point constraint.

        Args:
            component_name: Name of component to modify
            parameter_name: Parameter to modify
            station: Station where constraint applies
            value: Parameter value at this station
            description: Optional description
            constraint_id: Optional ID (generated if not provided)

        Returns:
            New ParametricConstraint configured as POINT type
        """
        return cls(
            id=constraint_id or str(uuid.uuid4()),
            component_name=component_name,
            parameter_name=parameter_name,
            constraint_type=ConstraintType.POINT,
            start_station=station,
            end_station=station,
            start_value=value,
            end_value=value,
            description=description
        )

    @classmethod
    def create_range_constraint(
        cls,
        component_name: str,
        parameter_name: str,
        start_station: float,
        end_station: float,
        start_value: float,
        end_value: float,
        interpolation: InterpolationType = InterpolationType.LINEAR,
        description: str = "",
        constraint_id: Optional[str] = None
    ) -> 'ParametricConstraint':
        """
        Factory method to create a range constraint.

        Args:
            component_name: Name of component to modify
            parameter_name: Parameter to modify
            start_station: Station where transition begins
            end_station: Station where transition ends
            start_value: Parameter value at start
            end_value: Parameter value at end
            interpolation: Interpolation method
            description: Optional description
            constraint_id: Optional ID (generated if not provided)

        Returns:
            New ParametricConstraint configured as RANGE type
        """
        return cls(
            id=constraint_id or str(uuid.uuid4()),
            component_name=component_name,
            parameter_name=parameter_name,
            constraint_type=ConstraintType.RANGE,
            start_station=start_station,
            end_station=end_station,
            start_value=start_value,
            end_value=end_value,
            interpolation=interpolation,
            description=description
        )

    def __repr__(self) -> str:
        if self.constraint_type == ConstraintType.POINT:
            return (f"ParametricConstraint(POINT, {self.component_name}.{self.parameter_name}"
                    f"={self.start_value} @ sta {self.start_station:.2f})")
        else:
            return (f"ParametricConstraint(RANGE, {self.component_name}.{self.parameter_name}"
                    f"={self.start_value}->{self.end_value} @ sta {self.start_station:.2f}"
                    f"-{self.end_station:.2f}, {self.interpolation.value})")


@dataclass
class ConstraintManager:
    """
    Manages all parametric constraints for a corridor/assembly.

    Provides methods for:
    - Adding/removing/updating constraints
    - Resolving effective values at stations (with constraint priority)
    - Validation
    - Serialization for IFC storage

    This is a CORE layer class - no Blender dependencies.

    Constraint Resolution:
        When multiple constraints affect the same parameter at a station,
        later constraints in the list take priority (last-write-wins).
        Constraints are automatically sorted by start_station.
    """
    constraints: List[ParametricConstraint] = field(default_factory=list)

    def add_constraint(self, constraint: ParametricConstraint) -> None:
        """
        Add a constraint and maintain station order.

        Args:
            constraint: Constraint to add
        """
        self.constraints.append(constraint)
        self._sort_constraints()

    def remove_constraint(self, constraint_id: str) -> bool:
        """
        Remove a constraint by its ID.

        Args:
            constraint_id: ID of constraint to remove

        Returns:
            True if removed, False if not found
        """
        for i, c in enumerate(self.constraints):
            if c.id == constraint_id:
                del self.constraints[i]
                return True
        return False

    def get_constraint(self, constraint_id: str) -> Optional[ParametricConstraint]:
        """
        Get a constraint by its ID.

        Args:
            constraint_id: ID of constraint to find

        Returns:
            Constraint or None if not found
        """
        for c in self.constraints:
            if c.id == constraint_id:
                return c
        return None

    def update_constraint(self, constraint_id: str, **kwargs) -> bool:
        """
        Update constraint properties.

        Args:
            constraint_id: ID of constraint to update
            **kwargs: Properties to update

        Returns:
            True if updated, False if not found
        """
        constraint = self.get_constraint(constraint_id)
        if not constraint:
            return False

        for key, value in kwargs.items():
            if hasattr(constraint, key):
                setattr(constraint, key, value)

        # Re-sort in case stations changed
        self._sort_constraints()
        return True

    def _sort_constraints(self) -> None:
        """Sort constraints by start station."""
        self.constraints.sort(key=lambda c: c.start_station)

    def get_constraints_at_station(self, station: float) -> List[ParametricConstraint]:
        """
        Get all active constraints at a station.

        Args:
            station: Query station in meters

        Returns:
            List of constraints that apply at this station
        """
        return [c for c in self.constraints if c.applies_to_station(station)]

    def get_constraints_for_component(
        self,
        component_name: str,
        parameter_name: Optional[str] = None
    ) -> List[ParametricConstraint]:
        """
        Get all constraints for a component.

        Args:
            component_name: Name of component
            parameter_name: Optional parameter to filter by

        Returns:
            List of matching constraints
        """
        result = [c for c in self.constraints if c.component_name == component_name]
        if parameter_name:
            result = [c for c in result if c.parameter_name == parameter_name]
        return result

    def get_effective_value(
        self,
        component_name: str,
        parameter_name: str,
        station: float,
        default_value: float
    ) -> float:
        """
        Get effective parameter value at station.

        Applies all relevant constraints in order (last wins).

        Args:
            component_name: Name of component
            parameter_name: Parameter to query
            station: Query station in meters
            default_value: Default value if no constraints apply

        Returns:
            Effective parameter value
        """
        value = default_value

        for constraint in self.constraints:
            if (constraint.component_name == component_name and
                constraint.parameter_name == parameter_name):

                constraint_value = constraint.get_value_at_station(station)
                if constraint_value is not None:
                    value = constraint_value

        return value

    def get_modified_parameters(
        self,
        station: float
    ) -> Dict[Tuple[str, str], float]:
        """
        Get all parameters that are modified at a station.

        Args:
            station: Query station in meters

        Returns:
            Dictionary mapping (component_name, parameter_name) to value
        """
        active = self.get_constraints_at_station(station)
        modified = {}

        for constraint in active:
            key = (constraint.component_name, constraint.parameter_name)
            value = constraint.get_value_at_station(station)
            if value is not None:
                modified[key] = value

        return modified

    def get_station_range(self) -> Tuple[float, float]:
        """
        Get the station range covered by all constraints.

        Returns:
            (min_station, max_station) tuple, or (0, 0) if no constraints
        """
        if not self.constraints:
            return (0.0, 0.0)

        min_sta = min(c.start_station for c in self.constraints)
        max_sta = max(c.end_station for c in self.constraints)
        return (min_sta, max_sta)

    def validate(self) -> List[str]:
        """
        Validate all constraints.

        Returns:
            List of validation error/warning messages (empty if valid)
        """
        issues = []

        for c in self.constraints:
            # Check station order
            if c.start_station > c.end_station:
                issues.append(
                    f"Constraint '{c.id}': start_station ({c.start_station}) > "
                    f"end_station ({c.end_station})"
                )

            # Check POINT constraint consistency
            if c.constraint_type == ConstraintType.POINT:
                if c.start_station != c.end_station:
                    issues.append(
                        f"Constraint '{c.id}': POINT constraint has different "
                        f"start/end stations"
                    )
                if c.start_value != c.end_value:
                    issues.append(
                        f"Constraint '{c.id}': POINT constraint has different "
                        f"start/end values"
                    )

            # Check for empty component/parameter names
            if not c.component_name:
                issues.append(f"Constraint '{c.id}': empty component_name")
            if not c.parameter_name:
                issues.append(f"Constraint '{c.id}': empty parameter_name")

        return issues

    def clear(self) -> None:
        """Remove all constraints."""
        self.constraints.clear()

    def to_list(self) -> List[dict]:
        """
        Serialize all constraints to list of dictionaries.

        Returns:
            List of constraint dictionaries for JSON serialization
        """
        return [c.to_dict() for c in self.constraints]

    @classmethod
    def from_list(cls, data: List[dict]) -> 'ConstraintManager':
        """
        Deserialize constraints from list of dictionaries.

        Args:
            data: List of constraint dictionaries

        Returns:
            New ConstraintManager with loaded constraints
        """
        manager = cls()
        for item in data:
            try:
                constraint = ParametricConstraint.from_dict(item)
                manager.add_constraint(constraint)
            except (KeyError, ValueError) as e:
                # Log warning but continue loading other constraints
                print(f"Warning: Failed to load constraint: {e}")
        return manager

    def __len__(self) -> int:
        return len(self.constraints)

    def __iter__(self):
        return iter(self.constraints)

    def __repr__(self) -> str:
        return f"ConstraintManager(constraints={len(self.constraints)})"
