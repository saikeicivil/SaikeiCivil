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
Vertical Alignment Package
===========================

IFC 4.3 compliant vertical alignment design and export.

This package provides:
- PVI (Point of Vertical Intersection) management
- Vertical curve generation (parabolic)
- Grade calculations
- Station/elevation queries
- Native IFC IfcAlignmentVertical export

Example:
    >>> from blendercivil.core.vertical_alignment import VerticalAlignment, PVI
    >>> valign = VerticalAlignment("Main Street Profile")
    >>> valign.add_pvi(0.0, 100.0)
    >>> valign.add_pvi(200.0, 105.0, curve_length=80.0)
    >>> elev = valign.get_elevation(100.0)
"""

# Constants
from .constants import (
    DESIGN_STANDARDS,
    MIN_K_CREST_80KPH,
    MIN_K_SAG_80KPH,
)

# Data classes
from .pvi import PVI

# Segment classes
from .segments import (
    ParabolicSegment,
    TangentSegment,
    VerticalSegment,
)

# Main manager class
from .manager import VerticalAlignment

# IFC loading functions
from .ifc_loader import (
    calculate_k_value,
    calculate_required_curve_length,
    get_minimum_k_value,
    load_vertical_alignments_from_ifc,
)

__version__ = "1.0.0"
__author__ = "Michael Yoder"

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