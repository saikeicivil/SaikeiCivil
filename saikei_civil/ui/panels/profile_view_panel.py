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
Saikei Civil - Profile View Panel (UI)
=======================================

Blender UI panel for profile view controls.
Displays in the 3D viewport sidebar (N-panel).

This follows Saikei Civil's architecture pattern:
- ui/ = Blender UI elements (properties, panels)

Author: Saikei Civil Development Team
Date: November 2025
License: GPL v3
"""

import bpy
from bpy.types import Panel


class BC_PT_ProfileViewPanel(Panel):
    """Profile View Control Panel (Sub-panel of Vertical Alignment)"""
    bl_label = "Profile View"
    bl_idname = "BC_PT_profile_view"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = "VIEW3D_PT_bc_vertical_alignment"  # Make this a sub-panel
    bl_order = 100  # Display after other vertical alignment sub-panels
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        # Get overlay status
        try:
            from ...core.profile_view_overlay import get_profile_overlay
            overlay = get_profile_overlay()
            enabled = overlay.enabled
            num_pvis = len(overlay.data.pvis)
            num_terrain = len(overlay.data.terrain_points)
        except:
            enabled = False
            num_pvis = 0
            num_terrain = 0
        
        # Main toggle button
        box = layout.box()
        box.label(text="Profile View Overlay", icon='VIEW_ORTHO')
        
        row = box.row()
        row.scale_y = 1.5
        if enabled:
            row.operator("saikei.profile_view_toggle", 
                        text="Hide Profile View", icon='HIDE_ON')
        else:
            row.operator("saikei.profile_view_toggle",
                        text="Show Profile View", icon='HIDE_OFF')
        
        if not enabled:
            return

        # Get properties for view extents
        props = context.scene.bc_profile_view_props

        # PVI Operations
        box = layout.box()
        box.label(text="PVI Operations", icon='CURVE_BEZCIRCLE')
        
        col = box.column(align=True)
        col.operator("saikei.profile_view_add_pvi",
                    text="Add PVI", icon='ADD')
        col.operator("saikei.profile_view_delete_selected_pvi",
                    text="Delete Selected", icon='X')
        
        # View Controls
        box = layout.box()
        box.label(text="View Controls", icon='VIEWZOOM')
        
        col = box.column(align=True)
        col.operator("saikei.profile_view_fit_to_data",
                    text="Fit to Data", icon='FULLSCREEN_ENTER')
        col.operator("saikei.profile_view_clear_data",
                    text="Clear All", icon='TRASH')
        
        # View Extents (collapsible)
        box = layout.box()
        row = box.row()
        row.label(text="View Extents", icon='EMPTY_ARROWS')
        
        split = box.split(factor=0.4)
        col = split.column()
        col.label(text="Station:")
        col.label(text="")
        col.label(text="Elevation:")
        
        col = split.column()
        col.prop(props, "station_min", text="Min")
        col.prop(props, "station_max", text="Max")
        col.prop(props, "elevation_min", text="Min")
        col.prop(props, "elevation_max", text="Max")
        
        # Statistics
        if num_pvis > 0 or num_terrain > 0:
            box = layout.box()
            box.label(text="Statistics", icon='INFO')
            
            col = box.column(align=True)
            col.label(text=f"PVIs: {num_pvis}")
            col.label(text=f"Terrain Points: {num_terrain}")
            
            if enabled:
                col.label(text=f"Status: {overlay.get_status()}")


def register():
    bpy.utils.register_class(BC_PT_ProfileViewPanel)


def unregister():
    bpy.utils.unregister_class(BC_PT_ProfileViewPanel)


if __name__ == "__main__":
    register()
