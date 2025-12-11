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
2D Vector Utilities for Horizontal Alignment
==============================================

Provides a lightweight 2D vector class for alignment geometry calculations.
This avoids dependency on mathutils for pure Python operations.
"""

import math


class SimpleVector:
    """Lightweight 2D vector for alignment geometry calculations.

    Provides basic vector operations without external dependencies.
    Used for PI positions, tangent directions, and curve geometry.

    Attributes:
        x: X coordinate (Easting)
        y: Y coordinate (Northing)

    Example:
        >>> v1 = SimpleVector(100.0, 200.0)
        >>> v2 = SimpleVector(150.0, 250.0)
        >>> direction = (v2 - v1).normalized()
        >>> print(f"Length: {(v2 - v1).length:.2f}")
    """

    def __init__(self, x, y=0):
        """Initialize vector from coordinates or tuple/list.

        Args:
            x: X coordinate, or tuple/list of (x, y)
            y: Y coordinate (ignored if x is tuple/list)
        """
        if isinstance(x, (list, tuple)):
            self.x = float(x[0])
            self.y = float(x[1])
        else:
            self.x = float(x)
            self.y = float(y)

    def __sub__(self, other):
        """Subtract two vectors."""
        return SimpleVector(self.x - other.x, self.y - other.y)

    def __add__(self, other):
        """Add two vectors."""
        return SimpleVector(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar):
        """Multiply vector by scalar."""
        return SimpleVector(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar):
        """Multiply scalar by vector (reverse)."""
        return self.__mul__(scalar)

    def __truediv__(self, scalar):
        """Divide vector by scalar."""
        return SimpleVector(self.x / scalar, self.y / scalar)

    def __neg__(self):
        """Negate vector."""
        return SimpleVector(-self.x, -self.y)

    def __eq__(self, other):
        """Check equality with tolerance."""
        if not isinstance(other, SimpleVector):
            return False
        return abs(self.x - other.x) < 1e-9 and abs(self.y - other.y) < 1e-9

    def __repr__(self):
        """String representation."""
        return f"SimpleVector({self.x:.3f}, {self.y:.3f})"

    @property
    def length(self) -> float:
        """Vector magnitude (length)."""
        return math.sqrt(self.x**2 + self.y**2)

    @property
    def length_squared(self) -> float:
        """Squared length (avoids sqrt for comparisons)."""
        return self.x**2 + self.y**2

    @property
    def angle(self) -> float:
        """Angle in radians from positive X axis."""
        return math.atan2(self.y, self.x)

    def normalized(self) -> "SimpleVector":
        """Return unit vector in same direction.

        Returns:
            Unit vector, or zero vector if length is zero.
        """
        length = self.length
        if length > 0:
            return SimpleVector(self.x / length, self.y / length)
        return SimpleVector(0, 0)

    def dot(self, other: "SimpleVector") -> float:
        """Dot product with another vector.

        Args:
            other: Vector to dot with

        Returns:
            Scalar dot product
        """
        return self.x * other.x + self.y * other.y

    def cross(self, other: "SimpleVector") -> float:
        """2D cross product (returns scalar z-component).

        Args:
            other: Vector to cross with

        Returns:
            Scalar representing z-component of 3D cross product
        """
        return self.x * other.y - self.y * other.x

    def rotate(self, angle: float) -> "SimpleVector":
        """Rotate vector by angle.

        Args:
            angle: Rotation angle in radians (counter-clockwise positive)

        Returns:
            Rotated vector
        """
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return SimpleVector(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a
        )

    def perpendicular(self, clockwise: bool = False) -> "SimpleVector":
        """Return perpendicular vector.

        Args:
            clockwise: If True, rotate 90° clockwise; else counter-clockwise

        Returns:
            Perpendicular vector with same length
        """
        if clockwise:
            return SimpleVector(self.y, -self.x)
        return SimpleVector(-self.y, self.x)

    def to_tuple(self) -> tuple:
        """Convert to (x, y) tuple."""
        return (self.x, self.y)

    def distance_to(self, other: "SimpleVector") -> float:
        """Calculate distance to another point.

        Args:
            other: Target point

        Returns:
            Distance in same units as coordinates
        """
        return (other - self).length


__all__ = ["SimpleVector"]
