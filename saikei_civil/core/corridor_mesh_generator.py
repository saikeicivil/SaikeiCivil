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
DEPRECATED: Corridor mesh generation has been moved to the tool layer.

Import from the correct location:

    from saikei_civil.tool.corridor import LODSettings
    from saikei_civil.tool import Corridor

    # Generate mesh using the new API:
    mesh_obj, stats = Corridor.generate_corridor_mesh(
        stations=station_list,
        assembly=assembly_wrapper,
        name="Corridor",
        lod='medium'
    )

This module is a compatibility shim. Blender-specific mesh generation code
belongs in the tool/ layer (Layer 2), not core/ (Layer 1) per the three-layer
architecture.
"""

import warnings

warnings.warn(
    "Importing from core.corridor_mesh_generator is deprecated. "
    "Use saikei_civil.tool.corridor instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backwards compatibility
from ..tool.corridor import LODSettings, Corridor

__all__ = ["LODSettings", "Corridor"]
