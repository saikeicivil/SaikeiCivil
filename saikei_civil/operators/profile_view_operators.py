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
Saikei Civil - Profile View Operators
======================================

Blender operators for profile view interaction.
Handles user actions: toggle, load data, edit PVIs, etc.

This follows Saikei Civil's architecture pattern:
- operators/ = User actions and workflows
- Imports from core/ for business logic

Operators:
    BC_OT_ProfileView_Toggle: Toggle profile view overlay on/off
    BC_OT_ProfileView_Enable: Enable profile view overlay
    BC_OT_ProfileView_Disable: Disable profile view overlay
    BC_OT_ProfileView_LoadFromSprint3: Load vertical alignment from Sprint 3 data
    BC_OT_ProfileView_SyncToSprint3: Sync profile view changes back to Sprint 3
    BC_OT_ProfileView_LoadTerrain: Load terrain profile from selected mesh
    BC_OT_ProfileView_AddPVI: Add a new PVI at specified location
    BC_OT_ProfileView_DeleteSelectedPVI: Delete the currently selected PVI
    BC_OT_ProfileView_SelectPVI: Select a PVI by index
    BC_OT_ProfileView_FitToData: Automatically fit view extents to data
    BC_OT_ProfileView_ClearData: Clear all profile view data
    BC_OT_ProfileView_ModalHandler: Modal event handler for profile view interaction

