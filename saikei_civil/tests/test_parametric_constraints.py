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
Unit Tests for Parametric Constraints Module
=============================================

These tests verify the CORE layer constraint system without requiring Blender.
Run with: pytest test_parametric_constraints.py

Tests cover:
- ParametricConstraint dataclass creation and methods
- Point constraints (single station)
- Range constraints (interpolation)
- ConstraintManager add/remove/query
- Constraint resolution (last-write-wins)
- Serialization (to_dict/from_dict)
- Validation
"""

import sys
import os
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parametric_constraints import (
    ParametricConstraint,
    ConstraintManager,
    ConstraintType,
    InterpolationType,
)


class TestParametricConstraint:
    """Tests for ParametricConstraint dataclass."""

    def test_point_constraint_creation(self):
        """Test creating a point constraint."""
        constraint = ParametricConstraint.create_point_constraint(
            component_name="Right Travel Lane",
            parameter_name="width",
            station=100.0,
            value=4.0,
            description="Test point constraint"
        )

        assert constraint.constraint_type == ConstraintType.POINT
        assert constraint.component_name == "Right Travel Lane"
        assert constraint.parameter_name == "width"
        assert constraint.start_station == 100.0
        assert constraint.end_station == 100.0  # Same as start for POINT
        assert constraint.start_value == 4.0
        assert constraint.end_value == 4.0  # Same as start for POINT
        assert constraint.enabled is True

    def test_range_constraint_creation(self):
        """Test creating a range constraint."""
        constraint = ParametricConstraint.create_range_constraint(
            component_name="Right Travel Lane",
            parameter_name="width",
            start_station=100.0,
            end_station=200.0,
            start_value=3.6,
            end_value=4.2,
            interpolation=InterpolationType.LINEAR,
            description="Lane widening"
        )

        assert constraint.constraint_type == ConstraintType.RANGE
        assert constraint.start_station == 100.0
        assert constraint.end_station == 200.0
        assert constraint.start_value == 3.6
        assert constraint.end_value == 4.2
        assert constraint.interpolation == InterpolationType.LINEAR

    def test_applies_to_station(self):
        """Test applies_to_station method."""
        constraint = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="width",
            start_station=100.0,
            end_station=200.0,
            start_value=3.6,
            end_value=4.2
        )

        # Within range
        assert constraint.applies_to_station(100.0) is True
        assert constraint.applies_to_station(150.0) is True
        assert constraint.applies_to_station(200.0) is True

        # Outside range
        assert constraint.applies_to_station(99.0) is False
        assert constraint.applies_to_station(201.0) is False

        # Disabled constraint
        constraint.enabled = False
        assert constraint.applies_to_station(150.0) is False

    def test_linear_interpolation(self):
        """Test linear interpolation for range constraints."""
        constraint = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="width",
            start_station=100.0,
            end_station=200.0,
            start_value=3.6,
            end_value=4.2,
            interpolation=InterpolationType.LINEAR
        )

        # At start
        assert constraint.get_value_at_station(100.0) == 3.6

        # At end
        assert constraint.get_value_at_station(200.0) == 4.2

        # At midpoint (should be 3.9)
        value = constraint.get_value_at_station(150.0)
        assert abs(value - 3.9) < 0.001

        # At 25%
        value = constraint.get_value_at_station(125.0)
        assert abs(value - 3.75) < 0.001

        # At 75%
        value = constraint.get_value_at_station(175.0)
        assert abs(value - 4.05) < 0.001

    def test_smooth_interpolation(self):
        """Test smooth (smoothstep) interpolation."""
        constraint = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="cross_slope",
            start_station=100.0,
            end_station=200.0,
            start_value=0.02,
            end_value=-0.04,
            interpolation=InterpolationType.SMOOTH
        )

        # At endpoints
        assert constraint.get_value_at_station(100.0) == 0.02
        assert constraint.get_value_at_station(200.0) == -0.04

        # Midpoint should still be midpoint (smoothstep(0.5) = 0.5)
        value = constraint.get_value_at_station(150.0)
        expected = 0.02 + 0.5 * (-0.04 - 0.02)  # -0.01
        assert abs(value - expected) < 0.001

    def test_step_interpolation(self):
        """Test step interpolation (instant change at end)."""
        constraint = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="width",
            start_station=100.0,
            end_station=200.0,
            start_value=3.6,
            end_value=4.2,
            interpolation=InterpolationType.STEP
        )

        # Before end - should be start value
        assert constraint.get_value_at_station(100.0) == 3.6
        assert constraint.get_value_at_station(150.0) == 3.6
        assert constraint.get_value_at_station(199.99) == 3.6

        # At end - should be end value
        assert constraint.get_value_at_station(200.0) == 4.2

    def test_point_constraint_value(self):
        """Test point constraint returns correct value."""
        constraint = ParametricConstraint.create_point_constraint(
            component_name="Lane",
            parameter_name="width",
            station=100.0,
            value=4.5
        )

        # At the exact station
        assert constraint.get_value_at_station(100.0) == 4.5

        # Not at station
        assert constraint.get_value_at_station(99.0) is None
        assert constraint.get_value_at_station(101.0) is None

    def test_serialization(self):
        """Test to_dict and from_dict round-trip."""
        original = ParametricConstraint.create_range_constraint(
            component_name="Right Shoulder",
            parameter_name="width",
            start_station=50.0,
            end_station=150.0,
            start_value=2.4,
            end_value=3.0,
            interpolation=InterpolationType.SMOOTH,
            description="Shoulder widening for turn lane"
        )
        original.enabled = False

        # Serialize to dict
        data = original.to_dict()

        # Verify dict structure
        assert data['component_name'] == "Right Shoulder"
        assert data['constraint_type'] == "RANGE"
        assert data['interpolation'] == "SMOOTH"
        assert data['enabled'] is False

        # Deserialize from dict
        restored = ParametricConstraint.from_dict(data)

        # Verify all properties match
        assert restored.id == original.id
        assert restored.component_name == original.component_name
        assert restored.parameter_name == original.parameter_name
        assert restored.constraint_type == original.constraint_type
        assert restored.start_station == original.start_station
        assert restored.end_station == original.end_station
        assert restored.start_value == original.start_value
        assert restored.end_value == original.end_value
        assert restored.interpolation == original.interpolation
        assert restored.description == original.description
        assert restored.enabled == original.enabled

    def test_json_serialization(self):
        """Test JSON serialization via to_dict."""
        constraint = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="width",
            start_station=0.0,
            end_station=100.0,
            start_value=3.6,
            end_value=4.0
        )

        # Should be JSON serializable
        json_str = json.dumps(constraint.to_dict())
        assert isinstance(json_str, str)

        # Should deserialize back
        data = json.loads(json_str)
        restored = ParametricConstraint.from_dict(data)
        assert restored.component_name == "Lane"


class TestConstraintManager:
    """Tests for ConstraintManager class."""

    def test_add_constraint(self):
        """Test adding constraints."""
        manager = ConstraintManager()

        constraint1 = ParametricConstraint.create_point_constraint(
            component_name="Lane",
            parameter_name="width",
            station=100.0,
            value=4.0
        )
        constraint2 = ParametricConstraint.create_point_constraint(
            component_name="Lane",
            parameter_name="width",
            station=50.0,
            value=3.8
        )

        manager.add_constraint(constraint1)
        manager.add_constraint(constraint2)

        assert len(manager) == 2

        # Should be sorted by station
        assert manager.constraints[0].start_station == 50.0
        assert manager.constraints[1].start_station == 100.0

    def test_remove_constraint(self):
        """Test removing constraints by ID."""
        manager = ConstraintManager()

        constraint = ParametricConstraint.create_point_constraint(
            component_name="Lane",
            parameter_name="width",
            station=100.0,
            value=4.0
        )
        manager.add_constraint(constraint)

        assert len(manager) == 1

        # Remove by ID
        result = manager.remove_constraint(constraint.id)
        assert result is True
        assert len(manager) == 0

        # Remove non-existent
        result = manager.remove_constraint("nonexistent")
        assert result is False

    def test_get_constraint(self):
        """Test getting constraint by ID."""
        manager = ConstraintManager()

        constraint = ParametricConstraint.create_point_constraint(
            component_name="Lane",
            parameter_name="width",
            station=100.0,
            value=4.0
        )
        manager.add_constraint(constraint)

        # Get existing
        found = manager.get_constraint(constraint.id)
        assert found is constraint

        # Get non-existent
        found = manager.get_constraint("nonexistent")
        assert found is None

    def test_get_effective_value_single_constraint(self):
        """Test effective value with single constraint."""
        manager = ConstraintManager()

        constraint = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="width",
            start_station=100.0,
            end_station=200.0,
            start_value=3.6,
            end_value=4.2
        )
        manager.add_constraint(constraint)

        # Before constraint
        value = manager.get_effective_value("Lane", "width", 50.0, 3.6)
        assert value == 3.6  # Default

        # During constraint (midpoint)
        value = manager.get_effective_value("Lane", "width", 150.0, 3.6)
        assert abs(value - 3.9) < 0.001

        # After constraint
        value = manager.get_effective_value("Lane", "width", 250.0, 3.6)
        assert value == 3.6  # Default

    def test_get_effective_value_multiple_constraints(self):
        """Test effective value with overlapping constraints (last wins)."""
        manager = ConstraintManager()

        # First constraint: width = 4.0 from sta 100-200
        constraint1 = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="width",
            start_station=100.0,
            end_station=200.0,
            start_value=4.0,
            end_value=4.0
        )
        manager.add_constraint(constraint1)

        # Second constraint: width = 4.5 from sta 150-250 (overlaps)
        constraint2 = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="width",
            start_station=150.0,
            end_station=250.0,
            start_value=4.5,
            end_value=4.5
        )
        manager.add_constraint(constraint2)

        # At sta 125 - only first constraint applies
        value = manager.get_effective_value("Lane", "width", 125.0, 3.6)
        assert value == 4.0

        # At sta 175 - both apply, second wins (last-write-wins)
        value = manager.get_effective_value("Lane", "width", 175.0, 3.6)
        assert value == 4.5

        # At sta 225 - only second constraint applies
        value = manager.get_effective_value("Lane", "width", 225.0, 3.6)
        assert value == 4.5

    def test_get_constraints_for_component(self):
        """Test filtering constraints by component."""
        manager = ConstraintManager()

        lane_constraint = ParametricConstraint.create_point_constraint(
            component_name="Lane",
            parameter_name="width",
            station=100.0,
            value=4.0
        )
        shoulder_constraint = ParametricConstraint.create_point_constraint(
            component_name="Shoulder",
            parameter_name="width",
            station=100.0,
            value=3.0
        )
        manager.add_constraint(lane_constraint)
        manager.add_constraint(shoulder_constraint)

        lane_constraints = manager.get_constraints_for_component("Lane")
        assert len(lane_constraints) == 1
        assert lane_constraints[0].component_name == "Lane"

        shoulder_constraints = manager.get_constraints_for_component("Shoulder")
        assert len(shoulder_constraints) == 1

    def test_get_modified_parameters(self):
        """Test getting all modified parameters at a station."""
        manager = ConstraintManager()

        constraint1 = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="width",
            start_station=100.0,
            end_station=200.0,
            start_value=3.6,
            end_value=4.2
        )
        constraint2 = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="cross_slope",
            start_station=100.0,
            end_station=200.0,
            start_value=0.02,
            end_value=-0.04
        )
        manager.add_constraint(constraint1)
        manager.add_constraint(constraint2)

        # At station 150 (midpoint)
        modified = manager.get_modified_parameters(150.0)

        assert len(modified) == 2
        assert ("Lane", "width") in modified
        assert ("Lane", "cross_slope") in modified
        assert abs(modified[("Lane", "width")] - 3.9) < 0.001

    def test_validation(self):
        """Test constraint validation."""
        manager = ConstraintManager()

        # Valid constraint
        valid = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="width",
            start_station=100.0,
            end_station=200.0,
            start_value=3.6,
            end_value=4.2
        )
        manager.add_constraint(valid)

        issues = manager.validate()
        assert len(issues) == 0

        # Add constraint with empty component name
        invalid = ParametricConstraint(
            id="invalid",
            component_name="",
            parameter_name="width",
            constraint_type=ConstraintType.POINT,
            start_station=100.0,
            end_station=100.0,
            start_value=4.0,
            end_value=4.0
        )
        manager.add_constraint(invalid)

        issues = manager.validate()
        assert len(issues) > 0
        assert any("empty component_name" in issue for issue in issues)

    def test_serialization_round_trip(self):
        """Test manager serialization and deserialization."""
        manager = ConstraintManager()

        constraint1 = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="width",
            start_station=100.0,
            end_station=200.0,
            start_value=3.6,
            end_value=4.2
        )
        constraint2 = ParametricConstraint.create_point_constraint(
            component_name="Shoulder",
            parameter_name="width",
            station=150.0,
            value=3.0
        )
        manager.add_constraint(constraint1)
        manager.add_constraint(constraint2)

        # Serialize
        data = manager.to_list()
        assert len(data) == 2

        # JSON round-trip
        json_str = json.dumps(data)
        data_restored = json.loads(json_str)

        # Deserialize
        restored = ConstraintManager.from_list(data_restored)

        assert len(restored) == 2
        assert restored.constraints[0].component_name == "Lane"
        assert restored.constraints[1].component_name == "Shoulder"

    def test_clear(self):
        """Test clearing all constraints."""
        manager = ConstraintManager()

        for i in range(5):
            constraint = ParametricConstraint.create_point_constraint(
                component_name="Lane",
                parameter_name="width",
                station=float(i * 100),
                value=3.6 + i * 0.1
            )
            manager.add_constraint(constraint)

        assert len(manager) == 5

        manager.clear()

        assert len(manager) == 0

    def test_station_range(self):
        """Test getting station range covered by constraints."""
        manager = ConstraintManager()

        # Empty manager
        min_sta, max_sta = manager.get_station_range()
        assert min_sta == 0.0
        assert max_sta == 0.0

        # Add constraints
        constraint1 = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="width",
            start_station=100.0,
            end_station=200.0,
            start_value=3.6,
            end_value=4.0
        )
        constraint2 = ParametricConstraint.create_range_constraint(
            component_name="Shoulder",
            parameter_name="width",
            start_station=50.0,
            end_station=300.0,
            start_value=2.4,
            end_value=3.0
        )
        manager.add_constraint(constraint1)
        manager.add_constraint(constraint2)

        min_sta, max_sta = manager.get_station_range()
        assert min_sta == 50.0
        assert max_sta == 300.0


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_length_range(self):
        """Test range constraint with zero length (same start/end station)."""
        constraint = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="width",
            start_station=100.0,
            end_station=100.0,
            start_value=3.6,
            end_value=4.0
        )

        # Should return start value (no interpolation possible)
        value = constraint.get_value_at_station(100.0)
        assert value == 3.6

    def test_reversed_stations(self):
        """Test that reversed stations are auto-corrected."""
        constraint = ParametricConstraint(
            id="test",
            component_name="Lane",
            parameter_name="width",
            constraint_type=ConstraintType.RANGE,
            start_station=200.0,  # Higher than end
            end_station=100.0,    # Lower than start
            start_value=4.0,
            end_value=3.6
        )

        # Should be corrected so start < end
        assert constraint.start_station == 100.0
        assert constraint.end_station == 200.0
        assert constraint.start_value == 3.6
        assert constraint.end_value == 4.0

    def test_negative_values(self):
        """Test constraints with negative values (e.g., superelevation)."""
        constraint = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="cross_slope",
            start_station=100.0,
            end_station=200.0,
            start_value=0.02,
            end_value=-0.04  # Negative for superelevation
        )

        # Midpoint
        value = constraint.get_value_at_station(150.0)
        expected = 0.02 + 0.5 * (-0.04 - 0.02)
        assert abs(value - expected) < 0.001

    def test_very_small_station_range(self):
        """Test with very small station range (submillimeter)."""
        constraint = ParametricConstraint.create_range_constraint(
            component_name="Lane",
            parameter_name="width",
            start_station=100.0,
            end_station=100.0001,  # 0.1mm range
            start_value=3.6,
            end_value=4.0
        )

        # Should return start value for such small ranges
        value = constraint.get_value_at_station(100.0)
        assert value == 3.6


def run_all_tests():
    """Run all tests and print results."""
    import traceback

    test_classes = [
        TestParametricConstraint,
        TestConstraintManager,
        TestEdgeCases,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for test_class in test_classes:
        instance = test_class()
        methods = [m for m in dir(instance) if m.startswith('test_')]

        for method_name in methods:
            total_tests += 1
            try:
                getattr(instance, method_name)()
                passed_tests += 1
                print(f"  PASS: {test_class.__name__}.{method_name}")
            except Exception as e:
                failed_tests.append((f"{test_class.__name__}.{method_name}", e))
                print(f"  FAIL: {test_class.__name__}.{method_name}")
                traceback.print_exc()

    print("\n" + "=" * 50)
    print(f"Tests: {total_tests} total, {passed_tests} passed, {len(failed_tests)} failed")

    if failed_tests:
        print("\nFailed tests:")
        for name, error in failed_tests:
            print(f"  - {name}: {error}")
        return False

    print("\nAll tests passed!")
    return True


if __name__ == "__main__":
    run_all_tests()
