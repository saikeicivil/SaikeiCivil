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
DEPRECATED: Alignment update system has been moved to operators layer.

Import from the correct location:

    from saikei_civil.operators.update_system_operators import (
        register_alignment,
        unregister_alignment,
        get_alignment_from_pi,
        saikei_update_handler,
        register_handler,
        unregister_handler,
        SAIKEI_OT_update_alignment,
        SAIKEI_OT_toggle_auto_update,
        AlignmentVisualizer,
    )

Blender operators and handlers belong in the operators/ layer (Layer 3),
not core/ (Layer 1) per the three-layer architecture.
"""

import warnings

__all__ = [
    "register_alignment",
    "unregister_alignment",
    "get_alignment_from_pi",
    "saikei_update_handler",
    "register_handler",
    "unregister_handler",
    "SAIKEI_OT_update_alignment",
    "SAIKEI_OT_toggle_auto_update",
    "AlignmentVisualizer",
    "register",
    "unregister",
    "test_system",
]

# Lazy imports to avoid circular dependency with operators module
_module_cache = {}


def __getattr__(name):
    """Lazy import from operators.update_system_operators to avoid circular imports."""
    if name in __all__:
        warnings.warn(
            "Importing from core.complete_update_system is deprecated. "
            "Import from saikei_civil.operators.update_system_operators instead.",
            DeprecationWarning,
            stacklevel=2
        )
        if "module" not in _module_cache:
            from ..operators import update_system_operators
            _module_cache["module"] = update_system_operators
        return getattr(_module_cache["module"], name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
