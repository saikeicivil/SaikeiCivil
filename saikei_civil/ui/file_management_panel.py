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
Saikei Civil File Management Panel
UI panel for managing IFC files with spatial hierarchy
"""

import bpy
from bpy.types import Panel

from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Import from parent ui module
from . import NativeIfcManager


class VIEW3D_PT_file_management(Panel):
    """IFC File Management Panel"""
    bl_label = "File Management"
    bl_idname = "VIEW3D_PT_file_management"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei Civil"
    bl_order = 2
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # ==========================================
        # IFC File Status
        # ==========================================

        box = layout.box()
        box.label(text="IFC Project", icon='FILE_3D')

        info = NativeIfcManager.get_info()

        if info['loaded']:
            # Show file info
            col = box.column(align=True)
            col.scale_y = 0.9

            # Project name
            row = col.row()
            row.label(text=f"{info['project']}", icon='SCENE_DATA')

            # File path (if saved)
            if info['filepath']:
                import os
                filename = os.path.basename(info['filepath'])
                col.label(text=f"  File: {filename}")
            else:
                col.label(text="  [Not saved]", icon='ERROR')

            # Schema
            col.label(text=f"  Schema: {info['schema']}")

            # Entity counts
            col.separator()
            stats = col.column(align=True)
            stats.scale_y = 0.8
            stats.label(text=f"  Total Entities: {info['entities']}")
            stats.label(text=f"  Alignments: {info['alignments']}")
            stats.label(text=f"  Geomodels: {info['geomodels']}")

            # ==========================================
            # File Actions
            # ==========================================

            col.separator()
            row = col.row(align=True)
            row.operator("bc.save_ifc", text="Save", icon='FILE_TICK')
            row.operator("bc.reload_ifc", text="", icon='FILE_REFRESH')
            row.operator("bc.show_ifc_info", text="", icon='INFO')

            col.separator()
            col.operator("bc.clear_ifc", text="Close Project", icon='PANEL_CLOSE')

        else:
            # No file loaded - show create/open options
            col = box.column(align=True)
            col.label(text="No project loaded", icon='ERROR')
            col.separator()

            # Primary actions
            col.scale_y = 1.2
            col.operator("bc.new_ifc", text="New Project", icon='FILE_NEW')
            col.operator("bc.open_ifc", text="Open Project", icon='FILE_FOLDER')

        # ==========================================
        # Spatial Hierarchy Info
        # ==========================================

        if info['loaded']:
            box = layout.box()
            box.label(text="Spatial Structure", icon='OUTLINER')

            col = box.column(align=True)
            col.scale_y = 0.85

            # Show hierarchy
            col.label(text=f"  Project: {info['project']}")
            col.label(text=f"    └─ Site: {info['site']}")
            col.label(text=f"        └─ Road: {info['road']}")

            # Tip
            col.separator()
            tip = col.column(align=True)
            tip.scale_y = 0.7
            tip.label(text="Check Blender outliner", icon='OUTLINER_OB_EMPTY')
            tip.label(text="for visual hierarchy")


# ============================================================================
# Registration
# ============================================================================

classes = (
    VIEW3D_PT_file_management,
)


def register():
    """Register panel classes"""
    for cls in classes:
        bpy.utils.register_class(cls)
    logger.debug("File Management panel registered")


def unregister():
    """Unregister panel classes"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    logger.debug("File Management panel unregistered")


if __name__ == "__main__":
    register()
