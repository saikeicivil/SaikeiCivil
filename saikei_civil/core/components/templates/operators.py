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
DEPRECATED: Template operators have been moved.

This module is a compatibility shim. Import from the correct location:

    from saikei_civil.operators.template_operators import (
        SAIKEI_OT_load_template,
        SAIKEI_OT_template_browser,
    )

Operators should not be in the core layer (Layer 1) - they belong in
the operators directory (Layer 3) per the three-layer architecture.
"""

import warnings

__all__ = [
    "SAIKEI_OT_load_template",
    "SAIKEI_OT_template_browser",
    "register",
    "unregister",
]

# Lazy imports to avoid circular dependency with operators module
_module_cache = {}


def __getattr__(name):
    """Lazy import from operators.template_operators to avoid circular imports."""
    if name in __all__:
        warnings.warn(
            "Importing operators from core.components.templates.operators is deprecated. "
            "Import from saikei_civil.operators.template_operators instead.",
            DeprecationWarning,
            stacklevel=2
        )
        if "module" not in _module_cache:
            from ....operators import template_operators
            _module_cache["module"] = template_operators
        return getattr(_module_cache["module"], name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
