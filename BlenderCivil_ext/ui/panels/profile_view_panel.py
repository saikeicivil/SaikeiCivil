# ==============================================================================
# BlenderCivil - Civil Engineering Tools for Blender
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
BlenderCivil - Profile View Panel (UI)
=======================================

Blender UI panel for profile view controls.
Displays in the 3D viewport sidebar (N-panel).

This follows BlenderCivil's architecture pattern:
- ui/ = Blender UI elements (properties, panels)

Author: BlenderCivil Development Team
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
            row.operator("blendercivil.profile_view_toggle", 
                        text="Hide Profile View", icon='HIDE_ON')
        else:
            row.operator("blendercivil.profile_view_toggle",
                        text="Show Profile View", icon='HIDE_OFF')
        
        if not enabled:
            return
        
        # Data loading section
        box = layout.box()
        box.label(text="Load Data", icon='IMPORT')
        
        col = box.column(align=True)
        col.operator("blendercivil.profile_view_load_from_sprint3", 
                    text="Load from Sprint 3", icon='CURVE_BEZCIRCLE')
        col.operator("blendercivil.profile_view_load_terrain",
                    text="Load Terrain", icon='MESH_GRID')
        col.separator()
        col.operator("blendercivil.profile_view_sync_to_sprint3",
                    text="Sync to Sprint 3", icon='FILE_REFRESH')
        
        # Display settings
        box = layout.box()
        box.label(text="Display", icon='PREFERENCES')
        
        props = context.scene.bc_profile_view_props
        
        row = box.row(align=True)
        row.prop(props, "show_terrain", text="", icon='MESH_GRID')
        row.label(text="Terrain")
        
        row = box.row(align=True)
        row.prop(props, "show_alignment", text="", icon='CURVE_PATH')
        row.label(text="Alignment")
        
        row = box.row(align=True)
        row.prop(props, "show_pvis", text="", icon='CURVE_BEZCIRCLE')
        row.label(text="PVIs")
        
        row = box.row(align=True)
        row.prop(props, "show_grades", text="", icon='DRIVER_DISTANCE')
        row.label(text="Grades")
        
        row = box.row(align=True)
        row.prop(props, "show_grid", text="", icon='GRID')
        row.label(text="Grid")
        
        # PVI Operations
        box = layout.box()
        box.label(text="PVI Operations", icon='CURVE_BEZCIRCLE')
        
        col = box.column(align=True)
        col.operator("blendercivil.profile_view_add_pvi",
                    text="Add PVI", icon='ADD')
        col.operator("blendercivil.profile_view_delete_selected_pvi",
                    text="Delete Selected", icon='X')
        
        # View Controls
        box = layout.box()
        box.label(text="View Controls", icon='VIEWZOOM')
        
        col = box.column(align=True)
        col.operator("blendercivil.profile_view_fit_to_data",
                    text="Fit to Data", icon='FULLSCREEN_ENTER')
        col.operator("blendercivil.profile_view_clear_data",
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
