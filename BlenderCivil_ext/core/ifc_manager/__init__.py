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
IFC Manager Package
====================

Central management for IFC file lifecycle and Blender visualization.

This package provides:
- IFC file creation and loading
- Spatial hierarchy management (Project → Site → Road)
- Blender collection/hierarchy visualization
- Validation for external viewers

Example:
    >>> from blendercivil.core.ifc_manager import NativeIfcManager
    >>> result = NativeIfcManager.new_file()
    >>> print(f"Created project: {result['project'].Name}")
"""

# Main manager class
from .manager import NativeIfcManager

# IFC entity creation
from .ifc_entities import (
    create_units,
    create_geometric_context,
    create_local_placement,
    find_geometric_context,
    find_axis_subcontext,
)

# Blender hierarchy management
from .blender_hierarchy import (
    create_blender_hierarchy,
    clear_blender_hierarchy,
    add_alignment_to_hierarchy,
    add_geomodel_to_hierarchy,
)

# Validation
from .validation import (
    validate_for_external_viewers,
    validate_and_report,
)

__version__ = "1.0.0"
__author__ = "Michael Yoder"

__all__ = [
    # Main class
    "NativeIfcManager",
    # IFC entity creation
    "create_units",
    "create_geometric_context",
    "create_local_placement",
    "find_geometric_context",
    "find_axis_subcontext",
    # Blender hierarchy
    "create_blender_hierarchy",
    "clear_blender_hierarchy",
    "add_alignment_to_hierarchy",
    "add_geomodel_to_hierarchy",
    # Validation
    "validate_for_external_viewers",
    "validate_and_report",
]
