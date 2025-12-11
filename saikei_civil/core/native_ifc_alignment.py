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
Native IFC Alignment Module (Backwards Compatibility Shim)
===========================================================

This module has been refactored into the horizontal_alignment package.
This shim provides backwards compatibility for existing imports.

New code should import from:
    from saikei.core.horizontal_alignment import NativeIfcAlignment

This shim re-exports all public API from the new package.
"""

# Re-export everything from the new package for backwards compatibility
from .horizontal_alignment import (
    # Classes
    SimpleVector,
    StationingManager,
    NativeIfcAlignment,
    # Curve geometry functions
    calculate_curve_geometry,
    calculate_curve_center,
    calculate_point_on_curve,
    get_tangent_intersection,
    # Segment building functions
    create_tangent_segment,
    create_curve_segment,
    build_composite_curve,
    cleanup_old_geometry,
)

__version__ = "1.0.0"
__author__ = "Michael Yoder"

# Export public API (matches original module)
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
