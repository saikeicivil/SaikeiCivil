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
DEPRECATED: Cross-section view overlay has been moved.

This module is a compatibility shim. Import from the correct location:

    from saikei_civil.tool.cross_section_view_overlay import (
        OverlayPosition,
        ResizeEdge,
        CrossSectionViewOverlay,
        get_cross_section_overlay,
        reset_cross_section_overlay,
        load_assembly_to_overlay,
        load_active_assembly_to_overlay,
    )

Blender-specific overlay management code belongs in the tool/ layer (Layer 2),
not core/ (Layer 1) per the three-layer architecture.
"""

import warnings

__all__ = [
    "OverlayPosition",
    "ResizeEdge",
    "CrossSectionViewOverlay",
    "get_cross_section_overlay",
    "reset_cross_section_overlay",
    "load_assembly_to_overlay",
    "load_active_assembly_to_overlay",
]

# Lazy imports to avoid potential circular dependencies
_module_cache = {}


def __getattr__(name):
    """Lazy import from tool.cross_section_view_overlay to avoid circular imports."""
    if name in __all__:
        warnings.warn(
            "Importing from core.cross_section_view_overlay is deprecated. "
            "Import from saikei_civil.tool.cross_section_view_overlay instead.",
            DeprecationWarning,
            stacklevel=2
        )
        if "module" not in _module_cache:
            from ..tool import cross_section_view_overlay
            _module_cache["module"] = cross_section_view_overlay
        return getattr(_module_cache["module"], name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
