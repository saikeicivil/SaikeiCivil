# ==============================================================================
# BlenderCivil - Civil Engineering Tools for Blender
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
Native IFC Alignment Module (Backwards Compatibility Shim)
===========================================================

This module has been refactored into the horizontal_alignment package.
This shim provides backwards compatibility for existing imports.

New code should import from:
    from blendercivil.core.horizontal_alignment import NativeIfcAlignment

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
