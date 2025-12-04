# ==============================================================================
# Saikei Civil - Civil Engineering Tools for Blender
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
    profile_view_properties.unregister()
    cross_section_properties.unregister()
    vertical_properties.unregister()
    georef_properties.unregister()

    # Unregister alignment properties LAST (unregister first registered last)
    alignment_properties.unregister()
