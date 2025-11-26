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
Tests for Horizontal Alignment Module
======================================

Tests for SimpleVector, curve geometry, and stationing calculations.
"""

import math

import pytest

from core.horizontal_alignment import SimpleVector, StationingManager


class TestSimpleVector:
    """Tests for SimpleVector 2D math class."""

    @pytest.mark.unit
    def test_vector_creation(self):
        """Test basic vector creation."""
        v = SimpleVector(3.0, 4.0)
        assert v.x == 3.0
        assert v.y == 4.0

    @pytest.mark.unit
    def test_vector_addition(self):
        """Test vector addition."""
        v1 = SimpleVector(1.0, 2.0)
        v2 = SimpleVector(3.0, 4.0)
        result = v1 + v2
        assert result.x == 4.0
        assert result.y == 6.0

    @pytest.mark.unit
    def test_vector_subtraction(self):
        """Test vector subtraction."""
        v1 = SimpleVector(5.0, 7.0)
        v2 = SimpleVector(2.0, 3.0)
        result = v1 - v2
        assert result.x == 3.0
        assert result.y == 4.0

    @pytest.mark.unit
    def test_vector_scalar_multiply(self):
        """Test scalar multiplication."""
        v = SimpleVector(2.0, 3.0)
        result = v * 2.0
        assert result.x == 4.0
        assert result.y == 6.0

    @pytest.mark.unit
    def test_vector_length(self):
        """Test vector length calculation."""
        v = SimpleVector(3.0, 4.0)
        assert v.length == pytest.approx(5.0)

    @pytest.mark.unit
    def test_vector_length_zero(self):
        """Test zero vector length."""
        v = SimpleVector(0.0, 0.0)
        assert v.length == 0.0

    @pytest.mark.unit
    def test_vector_normalized(self):
        """Test vector normalization."""
        v = SimpleVector(3.0, 4.0)
        n = v.normalized()
        assert n.length == pytest.approx(1.0)
        assert n.x == pytest.approx(0.6)
        assert n.y == pytest.approx(0.8)

    @pytest.mark.unit
    def test_vector_dot_product(self):
        """Test dot product calculation."""
        v1 = SimpleVector(1.0, 0.0)
        v2 = SimpleVector(0.0, 1.0)
        # Perpendicular vectors have dot product of 0
        assert v1.dot(v2) == pytest.approx(0.0)

    @pytest.mark.unit
    def test_vector_dot_parallel(self):
        """Test dot product of parallel vectors."""
        v1 = SimpleVector(2.0, 0.0)
        v2 = SimpleVector(3.0, 0.0)
        assert v1.dot(v2) == pytest.approx(6.0)

    @pytest.mark.unit
    def test_vector_cross_2d(self):
        """Test 2D cross product (returns scalar)."""
        v1 = SimpleVector(1.0, 0.0)
        v2 = SimpleVector(0.0, 1.0)
        # Cross product indicates rotation direction
        cross = v1.cross(v2)
        assert cross == pytest.approx(1.0)

    @pytest.mark.unit
    def test_vector_angle_between(self):
        """Test angle between vectors."""
        v1 = SimpleVector(1.0, 0.0)
        v2 = SimpleVector(0.0, 1.0)
        # Should be 90 degrees
        angle = math.acos(v1.dot(v2) / (v1.length * v2.length))
        assert math.degrees(angle) == pytest.approx(90.0)


class TestStationingManager:
    """Tests for StationingManager class."""

    @pytest.mark.unit
    def test_stationing_creation(self):
        """Test basic stationing manager creation."""
        sm = StationingManager(start_station=10000.0)
        assert sm.start_station == 10000.0

    @pytest.mark.unit
    def test_station_at_distance(self):
        """Test station calculation at distance."""
        sm = StationingManager(start_station=10000.0)
        station = sm.get_station_at_distance(150.0)
        assert station == pytest.approx(10150.0)

    @pytest.mark.unit
    def test_distance_at_station(self):
        """Test distance calculation from station."""
        sm = StationingManager(start_station=10000.0)
        distance = sm.get_distance_at_station(10150.0)
        assert distance == pytest.approx(150.0)

    @pytest.mark.unit
    def test_station_round_trip(self):
        """Test station/distance round trip."""
        sm = StationingManager(start_station=5000.0)
        original_distance = 250.0
        station = sm.get_station_at_distance(original_distance)
        distance_back = sm.get_distance_at_station(station)
        assert distance_back == pytest.approx(original_distance)


class TestCurveGeometry:
    """Tests for horizontal curve geometry calculations."""

    @pytest.mark.unit
    def test_deflection_angle(self):
        """Test deflection angle calculation."""
        # Two tangent directions
        bearing_in = 45.0   # degrees
        bearing_out = 90.0  # degrees

        deflection = bearing_out - bearing_in
        assert deflection == pytest.approx(45.0)

    @pytest.mark.unit
    def test_tangent_length(self):
        """Test tangent length calculation."""
        radius = 500.0
        deflection_rad = math.radians(30.0)

        # T = R * tan(delta/2)
        tangent_length = radius * math.tan(deflection_rad / 2)
        assert tangent_length == pytest.approx(133.97, rel=0.01)

    @pytest.mark.unit
    def test_arc_length(self):
        """Test arc length calculation."""
        radius = 500.0
        deflection_rad = math.radians(30.0)

        # L = R * delta (in radians)
        arc_length = radius * deflection_rad
        assert arc_length == pytest.approx(261.80, rel=0.01)

    @pytest.mark.unit
    def test_external_distance(self):
        """Test external distance calculation."""
        radius = 500.0
        deflection_rad = math.radians(30.0)

        # E = R * (1/cos(delta/2) - 1)
        external = radius * (1 / math.cos(deflection_rad / 2) - 1)
        assert external == pytest.approx(17.63, rel=0.01)

    @pytest.mark.unit
    def test_middle_ordinate(self):
        """Test middle ordinate calculation."""
        radius = 500.0
        deflection_rad = math.radians(30.0)

        # M = R * (1 - cos(delta/2))
        middle_ordinate = radius * (1 - math.cos(deflection_rad / 2))
        assert middle_ordinate == pytest.approx(16.75, rel=0.01)

    @pytest.mark.unit
    def test_chord_length(self):
        """Test long chord length calculation."""
        radius = 500.0
        deflection_rad = math.radians(30.0)

        # C = 2 * R * sin(delta/2)
        chord = 2 * radius * math.sin(deflection_rad / 2)
        assert chord == pytest.approx(258.82, rel=0.01)

    @pytest.mark.unit
    def test_degree_of_curve(self):
        """Test degree of curve calculation (arc definition)."""
        radius = 500.0

        # D = 5729.578 / R (for 100 ft arc)
        # Using metric: D = 1745.33 / R (for 30m arc)
        degree_100ft = 5729.578 / radius
        assert degree_100ft == pytest.approx(11.46, rel=0.01)


class TestAlignmentPI:
    """Tests for Point of Intersection (PI) handling."""

    @pytest.mark.unit
    def test_pi_coordinates(self, sample_pi_points):
        """Test PI point coordinate storage."""
        pi = sample_pi_points[0]
        assert len(pi) == 3  # x, y, z
        assert pi[0] == 0.0  # x
        assert pi[1] == 0.0  # y
        assert pi[2] == 100.0  # z (elevation)

    @pytest.mark.unit
    def test_tangent_direction(self, sample_pi_points):
        """Test tangent direction between PIs."""
        p1 = sample_pi_points[0]
        p2 = sample_pi_points[1]

        # Direction vector
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        # First tangent is along X axis
        assert dx == pytest.approx(100.0)
        assert dy == pytest.approx(0.0)

    @pytest.mark.unit
    def test_tangent_length_calculation(self, sample_pi_points):
        """Test tangent segment length."""
        p1 = sample_pi_points[0]
        p2 = sample_pi_points[1]

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.sqrt(dx**2 + dy**2)

        assert length == pytest.approx(100.0)
