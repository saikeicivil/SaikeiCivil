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
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================

"""
Cross-Section Overlay Operators
================================

Operators for the OpenRoads-style cross-section overlay viewer that displays
assemblies as a 2D overlay in the viewport.

Operators:
    BC_OT_ToggleCrossSectionView: Toggle overlay on/off
    BC_OT_LoadAssemblyToView: Load active assembly to overlay
    BC_OT_RefreshCrossSectionView: Force refresh overlay
    BC_OT_FitCrossSectionView: Fit view to show all components
    BC_OT_SetCrossSectionViewPosition: Set overlay anchor position
    BC_OT_CrossSectionViewInteraction: Modal operator for mouse interaction
"""

import bpy
from bpy.types import Operator
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class BC_OT_ToggleCrossSectionView(Operator):
    """
    Toggle the cross-section overlay viewer on/off.

    This operator provides an OpenRoads-style cross-section viewer that
    displays the assembly as a 2D overlay in the viewport, rather than
    creating 3D geometry in the model space.

    The overlay viewer shows:
    - Cross-section profile with colored components
    - Grid with offset and elevation labels
    - Centerline reference
    - Component names and dimensions

    Usage:
        Press to toggle the overlay on/off. When enabled, the overlay
        appears at the bottom of the 3D viewport.
    """
    bl_idname = "bc.toggle_cross_section_view"
    bl_label = "Toggle Cross-Section Viewer"
    bl_description = "Toggle the cross-section overlay viewer (OpenRoads-style)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from ..tool.cross_section_view_overlay import get_cross_section_overlay

        overlay = get_cross_section_overlay()
        overlay.toggle(context)

        if overlay.enabled:
            # Load active assembly if available
            self._load_active_assembly(context, overlay)

            # Start the interaction modal operator for drag/resize/hover
            if not BC_OT_CrossSectionViewInteraction._is_running:
                bpy.ops.bc.cross_section_view_interaction('INVOKE_DEFAULT')

            self.report({'INFO'}, "Cross-section viewer enabled")
        else:
            self.report({'INFO'}, "Cross-section viewer disabled")

        return {'FINISHED'}

    def _load_active_assembly(self, context, overlay):
        """Load the active assembly into the overlay."""
        if not hasattr(context.scene, 'bc_cross_section'):
            return

        cs = context.scene.bc_cross_section
        if cs.active_assembly_index < 0 or cs.active_assembly_index >= len(cs.assemblies):
            return

        assembly = cs.assemblies[cs.active_assembly_index]
        overlay.load_from_assembly(assembly)


class BC_OT_LoadAssemblyToView(Operator):
    """
    Load the active assembly into the cross-section overlay viewer.

    This refreshes the overlay with the current active assembly's data,
    updating the visualization to show any changes made to components.

    Usage:
        Call after making changes to the assembly to refresh the viewer.
    """
    bl_idname = "bc.load_assembly_to_view"
    bl_label = "Load to Viewer"
    bl_description = "Load the active assembly into the cross-section viewer"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if not hasattr(context.scene, 'bc_cross_section'):
            return False
        cs = context.scene.bc_cross_section
        return cs.active_assembly_index >= 0 and cs.active_assembly_index < len(cs.assemblies)

    def execute(self, context):
        from ..tool.cross_section_view_overlay import (
            get_cross_section_overlay,
            load_active_assembly_to_overlay
        )

        overlay = get_cross_section_overlay()

        # Enable overlay if not already enabled
        if not overlay.enabled:
            overlay.enable(context)

        # Load the active assembly
        success = load_active_assembly_to_overlay(context)

        if success:
            cs = context.scene.bc_cross_section
            assembly = cs.assemblies[cs.active_assembly_index]
            self.report({'INFO'}, f"Loaded assembly: {assembly.name}")
        else:
            self.report({'WARNING'}, "Failed to load assembly")

        return {'FINISHED'}


class BC_OT_RefreshCrossSectionView(Operator):
    """
    Refresh the cross-section overlay viewer.

    Forces a redraw of the overlay with the current assembly data.

    Usage:
        Call to force a refresh after external changes.
    """
    bl_idname = "bc.refresh_cross_section_view"
    bl_label = "Refresh Viewer"
    bl_description = "Refresh the cross-section overlay viewer"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        from ..tool.cross_section_view_overlay import get_cross_section_overlay
        return get_cross_section_overlay().enabled

    def execute(self, context):
        from ..tool.cross_section_view_overlay import (
            get_cross_section_overlay,
            load_active_assembly_to_overlay
        )

        # Reload the active assembly
        load_active_assembly_to_overlay(context)

        # Force redraw
        overlay = get_cross_section_overlay()
        overlay.refresh(context)

        self.report({'INFO'}, "Cross-section viewer refreshed")
        return {'FINISHED'}


class BC_OT_FitCrossSectionView(Operator):
    """
    Fit the cross-section view to show all components.

    Adjusts the view extents to show the full cross-section with
    appropriate padding.
    """
    bl_idname = "bc.fit_cross_section_view"
    bl_label = "Fit to Data"
    bl_description = "Fit the cross-section view to show all components"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        from ..tool.cross_section_view_overlay import get_cross_section_overlay
        overlay = get_cross_section_overlay()
        return overlay.enabled and len(overlay.data.components) > 0

    def execute(self, context):
        from ..tool.cross_section_view_overlay import get_cross_section_overlay

        overlay = get_cross_section_overlay()
        overlay.data.update_view_extents()
        overlay.refresh(context)

        self.report({'INFO'}, "View fitted to cross-section data")
        return {'FINISHED'}


