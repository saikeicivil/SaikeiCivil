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
