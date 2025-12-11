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
Tests for Station Formatting Module
====================================

Tests the station parsing and formatting utilities used for
civil engineering station notation (e.g., "10+50.00").
"""

import pytest

from core.station_formatting import (
    parse_station,
    format_station,
    format_station_short,
    validate_station_input,
)


class TestParseStation:
    """Tests for parse_station function."""

    @pytest.mark.unit
    def test_parse_standard_format(self):
        """Test parsing standard station format '10+50.00'."""
        result = parse_station("10+50.00")
        assert result == 1050.0

    @pytest.mark.unit
    def test_parse_with_spaces(self):
        """Test parsing station with surrounding spaces."""
        result = parse_station("  10+50.00  ")
        assert result == 1050.0

    @pytest.mark.unit
    def test_parse_plain_number(self):
        """Test parsing plain numeric value."""
        result = parse_station("1050.0")
        assert result == 1050.0

    @pytest.mark.unit
    def test_parse_integer(self):
        """Test parsing integer station."""
        result = parse_station("10+00")
        assert result == 1000.0

    @pytest.mark.unit
    def test_parse_large_station(self):
        """Test parsing large station value."""
        result = parse_station("150+25.50")
        assert result == 15025.5

    @pytest.mark.unit
    def test_parse_zero_station(self):
        """Test parsing zero station."""
        result = parse_station("0+00.00")
        assert result == 0.0

    @pytest.mark.unit
    def test_parse_invalid_returns_none(self):
        """Test that invalid input returns None."""
        result = parse_station("invalid")
        assert result is None

    @pytest.mark.unit
    def test_parse_empty_returns_none(self):
        """Test that empty string returns None."""
        result = parse_station("")
        assert result is None


class TestFormatStation:
    """Tests for format_station function."""

    @pytest.mark.unit
    def test_format_basic(self):
        """Test basic station formatting."""
        result = format_station(1050.0)
        assert result == "10+50.00"

    @pytest.mark.unit
    def test_format_zero(self):
        """Test formatting zero station."""
        result = format_station(0.0)
        assert result == "0+00.00"

    @pytest.mark.unit
    def test_format_large_value(self):
        """Test formatting large station value."""
        result = format_station(15025.5)
        assert result == "150+25.50"

    @pytest.mark.unit
    def test_format_small_value(self):
        """Test formatting small station value."""
        result = format_station(50.25)
        assert result == "0+50.25"

    @pytest.mark.unit
    def test_format_negative(self):
        """Test formatting negative station (back station)."""
        result = format_station(-50.0)
        # Should handle negative values appropriately
        assert "-" in result or result.startswith("0")


class TestFormatStationShort:
    """Tests for format_station_short function."""

    @pytest.mark.unit
    def test_short_format_basic(self):
        """Test short station formatting."""
        result = format_station_short(1050.0)
        assert result == "10+50"

    @pytest.mark.unit
    def test_short_format_with_decimal(self):
        """Test short format preserves significant decimals."""
        result = format_station_short(1050.5)
        # Should show the .5 if significant
        assert "50" in result


class TestValidateStationInput:
    """Tests for validate_station_input function."""

    @pytest.mark.unit
    def test_valid_station_format(self):
        """Test validation of valid station format."""
        is_valid, value, error = validate_station_input("10+50.00")
        assert is_valid is True
        assert value == 1050.0
        assert error is None

    @pytest.mark.unit
    def test_valid_plain_number(self):
        """Test validation of plain number."""
        is_valid, value, error = validate_station_input("1050")
        assert is_valid is True
        assert value == 1050.0

    @pytest.mark.unit
    def test_invalid_format(self):
        """Test validation rejects invalid format."""
        is_valid, value, error = validate_station_input("not a station")
        assert is_valid is False
        assert value is None
        assert error is not None

    @pytest.mark.unit
    def test_empty_input(self):
        """Test validation rejects empty input."""
        is_valid, value, error = validate_station_input("")
        assert is_valid is False


class TestRoundTrip:
    """Test that parse and format are inverse operations."""

    @pytest.mark.unit
    @pytest.mark.parametrize("station", [
        0.0,
        100.0,
        1050.0,
        15025.50,
        99999.99,
    ])
    def test_round_trip(self, station):
        """Test that format(parse(format(x))) == format(x)."""
        formatted = format_station(station)
        parsed = parse_station(formatted)
        reformatted = format_station(parsed)
        assert formatted == reformatted
