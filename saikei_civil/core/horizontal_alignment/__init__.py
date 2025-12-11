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
Horizontal Alignment Package
=============================

IFC 4.3 compliant horizontal alignment design and export.

This package provides:
- PI (Point of Intersection) based alignment design
- Circular curve insertion at interior PIs
- Stationing with station equations
- Native IFC IfcAlignmentHorizontal export

Example:
    >>> from saikei.core.horizontal_alignment import NativeIfcAlignment
    >>> alignment = NativeIfcAlignment(ifc_file, "Main Road")
    >>> alignment.add_pi(0, 0)
    >>> alignment.add_pi(100, 0)
    >>> alignment.add_pi(100, 100)
    >>> alignment.insert_curve_at_pi(1, radius=50.0)
"""

# Vector utilities
from .vector import SimpleVector

# Curve geometry calculations
from .curve_geometry import (
    calculate_curve_geometry,
    calculate_curve_center,
    calculate_point_on_curve,
    get_tangent_intersection,
)

# Segment building functions
from .segment_builder import (
    create_tangent_segment,
    create_curve_segment,
    build_composite_curve,
    cleanup_old_geometry,
)

# Stationing manager
from .stationing import StationingManager

# Main alignment class
from .manager import NativeIfcAlignment

__version__ = "1.0.0"
__author__ = "Michael Yoder"

__all__ = [
    # Classes
    "SimpleVector",
    "StationingManager",
    "NativeIfcAlignment",
    # Curve geometry functions
    "calculate_curve_geometry",
    "calculate_curve_center",
    "calculate_point_on_curve",
    "get_tangent_intersection",
    # Segment building functions
    "create_tangent_segment",
    "create_curve_segment",
    "build_composite_curve",
    "cleanup_old_geometry",
]
