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
            EndGradient=self.grade,  # Same as StartGradient for CONSTANTGRADIENT
            PredefinedType="CONSTANTGRADIENT"
        )

        return segment

    def get_end_point_and_tangent(self) -> tuple:
        """Calculate the exact end point and tangent direction.

        Returns:
            Tuple of ((end_station, end_elevation), (tangent_dx, tangent_dy))
        """
        theta = math.atan(self.grade)
        dx = math.cos(theta)
        dy = math.sin(theta)
        return ((self.end_station, self.end_elevation), (dx, dy))

    def to_ifc_curve_segment(
        self,
        ifc_file: ifcopenshell.file,
        start_point: tuple = None,
        start_tangent: tuple = None
    ) -> tuple:
        """Export to IFC IfcCurveSegment (GEOMETRIC layer).

        Creates geometric representation using IfcLine as ParentCurve.

        IMPORTANT: The end point calculation MUST match exactly what IFC validators
        compute when evaluating the curve at SegmentStart + SegmentLength.

        IFC Line Parameterization:
            P(t) = Pnt + t * normalize(Dir.Orientation) * Dir.Magnitude
            With Pnt=(0,0), Dir=(dx,dy), Magnitude=1.0:
            P(t) = (dx*t, dy*t)

        After Placement transformation (translation by (start_sta, start_elev)):
            End = (start_sta + dx*t, start_elev + dy*t)

        At t = SegmentLength = horizontal_length / dx:
            End = (start_sta + horizontal_length, start_elev + dy/dx * horizontal_length)
            End = (start_sta + horizontal_length, start_elev + grade * horizontal_length)

        Args:
            ifc_file: IFC file instance
            start_point: Optional (station, elevation) tuple to use as exact start
                         (for ensuring C0 continuity with previous segment)
            start_tangent: Optional (dx, dy) tuple for start tangent direction
                          (for ensuring C1 continuity - not used for tangent segments)

        Returns:
            Tuple of (IfcCurveSegment, actual_end_point, actual_end_tangent)
            where actual_end_point is computed to EXACTLY match IFC curve evaluation
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

        # Use provided start point for C0 continuity, or calculate from segment data
        if start_point is not None:
            start_sta = float(start_point[0])
            start_elev = float(start_point[1])
        else:
            start_sta = float(self.start_station)
            start_elev = float(self.start_elevation)

        placement_coords = (start_sta, start_elev)

        # Create placement at segment start
        # NOTE: RefDirection should be identity (1,0) - line's Dir already encodes grade
        placement_location = ifc_file.create_entity(
            "IfcCartesianPoint",
            Coordinates=placement_coords
        )
        placement = ifc_file.create_entity(
            "IfcAxis2Placement2D",
            Location=placement_location
            # RefDirection defaults to X-axis (1,0) - DO NOT set to grade direction!
        )

        # Calculate segment length along the line (arc length, not horizontal)
        # This is CRITICAL: SegmentLength must be the arc length parameter value
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

        # Calculate ACTUAL end point by evaluating the IFC curve EXACTLY as validators do
        # This ensures C0 continuity: next segment's start = this segment's computed end
        #
        # IFC evaluation at t = segment_length:
        #   curve_point = (dx * segment_length, dy * segment_length)
        #   world_point = placement + curve_point
        #              = (start_sta + dx * segment_length, start_elev + dy * segment_length)
        #
        # With segment_length = horizontal_length / dx:
        #   world_point = (start_sta + horizontal_length, start_elev + dy * horizontal_length / dx)
        #              = (start_sta + horizontal_length, start_elev + tan(theta) * horizontal_length)
        #              = (start_sta + horizontal_length, start_elev + grade * horizontal_length)
        #
        # CRITICAL: Use the EXACT same formula the IFC validator uses
        actual_end_sta = start_sta + dx * segment_length
        actual_end_elev = start_elev + dy * segment_length
        actual_end_point = (actual_end_sta, actual_end_elev)
        actual_end_tangent = (dx, dy)

        return curve_segment, actual_end_point, actual_end_tangent

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

    def get_end_point_and_tangent(self) -> tuple:
        """Calculate the exact end point and tangent direction.

        Returns:
            Tuple of ((end_station, end_elevation), (tangent_dx, tangent_dy))
        """
        # End tangent direction based on end grade (g2)
        theta = math.atan(self.g2)
        dx = math.cos(theta)
        dy = math.sin(theta)
        return ((self.end_station, self.end_elevation), (dx, dy))

    def to_ifc_curve_segment(
        self,
        ifc_file: ifcopenshell.file,
        start_point: tuple = None,
        start_tangent: tuple = None
    ) -> tuple:
        """Export to IFC IfcCurveSegment (GEOMETRIC layer).

        Creates geometric representation using IfcPolynomialCurve as ParentCurve.

        IMPORTANT: The end point calculation MUST match exactly what IFC validators
        compute when evaluating the curve at SegmentStart + SegmentLength.

        IFC Polynomial Parameterization:
            CoefficientsX = [0, 1] means x(t) = 0 + 1*t = t
            CoefficientsY = [C, B, A] means y(t) = C + B*t + A*t²

            With C=0, B=g1, A=(g2-g1)/(2L):
            x(t) = t
            y(t) = g1*t + A*t²

        At t = L (horizontal length = SegmentLength):
            x(L) = L
            y(L) = g1*L + A*L² = g1*L + (g2-g1)/(2L)*L² = g1*L + (g2-g1)*L/2
                 = (g1 + g2)/2 * L

        After Placement transformation (translation by (start_sta, start_elev)):
            End = (start_sta + L, start_elev + (g1+g2)/2 * L)

        Args:
            ifc_file: IFC file instance
            start_point: Optional (station, elevation) tuple to use as exact start
                         (for ensuring C0 continuity with previous segment)
            start_tangent: Optional (dx, dy) tuple for start tangent direction
                          (for ensuring C1 continuity)

        Returns:
            Tuple of (IfcCurveSegment, actual_end_point, actual_end_tangent)
            where actual_end_point is computed to EXACTLY match IFC curve evaluation
        """
        # Use provided start point for C0 continuity, or use segment data
        if start_point is not None:
            start_sta = float(start_point[0])
            start_elev = float(start_point[1])
        else:
            start_sta = float(self.start_station)
            start_elev = float(self.start_elevation)

        # Polynomial coefficients for parabola in LOCAL coordinates: y = Ax² + Bx + C
        # The polynomial is in the ParentCurve's local coordinate system (starts at origin).
        # The Placement transforms it to world coordinates by adding (start_sta, start_elev).
        #
        # Local curve: at t=0, we want y=0 (not start_elev!)
        # At t=L, we want y = elevation_change = (g1 + g2)/2 * L
        A = (self.g2 - self.g1) / (2.0 * self.length)
        B = self.g1
        C = 0.0  # Curve starts at LOCAL origin (0, 0), Placement adds world offset

        # Create IfcPolynomialCurve with X and Y coefficients
        # CoefficientsX = [0, 1] means x(t) = 0 + 1*t = t
        # CoefficientsY = [C, B, A] means y(t) = C + B*t + A*t² = 0 + g1*t + A*t²
        #
        # IMPORTANT: Since x(t) = t, the parameter t IS the horizontal distance.
        # Therefore SegmentLength must be the HORIZONTAL length, not arc length!
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

        # Use HORIZONTAL length as SegmentLength since polynomial is parameterized by t
        # where x(t) = t (horizontal distance from start)
        segment_length = float(self.length)

        # Create placement at segment start
        placement = ifc_file.create_entity(
            "IfcAxis2Placement2D",
            Location=ifc_file.create_entity(
                "IfcCartesianPoint",
                Coordinates=(start_sta, start_elev)
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
            SegmentLength=ifc_file.create_entity("IfcLengthMeasure", segment_length),
            ParentCurve=polynomial
        )

        # Calculate ACTUAL end point by evaluating the IFC curve EXACTLY as validators do
        # This ensures C0 continuity: next segment's start = this segment's computed end
        #
        # IFC evaluation at t = segment_length = L:
        #   curve_point = (x(L), y(L)) = (L, g1*L + A*L²)
        #   world_point = placement + curve_point
        #              = (start_sta + L, start_elev + g1*L + A*L²)
        #
        # Where A*L² = (g2-g1)/(2L) * L² = (g2-g1)*L/2
        # So y(L) = g1*L + (g2-g1)*L/2 = (g1 + g2)/2 * L
        #
        # CRITICAL: Compute using the EXACT same formula the IFC curve uses
        poly_x_at_L = segment_length  # x(t) = t, so x(L) = L
        poly_y_at_L = B * segment_length + A * segment_length * segment_length  # y = Bt + At²

        actual_end_sta = start_sta + poly_x_at_L
        actual_end_elev = start_elev + poly_y_at_L
        actual_end_point = (actual_end_sta, actual_end_elev)

        # End tangent direction based on end grade (g2)
        # y'(t) = B + 2At, so at t=L: y'(L) = B + 2A*L = g1 + 2*(g2-g1)/(2L)*L = g1 + (g2-g1) = g2
        theta = math.atan(self.g2)
        end_dx = math.cos(theta)
        end_dy = math.sin(theta)
        actual_end_tangent = (end_dx, end_dy)

        return curve_segment, actual_end_point, actual_end_tangent

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