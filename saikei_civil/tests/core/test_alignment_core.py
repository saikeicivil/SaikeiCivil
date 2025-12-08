# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under Apache License 2.0
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
Core Alignment Tests - NO BLENDER REQUIRED
===========================================

These tests verify the pure business logic in core/alignment.py
WITHOUT requiring Blender to be running. This enables:
- Fast unit testing in CI/CD pipelines
- Testing on systems without Blender installed
- Isolation of business logic from visualization

Run with:
    pytest saikei_civil/tests/core/test_alignment_core.py -v

Or from Python:
    python -m pytest saikei_civil/tests/core/test_alignment_core.py -v
"""
import math
import pytest
from typing import Dict, List
from unittest.mock import MagicMock

# Import the module under test - pure Python, no Blender deps
from saikei_civil.core.alignment import (
    # Data structures
    SimpleVector,
    create_pi_data,
    format_pi_for_ifc,
    pis_from_coordinates,
    # Geometry calculations
    calculate_tangent_direction,
    calculate_tangent_length,
    calculate_deflection_angle,
    get_total_alignment_length,
    interpolate_position_on_line,
    interpolate_position_on_arc,
    get_point_at_station,
    # Segment generation
    compute_tangent_segments,
    compute_segments_with_curves,
    insert_curve,
    remove_curve,
    # Curve geometry
    calculate_curve_geometry,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def simple_pis():
    """Simple 3-PI alignment (straight then 90° turn)."""
    return [
        create_pi_data(0, 0.0, 0.0),
        create_pi_data(1, 100.0, 0.0),
        create_pi_data(2, 100.0, 100.0),
    ]


@pytest.fixture
def straight_pis():
    """Simple 2-PI straight alignment."""
    return [
        create_pi_data(0, 0.0, 0.0),
        create_pi_data(1, 100.0, 0.0),
    ]


@pytest.fixture
def complex_pis():
    """4-PI alignment with S-curve potential."""
    return [
        create_pi_data(0, 0.0, 0.0),
        create_pi_data(1, 100.0, 0.0),
        create_pi_data(2, 200.0, 50.0),
        create_pi_data(3, 300.0, 50.0),
    ]


# =============================================================================
# SimpleVector Tests
# =============================================================================

class TestSimpleVector:
    """Tests for SimpleVector utility class."""

    def test_create_from_coordinates(self):
        v = SimpleVector(10.0, 20.0)
        assert v.x == 10.0
        assert v.y == 20.0

    def test_create_from_tuple(self):
        v = SimpleVector((10.0, 20.0))
        assert v.x == 10.0
        assert v.y == 20.0

    def test_addition(self):
        v1 = SimpleVector(10.0, 20.0)
        v2 = SimpleVector(5.0, 10.0)
        result = v1 + v2
        assert result.x == 15.0
        assert result.y == 30.0

    def test_subtraction(self):
        v1 = SimpleVector(10.0, 20.0)
        v2 = SimpleVector(5.0, 10.0)
        result = v1 - v2
        assert result.x == 5.0
        assert result.y == 10.0

    def test_scalar_multiplication(self):
        v = SimpleVector(10.0, 20.0)
        result = v * 2
        assert result.x == 20.0
        assert result.y == 40.0

    def test_length(self):
        v = SimpleVector(3.0, 4.0)
        assert v.length == 5.0

    def test_normalized(self):
        v = SimpleVector(3.0, 4.0)
        n = v.normalized()
        assert abs(n.length - 1.0) < 1e-9
        assert abs(n.x - 0.6) < 1e-9
        assert abs(n.y - 0.8) < 1e-9

    def test_angle(self):
        # Pointing right (east)
        v1 = SimpleVector(1.0, 0.0)
        assert abs(v1.angle) < 1e-9

        # Pointing up (north)
        v2 = SimpleVector(0.0, 1.0)
        assert abs(v2.angle - math.pi / 2) < 1e-9

    def test_dot_product(self):
        v1 = SimpleVector(1.0, 0.0)
        v2 = SimpleVector(0.0, 1.0)
        assert v1.dot(v2) == 0.0  # Perpendicular

        v3 = SimpleVector(1.0, 1.0)
        assert v1.dot(v3) == 1.0

    def test_distance_to(self):
        v1 = SimpleVector(0.0, 0.0)
        v2 = SimpleVector(3.0, 4.0)
        assert v1.distance_to(v2) == 5.0


# =============================================================================
# PI Data Structure Tests
# =============================================================================

class TestPIDataStructures:
    """Tests for PI data structure functions."""

    def test_create_pi_data(self):
        pi = create_pi_data(0, 100.0, 200.0)
        assert pi['id'] == 0
        assert pi['position'].x == 100.0
        assert pi['position'].y == 200.0
        assert 'curve' not in pi

    def test_create_pi_data_with_curve(self):
        curve = {'radius': 50.0, 'arc_length': 78.54}
        pi = create_pi_data(1, 100.0, 200.0, curve)
        assert pi['id'] == 1
        assert 'curve' in pi
        assert pi['curve']['radius'] == 50.0

    def test_format_pi_for_ifc(self):
        pi = create_pi_data(0, 100.0, 200.0)
        formatted = format_pi_for_ifc(pi)
        assert formatted['Coordinates'] == (100.0, 200.0)
        assert 'Radius' not in formatted

    def test_format_pi_for_ifc_with_curve(self):
        curve = {'radius': 50.0}
        pi = create_pi_data(0, 100.0, 200.0, curve)
        formatted = format_pi_for_ifc(pi)
        assert formatted['Radius'] == 50.0

    def test_pis_from_coordinates(self):
        coords = [(0, 0), (100, 0), (100, 100)]
        pis = pis_from_coordinates(coords)
        assert len(pis) == 3
        assert pis[0]['position'].x == 0
        assert pis[1]['position'].x == 100
        assert pis[2]['position'].y == 100


# =============================================================================
# Geometry Calculation Tests
# =============================================================================

class TestGeometryCalculations:
    """Tests for geometry calculation functions."""

    def test_tangent_direction_east(self):
        start = SimpleVector(0, 0)
        end = SimpleVector(100, 0)
        direction = calculate_tangent_direction(start, end)
        assert abs(direction) < 1e-9  # 0 radians = east

    def test_tangent_direction_north(self):
        start = SimpleVector(0, 0)
        end = SimpleVector(0, 100)
        direction = calculate_tangent_direction(start, end)
        assert abs(direction - math.pi / 2) < 1e-9  # 90° = north

    def test_tangent_direction_northeast(self):
        start = SimpleVector(0, 0)
        end = SimpleVector(100, 100)
        direction = calculate_tangent_direction(start, end)
        assert abs(direction - math.pi / 4) < 1e-9  # 45° = northeast

    def test_tangent_length(self):
        start = SimpleVector(0, 0)
        end = SimpleVector(3, 4)
        length = calculate_tangent_length(start, end)
        assert length == 5.0

    def test_deflection_angle_right_turn(self):
        """90° right turn (clockwise)."""
        prev = SimpleVector(0, 0)
        curr = SimpleVector(100, 0)
        next_ = SimpleVector(100, -100)
        deflection = calculate_deflection_angle(prev, curr, next_)
        assert abs(deflection - (-math.pi / 2)) < 1e-9

    def test_deflection_angle_left_turn(self):
        """90° left turn (counter-clockwise)."""
        prev = SimpleVector(0, 0)
        curr = SimpleVector(100, 0)
        next_ = SimpleVector(100, 100)
        deflection = calculate_deflection_angle(prev, curr, next_)
        assert abs(deflection - math.pi / 2) < 1e-9

    def test_deflection_angle_straight(self):
        """No deflection (straight)."""
        prev = SimpleVector(0, 0)
        curr = SimpleVector(100, 0)
        next_ = SimpleVector(200, 0)
        deflection = calculate_deflection_angle(prev, curr, next_)
        assert abs(deflection) < 1e-6

    def test_get_total_alignment_length(self):
        segments = [
            {'length': 100.0},
            {'length': 50.0},
            {'length': 75.5},
        ]
        total = get_total_alignment_length(segments)
        assert total == 225.5

    def test_interpolate_position_on_line(self):
        start = SimpleVector(0, 0)
        direction = 0.0  # East
        distance = 50.0

        pos = interpolate_position_on_line(start, direction, distance)
        assert abs(pos.x - 50.0) < 1e-9
        assert abs(pos.y) < 1e-9

    def test_interpolate_position_on_arc(self):
        center = SimpleVector(0, 0)
        radius = 100.0
        start_angle = 0.0
        arc_distance = math.pi * 100 / 2  # Quarter circle
        is_ccw = True

        pos, direction = interpolate_position_on_arc(
            center, radius, start_angle, arc_distance, is_ccw
        )

        # Should be at top of circle (0, 100)
        assert abs(pos.x) < 1e-6
        assert abs(pos.y - 100.0) < 1e-6


# =============================================================================
# Curve Geometry Tests
# =============================================================================

class TestCurveGeometry:
    """Tests for curve geometry calculations."""

    def test_calculate_curve_geometry_left_turn(self):
        """90° left turn with R=50m."""
        prev = SimpleVector(0, 0)
        curr = SimpleVector(100, 0)
        next_ = SimpleVector(100, 100)

        curve = calculate_curve_geometry(prev, curr, next_, 50.0)

        assert curve is not None
        assert curve['radius'] == 50.0
        assert curve['turn_direction'] == 'LEFT'
        assert abs(curve['deflection'] - math.pi / 2) < 1e-6

        # Arc length = R * theta
        expected_arc = 50.0 * math.pi / 2
        assert abs(curve['arc_length'] - expected_arc) < 1e-6

    def test_calculate_curve_geometry_right_turn(self):
        """90° right turn with R=50m."""
        prev = SimpleVector(0, 0)
        curr = SimpleVector(100, 0)
        next_ = SimpleVector(100, -100)

        curve = calculate_curve_geometry(prev, curr, next_, 50.0)

        assert curve is not None
        assert curve['turn_direction'] == 'RIGHT'
        assert curve['deflection'] < 0

    def test_calculate_curve_geometry_collinear_returns_none(self):
        """Collinear PIs should return None."""
        prev = SimpleVector(0, 0)
        curr = SimpleVector(100, 0)
        next_ = SimpleVector(200, 0)

        curve = calculate_curve_geometry(prev, curr, next_, 50.0)
        assert curve is None

    def test_bc_ec_positions(self):
        """Verify BC and EC are tangent length from PI."""
        prev = SimpleVector(0, 0)
        curr = SimpleVector(100, 0)
        next_ = SimpleVector(100, 100)

        curve = calculate_curve_geometry(prev, curr, next_, 50.0)

        # Tangent length = R * tan(delta/2)
        expected_T = 50.0 * math.tan(math.pi / 4)

        bc_dist = curr.distance_to(curve['bc'])
        ec_dist = curr.distance_to(curve['ec'])

        assert abs(bc_dist - expected_T) < 1e-6
        assert abs(ec_dist - expected_T) < 1e-6


# =============================================================================
# Segment Generation Tests
# =============================================================================

class TestSegmentGeneration:
    """Tests for segment generation functions."""

    def test_compute_tangent_segments_simple(self, straight_pis):
        """Simple 2-PI alignment produces 1 tangent."""
        segments = compute_tangent_segments(straight_pis)
        assert len(segments) == 1
        assert segments[0]['type'] == 'LINE'
        assert segments[0]['length'] == 100.0

    def test_compute_tangent_segments_3pi(self, simple_pis):
        """3-PI alignment produces 2 tangents."""
        segments = compute_tangent_segments(simple_pis)
        assert len(segments) == 2
        assert all(s['type'] == 'LINE' for s in segments)

    def test_insert_curve_at_interior_pi(self, simple_pis):
        """Insert curve at PI index 1."""
        result = insert_curve(simple_pis, 1, 50.0)

        assert result is not None
        assert 'curve' in simple_pis[1]
        assert simple_pis[1]['curve']['radius'] == 50.0

    def test_insert_curve_at_first_pi_fails(self, simple_pis):
        """Cannot insert curve at first PI."""
        result = insert_curve(simple_pis, 0, 50.0)
        assert result is None

    def test_insert_curve_at_last_pi_fails(self, simple_pis):
        """Cannot insert curve at last PI."""
        result = insert_curve(simple_pis, 2, 50.0)
        assert result is None

    def test_remove_curve(self, simple_pis):
        """Remove existing curve."""
        insert_curve(simple_pis, 1, 50.0)
        assert 'curve' in simple_pis[1]

        result = remove_curve(simple_pis, 1)
        assert result is True
        assert 'curve' not in simple_pis[1]

    def test_remove_curve_nonexistent(self, simple_pis):
        """Remove curve that doesn't exist."""
        result = remove_curve(simple_pis, 1)
        assert result is False

    def test_compute_segments_with_curves(self, simple_pis):
        """Segments with curve at PI 1."""
        insert_curve(simple_pis, 1, 50.0)
        segments = compute_segments_with_curves(simple_pis)

        # Should have: Tangent, Curve, Tangent
        assert len(segments) == 3

        types = [s['type'] for s in segments]
        assert types == ['LINE', 'CIRCULARARC', 'LINE']


