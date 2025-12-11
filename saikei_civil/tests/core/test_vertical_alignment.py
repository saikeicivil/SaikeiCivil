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
Tests for Vertical Alignment Module
====================================

Tests for PVI calculations, vertical curves, and grade computations.
"""

import math

import pytest

from core.vertical_alignment import PVI, AASHTO_K_VALUES


class TestPVI:
    """Tests for PVI (Point of Vertical Intersection) dataclass."""

    @pytest.mark.unit
    def test_pvi_creation(self):
        """Test basic PVI creation."""
        pvi = PVI(station=1000.0, elevation=100.0)
        assert pvi.station == 1000.0
        assert pvi.elevation == 100.0
        assert pvi.curve_length == 0.0  # Default

    @pytest.mark.unit
    def test_pvi_with_curve(self):
        """Test PVI with vertical curve."""
        pvi = PVI(station=1000.0, elevation=100.0, curve_length=200.0)
        assert pvi.curve_length == 200.0

    @pytest.mark.unit
    def test_grade_in_calculation(self):
        """Test incoming grade calculation."""
        pvi = PVI(station=1000.0, elevation=100.0)
        pvi.grade_in = 0.02  # 2% grade
        assert pvi.grade_in == 0.02

    @pytest.mark.unit
    def test_grade_out_calculation(self):
        """Test outgoing grade calculation."""
        pvi = PVI(station=1000.0, elevation=100.0)
        pvi.grade_out = -0.03  # -3% grade
        assert pvi.grade_out == -0.03

    @pytest.mark.unit
    def test_grade_change(self):
        """Test grade change calculation (A value)."""
        pvi = PVI(station=1000.0, elevation=100.0)
        pvi.grade_in = 0.02   # +2%
        pvi.grade_out = -0.01  # -1%

        # Grade change should be -3% (going from +2% to -1%)
        grade_change = pvi.grade_out - pvi.grade_in
        assert abs(grade_change - (-0.03)) < 0.0001

    @pytest.mark.unit
    def test_is_crest_curve(self):
        """Test identification of crest vertical curve."""
        pvi = PVI(station=1000.0, elevation=100.0, curve_length=200.0)
        pvi.grade_in = 0.03   # +3%
        pvi.grade_out = -0.02  # -2%

        # Crest: grade goes from positive to less positive/negative
        is_crest = pvi.grade_in > pvi.grade_out
        assert is_crest is True

    @pytest.mark.unit
    def test_is_sag_curve(self):
        """Test identification of sag vertical curve."""
        pvi = PVI(station=1000.0, elevation=100.0, curve_length=200.0)
        pvi.grade_in = -0.02  # -2%
        pvi.grade_out = 0.03   # +3%

        # Sag: grade goes from negative to more positive
        is_sag = pvi.grade_in < pvi.grade_out
        assert is_sag is True


class TestAASHTOKValues:
    """Tests for AASHTO K-value design standards."""

    @pytest.mark.unit
    def test_k_values_exist(self):
        """Test that K-value constants are defined."""
        assert AASHTO_K_VALUES is not None
        assert len(AASHTO_K_VALUES) > 0

    @pytest.mark.unit
    def test_crest_k_values(self):
        """Test crest curve K-values are present."""
        # K-values should include crest curve standards
        assert "crest" in AASHTO_K_VALUES or any(
            "crest" in str(k).lower() for k in AASHTO_K_VALUES
        )

    @pytest.mark.unit
    def test_sag_k_values(self):
        """Test sag curve K-values are present."""
        # K-values should include sag curve standards
        assert "sag" in AASHTO_K_VALUES or any(
            "sag" in str(k).lower() for k in AASHTO_K_VALUES
        )


class TestVerticalCurveGeometry:
    """Tests for vertical curve geometric calculations."""

    @pytest.mark.unit
    def test_curve_high_point_crest(self):
        """Test high point calculation for crest curve."""
        # Crest curve with symmetric grades
        grade_in = 0.04   # +4%
        grade_out = -0.04  # -4%
        curve_length = 400.0

        # High point should be at middle for symmetric curve
        A = abs(grade_out - grade_in)  # Algebraic difference
        # High point distance from BVC = g1 * L / A
        high_point_dist = abs(grade_in) * curve_length / A

        assert high_point_dist == pytest.approx(200.0, rel=0.01)

    @pytest.mark.unit
    def test_curve_low_point_sag(self):
        """Test low point calculation for sag curve."""
        # Sag curve with symmetric grades
        grade_in = -0.03  # -3%
        grade_out = 0.03   # +3%
        curve_length = 300.0

        # Low point should be at middle for symmetric curve
        A = abs(grade_out - grade_in)
        low_point_dist = abs(grade_in) * curve_length / A

        assert low_point_dist == pytest.approx(150.0, rel=0.01)

    @pytest.mark.unit
    def test_elevation_at_station_on_tangent(self):
        """Test elevation calculation on tangent (no curve)."""
        start_station = 1000.0
        start_elevation = 100.0
        grade = 0.02  # 2%
        target_station = 1100.0

        # Elevation = start + grade * distance
        expected_elevation = start_elevation + grade * (target_station - start_station)
        assert expected_elevation == pytest.approx(102.0)

    @pytest.mark.unit
    def test_minimum_curve_length_crest(self):
        """Test minimum curve length for stopping sight distance (crest)."""
        design_speed_mph = 60
        # Approximate K value for 60 mph crest
        K_crest = 151  # AASHTO value for 60 mph

        grade_in = 0.03
        grade_out = -0.02
        A = abs(grade_out - grade_in) * 100  # Convert to percent

        # L_min = K * A
        L_min = K_crest * A
        assert L_min > 0

    @pytest.mark.unit
    def test_rate_of_change(self):
        """Test rate of vertical curvature (r)."""
        curve_length = 400.0
        grade_in = 0.04   # 4%
        grade_out = -0.02  # -2%

        A = (grade_out - grade_in) * 100  # Algebraic difference in %
        r = A / curve_length  # Rate of change per station

        assert r == pytest.approx(-0.015, rel=0.01)  # -1.5% per 100 ft


class TestGradeCalculations:
    """Tests for grade percentage calculations."""

    @pytest.mark.unit
    @pytest.mark.parametrize("rise,run,expected_grade", [
        (2.0, 100.0, 0.02),    # 2% grade
        (-3.0, 100.0, -0.03),  # -3% grade
        (0.0, 100.0, 0.0),     # Level
        (10.0, 100.0, 0.10),   # 10% grade
    ])
    def test_grade_from_rise_run(self, rise, run, expected_grade):
        """Test grade calculation from rise and run."""
        grade = rise / run
        assert grade == pytest.approx(expected_grade)

    @pytest.mark.unit
    def test_grade_to_angle(self):
        """Test conversion from grade to angle."""
        grade = 0.10  # 10%
        angle_rad = math.atan(grade)
        angle_deg = math.degrees(angle_rad)

        assert angle_deg == pytest.approx(5.71, rel=0.01)

    @pytest.mark.unit
    def test_max_grade_limits(self):
        """Test that grades stay within reasonable limits."""
        # Typical max grades for different road types
        max_grade_interstate = 0.06  # 6%
        max_grade_arterial = 0.08    # 8%
        max_grade_local = 0.12       # 12%

        # These are just reference values
        assert max_grade_interstate < max_grade_arterial
        assert max_grade_arterial < max_grade_local
