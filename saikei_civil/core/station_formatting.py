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
Station Formatting Utilities

Handles conversion between station notation (XX+XXX.XX) and numeric values.

Stationing Notation:
- Metric: XX+XXX.XX (1000m stations)
  Examples: 0+000 = 0m, 0+472.58 = 472.58m, 10+000 = 10000m
- US Customary: XX+XX.XX (100ft stations)
  Examples: 0+00 = 0ft, 5+47.23 = 547.23ft, 10+00 = 1000ft

This module uses metric (1000m) by default.
"""

import re
from typing import Union

from .logging_config import get_logger

logger = get_logger(__name__)


def parse_station(station_str: Union[str, float]) -> float:
    """
    Parse station input and convert to numeric value (meters).

    Accepts formats:
    - "10+472.58" → 10472.58
    - "10+472" → 10472.0
    - "472.58" → 472.58 (no + symbol)
    - 472.58 → 472.58 (already numeric)

    Args:
        station_str: Station string or numeric value

    Returns:
        Numeric station value in meters

    Raises:
        ValueError: If input format is invalid
    """
    # Already a number
    if isinstance(station_str, (int, float)):
        return float(station_str)

    # String input - strip whitespace
    station_str = str(station_str).strip()

    # Check for + symbol
    if '+' in station_str:
        parts = station_str.split('+')
        if len(parts) != 2:
            raise ValueError(f"Invalid station format: {station_str}. Expected format: XX+XXX.XX")

        try:
            # Parse major station (before +)
            major = float(parts[0])
            # Parse minor station (after +)
            minor = float(parts[1])

            # Combine: major*1000 + minor (for metric)
            # Example: "10+472.58" = 10*1000 + 472.58 = 10472.58
            return major * 1000.0 + minor

        except ValueError:
            raise ValueError(f"Invalid station format: {station_str}. Non-numeric values found.")
    else:
        # No + symbol, treat as direct numeric input
        try:
            return float(station_str)
        except ValueError:
            raise ValueError(f"Invalid station value: {station_str}")


def format_station(station_value: float, decimals: int = 2, include_plus: bool = True) -> str:
    """
    Format numeric station value to standard notation.

    Args:
        station_value: Numeric station value in meters
        decimals: Number of decimal places (default: 2)
        include_plus: Include the + symbol (default: True)

    Returns:
        Formatted station string

    Examples:
        >>> format_station(10472.58)
        '10+472.58'
        >>> format_station(472.58)
        '0+472.58'
        >>> format_station(10000.0)
        '10+000.00'
        >>> format_station(10000.0, decimals=0)
        '10+000'
    """
    # Calculate major and minor parts
    major = int(station_value // 1000)
    minor = station_value % 1000

    if include_plus:
        # Format with + symbol
        # Minor part padded to 3 digits before decimal (for metric 1000m stations)
        if decimals > 0:
            return f"{major}+{minor:0{6+decimals}.{decimals}f}"
        else:
            return f"{major}+{int(minor):03d}"
    else:
        # Just format as number
        return f"{station_value:.{decimals}f}"


def format_station_short(station_value: float) -> str:
    """
    Format station value in short form (no unnecessary decimals).

    Args:
        station_value: Numeric station value in meters

    Returns:
        Formatted station string

    Examples:
        >>> format_station_short(10472.58)
        '10+472.58'
        >>> format_station_short(10000.0)
        '10+000'
        >>> format_station_short(472.5)
        '0+472.5'
    """
    # Calculate major and minor parts
    major = int(station_value // 1000)
    minor = station_value % 1000

    # Check if minor has decimal portion
    if minor == int(minor):
        # No decimal portion
        return f"{major}+{int(minor):03d}"
    else:
        # Has decimal portion - format with minimal decimals
        # Remove trailing zeros
        minor_str = f"{minor:06.2f}".rstrip('0').rstrip('.')
        # Ensure at least 3 digits before decimal
        if '.' in minor_str:
            int_part, dec_part = minor_str.split('.')
            minor_str = f"{int_part:03s}.{dec_part}"
        else:
            minor_str = f"{minor_str:03s}"

        return f"{major}+{minor_str}"


def validate_station_input(station_str: str) -> tuple[bool, str]:
    """
    Validate station input format.

    Args:
        station_str: Station string to validate

    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is empty string
    """
    try:
        parse_station(station_str)
        return True, ""
    except ValueError as e:
        return False, str(e)


# Example usage and tests
if __name__ == "__main__":
    # Test parsing
    logger.debug("Parsing tests:")
    logger.debug("  '10+472.58' → %s", parse_station('10+472.58'))  # 10472.58
    logger.debug("  '0+000' → %s", parse_station('0+000'))          # 0.0
    logger.debug("  '10+000' → %s", parse_station('10+000'))        # 10000.0
    logger.debug("  '472.58' → %s", parse_station('472.58'))        # 472.58
    logger.debug("  472.58 → %s", parse_station(472.58))            # 472.58

    logger.debug("\nFormatting tests:")
    logger.debug("  10472.58 → '%s'", format_station(10472.58))    # 10+472.58
    logger.debug("  10000.0 → '%s'", format_station(10000.0))      # 10+000.00
    logger.debug("  472.58 → '%s'", format_station(472.58))        # 0+472.58
    logger.debug("  0.0 → '%s'", format_station(0.0))              # 0+000.00

    logger.debug("\nShort formatting tests:")
    logger.debug("  10472.58 → '%s'", format_station_short(10472.58))  # 10+472.58
    logger.debug("  10000.0 → '%s'", format_station_short(10000.0))    # 10+000
    logger.debug("  472.5 → '%s'", format_station_short(472.5))        # 0+472.5
    logger.debug("  0.0 → '%s'", format_station_short(0.0))            # 0+000