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
Native IFC Vertical Alignment Module (Backwards Compatibility Shim)
====================================================================

This module has been refactored into the vertical_alignment package.
This shim provides backwards compatibility for existing imports.

New code should import from:
    from blendercivil.core.vertical_alignment import VerticalAlignment, PVI

This shim re-exports all public API from the new package.
"""

# Re-export everything from the new package for backwards compatibility
from .vertical_alignment import (
    # Classes
    PVI,
    VerticalSegment,
    TangentSegment,
    ParabolicSegment,
    VerticalAlignment,
    # Helper functions
    calculate_required_curve_length,
    calculate_k_value,
    get_minimum_k_value,
    load_vertical_alignments_from_ifc,
    # Constants
    DESIGN_STANDARDS,
    MIN_K_CREST_80KPH,
    MIN_K_SAG_80KPH,
)

__version__ = "1.0.0"
__author__ = "Michael Yoder"

# Export public API (matches original module)
__all__ = [
    # Classes
    "PVI",
    "VerticalSegment",
    "TangentSegment",
    "ParabolicSegment",
    "VerticalAlignment",
    # Helper functions
    "calculate_required_curve_length",
    "calculate_k_value",
    "get_minimum_k_value",
    "load_vertical_alignments_from_ifc",
    # Constants
    "DESIGN_STANDARDS",
    "MIN_K_CREST_80KPH",
    "MIN_K_SAG_80KPH",
]
