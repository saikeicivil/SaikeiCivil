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
Saikei Civil UI Module

User interface panels and menus for Saikei Civil.
All UI classes will be organized here.
"""

import bpy
from .. import core

from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Always import dependency panel (no IFC dependency)
from . import dependency_panel

# Import alignment properties (no IFC dependency for properties)
from . import alignment_properties

# Import georeferencing properties (no IFC dependency for properties)
from . import georef_properties

# Import vertical alignment properties (no IFC dependency for properties)
from . import vertical_properties

# Import cross section properties (no IFC dependency for properties)
from . import cross_section_properties

# Import profile view properties (no IFC dependency for properties)
from . import profile_view_properties

# Import corridor properties (no IFC dependency for properties)
from . import corridor_properties

# List of UI modules
_ui_modules = [dependency_panel]

# Conditionally import IFC-dependent UI modules
if core.has_ifc_support():
    # Import core classes needed by UI panels
    from ..core.native_ifc_manager import NativeIfcManager

    # Make them available to UI modules
    import sys
    current_module = sys.modules[__name__]
    current_module.NativeIfcManager = NativeIfcManager

    # Import UI panel modules
    from . import file_management_panel
    from . import alignment_panel
    from . import validation_panel
    from . import corridor_panel
    from . import panels
    from .panels import profile_view_panel

    _ui_modules.extend([
        file_management_panel,
        alignment_panel,
        validation_panel,
        corridor_panel,
        panels,
        profile_view_panel,
    ])


def register():
    """Register UI classes"""
    logger.debug("UI module loaded")

    # Register alignment properties FIRST (required by other modules)
    alignment_properties.register()

    # Register other property modules
    georef_properties.register()
    vertical_properties.register()
    cross_section_properties.register()
    profile_view_properties.register()
    corridor_properties.register()

    # Register UI panel modules
    for module in _ui_modules:
        module.register()

    logger.debug("Registered %s UI panel modules", len(_ui_modules))


def unregister():
    """Unregister UI classes"""
    # Unregister UI panel modules
    for module in reversed(_ui_modules):
        module.unregister()

    # Unregister properties in reverse order
    corridor_properties.unregister()
    profile_view_properties.unregister()
    cross_section_properties.unregister()
    vertical_properties.unregister()
    georef_properties.unregister()

    # Unregister alignment properties LAST (unregister first registered last)
    alignment_properties.unregister()
