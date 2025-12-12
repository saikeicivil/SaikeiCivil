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
Saikei Civil Core Module

Core functionality and data structures for Saikei Civil.
This module contains:
- Interface definitions (tool.py) for the three-layer architecture
- IFC utilities and managers
- Geometry helpers and core algorithms

Architecture:
    Layer 1: Core (this module) - Pure Python interfaces and business logic
    Layer 2: Tool (saikei_civil.tool) - Blender-specific implementations
    Layer 3: BIM Modules - UI, operators, and properties
"""

import bpy

# Import logging configuration first (no dependencies)
from .logging_config import get_logger, setup_logging

# Import interface definitions (no external dependencies)
from .tool import (
    interface,
    Ifc,
    Blender,
    Alignment,
    VerticalAlignment,
    Georeference,
    CrossSection,
    Corridor,
    Spatial,
    Visualizer,
)

logger = get_logger(__name__)

# Always import dependency_manager (no ifcopenshell dependency)
from . import dependency_manager

# Conditionally import IFC-dependent modules
_ifc_modules_loaded = False
_ifc_modules = []

try:
    import ifcopenshell

    # Import IFC-dependent modules
    from . import ifc_api  # API wrappers for ifcopenshell.api
    from . import ifc_manager  # Refactored package
    from . import native_ifc_manager  # Backwards compatibility shim
    from . import ifc_relationship_manager
    from . import horizontal_alignment  # Refactored package
    from . import native_ifc_alignment  # Backwards compatibility shim
    from . import vertical_alignment  # Refactored package
    from . import native_ifc_vertical_alignment  # Backwards compatibility shim
    from . import native_ifc_cross_section
    from . import corridor  # Pure Python corridor logic (three-layer architecture)
    from . import alignment_3d
    from . import alignment_visualizer
    from . import alignment_registry
    from . import complete_update_system
    from . import ifc_geometry_builders
    from . import corridor_mesh_generator
    from . import profile_view_data
    from . import profile_view_renderer
    from . import profile_view_overlay

    _ifc_modules = [
        ifc_manager,
        ifc_relationship_manager,
        horizontal_alignment,
        vertical_alignment,
        native_ifc_cross_section,
        corridor,  # Pure Python corridor logic
        alignment_3d,
        alignment_visualizer,
        alignment_registry,
        complete_update_system,
        ifc_geometry_builders,
        corridor_mesh_generator,  # Deprecated, kept for backwards compatibility
        profile_view_data,
        profile_view_renderer,
        profile_view_overlay,
    ]
    _ifc_modules_loaded = True

except ImportError as e:
    logger.warning("IFC modules not available: %s", e)
    logger.info("Install ifcopenshell to enable IFC features")


def register():
    """Register core module"""
    logger.info("Core module loaded")

    if _ifc_modules_loaded:
        logger.info("IFC features enabled")
    else:
        logger.warning("IFC features disabled (ifcopenshell not found)")


def unregister():
    """Unregister core module"""
    pass


def has_ifc_support():
    """Check if IFC support is available"""
    return _ifc_modules_loaded
