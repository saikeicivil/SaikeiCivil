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
Native IFC Manager Module (Backwards Compatibility Shim)
=========================================================

This module has been refactored into the ifc_manager package.
This shim provides backwards compatibility for existing imports.

New code should import from:
    from blendercivil.core.ifc_manager import NativeIfcManager

This shim re-exports all public API from the new package.
"""

# Re-export everything from the new package for backwards compatibility
from .ifc_manager import (
    # Main class
    NativeIfcManager,
    # IFC entity creation
    create_units,
    create_geometric_context,
    create_local_placement,
    find_geometric_context,
    find_axis_subcontext,
    # Blender hierarchy
    create_blender_hierarchy,
    clear_blender_hierarchy,
    add_alignment_to_hierarchy,
    add_geomodel_to_hierarchy,
    # Validation
    validate_for_external_viewers,
    validate_and_report,
)

__version__ = "1.0.0"
__author__ = "Michael Yoder"

__all__ = [
    "NativeIfcManager",
    "create_units",
    "create_geometric_context",
    "create_local_placement",
    "find_geometric_context",
    "find_axis_subcontext",
    "create_blender_hierarchy",
    "clear_blender_hierarchy",
    "add_alignment_to_hierarchy",
    "add_geomodel_to_hierarchy",
    "validate_for_external_viewers",
    "validate_and_report",
]
