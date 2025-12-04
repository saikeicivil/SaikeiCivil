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
Saikei Civil Operators Module

Blender operators for user actions and commands.
All operator classes will be organized here.
"""

import bpy
from .. import core
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Conditionally import operator modules based on IFC support
_operator_modules = []

if core.has_ifc_support():
    # Import core classes needed by operators
    from ..core.native_ifc_manager import NativeIfcManager
    from ..core.native_ifc_alignment import NativeIfcAlignment
    from ..core.alignment_visualizer import AlignmentVisualizer

    # Make them available to operator modules
    import sys
    current_module = sys.modules[__name__]
    current_module.NativeIfcManager = NativeIfcManager
    current_module.NativeIfcAlignment = NativeIfcAlignment
    current_module.AlignmentVisualizer = AlignmentVisualizer

    # Import operator modules
    from . import alignment_management_operators
    from . import alignment_operators
    from . import file_operators
    from . import pi_operators
    from . import validation_operators
    from . import georef_operators
    from . import vertical_operators
    from . import cross_section_operators
    from . import cross_section_import_export
    from . import visualization_operators
    from . import curve_operators
    from . import corridor_operators
    from . import ifc_hierarchy_operators
    from . import profile_view_operators
    from . import stationing_operators
    from . import terrain_sampling_operators

    _operator_modules = [
        alignment_management_operators,
        alignment_operators,
        file_operators,
        pi_operators,
        validation_operators,
        georef_operators,
        vertical_operators,
        cross_section_operators,
        cross_section_import_export,
        visualization_operators,
        curve_operators,
        corridor_operators,
        ifc_hierarchy_operators,
        profile_view_operators,
        stationing_operators,
        terrain_sampling_operators,
    ]


def register():
    """Register operators"""
    logger.info("Operators module loaded")

    if _operator_modules:
        for module in _operator_modules:
            module.register()
        logger.info("Registered %d operator modules", len(_operator_modules))
    else:
        logger.warning("IFC operators disabled (ifcopenshell not found)")


def unregister():
    """Unregister operators"""
    if _operator_modules:
        for module in reversed(_operator_modules):
            module.unregister()
