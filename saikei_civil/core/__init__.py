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
    from . import ifc_manager  # Refactored package
    from . import native_ifc_manager  # Backwards compatibility shim
    from . import ifc_relationship_manager
    from . import horizontal_alignment  # Refactored package
    from . import native_ifc_alignment  # Backwards compatibility shim
    from . import vertical_alignment  # Refactored package
    from . import native_ifc_vertical_alignment  # Backwards compatibility shim
    from . import native_ifc_cross_section
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
        alignment_3d,
        alignment_visualizer,
        alignment_registry,
        complete_update_system,
        ifc_geometry_builders,
        corridor_mesh_generator,
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
