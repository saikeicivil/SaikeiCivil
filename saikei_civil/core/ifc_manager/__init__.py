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
IFC Manager Package
====================

Central management for IFC file lifecycle and Blender visualization.

This package provides:
- IFC file creation and loading
- Spatial hierarchy management (Project → Site → Road)
- Blender collection/hierarchy visualization
- Validation for external viewers

Example:
    >>> from saikei.core.ifc_manager import NativeIfcManager
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