Author: Saikei Civil Development Team
Date: November 2025
License: GPL v3
"""

import bpy
from bpy.types import Operator
from bpy.props import FloatProperty, IntProperty, StringProperty

# Import core functionality
import sys
import os

# Note: Adjust import path based on actual installation
# from saikei.core.profile_view_overlay import (
#     get_profile_overlay,
#     load_from_sprint3_vertical,
#     sync_to_sprint3_vertical
# )


# ============================================================================
# OVERLAY CONTROL OPERATORS
# ============================================================================

class BC_OT_ProfileView_Toggle(Operator):
    """
    Toggle profile view overlay on/off.

    Toggles the visibility of the profile view overlay in the 3D viewport.
    The profile view displays vertical alignment information at the bottom
    of the viewport, showing PVIs, grades, and terrain profiles.

    When enabled, this operator also starts the modal event handler for
    interactive resize and editing capabilities.

    Usage context: Primary toggle button in the UI panel for showing/hiding
    the profile view overlay.
    """
    bl_idname = "saikei.profile_view_toggle"
    bl_label = "Toggle Profile View"
    bl_description = "Show/hide the profile view overlay at bottom of viewport"
    bl_options = {'REGISTER'}

    def execute(self, context):
        # Import here to avoid circular dependencies
        from ..core.profile_view_overlay import get_profile_overlay

        overlay = get_profile_overlay()
        was_enabled = overlay.enabled
        overlay.toggle(context)

        # Start or stop the modal event handler
        if overlay.enabled and not was_enabled:
            # Start the modal event handler
            bpy.ops.saikei.profile_view_modal_handler('INVOKE_DEFAULT')
            self.report({'INFO'}, "Profile view enabled")
        else:
            self.report({'INFO'}, "Profile view disabled")
            # Modal handler will stop itself when overlay is disabled

        return {'FINISHED'}


class BC_OT_ProfileView_Enable(Operator):
    """
    Enable profile view overlay.

    Explicitly enables the profile view overlay, ensuring it is visible
    in the 3D viewport. Unlike Toggle, this always enables the overlay
    regardless of current state.

    Automatically starts the modal event handler if not already running.

    Usage context: Called programmatically when loading data or when
    explicit enable is needed (e.g., after loading vertical alignment data).
    """
    bl_idname = "saikei.profile_view_enable"
    bl_label = "Enable Profile View"
    bl_description = "Show the profile view overlay"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from ..core.profile_view_overlay import get_profile_overlay

        overlay = get_profile_overlay()
        was_enabled = overlay.enabled
        overlay.enable(context)

        # Start the modal event handler if not already running
        if not was_enabled:
            bpy.ops.saikei.profile_view_modal_handler('INVOKE_DEFAULT')

        self.report({'INFO'}, "Profile view enabled")
        return {'FINISHED'}


class BC_OT_ProfileView_Disable(Operator):
    """
    Disable profile view overlay.

    Explicitly disables the profile view overlay, hiding it from the
    3D viewport. Unlike Toggle, this always disables the overlay
    regardless of current state.

    The modal event handler will automatically stop itself when the
    overlay is disabled.

    Usage context: Called when user wants to explicitly hide the overlay
    or when cleaning up the viewport.
    """
    bl_idname = "saikei.profile_view_disable"
    bl_label = "Disable Profile View"
    bl_description = "Hide the profile view overlay"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        from ..core.profile_view_overlay import get_profile_overlay
        
        overlay = get_profile_overlay()
        overlay.disable(context)
        self.report({'INFO'}, "Profile view disabled")
        return {'FINISHED'}


# ============================================================================
# DATA LOADING OPERATORS
# ============================================================================

class BC_OT_ProfileView_LoadFromSprint3(Operator):
    """
    Load vertical alignment from Sprint 3 data.

    Imports vertical alignment data from the Sprint 3 vertical alignment
    system (bc_vertical properties) into the profile view overlay.
    This provides backward compatibility and data migration.

    The operator reads PVIs, grades, and curve information from Sprint 3's
    property-based storage and converts it to the profile view data model.
    Automatically enables the profile view overlay after loading.

    Usage context: Called when migrating existing projects or when working
    with Sprint 3 vertical alignment data.
    """
    bl_idname = "saikei.profile_view_load_from_sprint3"
    bl_label = "Load from Sprint 3"
    bl_description = "Load vertical alignment data from Sprint 3 bc_vertical properties"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from ..core.profile_view_overlay import (
            get_profile_overlay,
            load_from_sprint3_vertical
        )
        
        success = load_from_sprint3_vertical(context)
        
        if not success:
            self.report({'ERROR'}, "Sprint 3 vertical alignment not found")
            return {'CANCELLED'}
        
        overlay = get_profile_overlay()
        
        # Enable overlay if not already enabled
        if not overlay.enabled:
            overlay.enable(context)
        
        overlay.refresh(context)
        
        self.report({'INFO'}, 
                   f"Loaded {len(overlay.data.pvis)} PVIs from Sprint 3")
        return {'FINISHED'}


class BC_OT_ProfileView_SyncToSprint3(Operator):
    """
    Sync profile view changes back to Sprint 3.

    Writes modifications made in the profile view overlay back to the
    Sprint 3 vertical alignment system (bc_vertical properties).
    This maintains bidirectional compatibility between systems.

    Any PVIs added, modified, or deleted in the profile view will be
    reflected in the Sprint 3 data structures. Refreshes the profile
    view after syncing.

    Usage context: Called after editing vertical alignment in profile view
    to persist changes to Sprint 3 storage.
    """
    bl_idname = "saikei.profile_view_sync_to_sprint3"
    bl_label = "Sync to Sprint 3"
    bl_description = "Write profile view changes back to Sprint 3 vertical alignment"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from ..core.profile_view_overlay import (
            get_profile_overlay,
            sync_to_sprint3_vertical
        )
        
        success = sync_to_sprint3_vertical(context)
        
        if not success:
            self.report({'ERROR'}, "Failed to sync to Sprint 3")
            return {'CANCELLED'}
        
        overlay = get_profile_overlay()
        overlay.refresh(context)
        
        self.report({'INFO'}, "Synced changes to Sprint 3")
        return {'FINISHED'}


class BC_OT_ProfileView_LoadTerrain(Operator):
    """
    Load terrain profile from selected mesh.

    Samples elevation data from the active mesh object (DTM/terrain)
    along the horizontal alignment. Creates a terrain profile that can
    be displayed in the profile view for comparison with the design
    vertical alignment.

    The operator performs raycasting or vertex sampling along the alignment
    path to extract terrain elevation points. Currently includes placeholder
    implementation that will be replaced with actual terrain sampling.

    Usage context: Called when user wants to display existing ground
    elevations in the profile view for design comparison.
    """
    bl_idname = "saikei.profile_view_load_terrain"
    bl_label = "Load Terrain"
    bl_description = "Sample terrain elevations from selected mesh along alignment"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from ..core.profile_view_overlay import get_profile_overlay
        
        mesh_obj = context.active_object
        
        if not mesh_obj or mesh_obj.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object (DTM/terrain)")
            return {'CANCELLED'}
        
        overlay = get_profile_overlay()
        
        # TODO: Implement terrain raycasting
        # For now, create placeholder data
        import numpy as np
        
        overlay.data.clear_terrain()
        
        stations = np.linspace(
            overlay.data.station_min,
            overlay.data.station_max,
            100
        )
        
        for station in stations:
            # Placeholder: sine wave terrain
            elevation = 50.0 + 20.0 * np.sin(station / 100.0)
            overlay.data.add_terrain_point(station, elevation)
        
        overlay.refresh(context)
        
        self.report({'INFO'}, 
                   f"Loaded {len(overlay.data.terrain_points)} terrain points")
        return {'FINISHED'}


# ============================================================================
# PVI EDITING OPERATORS
# ============================================================================

class BC_OT_ProfileView_AddPVI(Operator):
    """
    Add a new PVI at specified location.

    Creates a new Point of Vertical Intersection (PVI) in the vertical
    alignment. PVIs are the fundamental control points that define the
    vertical profile of the alignment.

    Properties:
        station: Station coordinate where PVI should be placed (m)
        elevation: Elevation of the PVI (m)
        curve_length: Length of the vertical curve at this PVI (m)

    The operator presents a dialog for entering PVI parameters and
    automatically sorts PVIs by station after insertion. Refreshes
    the profile view to show the new PVI.

    Usage context: Called when user needs to add a new control point
    to the vertical alignment design.
    """
    bl_idname = "saikei.profile_view_add_pvi"
    bl_label = "Add PVI"
    bl_description = "Add a new Point of Vertical Intersection"
    bl_options = {'REGISTER', 'UNDO'}
    
    station: FloatProperty(
        name="Station",
        description="Station coordinate (m)",
        default=0.0,
        unit='LENGTH'
    )
    
    elevation: FloatProperty(
        name="Elevation",
        description="Elevation coordinate (m)",
        default=100.0,
        unit='LENGTH'
    )
    
    curve_length: FloatProperty(
        name="Curve Length",
        description="Vertical curve length (m)",
        default=100.0,
        min=0.0,
        unit='LENGTH'
    )
    
    def execute(self, context):
        from ..core.profile_view_overlay import get_profile_overlay
        
        overlay = get_profile_overlay()
        
        metadata = {'curve_length': self.curve_length}
        overlay.data.add_pvi(self.station, self.elevation, metadata)
        overlay.data.sort_pvis_by_station()
        overlay.refresh(context)
        
        self.report({'INFO'}, 
                   f"Added PVI at station {self.station:.2f}m, "
                   f"elevation {self.elevation:.2f}m")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class BC_OT_ProfileView_DeleteSelectedPVI(Operator):
    """
    Delete the currently selected PVI.

    Removes the currently selected Point of Vertical Intersection from
    the vertical alignment. This operation requires a PVI to be selected
    first (via clicking or the SelectPVI operator).

    The operator validates that a PVI is selected before attempting
    deletion and refreshes the profile view after successful removal.

    Usage context: Called when user wants to remove a control point
    from the vertical alignment. Typically bound to keyboard shortcuts
    or delete buttons in the UI.
    """
    bl_idname = "saikei.profile_view_delete_selected_pvi"
    bl_label = "Delete PVI"
    bl_description = "Delete the currently selected PVI"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from ..core.profile_view_overlay import get_profile_overlay
        
        overlay = get_profile_overlay()
        
        if overlay.data.selected_pvi_index is None:
            self.report({'WARNING'}, "No PVI selected")
            return {'CANCELLED'}
        
        success = overlay.data.remove_pvi(overlay.data.selected_pvi_index)
        
        if success:
            overlay.refresh(context)
            self.report({'INFO'}, "Deleted PVI")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Failed to delete PVI")
            return {'CANCELLED'}


class BC_OT_ProfileView_SelectPVI(Operator):
    """
    Select a PVI by index.

    Sets the active/selected PVI in the profile view data model.
    Selection is required for operations like deletion or editing.

    Properties:
        pvi_index: Zero-based index of the PVI to select

    The operator validates the index before setting selection and
    refreshes the profile view to highlight the selected PVI.

    Usage context: Called internally by profile view mouse interactions
    or when programmatically selecting a PVI for editing.
    """
    bl_idname = "saikei.profile_view_select_pvi"
    bl_label = "Select PVI"
    bl_description = "Select a PVI for editing"
    bl_options = {'REGISTER', 'UNDO'}
    
    pvi_index: IntProperty(
        name="PVI Index",
        description="Index of PVI to select",
        default=0,
        min=0
    )
    
    def execute(self, context):
        from ..core.profile_view_overlay import get_profile_overlay
        
        overlay = get_profile_overlay()
        
        success = overlay.data.select_pvi(self.pvi_index)
        
        if success:
            overlay.refresh(context)
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Invalid PVI index")
            return {'CANCELLED'}


# ============================================================================
# VIEW CONTROL OPERATORS
# ============================================================================

class BC_OT_ProfileView_FitToData(Operator):
    """
    Automatically fit view extents to data.

    Calculates appropriate view bounds to display all profile data
    (PVIs, terrain, alignment) and adjusts the profile view's display
    extents accordingly. Similar to "zoom to fit" functionality.

    The operator examines all data points and determines optimal
    station and elevation ranges with appropriate padding for
    comfortable viewing.

    Usage context: Called when user wants to quickly frame all profile
    data or after loading new data that may be outside current view.
    """
    bl_idname = "saikei.profile_view_fit_to_data"
    bl_label = "Fit to Data"
    bl_description = "Automatically adjust view extents to fit all data"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from ..core.profile_view_overlay import get_profile_overlay
        from ..core.logging_config import get_logger

        logger = get_logger(__name__)
        overlay = get_profile_overlay()
        data = overlay.data

        # Count data points
        num_terrain = len(data.terrain_points)
        num_alignment = len(data.alignment_points)
        num_pvis = len(data.pvis)
        num_valigns = len(data.vertical_alignments)

        # Count PVIs from vertical alignments
        num_valign_pvis = sum(len(va.pvis) for va in data.vertical_alignments)

        total_points = num_terrain + num_alignment + num_pvis + num_valign_pvis

        logger.info("Fit to Data: terrain=%d, alignment=%d, pvis=%d, valigns=%d (pvis=%d)",
                   num_terrain, num_alignment, num_pvis, num_valigns, num_valign_pvis)

        if total_points == 0:
            self.report({'WARNING'}, "No data to fit - load terrain or vertical alignment first")
            return {'CANCELLED'}

        # Store old extents for comparison
        old_extents = (data.station_min, data.station_max,
                      data.elevation_min, data.elevation_max)

        # Update view extents
        data.update_view_extents()

        new_extents = (data.station_min, data.station_max,
                      data.elevation_min, data.elevation_max)

        logger.info("View extents: Station %.1f to %.1f, Elevation %.1f to %.1f",
                   data.station_min, data.station_max,
                   data.elevation_min, data.elevation_max)

        # Also sync to UI properties directly
        if hasattr(context.scene, 'bc_profile_view_props'):
            props = context.scene.bc_profile_view_props
            props.station_min = data.station_min
            props.station_max = data.station_max
            props.elevation_min = data.elevation_min
            props.elevation_max = data.elevation_max

        overlay.refresh(context)

        self.report({'INFO'},
                   f"Fitted view: Station {data.station_min:.0f}-{data.station_max:.0f}m, "
                   f"Elev {data.elevation_min:.0f}-{data.elevation_max:.0f}m")
        return {'FINISHED'}


class BC_OT_ProfileView_ClearData(Operator):
    """
    Clear all profile view data.

    Removes all data from the profile view including:
    - Terrain profile points
    - Vertical alignment PVIs
    - Computed curve data

    This is a destructive operation and presents a confirmation dialog
    before clearing. Use this to start fresh with a new vertical
    alignment design.

    Usage context: Called when resetting the profile view or starting
    a new vertical alignment design from scratch.
    """
    bl_idname = "saikei.profile_view_clear_data"
    bl_label = "Clear All Data"
    bl_description = "Clear all terrain, alignment, and PVI data"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from ..core.profile_view_overlay import get_profile_overlay
        
        overlay = get_profile_overlay()
        overlay.data.clear_all()
        overlay.refresh(context)
        
        self.report({'INFO'}, "Cleared all profile data")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class BC_OT_ProfileView_ModalHandler(Operator):
    """
    Modal event handler for profile view interaction.

    Handles continuous mouse events for interactive profile view features:
    - Resize overlay by dragging top border
    - Hover detection for resize cursor
    - PVI selection by clicking (future)
    - PVI dragging for editing (future)

    This operator runs in modal mode, continuously processing mouse events
    while the profile view is enabled. It automatically terminates when
    the profile view is disabled.

    The modal handler uses a state machine to track:
    - Hover state (over resize border)
    - Resizing state (actively dragging)
    - Normal state (pass-through events)

    Usage context: Automatically invoked when profile view is enabled.
    Should not be called directly by users.
    """
    bl_idname = "saikei.profile_view_modal_handler"
    bl_label = "Profile View Modal Handler"
    bl_description = "Handle mouse events for profile view resize and interaction"
    bl_options = {'INTERNAL'}

    def modal(self, context, event):
        from ..core.profile_view_overlay import get_profile_overlay

        overlay = get_profile_overlay()

        # Stop modal handler if overlay is disabled
        if not overlay.enabled:
            # Restore cursor
            context.window.cursor_set('DEFAULT')
            return {'FINISHED'}

        # Handle mouse movement
        if event.type == 'MOUSEMOVE':
            overlay.handle_mouse_move(context, event)
            # Tag viewport for redraw if hovering or resizing
            if overlay.hover_resize_border or overlay.is_resizing:
                if context.area:
                    context.area.tag_redraw()

        # Handle mouse press
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if overlay.handle_mouse_press(context, event):
                return {'RUNNING_MODAL'}

        # Handle mouse release
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if overlay.handle_mouse_release(context, event):
                if context.area:
                    context.area.tag_redraw()

        # Pass through other events
        if overlay.is_resizing:
            # Block other events while resizing
            return {'RUNNING_MODAL'}
        else:
            # Pass through when not resizing
            return {'PASS_THROUGH'}

    def invoke(self, context, event):
        # Add modal handler to window manager
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    BC_OT_ProfileView_Toggle,
    BC_OT_ProfileView_Enable,
    BC_OT_ProfileView_Disable,
    BC_OT_ProfileView_LoadFromSprint3,
    BC_OT_ProfileView_SyncToSprint3,
    BC_OT_ProfileView_LoadTerrain,
    BC_OT_ProfileView_AddPVI,
    BC_OT_ProfileView_DeleteSelectedPVI,
    BC_OT_ProfileView_SelectPVI,
    BC_OT_ProfileView_FitToData,
    BC_OT_ProfileView_ClearData,
    BC_OT_ProfileView_ModalHandler,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