class BC_OT_SetCrossSectionViewPosition(Operator):
    """
    Set the cross-section overlay viewer position/anchor.

    Allows positioning the overlay at different edges of the viewport
    or as a floating, draggable window.

    Positions:
    - BOTTOM: Anchored to bottom edge (default)
    - TOP: Anchored to top edge
    - LEFT: Anchored to left edge
    - RIGHT: Anchored to right edge
    - FLOATING: Free-floating, draggable with title bar
    """
    bl_idname = "bc.set_cross_section_view_position"
    bl_label = "Set Viewer Position"
    bl_description = "Set the cross-section overlay position"
    bl_options = {'REGISTER'}

    position: bpy.props.EnumProperty(
        name="Position",
        description="Overlay anchor position",
        items=[
            ('BOTTOM', "Bottom", "Anchor to bottom edge"),
            ('TOP', "Top", "Anchor to top edge"),
            ('LEFT', "Left", "Anchor to left edge"),
            ('RIGHT', "Right", "Anchor to right edge"),
            ('FLOATING', "Floating", "Free-floating, draggable window"),
        ],
        default='BOTTOM'
    )

    @classmethod
    def poll(cls, context):
        from ..tool.cross_section_view_overlay import get_cross_section_overlay
        return get_cross_section_overlay().enabled

    def execute(self, context):
        from ..tool.cross_section_view_overlay import (
            get_cross_section_overlay,
            OverlayPosition
        )

        overlay = get_cross_section_overlay()

        # Convert string to enum
        position_map = {
            'BOTTOM': OverlayPosition.BOTTOM,
            'TOP': OverlayPosition.TOP,
            'LEFT': OverlayPosition.LEFT,
            'RIGHT': OverlayPosition.RIGHT,
            'FLOATING': OverlayPosition.FLOATING,
        }

        new_position = position_map.get(self.position, OverlayPosition.BOTTOM)
        overlay.set_position(new_position)
        overlay.refresh(context)

        self.report({'INFO'}, f"Viewer position set to: {self.position}")
        return {'FINISHED'}


class BC_OT_CrossSectionViewInteraction(Operator):
    """
    Modal operator for cross-section overlay interaction.

    This operator handles mouse events for:
    - Dragging the floating overlay by the title bar
    - Resizing the overlay by dragging edges
    - Hovering over components
    - Selecting components by clicking

    The operator runs modally while the overlay is enabled, capturing
    mouse events and routing them to the overlay's handler methods.

    Usage:
        Automatically started when the overlay is enabled in floating mode.
        Can also be manually invoked to enable interaction.
    """
    bl_idname = "bc.cross_section_view_interaction"
    bl_label = "Cross-Section View Interaction"
    bl_description = "Enable mouse interaction with the cross-section overlay"
    bl_options = {'INTERNAL'}

    _is_running = False  # Class variable to track if modal is active

    @classmethod
    def poll(cls, context):
        from ..tool.cross_section_view_overlay import get_cross_section_overlay
        overlay = get_cross_section_overlay()
        return overlay.enabled and not cls._is_running

    def invoke(self, context, event):
        from ..tool.cross_section_view_overlay import get_cross_section_overlay

        overlay = get_cross_section_overlay()
        if not overlay.enabled:
            self.report({'WARNING'}, "Cross-section overlay is not enabled")
            return {'CANCELLED'}

        # Mark as running
        BC_OT_CrossSectionViewInteraction._is_running = True

        # Add modal handler
        context.window_manager.modal_handler_add(self)

        logger.info("Cross-section view interaction started")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        from ..tool.cross_section_view_overlay import get_cross_section_overlay

        overlay = get_cross_section_overlay()

        # Stop if overlay is disabled
        if not overlay.enabled:
            BC_OT_CrossSectionViewInteraction._is_running = False
            context.window.cursor_set('DEFAULT')
            logger.info("Cross-section view interaction stopped (overlay disabled)")
            return {'CANCELLED'}

        # Only process events in the VIEW_3D area
        if context.area and context.area.type != 'VIEW_3D':
            return {'PASS_THROUGH'}

        # Handle mouse movement
        if event.type == 'MOUSEMOVE':
            handled = overlay.handle_mouse_move(context, event)
            if handled:
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}

        # Handle mouse press
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            handled = overlay.handle_mouse_press(context, event)
            if handled:
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}

        # Handle mouse release
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            handled = overlay.handle_mouse_release(context, event)
            if handled:
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}

        # ESC key cancels drag/resize operations
        if event.type == 'ESC' and event.value == 'PRESS':
            if overlay.is_dragging or overlay.is_resizing:
                overlay.is_dragging = False
                overlay.is_resizing = False
                context.window.cursor_set('DEFAULT')
                if context.area:
                    context.area.tag_redraw()
                return {'RUNNING_MODAL'}

        # Pass through all other events
        return {'PASS_THROUGH'}

    def cancel(self, context):
        BC_OT_CrossSectionViewInteraction._is_running = False
        context.window.cursor_set('DEFAULT')
        logger.info("Cross-section view interaction cancelled")


# Registration
classes = (
    BC_OT_ToggleCrossSectionView,
    BC_OT_LoadAssemblyToView,
    BC_OT_RefreshCrossSectionView,
    BC_OT_FitCrossSectionView,
    BC_OT_SetCrossSectionViewPosition,
    BC_OT_CrossSectionViewInteraction,
)


def register():
    """Register operator classes"""
    for cls in classes:
        bpy.utils.register_class(cls)

    logger.info("Cross-section overlay operators registered")


def unregister():
    """Unregister operator classes"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    logger.info("Cross-section overlay operators unregistered")
