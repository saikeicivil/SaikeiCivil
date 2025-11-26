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
Horizontal Alignment Package
=============================

IFC 4.3 compliant horizontal alignment design and export.

This package provides:
- PI (Point of Intersection) based alignment design
- Circular curve insertion at interior PIs
- Stationing with station equations
- Native IFC IfcAlignmentHorizontal export

Example:
    >>> from blendercivil.core.horizontal_alignment import NativeIfcAlignment
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
