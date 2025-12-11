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
Enhanced Cross-Section Panel with 3D Visualization
Sprint 4 Day 4 - Updated UI panel with visualization controls

This extends the cross-section panel to include a dedicated
visualization section with one-click buttons for:
- Quick preview
- Single station visualization
- Full corridor creation
- Station markers
- Component previews
- Clear visualization

Author: Saikei Civil Team
Date: November 3, 2025
"""

import bpy
from bpy.types import Panel
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class SAIKEI_PT_cross_section_visualization(Panel):
    """3D Visualization panel for cross-sections"""
    bl_label = "3D Visualization"
    bl_idname = "SAIKEI_PT_cross_section_visualization"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Saikei Civil'
    bl_order = 7
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        """Draw the panel."""
        layout = self.layout
        scene = context.scene
        
        # Check if we have active data
        # TODO: Link to actual data structures
        has_alignment = False  # scene.saikei.has_alignment
        has_assembly = False   # scene.saikei.has_assembly
        
        # Header info
        box = layout.box()
        col = box.column(align=True)
        
        if has_alignment and has_assembly:
            col.label(text="[+] Ready to Visualize", icon='CHECKMARK')
            # TODO: Show current station, assembly name
        else:
            col.label(text="[!] Setup Required", icon='ERROR')
            if not has_alignment:
                col.label(text="• Create alignment first", icon='BLANK1')
            if not has_assembly:
                col.label(text="• Create cross-section assembly", icon='BLANK1')
        
        layout.separator()
        
        # Quick Actions
        box = layout.box()
        box.label(text="Quick Actions:", icon='PLAY')
        
        col = box.column(align=True)
        col.operator(
            "saikei.quick_preview",
            text="⚡ Quick Preview",
            icon='HIDE_OFF'
        )
        col.operator(
            "saikei.visualize_station",
            text="📍 Visualize Station",
            icon='MESH_DATA'
        )
        
        layout.separator()
        
        # Corridor Creation
        box = layout.box()
        box.label(text="Full Corridor:", icon='OUTLINER_OB_SURFACE')
        
        col = box.column(align=True)
        col.operator(
            "saikei.create_corridor",
            text="🏗️ Create Corridor",
            icon='SURFACE_DATA'
        )
        
        # Corridor settings preview (read-only for now)
        sub = col.box()
        sub.scale_y = 0.8
        sub.label(text="Settings:", icon='PREFERENCES')
        row = sub.row()
        row.label(text="Start: 0.00 m")
        row.label(text="End: 100.00 m")
        sub.label(text="Interval: 10.00 m")
        
        layout.separator()
        
        # Station Markers
        box = layout.box()
        box.label(text="Station Markers:", icon='DRIVER_DISTANCE')
        
        col = box.column(align=True)
        col.operator(
            "saikei.add_station_markers",
            text="📍 Add Markers",
            icon='OUTLINER_OB_FONT'
        )
        
        layout.separator()
        
        # Component Preview
        box = layout.box()
        box.label(text="Component Preview:", icon='MESH_CUBE')
        
        col = box.column(align=True)
        col.operator(
            "saikei.component_preview",
            text="🔍 Preview Component",
            icon='VIEWZOOM'
        )
        
        # Component list (simplified)
        if has_assembly:
            sub = col.box()
            sub.scale_y = 0.8
            sub.label(text="Available Components:")
            # TODO: List actual components
            sub.label(text="• Lane 1", icon='BLANK1')
            sub.label(text="• Lane 2", icon='BLANK1')
            sub.label(text="• Shoulder", icon='BLANK1')
        
        layout.separator()
        
        # Utilities
        box = layout.box()
        box.label(text="Utilities:", icon='TOOL_SETTINGS')
        
        col = box.column(align=True)
        col.operator(
            "saikei.clear_visualization",
            text="🧹 Clear Visualization",
            icon='TRASH'
        )
        
        # Statistics box
        layout.separator()
        box = layout.box()
        box.label(text="📊 Statistics:", icon='INFO')
        
        col = box.column(align=True)
        col.scale_y = 0.8
        
        # TODO: Show actual statistics
        col.label(text="Corridor Objects: 0")
        col.label(text="Station Markers: 0")
        col.label(text="Total Vertices: 0")
        col.label(text="Total Faces: 0")
        
        layout.separator()
        
        # Performance info
        box = layout.box()
        box.label(text="⚡ Performance:", icon='TIME')
        col = box.column(align=True)
        col.scale_y = 0.8
        col.label(text="Target: < 100ms per section")
        col.label(text="Status: Ready")


class SAIKEI_PT_visualization_settings(Panel):
    """Visualization settings subpanel"""
    bl_label = "Visualization Settings"
    bl_idname = "SAIKEI_PT_visualization_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Saikei Civil'
    bl_parent_id = "SAIKEI_PT_cross_section_visualization"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        """Draw settings panel."""
        layout = self.layout
        scene = context.scene
        
        # Appearance settings
        box = layout.box()
        box.label(text="Appearance:", icon='COLOR')
        
        col = box.column(align=True)
        
        # Material settings
        row = col.row()
        row.label(text="Show Materials:")
        row.prop(scene, "cross_section_show_materials", text="")
        
        # Smooth shading
        row = col.row()
        row.label(text="Smooth Shading:")
        row.prop(scene, "cross_section_smooth_shading", text="")
        
        # Color scheme (future)
        col.separator()
        col.label(text="Color Scheme: Default", icon='BLANK1')
        
        layout.separator()
        
        # Performance settings
        box = layout.box()
        box.label(text="Performance:", icon='PREFERENCES')
        
        col = box.column(align=True)
        
        # LOD settings (future)
        col.label(text="Level of Detail: Auto", icon='BLANK1')
        
        # Cache settings
        row = col.row()
        row.label(text="Use Cache:")
        row.prop(scene, "cross_section_use_cache", text="")
        
        layout.separator()
        
        # Export settings
        box = layout.box()
        box.label(text="Export Options:", icon='EXPORT')
        
        col = box.column(align=True)
        col.label(text="Format: IFC 4.3", icon='BLANK1')
        col.label(text="Include: All Components", icon='BLANK1')


class SAIKEI_PT_visualization_help(Panel):
    """Visualization help and tips"""
    bl_label = "Tips & Help"
    bl_idname = "SAIKEI_PT_visualization_help"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Saikei Civil'
    bl_parent_id = "SAIKEI_PT_cross_section_visualization"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        """Draw help panel."""
        layout = self.layout
        
        # Quick tips
        box = layout.box()
        box.label(text="💡 Quick Tips:", icon='INFO')
        
        col = box.column(align=True)
        col.scale_y = 0.8
        
        col.label(text="1. Create alignment first", icon='BLANK1')
        col.label(text="2. Design cross-section assembly", icon='BLANK1')
        col.label(text="3. Use Quick Preview to test", icon='BLANK1')
        col.label(text="4. Create full corridor", icon='BLANK1')
        col.label(text="5. Add station markers for labels", icon='BLANK1')
        
        layout.separator()
        
        # Performance tips
        box = layout.box()
        box.label(text="⚡ Performance:", icon='TIME')
        
        col = box.column(align=True)
        col.scale_y = 0.8
        
        col.label(text="• Start with short corridors", icon='BLANK1')
        col.label(text="• Use larger intervals (20-50m)", icon='BLANK1')
        col.label(text="• Clear old visualizations", icon='BLANK1')
        col.label(text="• Disable smooth shading for speed", icon='BLANK1')
        
        layout.separator()
        
        # Keyboard shortcuts (future)
        box = layout.box()
        box.label(text="⌨️ Shortcuts:", icon='EVENT_V')
        
        col = box.column(align=True)
        col.scale_y = 0.8
        
        col.label(text="Ctrl+Shift+V: Quick Preview", icon='BLANK1')
        col.label(text="Ctrl+Shift+C: Create Corridor", icon='BLANK1')
        col.label(text="Ctrl+Shift+M: Station Markers", icon='BLANK1')


# Registration
classes = (
    SAIKEI_PT_cross_section_visualization,
    SAIKEI_PT_visualization_settings,
    SAIKEI_PT_visualization_help,
)


def register():
    """Register panels."""
    for cls in classes:
        bpy.utils.register_class(cls)

    # Register scene properties for settings
    bpy.types.Scene.cross_section_show_materials = bpy.props.BoolProperty(
        name="Show Materials",
        description="Apply component materials to visualization",
        default=True
    )

    bpy.types.Scene.cross_section_smooth_shading = bpy.props.BoolProperty(
        name="Smooth Shading",
        description="Use smooth shading for better appearance",
        default=True
    )

    bpy.types.Scene.cross_section_use_cache = bpy.props.BoolProperty(
        name="Use Cache",
        description="Use cached geometry for faster updates",
        default=True
    )

    logger.info("Visualization panels registered")


def unregister():
    """Unregister panels."""
    # Remove scene properties
    del bpy.types.Scene.cross_section_show_materials
    del bpy.types.Scene.cross_section_smooth_shading
    del bpy.types.Scene.cross_section_use_cache

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    logger.info("Visualization panels unregistered")


if __name__ == "__main__":
    register()
