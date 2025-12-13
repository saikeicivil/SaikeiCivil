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
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================

"""
DEPRECATED: Blender hierarchy module has been moved.

This module is a compatibility shim. Import from the correct location:

    from saikei_civil.tool.blender_hierarchy import (
        create_blender_hierarchy,
        clear_blender_hierarchy,
        get_or_find_collection,
        get_or_find_object,
        # ... etc
    )

Blender-specific code belongs in the tool/ layer (Layer 2), not core/ (Layer 1)
per the three-layer architecture.
"""

import warnings

__all__ = [
    "create_blender_hierarchy",
    "clear_blender_hierarchy",
    "get_or_find_collection",
    "get_or_find_object",
    "add_alignment_to_hierarchy",
    "add_geomodel_to_hierarchy",
    "PROJECT_COLLECTION_NAME",
    "PROJECT_EMPTY_NAME",
    "SITE_EMPTY_NAME",
    "ROAD_EMPTY_NAME",
    "ALIGNMENTS_EMPTY_NAME",
    "GEOMODELS_EMPTY_NAME",
]

# Lazy imports to avoid potential circular dependencies
_module_cache = {}


def __getattr__(name):
    """Lazy import from tool.blender_hierarchy to avoid circular imports."""
    if name in __all__:
        warnings.warn(
            "Importing from core.ifc_manager.blender_hierarchy is deprecated. "
            "Import from saikei_civil.tool.blender_hierarchy instead.",
            DeprecationWarning,
            stacklevel=2
        )
        if "module" not in _module_cache:
            from ...tool import blender_hierarchy
            _module_cache["module"] = blender_hierarchy
        return getattr(_module_cache["module"], name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
