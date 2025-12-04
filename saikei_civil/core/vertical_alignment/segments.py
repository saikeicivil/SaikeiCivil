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
Vertical Alignment Segments Module
===================================

Defines vertical alignment segment types:
- VerticalSegment: Abstract base class
- TangentSegment: Constant grade (linear)
- ParabolicSegment: Parabolic vertical curve

Segments implement both semantic (design parameters) and geometric
(IfcCurveSegment) IFC 4.3 export.
"""

import math
from abc import ABC, abstractmethod
from typing import Optional

import ifcopenshell


class VerticalSegment(ABC):
    """Abstract base class for vertical alignment segments.

    Vertical alignments are composed of segments:
    - TangentSegment: constant grade
    - ParabolicSegment: parabolic vertical curve

    All segments must implement:
    - get_elevation(station): elevation at given station
    - get_grade(station): grade at given station
    - to_ifc_segment(): export to IFC format
    """

    def __init__(self, start_station: float, end_station: float, segment_type: str):
        """Initialize base segment.

        Args:
            start_station: Starting station (m)
            end_station: Ending station (m)
            segment_type: Type identifier ("TANGENT", "PARABOLIC", etc.)
        """
        if end_station <= start_station:
            raise ValueError(
                f"End station ({end_station}) must be > start station ({start_station})"
            )

        self.start_station = start_station
        self.end_station = end_station
        self.segment_type = segment_type

    @property
    def length(self) -> float:
        """Segment length in meters."""
        return self.end_station - self.start_station

    @property
    def mid_station(self) -> float:
        """Station at segment midpoint."""
        return (self.start_station + self.end_station) / 2.0

    def contains_station(self, station: float, tolerance: float = 1e-6) -> bool:
        """Check if station is within this segment.

        Args:
            station: Station to check (m)
            tolerance: Numerical tolerance (m)

        Returns:
            True if station is in [start_station, end_station]
        """
        return (self.start_station - tolerance) <= station <= (self.end_station + tolerance)

    @abstractmethod
    def get_elevation(self, station: float) -> float:
        """Calculate elevation at given station.

        Args:
            station: Station along alignment (m)

        Returns:
            Elevation (m)

        Raises:
            ValueError: If station is outside segment bounds
        """
        pass

    @abstractmethod
    def get_grade(self, station: float) -> float:
        """Calculate grade at given station.

        Args:
            station: Station along alignment (m)

        Returns:
            Grade as decimal (e.g., 0.02 = 2%)

        Raises:
            ValueError: If station is outside segment bounds
        """
        pass

    @abstractmethod
    def to_ifc_segment(
        self, ifc_file: ifcopenshell.file
    ) -> ifcopenshell.entity_instance:
        """Export segment to IFC IfcAlignmentVerticalSegment.

        Args:
            ifc_file: IFC file instance

        Returns:
            IfcAlignmentVerticalSegment entity
        """
        pass

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"{self.__class__.__name__}({self.start_station:.1f}-{self.end_station:.1f}m)"


class TangentSegment(VerticalSegment):
    """Constant grade (tangent) segment.

    Linear elevation profile with constant grade.

    Elevation equation:
        E(x) = E0 + g * (x - x0)

    where:
        E0 = elevation at start
        g = grade (decimal)
        x = current station
        x0 = start station

    Attributes:
        start_station: Starting station (m)
        end_station: Ending station (m)
        start_elevation: Elevation at start (m)
        grade: Constant grade (decimal, e.g., 0.02 = 2%)

    Example:
        >>> tangent = TangentSegment(0.0, 100.0, 100.0, 0.02)
        >>> tangent.get_elevation(50.0)
        101.0
        >>> tangent.get_grade(50.0)
        0.02
    """

    def __init__(
        self,
        start_station: float,
        end_station: float,
        start_elevation: float,
        grade: float
    ):
        """Initialize tangent segment.

        Args:
            start_station: Starting station (m)
            end_station: Ending station (m)
            start_elevation: Elevation at start station (m)
            grade: Constant grade (decimal)
        """
        super().__init__(start_station, end_station, "TANGENT")

        self.start_elevation = start_elevation
        self.grade = grade

    @property
    def end_elevation(self) -> float:
        """Elevation at end of segment."""
        return self.start_elevation + (self.grade * self.length)

    @property
    def grade_percent(self) -> float:
        """Grade as percentage."""
        return self.grade * 100

    def get_elevation(self, station: float) -> float:
        """Calculate elevation at given station.

        Uses linear equation: E = E0 + g*(x - x0)

        Args:
            station: Station along alignment (m)

        Returns:
            Elevation (m)

        Raises:
            ValueError: If station is outside segment bounds
        """
        if not self.contains_station(station):
            raise ValueError(
                f"Station {station:.3f}m outside segment bounds "
                f"[{self.start_station:.3f}, {self.end_station:.3f}]"
            )

        distance_along = station - self.start_station
        elevation = self.start_elevation + (self.grade * distance_along)

        return elevation

    def get_grade(self, station: float) -> float:
        """Calculate grade at given station.

        For tangent segments, grade is constant everywhere.

        Args:
            station: Station along alignment (m)

        Returns:
            Grade as decimal (constant for tangent)

        Raises:
            ValueError: If station is outside segment bounds
        """
        if not self.contains_station(station):
            raise ValueError(
                f"Station {station:.3f}m outside segment bounds "
                f"[{self.start_station:.3f}, {self.end_station:.3f}]"
            )

        return self.grade

    def to_ifc_segment(
        self, ifc_file: ifcopenshell.file
    ) -> ifcopenshell.entity_instance:
        """Export to IFC IfcAlignmentVerticalSegment (SEMANTIC layer only).

        Creates IFC entity with CONSTANTGRADIENT type.

        Args:
            ifc_file: IFC file instance

        Returns:
            IfcAlignmentVerticalSegment entity
        """
        segment = ifc_file.create_entity(
            "IfcAlignmentVerticalSegment",
            StartDistAlong=self.start_station,
            HorizontalLength=self.length,
            StartHeight=self.start_elevation,
            StartGradient=self.grade,
            PredefinedType="CONSTANTGRADIENT"
        )

        return segment

    def to_ifc_curve_segment(
        self, ifc_file: ifcopenshell.file
    ) -> ifcopenshell.entity_instance:
        """Export to IFC IfcCurveSegment (GEOMETRIC layer).

        Creates geometric representation using IfcLine as ParentCurve.

        Args:
            ifc_file: IFC file instance

        Returns:
            IfcCurveSegment entity
        """
        # Calculate direction vector based on grade (in 2D distance-elevation plane)
        theta = math.atan(self.grade)
        dx = math.cos(theta)
        dy = math.sin(theta)

        # Create IfcLine through origin with direction based on grade
        direction = ifc_file.create_entity("IfcDirection", DirectionRatios=(dx, dy))
        line = ifc_file.create_entity(
            "IfcLine",
            Pnt=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0)),
            Dir=ifc_file.create_entity("IfcVector", Orientation=direction, Magnitude=1.0)
        )

        # Create placement at segment start
        # NOTE: RefDirection should be identity (1,0) - line's Dir already encodes grade
        placement_location = ifc_file.create_entity(
            "IfcCartesianPoint",
            Coordinates=(self.start_station, self.start_elevation)
        )
        placement = ifc_file.create_entity(
            "IfcAxis2Placement2D",
            Location=placement_location
            # RefDirection defaults to X-axis (1,0) - DO NOT set to grade direction!
        )

        # Calculate segment length along the line (not just horizontal)
        segment_length = self.length / dx if abs(dx) > 1e-10 else self.length

        # Create IfcCurveSegment
        curve_segment = ifc_file.create_entity(
            "IfcCurveSegment",
            Transition="CONTINUOUS",
            Placement=placement,
            SegmentStart=ifc_file.create_entity("IfcLengthMeasure", 0.0),
            SegmentLength=ifc_file.create_entity("IfcLengthMeasure", segment_length),
            ParentCurve=line
        )

        return curve_segment

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"TangentSegment({self.start_station:.1f}-{self.end_station:.1f}m, "
            f"g={self.grade_percent:.2f}%)"
        )


class ParabolicSegment(VerticalSegment):
    """Parabolic vertical curve segment.

    Smooth transition between two grades using a parabolic arc.
    Used at PVIs to provide comfortable grade changes.

    Mathematics:
        Elevation: E(x) = E_BVC + g1*x + ((g2-g1)/(2L))*x^2
        Grade:     g(x) = g1 + ((g2-g1)/L)*x

    where:
        x = distance from BVC (begin vertical curve)
        E_BVC = elevation at BVC
        g1 = incoming grade (decimal)
        g2 = outgoing grade (decimal)
        L = curve length

    Curve Types:
        - Crest: g1 > g2 (convex, looks like hilltop)
        - Sag: g1 < g2 (concave, looks like valley)

    Attributes:
        start_station: BVC station (m)
        end_station: EVC station (m)
        start_elevation: Elevation at BVC (m)
        g1: Incoming grade (decimal)
        g2: Outgoing grade (decimal)
        pvi_station: PVI station (midpoint of curve)

    Example:
        >>> curve = ParabolicSegment(
        ...     start_station=160.0,
        ...     end_station=240.0,
        ...     start_elevation=104.0,
        ...     g1=0.02,
        ...     g2=-0.01
        ... )
        >>> curve.get_elevation(200.0)  # At PVI
        105.6
    """

    def __init__(
        self,
        start_station: float,
        end_station: float,
        start_elevation: float,
        g1: float,
        g2: float,
        pvi_station: Optional[float] = None
    ):
        """Initialize parabolic segment.

        Args:
            start_station: BVC station (m)
            end_station: EVC station (m)
            start_elevation: Elevation at BVC (m)
            g1: Incoming grade (decimal)
            g2: Outgoing grade (decimal)
            pvi_station: Optional PVI station (defaults to midpoint)
        """
        super().__init__(start_station, end_station, "PARABOLIC")

        self.start_elevation = start_elevation
        self.g1 = g1
        self.g2 = g2

        # PVI is at curve midpoint
        if pvi_station is None:
            self.pvi_station = (start_station + end_station) / 2.0
        else:
            self.pvi_station = pvi_station

    @property
    def end_elevation(self) -> float:
        """Elevation at end of curve (EVC)."""
        return self.get_elevation(self.end_station)

    @property
    def is_crest(self) -> bool:
        """True if this is a crest (convex) curve."""
        return self.g1 > self.g2

    @property
    def is_sag(self) -> bool:
        """True if this is a sag (concave) curve."""
        return self.g1 < self.g2

    @property
    def grade_change(self) -> float:
        """Algebraic difference in grades (A-value)."""
        return abs(self.g2 - self.g1)

    @property
    def k_value(self) -> float:
        """K-value of this curve (L/A in m/%)."""
        grade_change_percent = self.grade_change * 100
        if grade_change_percent == 0:
            return float('inf')
        return self.length / grade_change_percent

    @property
    def pvi_elevation(self) -> float:
        """Elevation at PVI (highest/lowest point for crest/sag)."""
        return self.get_elevation(self.pvi_station)

    @property
    def turning_point_station(self) -> Optional[float]:
        """Station where grade = 0 (high/low point of curve).

        Returns None if curve doesn't cross zero grade.
        """
        # At grade = 0: g1 + ((g2-g1)/L)*x = 0
        # Solve for x: x = -g1 * L / (g2 - g1)

        if self.g2 == self.g1:
            return None  # No grade change

        x = -self.g1 * self.length / (self.g2 - self.g1)

        # Check if turning point is within curve
        if 0 <= x <= self.length:
            return self.start_station + x

        return None

    def get_elevation(self, station: float) -> float:
        """Calculate elevation at given station.

        Uses parabolic equation:
            E(x) = E_BVC + g1*x + ((g2-g1)/(2L))*x^2

        Args:
            station: Station along alignment (m)

        Returns:
            Elevation (m)

        Raises:
            ValueError: If station is outside segment bounds
        """
        if not self.contains_station(station):
            raise ValueError(
                f"Station {station:.3f}m outside segment bounds "
                f"[{self.start_station:.3f}, {self.end_station:.3f}]"
            )

        # Distance from BVC
        x = station - self.start_station

        # Parabolic elevation equation
        # E = E0 + g1*x + ((g2-g1)/(2L))*x^2
        elevation = (
            self.start_elevation +
            self.g1 * x +
            ((self.g2 - self.g1) / (2.0 * self.length)) * (x ** 2)
        )

        return elevation

    def get_grade(self, station: float) -> float:
        """Calculate grade at given station.

        Uses parabolic grade equation:
            g(x) = g1 + ((g2-g1)/L)*x

        Args:
            station: Station along alignment (m)

        Returns:
            Grade as decimal at this station

        Raises:
            ValueError: If station is outside segment bounds
        """
        if not self.contains_station(station):
            raise ValueError(
                f"Station {station:.3f}m outside segment bounds "
                f"[{self.start_station:.3f}, {self.end_station:.3f}]"
            )

        # Distance from BVC
        x = station - self.start_station

        # Linear grade change: g = g1 + ((g2-g1)/L)*x
        grade = self.g1 + ((self.g2 - self.g1) / self.length) * x

        return grade

    def to_ifc_segment(
        self, ifc_file: ifcopenshell.file
    ) -> ifcopenshell.entity_instance:
        """Export to IFC IfcAlignmentVerticalSegment.

        Creates IFC entity with PARABOLICARC type.

        Args:
            ifc_file: IFC file instance

        Returns:
            IfcAlignmentVerticalSegment entity
        """
        segment = ifc_file.create_entity(
            "IfcAlignmentVerticalSegment",
            StartDistAlong=self.start_station,
            HorizontalLength=self.length,
            StartHeight=self.start_elevation,
            StartGradient=self.g1,
            EndGradient=self.g2,
            PredefinedType="PARABOLICARC"
        )

        return segment

    def to_ifc_curve_segment(
        self, ifc_file: ifcopenshell.file
    ) -> ifcopenshell.entity_instance:
        """Export to IFC IfcCurveSegment (GEOMETRIC layer).

        Creates geometric representation using IfcPolynomialCurve as ParentCurve.
        The parabola equation is y(x) = Ax^2 + Bx + C where:
            A = (g2 - g1) / (2L)
            B = g1
            C = E_BVC (start elevation)

        Args:
            ifc_file: IFC file instance

        Returns:
            IfcCurveSegment entity
        """
        # Polynomial coefficients for parabola: y = Ax^2 + Bx + C
        A = (self.g2 - self.g1) / (2.0 * self.length)
        B = self.g1
        C = self.start_elevation

        # Create IfcPolynomialCurve with X and Y coefficients
        # CoefficientsX = (0, 1) means x(t) = 0 + 1*t = t
        # CoefficientsY = (C, B, A) means y(t) = C + B*t + A*t^2
        polynomial = ifc_file.create_entity(
            "IfcPolynomialCurve",
            Position=ifc_file.create_entity(
                "IfcAxis2Placement2D",
                Location=ifc_file.create_entity(
                    "IfcCartesianPoint", Coordinates=(0.0, 0.0)
                ),
                RefDirection=ifc_file.create_entity(
                    "IfcDirection", DirectionRatios=(1.0, 0.0)
                )
            ),
            CoefficientsX=[0.0, 1.0],
            CoefficientsY=[C, B, A]
        )

        # Calculate arc length along the parabolic curve
        curve_length = self._calculate_arc_length(self.length)

        # Create placement at segment start
        placement = ifc_file.create_entity(
            "IfcAxis2Placement2D",
            Location=ifc_file.create_entity(
                "IfcCartesianPoint",
                Coordinates=(self.start_station, self.start_elevation)
            ),
            RefDirection=ifc_file.create_entity(
                "IfcDirection", DirectionRatios=(1.0, 0.0)
            )
        )

        # Create IfcCurveSegment
        curve_segment = ifc_file.create_entity(
            "IfcCurveSegment",
            Transition="CONTINUOUS",
            Placement=placement,
            SegmentStart=ifc_file.create_entity("IfcLengthMeasure", 0.0),
            SegmentLength=ifc_file.create_entity("IfcLengthMeasure", curve_length),
            ParentCurve=polynomial
        )

        return curve_segment

    def _calculate_arc_length(self, x: float) -> float:
        """Calculate arc length along parabola from 0 to x.

        Uses closed-form solution for arc length of parabola:
        s(x) = integral of sqrt(1 + (y')^2) dx where y' = 2Ax + B

        Args:
            x: Horizontal distance from start

        Returns:
            Arc length along parabola
        """
        A = (self.g2 - self.g1) / (2.0 * self.length)
        B = self.g1

        if abs(A) < 1e-10:
            # Nearly straight line, use simplified formula
            return x * math.sqrt(1 + B**2)

        a = 4 * A**2
        b = 4 * A * B
        c = B**2 + 1

        def integral(t: float) -> float:
            sqrt_val = math.sqrt(a * t**2 + b * t + c)
            term1 = (b + 2 * a * t) / (4 * a) * sqrt_val

            inner = 2 * a * t + b + 2 * math.sqrt(a * (a * t**2 + b * t + c))
            if inner <= 0:
                term2 = 0
            else:
                term2 = (4 * a * c - b**2) / (8 * a**1.5) * math.log(abs(inner))

            return term1 + term2

        return integral(x) - integral(0.0)

    def __repr__(self) -> str:
        """String representation for debugging."""
        curve_type = "CREST" if self.is_crest else "SAG"
        return (
            f"ParabolicSegment({self.start_station:.1f}-{self.end_station:.1f}m, "
            f"{curve_type}, g1={self.g1*100:.2f}% -> g2={self.g2*100:.2f}%, "
            f"K={self.k_value:.1f})"
        )


__all__ = [
    "VerticalSegment",
    "TangentSegment",
    "ParabolicSegment",
]