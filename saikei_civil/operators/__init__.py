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
    from ..core.ifc_manager.transaction import TransactionManager

    # Make them available to operator modules
    import sys
    current_module = sys.modules[__name__]
    current_module.NativeIfcManager = NativeIfcManager
    current_module.NativeIfcAlignment = NativeIfcAlignment
    current_module.AlignmentVisualizer = AlignmentVisualizer
    current_module.TransactionManager = TransactionManager

    # Import operator modules
    from . import base_operator  # Must be first - provides base class
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
    from . import alignment_operators_v2  # New three-layer architecture

    _operator_modules = [
        base_operator,  # Register first - provides undo/redo operators
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
        alignment_operators_v2,  # New three-layer architecture
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