# =============================================================================
# Station Query Tests
# =============================================================================

class TestStationQueries:
    """Tests for station-based queries."""

    def test_get_point_at_station_line(self):
        """Query point on straight segment."""
        segments = [{
            'type': 'LINE',
            'start': SimpleVector(0, 0),
            'direction': 0.0,
            'length': 100.0,
        }]

        result = get_point_at_station(segments, 50.0, start_station=0.0)

        assert result is not None
        assert abs(result['x'] - 50.0) < 1e-9
        assert abs(result['y']) < 1e-9
        assert abs(result['direction']) < 1e-9

    def test_get_point_at_station_start(self):
        """Query at start of alignment."""
        segments = [{
            'type': 'LINE',
            'start': SimpleVector(100, 200),
            'direction': math.pi / 4,
            'length': 100.0,
        }]

        result = get_point_at_station(segments, 0.0, start_station=0.0)

        assert result is not None
        assert abs(result['x'] - 100.0) < 1e-9
        assert abs(result['y'] - 200.0) < 1e-9

    def test_get_point_at_station_out_of_range(self):
        """Query beyond alignment returns None."""
        segments = [{
            'type': 'LINE',
            'start': SimpleVector(0, 0),
            'direction': 0.0,
            'length': 100.0,
        }]

        result = get_point_at_station(segments, 150.0, start_station=0.0)
        assert result is None

    def test_get_point_at_station_negative(self):
        """Query before alignment start returns None."""
        segments = [{
            'type': 'LINE',
            'start': SimpleVector(0, 0),
            'direction': 0.0,
            'length': 100.0,
        }]

        result = get_point_at_station(segments, -10.0, start_station=0.0)
        assert result is None


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_alignment_workflow(self):
        """Create alignment, add curve, compute segments."""
        # Create PIs
        pis = pis_from_coordinates([
            (0, 0),
            (100, 0),
            (200, 100),
            (300, 100),
        ])

        assert len(pis) == 4

        # Compute tangent-only segments
        tangent_segments = compute_tangent_segments(pis)
        assert len(tangent_segments) == 3

        # Insert curves at interior PIs
        insert_curve(pis, 1, 30.0)
        insert_curve(pis, 2, 50.0)

        # Compute full segments
        full_segments = compute_segments_with_curves(pis)

        # Should have: T1, C1, T2, C2, T3
        assert len(full_segments) == 5

        # Total length should be calculable
        total_length = get_total_alignment_length(full_segments)
        assert total_length > 0

    def test_pi_modification_recalculates_curves(self):
        """Moving a PI should invalidate/update curves."""
        pis = pis_from_coordinates([
            (0, 0),
            (100, 0),
            (100, 100),
        ])

        insert_curve(pis, 1, 50.0)
        original_arc = pis[1]['curve']['arc_length']

        # Modify PI position to reduce deflection
        pis[2]['position'] = SimpleVector(150, 50)

        # Recompute segments (this recalculates curves)
        segments = compute_segments_with_curves(pis)

        # Arc length should have changed
        if 'curve' in pis[1]:
            new_arc = pis[1]['curve']['arc_length']
            assert new_arc != original_arc


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])