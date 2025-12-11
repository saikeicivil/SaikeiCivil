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
Saikei Civil Extension
Version 0.5.0

A fresh start for native IFC civil engineering design in Blender.
"""

import bpy

# Reload support for development
def _reload_modules():
    """Reload all submodules in the correct order"""
    import sys
    import importlib

    # List of submodules in dependency order
    module_names = [
        "core",
        "tool",  # Tool layer (Blender implementations of core interfaces)
        "operators",
        "ui",
    ]

    # Reload each module if it's already loaded
    for name in module_names:
        full_name = f"{__package__}.{name}"
        if full_name in sys.modules:
            importlib.reload(sys.modules[full_name])

# Attempt reload if extension is being reloaded
if "bpy" in locals():
    _reload_modules()

# Import submodules after reload
from . import preferences
from . import core
from . import tool  # Tool layer (Blender implementations of core interfaces)
from . import operators
from . import ui

# Import logging utilities
from .core.logging_config import (
    setup_logging,
    get_logger,
    log_startup_banner,
    log_startup_complete,
    log_shutdown,
)


def register():
    """Register extension modules and classes"""
    # Initialize logging first
    setup_logging()
    logger = get_logger(__name__)

    log_startup_banner("0.5.0")

    # Register modules in order
    logger.info("Loading modules...")
    preferences.register()  # Register preferences FIRST (for API keys, etc.)
    core.register()
    tool.register()       # Tool layer (Blender implementations)
    ui.register()         # Register UI properties FIRST (operators depend on them)
    operators.register()  # Then operators can use the properties

    # Register update system for real-time PI movement
    from .core import complete_update_system
    complete_update_system.register()

    log_startup_complete()


def unregister():
    """Unregister extension modules and classes"""
    logger = get_logger(__name__)
    logger.info("Saikei Civil Extension - Unregistering...")

    # Unregister update system first
    from .core import complete_update_system
    complete_update_system.unregister()

    # Unregister modules in reverse order
    operators.unregister()  # Unregister operators first (they use properties)
    ui.unregister()         # Then UI properties
    tool.unregister()       # Tool layer
    core.unregister()
    preferences.unregister()  # Unregister preferences last

    log_shutdown()


if __name__ == "__main__":
    register()
