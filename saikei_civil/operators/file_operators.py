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
File Operations
================

IFC file creation and management operators.

This module provides Blender operators for creating and managing IFC files
within the Saikei Civil addon. These operators handle fundamental file
operations like creating new IFC projects with proper initialization.

Operators:
    BC_OT_new_ifc_file: Create a new IFC file with Saikei Civil schema
"""

import bpy
from bpy.props import StringProperty, FloatProperty, IntProperty, BoolProperty

# Import from parent operators module
from . import NativeIfcManager


class BC_OT_new_ifc_file(bpy.types.Operator):
    """
    Create a new IFC file.

    Initializes a new IFC file with proper project structure and schema.
    This creates an empty IFC project that can be populated with civil
    engineering entities like alignments, profiles, and terrain.

    The new file uses IFC 4.3 schema which supports civil infrastructure
    entities and is managed through the NativeIfcManager.

    Usage context: Called when starting a new Saikei Civil project or
    when the user needs a fresh IFC file to work with.
    """
    bl_idname = "bc.new_ifc_file"
    bl_label = "New IFC File"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        ifc = NativeIfcManager.new_file()
        self.report({'INFO'}, f"Created new IFC file: {ifc.schema}")
        return {'FINISHED'}




# Registration
classes = (
    BC_OT_new_ifc_file,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
