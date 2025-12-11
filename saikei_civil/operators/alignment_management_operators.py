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
Alignment Management Operators
==============================

Helper operators for managing alignments, active alignment, and alignment list.

This module provides Blender operators for working with IFC alignments within
the Saikei Civil addon. These operators handle alignment list management,
active alignment selection, and collection selection.

Operators:
    BC_OT_refresh_alignment_list: Refresh the alignment list from IFC file
    BC_OT_set_active_alignment: Set the active alignment by index
    BC_OT_select_active_alignment_collection: Select the active alignment's collection
"""

import bpy
from bpy.props import StringProperty, IntProperty


class BC_OT_refresh_alignment_list(bpy.types.Operator):
    """
    Refresh the alignment list from IFC file.

    Scans the loaded IFC file and updates the alignment list property
    in the UI. This operator is typically called when:
    - A new IFC file is loaded
    - User manually requests a refresh
    - IFC file contents have been modified

    The operation is fast and non-destructive, only updating the
    displayed list without modifying the IFC data.
    """
    bl_idname = "bc.refresh_alignment_list"
    bl_label = "Refresh Alignment List"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        from ..ui.alignment_properties import refresh_alignment_list
        
        refresh_alignment_list(context)
        
        props = context.scene.bc_alignment
        self.report({'INFO'}, props.status_message)
        
        return {'FINISHED'}


class BC_OT_set_active_alignment(bpy.types.Operator):
    """
    Set the active alignment by index.

    Designates a specific alignment as the "active" alignment for operations.
    The active alignment is used by other operators as the default target for:
    - Station calculations
    - Profile view display
    - Corridor generation
    - Vertical alignment operations

    Properties:
        alignment_index: Index of alignment in the list to set as active

    This operator refreshes the alignment list before setting the active
    alignment to ensure the index is valid.
    """
    bl_idname = "bc.set_active_alignment"
    bl_label = "Set Active Alignment"
    bl_options = {'REGISTER', 'UNDO'}
    
    alignment_index: IntProperty(
        name="Alignment Index",
        description="Index of alignment to set as active",
        default=0
    )
    
    def execute(self, context):
        from . import NativeIfcManager
        from ..ui.alignment_properties import set_active_alignment, refresh_alignment_list
        
        # Refresh list first
        refresh_alignment_list(context)
        
        props = context.scene.bc_alignment
        
        if self.alignment_index < 0 or self.alignment_index >= len(props.alignments):
            self.report({'ERROR'}, f"Invalid alignment index: {self.alignment_index}")
            return {'CANCELLED'}
        
        # Get alignment item
        item = props.alignments[self.alignment_index]
        
        # Get IFC entity
        ifc = NativeIfcManager.get_file()
        if not ifc:
            self.report({'ERROR'}, "No IFC file")
            return {'CANCELLED'}
        
        alignment = ifc.by_id(item.ifc_entity_id)
        if not alignment:
            self.report({'ERROR'}, "Alignment not found in IFC")
            return {'CANCELLED'}
        
        # Set as active
        set_active_alignment(context, alignment)
        
        self.report({'INFO'}, f"Active alignment: {item.name}")
        return {'FINISHED'}


class BC_OT_select_active_alignment_collection(bpy.types.Operator):
    """
    Select the active alignment's collection.

    Selects all objects that belong to the active alignment's collection
    in the 3D viewport. This is useful for:
    - Quickly isolating alignment geometry
    - Batch operations on alignment objects
    - Visual inspection of alignment components

    The operator deselects all other objects before selecting the
    alignment collection objects. Requires an active alignment to be set.
    """
    bl_idname = "bc.select_active_alignment_collection"
    bl_label = "Select Active Alignment"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from ..ui.alignment_properties import get_active_alignment_item
        
        item = get_active_alignment_item(context)
        if not item:
            self.report({'ERROR'}, "No active alignment")
            return {'CANCELLED'}
        
        if not item.collection_name:
            self.report({'ERROR'}, "Alignment collection not found")
            return {'CANCELLED'}
        
        # Find and select collection
        collection = bpy.data.collections.get(item.collection_name)
        if not collection:
            self.report({'ERROR'}, f"Collection '{item.collection_name}' not found")
            return {'CANCELLED'}
        
        # Select all objects in collection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in collection.objects:
            obj.select_set(True)
        
        self.report({'INFO'}, f"Selected {len(collection.objects)} objects from {item.name}")
        return {'FINISHED'}


# Registration
classes = (
    BC_OT_refresh_alignment_list,
    BC_OT_set_active_alignment,
    BC_OT_select_active_alignment_collection,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
