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
Saikei Civil - Georeferencing UI Panel

Main UI panel for georeferencing in Blender's 3D viewport sidebar.
Provides a complete interface for CRS search, false origin setup,
and coordinate transformation preview.

Author: Saikei Civil Team
Date: November 2025
Sprint: 2 Day 3 - UI Integration
"""

import bpy
from bpy.types import Panel, UIList


class BC_UL_crs_search_results(UIList):
    """UI List for displaying CRS search results."""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # Custom drawing for each search result
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            # EPSG Code (bold)
            col = row.column()
            col.label(text=f"EPSG:{item.epsg_code}", icon='WORLD')
            
            # CRS Name
            col = row.column()
            col.label(text=item.name)
            
            # Area (if space available)
            if self.layout_type == 'DEFAULT':
                col = row.column()
                col.label(text=item.area)
        
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=f"{item.epsg_code}")


class VIEW3D_PT_bc_georeferencing(Panel):
    """Main georeferencing panel in 3D viewport sidebar."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Saikei Civil'
    bl_label = "Georeferencing"
    bl_idname = "VIEW3D_PT_bc_georeferencing"
    bl_order = 5
    bl_options = {'DEFAULT_CLOSED'}

    # Header removed - text-only panel label
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        georef = scene.bc_georef
        
        # Status box
        box = layout.box()
        row = box.row()
        row.label(text="Status:", icon='INFO')
        row.label(text=georef.georef_status_message)
        
        # Show CRS info if selected
        if georef.selected_epsg_code > 0:
            box.separator()
            col = box.column(align=True)
            col.label(text=f"EPSG: {georef.selected_epsg_code}")
            col.label(text=f"CRS: {georef.selected_crs_name}", icon='WORLD')
            if georef.selected_crs_area:
                col.label(text=f"Area: {georef.selected_crs_area}")


class VIEW3D_PT_bc_georef_crs_search(Panel):
    """Sub-panel for CRS search."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Saikei Civil'
    bl_label = "CRS Search"
    bl_parent_id = "VIEW3D_PT_bc_georeferencing"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        georef = scene.bc_georef

        # API Key Status/Link
        try:
            preferences = context.preferences.addons[__package__.split('.')[0]].preferences
            if not preferences.maptiler_api_key:
                box = layout.box()
                box.alert = True
                col = box.column(align=True)
                col.label(text="⚠ MapTiler API Key Required", icon='ERROR')
                col.label(text="CRS search needs an API key")
                col.operator("screen.userpref_show", text="Open Preferences", icon='PREFERENCES').section = 'ADDONS'
                layout.separator()
        except:
            pass  # Preferences not available yet

        # Search box
        box = layout.box()
        row = box.row(align=True)
        row.prop(georef, "crs_search_query", text="", icon='VIEWZOOM')
        row.operator("bc.search_crs", text="", icon='PLAY')
        
        # Quick presets
        box.label(text="Quick Select:")
        flow = box.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
        
        presets = [
            ("WGS84", 4326),
            ("Web Mercator", 3857),
            ("NAD83", 4269),
            ("UTM 10N", 26910),
            ("UTM 11N", 26911),
            ("CA Zone 3", 2227),
        ]
        
        for name, epsg in presets:
            op = flow.operator("bc.select_crs", text=name)
            op.epsg_code = epsg
        
        # Search results
        if georef.search_results:
            layout.separator()
            layout.label(text="Search Results:", icon='PRESET')
            
            row = layout.row()
            row.template_list(
                "BC_UL_crs_search_results",
                "",
                georef,
                "search_results",
                georef,
                "search_results_index",
                rows=5
            )
            
            # Select button
            layout.operator("bc.select_crs", text="Use Selected CRS", icon='IMPORT')


class VIEW3D_PT_bc_georef_false_origin(Panel):
    """Sub-panel for false origin configuration."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Saikei Civil'
    bl_label = "False Origin"
    bl_parent_id = "VIEW3D_PT_bc_georeferencing"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        georef = scene.bc_georef
        
        # False origin coordinates
        box = layout.box()
        box.label(text="Map Coordinates:", icon='EMPTY_AXIS')
        
        col = box.column(align=True)
        col.prop(georef, "false_origin_easting")
        col.prop(georef, "false_origin_northing")
        col.prop(georef, "false_origin_elevation")
        
        # Pick from cursor
        row = box.row(align=True)
        row.operator("bc.pick_false_origin", text="Pick from 3D Cursor", icon='CURSOR')
        
        # Rotation and scale
        if georef.show_advanced_settings:
            box.separator()
            col = box.column(align=True)
            col.prop(georef, "grid_rotation")
            col.prop(georef, "map_scale")


