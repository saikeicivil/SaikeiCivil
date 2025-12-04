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
Horizontal Curve Geometry Module
=================================

Provides curve geometry calculations for horizontal alignments.
Includes functions for computing curve parameters from PI positions.
"""

import logging
import math
from typing import Optional

from .vector import SimpleVector

logger = logging.getLogger(__name__)


def calculate_curve_geometry(
    prev_pi: SimpleVector,
    curr_pi: SimpleVector,
    next_pi: SimpleVector,
    radius: float
) -> Optional[dict]:
    """Calculate horizontal curve geometry from three PIs.

    Computes curve parameters for a circular arc that fits between
    two tangent lines meeting at curr_pi.

    Args:
        prev_pi: Previous PI position (defines incoming tangent)
        curr_pi: Current PI position (curve location)
        next_pi: Next PI position (defines outgoing tangent)
        radius: Curve radius in meters

    Returns:
        Dictionary with curve data:
        - bc: Begin Curve point (SimpleVector)
        - ec: End Curve point (SimpleVector)
        - radius: Curve radius (float)
        - arc_length: Length of curve arc (float)
        - deflection: Signed deflection angle in radians (float)
        - start_direction: Direction at BC in radians (float)
        - turn_direction: 'LEFT' or 'RIGHT' (str)

        Returns None if curve cannot be computed (collinear PIs)

    Example:
        >>> prev = SimpleVector(0, 0)
        >>> curr = SimpleVector(100, 0)
        >>> next = SimpleVector(100, 100)
        >>> curve = calculate_curve_geometry(prev, curr, next, 50.0)
        >>> print(f"Arc length: {curve['arc_length']:.2f}m")
    """
    # Calculate tangent unit vectors
    t1 = (curr_pi - prev_pi).normalized()
    t2 = (next_pi - curr_pi).normalized()

    # Calculate signed deflection angle
    angle1 = math.atan2(t1.y, t1.x)
    angle2 = math.atan2(t2.y, t2.x)

    deflection = angle2 - angle1

    # Normalize to [-pi, pi]
    if deflection > math.pi:
        deflection -= 2 * math.pi
    elif deflection < -math.pi:
        deflection += 2 * math.pi

    # Check if deflection is too small (nearly collinear)
    if abs(deflection) < 0.001:
        logger.debug("Deflection angle too small for curve")
        return None

    # Calculate curve geometry
    # Tangent length: T = R * tan(|delta|/2)
    tangent_length = radius * math.tan(abs(deflection) / 2)

    # BC = PI - T * tangent1_direction
    bc = curr_pi - t1 * tangent_length

    # EC = PI + T * tangent2_direction
    ec = curr_pi + t2 * tangent_length

    # Arc length: L = R * |delta|
    arc_length = radius * abs(deflection)

    # Turn direction based on deflection sign
    # Positive deflection = left turn (counter-clockwise)
    # Negative deflection = right turn (clockwise)
    turn_direction = 'LEFT' if deflection > 0 else 'RIGHT'

    return {
        'bc': bc,
        'ec': ec,
        'radius': radius,
        'arc_length': arc_length,
        'deflection': deflection,
        'start_direction': angle1,
        'turn_direction': turn_direction
    }


def calculate_curve_center(
    bc: SimpleVector,
    start_direction: float,
    radius: float,
    turn_direction: str
) -> SimpleVector:
    """Calculate curve center point from BC and direction.

    Args:
        bc: Begin Curve point
        start_direction: Tangent direction at BC (radians)
        radius: Curve radius
        turn_direction: 'LEFT' or 'RIGHT'

    Returns:
        Center point as SimpleVector
    """
    # Center is perpendicular to tangent at BC
    if turn_direction == 'LEFT':
        # Center is 90 degrees counter-clockwise from tangent
        center_angle = start_direction + math.pi / 2
    else:
        # Center is 90 degrees clockwise from tangent
        center_angle = start_direction - math.pi / 2

    center_x = bc.x + radius * math.cos(center_angle)
    center_y = bc.y + radius * math.sin(center_angle)

    return SimpleVector(center_x, center_y)


def calculate_point_on_curve(
    center: SimpleVector,
    radius: float,
    start_angle: float,
    arc_angle: float,
    turn_direction: str
) -> SimpleVector:
    """Calculate point on circular arc at given arc angle.

    Args:
        center: Curve center point
        radius: Curve radius
        start_angle: Angle at BC (radians from X-axis)
        arc_angle: Angle along arc from BC (radians)
        turn_direction: 'LEFT' (CCW) or 'RIGHT' (CW)

    Returns:
        Point on curve as SimpleVector
    """
    if turn_direction == 'LEFT':
        angle = start_angle + arc_angle
    else:
        angle = start_angle - arc_angle

    x = center.x + radius * math.cos(angle)
    y = center.y + radius * math.sin(angle)

    return SimpleVector(x, y)


def get_tangent_intersection(
    p1: SimpleVector,
    d1: float,
    p2: SimpleVector,
    d2: float
) -> Optional[SimpleVector]:
    """Calculate intersection point of two tangent lines.

    Args:
        p1: Point on first line
        d1: Direction of first line (radians)
        p2: Point on second line
        d2: Direction of second line (radians)

    Returns:
        Intersection point, or None if lines are parallel
    """
    # Line 1: p1 + t1 * (cos(d1), sin(d1))
    # Line 2: p2 + t2 * (cos(d2), sin(d2))

    cos1, sin1 = math.cos(d1), math.sin(d1)
    cos2, sin2 = math.cos(d2), math.sin(d2)

    # Solve system of equations
    det = cos1 * (-sin2) - (-sin1) * cos2

    if abs(det) < 1e-10:
        # Lines are parallel
        return None

    dx = p2.x - p1.x
    dy = p2.y - p1.y

    t1 = ((-sin2) * dx + cos2 * dy) / det

    x = p1.x + t1 * cos1
    y = p1.y + t1 * sin1

    return SimpleVector(x, y)


__all__ = [
    "calculate_curve_geometry",
    "calculate_curve_center",
    "calculate_point_on_curve",
    "get_tangent_intersection",
]
