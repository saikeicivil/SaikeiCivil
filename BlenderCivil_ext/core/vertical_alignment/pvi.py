# ==============================================================================
# Saikei Civil - Civil Engineering Tools for Blender
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
Point of Vertical Intersection (PVI) Module
============================================

Defines the PVI dataclass for vertical alignment control points.

A PVI is the intersection point of two grade lines in vertical alignment
design. Vertical curves are placed at PVIs to provide smooth transitions.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from .constants import DESIGN_STANDARDS


@dataclass
class PVI:
    """Point of Vertical Intersection

    Control point for vertical alignment design. PVIs define the grade
    breakpoints and vertical curve locations.

    Attributes:
        station: Location along horizontal alignment (m)
        elevation: Height at this location (m)
        grade_in: Incoming grade (decimal, e.g., 0.02 = 2%)
        grade_out: Outgoing grade (decimal)
        curve_length: Length of vertical curve at this PVI (m), 0 = no curve
        k_value: K-value for curve design (m/%)
        description: Optional description of this PVI

    Properties:
        grade_in_percent: Incoming grade as percentage
        grade_out_percent: Outgoing grade as percentage
        grade_change: Algebraic difference in grades (A-value)
        is_crest_curve: True if this forms a crest (convex) curve
        is_sag_curve: True if this forms a sag (concave) curve
        bvc_station: Begin Vertical Curve station
        evc_station: End Vertical Curve station

    Example:
        >>> pvi = PVI(station=200.0, elevation=105.0, curve_length=80.0)
        >>> pvi.grade_in = 0.02
        >>> pvi.grade_out = -0.01
        >>> print(f"Grade change: {pvi.grade_change_percent:.1f}%")
        Grade change: 3.0%
    """

    station: float
    elevation: float
    grade_in: Optional[float] = None
    grade_out: Optional[float] = None
    curve_length: float = 0.0
    k_value: Optional[float] = None
    description: str = ""

    def __post_init__(self):
        """Validate PVI parameters after initialization."""
        if self.station < 0:
            raise ValueError(f"Station must be non-negative, got {self.station}")

        if self.curve_length < 0:
            raise ValueError(
                f"Curve length must be non-negative, got {self.curve_length}"
            )

        # Calculate K-value if curve length and grades are known
        if (self.curve_length > 0 and
            self.grade_in is not None and
            self.grade_out is not None):
            if self.k_value is None:
                self.k_value = self.calculate_k_value()

    @property
    def grade_in_percent(self) -> Optional[float]:
        """Incoming grade as percentage (e.g., 2.5%)."""
        return self.grade_in * 100 if self.grade_in is not None else None

    @property
    def grade_out_percent(self) -> Optional[float]:
        """Outgoing grade as percentage (e.g., -1.5%)."""
        return self.grade_out * 100 if self.grade_out is not None else None

    @property
    def grade_change(self) -> Optional[float]:
        """Algebraic difference in grades (decimal).

        This is the A-value: A = |g2 - g1|
        Always positive regardless of crest or sag.
        """
        if self.grade_in is not None and self.grade_out is not None:
            return abs(self.grade_out - self.grade_in)
        return None

    @property
    def grade_change_percent(self) -> Optional[float]:
        """Algebraic difference in grades (percentage)."""
        return self.grade_change * 100 if self.grade_change is not None else None

    @property
    def is_crest_curve(self) -> bool:
        """True if this PVI forms a crest (convex) curve.

        Crest curve: incoming grade > outgoing grade (g1 > g2)
        """
        if self.grade_in is not None and self.grade_out is not None:
            return self.grade_in > self.grade_out
        return False

    @property
    def is_sag_curve(self) -> bool:
        """True if this PVI forms a sag (concave) curve.

        Sag curve: incoming grade < outgoing grade (g1 < g2)
        """
        if self.grade_in is not None and self.grade_out is not None:
            return self.grade_in < self.grade_out
        return False

    @property
    def has_curve(self) -> bool:
        """True if this PVI has a vertical curve (curve_length > 0)."""
        return self.curve_length > 0

    @property
    def bvc_station(self) -> Optional[float]:
        """Begin Vertical Curve station.

        BVC is located L/2 before the PVI station.
        Returns None if no curve at this PVI.
        """
        if self.curve_length > 0:
            return self.station - (self.curve_length / 2.0)
        return None

    @property
    def evc_station(self) -> Optional[float]:
        """End Vertical Curve station.

        EVC is located L/2 after the PVI station.
        Returns None if no curve at this PVI.
        """
        if self.curve_length > 0:
            return self.station + (self.curve_length / 2.0)
        return None

    def calculate_k_value(self) -> float:
        """Calculate K-value from curve length and grade change.

        K = L / A
        where:
            L = curve length (m)
            A = |g2 - g1| * 100 (% grade change)

        Returns:
            K-value in m/% units

        Raises:
            ValueError: If grades are not set or curve length is zero
        """
        if self.curve_length <= 0:
            raise ValueError("Cannot calculate K-value: curve_length is zero")

        if self.grade_change is None:
            raise ValueError("Cannot calculate K-value: grades not set")

        grade_change_percent = self.grade_change * 100

        if grade_change_percent == 0:
            raise ValueError("Cannot calculate K-value: grade change is zero")

        return self.curve_length / grade_change_percent

    def calculate_curve_length_from_k(self, k_value: float) -> float:
        """Calculate required curve length for a given K-value.

        L = K * A
        where:
            K = K-value (m/%)
            A = |g2 - g1| * 100 (% grade change)

        Args:
            k_value: Desired K-value (m/%)

        Returns:
            Required curve length (m)

        Raises:
            ValueError: If grades are not set
        """
        if self.grade_change is None:
            raise ValueError("Cannot calculate curve length: grades not set")

        grade_change_percent = self.grade_change * 100
        return k_value * grade_change_percent

    def validate_k_value(self, design_speed: float) -> Tuple[bool, str]:
        """Validate K-value against design standards.

        Args:
            design_speed: Design speed in km/h

        Returns:
            Tuple of (is_valid, message)
        """
        if self.k_value is None:
            return False, "K-value not calculated"

        if design_speed not in DESIGN_STANDARDS:
            return False, f"No standards for design speed {design_speed} km/h"

        standards = DESIGN_STANDARDS[design_speed]

        if self.is_crest_curve:
            min_k = standards["k_crest"]
            curve_type = "crest"
        elif self.is_sag_curve:
            min_k = standards["k_sag"]
            curve_type = "sag"
        else:
            return False, "Cannot determine curve type (grades not set)"

        if self.k_value >= min_k:
            return True, (
                f"K-value {self.k_value:.1f} meets minimum {min_k:.1f} "
                f"for {curve_type} at {design_speed} km/h"
            )
        else:
            return False, (
                f"K-value {self.k_value:.1f} below minimum {min_k:.1f} "
                f"for {curve_type} at {design_speed} km/h"
            )

    def __repr__(self) -> str:
        """String representation for debugging."""
        curve_info = f"L={self.curve_length:.1f}m" if self.curve_length > 0 else "No curve"
        grade_info = ""

        if self.grade_in is not None and self.grade_out is not None:
            grade_info = (
                f" g_in={self.grade_in_percent:.2f}% "
                f"g_out={self.grade_out_percent:.2f}%"
            )

        return (
            f"PVI(sta={self.station:.1f}m, elev={self.elevation:.3f}m, "
            f"{curve_info}{grade_info})"
        )


__all__ = ["PVI"]