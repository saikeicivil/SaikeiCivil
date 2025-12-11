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
Validation Panel
UI panel for validation and debugging tools

NOTE: The Validation panel UI has been moved to Edit > Preferences > Extensions
This file is kept for potential future operator definitions.
"""

import bpy


# NOTE: The Validation panel UI has been moved to Edit > Preferences > Extensions
# Operators (bc.validate_ifc_alignment, bc.list_all_ifc_objects) are defined in
# operators/validation_operators.py


# Registration - No classes to register (panel moved to preferences)
classes = ()

def register():
    pass

def unregister():
    pass
