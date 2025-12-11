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
Alignment Operations
====================

Provides operators for creating and managing IFC horizontal alignments in Blender.
These operators integrate with the native IFC alignment system to create persistent
geometric data following IFC 4.3 standards.

Operators:
    BC_OT_create_native_alignment: Create new IFC alignment with automatic registration
    BC_OT_update_pi_from_location: Update PI coordinates from Blender object location
"""

import bpy
from bpy.props import StringProperty, FloatProperty, IntProperty, BoolProperty
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Import from parent operators module (where classes are injected)
from . import NativeIfcManager, NativeIfcAlignment, AlignmentVisualizer


class BC_OT_create_native_alignment(bpy.types.Operator):
    """Create new native IFC alignment with automatic registration.

    Creates a new IFC 4.3 compliant horizontal alignment entity in the active IFC file.
    If no IFC file exists, creates a new one with proper project hierarchy. The alignment
    is automatically registered in both the property system and instance registry for
    real-time visualization and editing.

    Properties:
        name: Name for the new alignment (default: "Alignment")

    Usage:
        Invoked via dialog to prompt user for alignment name. Creates the alignment
        with an attached visualizer for immediate feedback in the viewport.
    """
    bl_idname = "bc.create_native_alignment"
    bl_label = "Create Native Alignment"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(
        name="Name",
        default="Alignment",
        description="Alignment name"
    )

    def execute(self, context):
        from ..ui.alignment_properties import add_alignment_to_list, set_active_alignment
        from ..core.alignment_registry import register_alignment, register_visualizer

        # Ensure IFC file exists (create if needed)
        ifc = NativeIfcManager.get_file()
        if not ifc:
            # Create new IFC file with hierarchy if none exists
            result = NativeIfcManager.new_file()
            ifc = result['ifc_file']
            self.report({'INFO'}, "Created new IFC project")

        # Create alignment
        alignment = NativeIfcAlignment(ifc, self.name)

        # Register in property system
        add_alignment_to_list(context, alignment.alignment)
        set_active_alignment(context, alignment.alignment)

        # Register in instance registry
        register_alignment(alignment)

        # Create visualizer and store reference
        visualizer = AlignmentVisualizer(alignment)
        register_visualizer(visualizer, alignment.alignment.GlobalId)

        # CRITICAL: Store visualizer reference in alignment object for update system
        alignment.visualizer = visualizer

        self.report({'INFO'}, f"Created alignment: {self.name}")
        logger.info("Created and registered alignment: %s", self.name)
        logger.debug("Visualizer attached for real-time updates")

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)



class BC_OT_update_pi_from_location(bpy.types.Operator):
    """Update PI coordinates in IFC from Blender object location.

    Synchronizes the IFC alignment data with the current position of a PI marker
    object in Blender's 3D viewport. Updates both the underlying IFC IfcCartesianPoint
    entity and the alignment's internal PI data, then regenerates all dependent
    segments and visualizations.

    Requirements:
        - Active object must be a PI marker with "ifc_pi_id" custom property
        - Active alignment must be set in the property system
        - PI marker must have "ifc_point_id" linking to IFC entity

    Usage:
        Select a PI marker object in the viewport and invoke this operator to
        apply its current location to the IFC alignment geometry.
    """
    bl_idname = "bc.update_pi_from_location"
    bl_label = "Update from Location"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from ..ui.alignment_properties import get_active_alignment_ifc
        from ..core.alignment_registry import get_or_create_alignment, get_or_create_visualizer
        from ..core.native_ifc_alignment import SimpleVector

        obj = context.active_object

        if not obj or "ifc_pi_id" not in obj:
            self.report({'ERROR'}, "Select a PI marker")
            return {'CANCELLED'}

        # Get active alignment
        active_alignment_ifc = get_active_alignment_ifc(context)
        if not active_alignment_ifc:
            self.report({'ERROR'}, "No active alignment")
            return {'CANCELLED'}

        # Get or create alignment instance
        alignment_obj, _ = get_or_create_alignment(active_alignment_ifc)
        visualizer, _ = get_or_create_visualizer(alignment_obj)

        # Update IFC coordinates
        if "ifc_point_id" in obj:
            ifc = NativeIfcManager.get_file()
            point = ifc.by_id(obj["ifc_point_id"])
            point.Coordinates = [float(obj.location.x), float(obj.location.y)]

            # Update PI in alignment object
            pi_id = obj["ifc_pi_id"]
            if pi_id < len(alignment_obj.pis):
                alignment_obj.pis[pi_id]['position'] = SimpleVector(obj.location.x, obj.location.y)

            # Regenerate segments
            alignment_obj.regenerate_segments()

            # Update visualization
            visualizer.update_visualizations()

            self.report({'INFO'}, f"Updated PI {obj.name}")
            return {'FINISHED'}

        return {'CANCELLED'}




# Registration
classes = (
    BC_OT_create_native_alignment,
    BC_OT_update_pi_from_location,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
