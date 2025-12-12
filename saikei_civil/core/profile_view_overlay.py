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
DEPRECATED: Profile view overlay has been moved.

This module is a compatibility shim. Import from the correct location:

    from saikei_civil.tool.profile_view_overlay import (
        ProfileViewOverlay,
        get_profile_overlay,
        reset_profile_overlay,
        load_from_sprint3_vertical,
        sync_to_sprint3_vertical,
    )

Blender-specific overlay management code belongs in the tool/ layer (Layer 2),
not core/ (Layer 1) per the three-layer architecture.
"""

import warnings

warnings.warn(
    "Importing from core.profile_view_overlay is deprecated. "
    "Import from saikei_civil.tool.profile_view_overlay instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backwards compatibility
from ..tool.profile_view_overlay import (
    ProfileViewOverlay,
    get_profile_overlay,
    reset_profile_overlay,
    load_from_sprint3_vertical,
    sync_to_sprint3_vertical,
)

__all__ = [
    "ProfileViewOverlay",
    "get_profile_overlay",
    "reset_profile_overlay",
    "load_from_sprint3_vertical",
    "sync_to_sprint3_vertical",
]