class VIEW3D_PT_bc_georef_setup(Panel):
    """Sub-panel for georeferencing setup."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Saikei Civil'
    bl_label = "Setup"
    bl_parent_id = "VIEW3D_PT_bc_georeferencing"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        georef = scene.bc_georef
        
        # IFC file path
        box = layout.box()
        box.prop(georef, "ifc_file_path", text="IFC File")
        
        # Setup button
        col = layout.column()
        col.scale_y = 1.5
        
        if georef.is_georeferenced:
            col.operator("bc.setup_georeferencing", 
                        text="Update Georeferencing", 
                        icon='FILE_REFRESH')
        else:
            col.operator("bc.setup_georeferencing", 
                        text="Setup Georeferencing", 
                        icon='WORLD')
        
        # Validation
        layout.separator()
        layout.operator("bc.validate_georeferencing", 
                       text="Validate Setup", 
                       icon='CHECKMARK')
        
        # Load from existing IFC
        layout.separator()
        layout.operator("bc.load_georeferencing", 
                       text="Load from IFC", 
                       icon='IMPORT')


class VIEW3D_PT_bc_georef_preview(Panel):
    """Sub-panel for coordinate transformation preview."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Saikei Civil'
    bl_label = "Coordinate Preview"
    bl_parent_id = "VIEW3D_PT_bc_georeferencing"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self, context):
        layout = self.layout
        georef = context.scene.bc_georef
        layout.prop(georef, "show_coordinate_preview", text="")
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        georef = scene.bc_georef
        
        layout.enabled = georef.show_coordinate_preview and georef.is_georeferenced
        
        # Local coordinates input
        box = layout.box()
        box.label(text="Local Coordinates:", icon='ORIENTATION_LOCAL')
        col = box.column(align=True)
        col.prop(georef, "preview_local_x", text="X")
        col.prop(georef, "preview_local_y", text="Y")
        col.prop(georef, "preview_local_z", text="Z")
        
        # Transform button
        box.operator("bc.preview_transform", text="Calculate Map Coordinates", icon='ARROW_LEFTRIGHT')
        
        # Map coordinates output
        box = layout.box()
        box.label(text="Map Coordinates:", icon='WORLD')
        col = box.column(align=True)
        col.enabled = False  # Read-only
        col.prop(georef, "preview_map_easting", text="Easting")
        col.prop(georef, "preview_map_northing", text="Northing")
        col.prop(georef, "preview_map_elevation", text="Elevation")


class VIEW3D_PT_bc_georef_advanced(Panel):
    """Sub-panel for advanced georeferencing settings."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Saikei Civil'
    bl_label = "Advanced"
    bl_parent_id = "VIEW3D_PT_bc_georeferencing"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self, context):
        layout = self.layout
        georef = context.scene.bc_georef
        layout.prop(georef, "show_advanced_settings", text="")
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        georef = scene.bc_georef
        
        layout.enabled = georef.show_advanced_settings
        
        # Auto-update option
        layout.prop(georef, "auto_update_transforms")
        
        # CRS details
        if georef.selected_epsg_code > 0:
            box = layout.box()
            box.label(text="CRS Details:", icon='INFO')
            col = box.column(align=True)
            col.label(text=f"Unit: {georef.selected_crs_unit}")
            col.label(text=f"Area: {georef.selected_crs_area}")


# Registration
classes = (
    BC_UL_crs_search_results,
    VIEW3D_PT_bc_georeferencing,
    VIEW3D_PT_bc_georef_crs_search,
    VIEW3D_PT_bc_georef_false_origin,
    VIEW3D_PT_bc_georef_setup,
    VIEW3D_PT_bc_georef_preview,
    VIEW3D_PT_bc_georef_advanced,
)


def register():
    """Register UI panels."""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister UI panels."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
