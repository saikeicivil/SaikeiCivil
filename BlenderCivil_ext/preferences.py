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
BlenderCivil Extension Preferences

Stores user preferences including API keys for external services.
Also includes Dependencies and Validation tools.
"""

import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty


class BlenderCivilPreferences(AddonPreferences):
    """BlenderCivil extension preferences"""

    # This must match the extension name
    bl_idname = __package__

    # MapTiler API Key for CRS search
    maptiler_api_key: StringProperty(
        name="MapTiler API Key",
        description="API key for MapTiler Coordinates API (used for CRS search). Get your free key at https://www.maptiler.com/cloud/",
        default="",
        subtype='PASSWORD'
    )

    def draw(self, context):
        """Draw preferences UI"""
        layout = self.layout

        # ===========================================
        # DEPENDENCIES SECTION
        # ===========================================
        box = layout.box()
        box.label(text="Dependencies", icon='PACKAGE')

        # Import dependency manager
        from .core import dependency_manager

        # Check dependencies
        results = dependency_manager.DependencyManager.check_all_dependencies()
        has_missing = dependency_manager.DependencyManager.has_missing_dependencies()

        if has_missing:
            # Show warning
            col = box.column(align=True)
            col.label(text="Missing dependencies:", icon='ERROR')
            col.separator(factor=0.5)

            # List missing dependencies
            for dep_key, (available, version) in results.items():
                if not available:
                    dep_info = dependency_manager.DependencyManager.DEPENDENCIES[dep_key]
                    row = col.row()
                    row.label(text=f"  ✗ {dep_info['display_name']}")

            col.separator()

            # Install button
            col.operator("blendercivil.install_dependencies", icon='IMPORT')

        else:
            # All dependencies available
            col = box.column(align=True)
            col.label(text="All dependencies installed", icon='CHECKMARK')
            col.separator(factor=0.5)

            # List installed dependencies
            for dep_key, (available, version) in results.items():
                dep_info = dependency_manager.DependencyManager.DEPENDENCIES[dep_key]
                version_str = f" ({version})" if version != "unknown" else ""
                col.label(text=f"  ✓ {dep_info['display_name']}{version_str}")

        # Check status button
        box.operator("blendercivil.check_dependencies", icon='FILE_REFRESH', text="Refresh Status")

        layout.separator()

        # ===========================================
        # MAPTILER API SECTION
        # ===========================================
        box = layout.box()
        box.label(text="MapTiler Coordinates API", icon='WORLD')

        col = box.column(align=True)
        col.label(text="Required for CRS (Coordinate Reference System) search")
        col.label(text="Get your free API key at: maptiler.com/cloud")

        row = box.row(align=True)
        row.prop(self, "maptiler_api_key", text="API Key")

        # Test button
        if self.maptiler_api_key:
            row.operator("bc.test_maptiler_connection", text="", icon='CHECKMARK')
            box.label(text="✓ API key saved", icon='INFO')
        else:
            box.label(text="⚠ No API key set - CRS search will not work", icon='ERROR')

        layout.separator()

        # ===========================================
        # VALIDATION/DEBUG SECTION
        # ===========================================
        box = layout.box()
        box.label(text="Validation & Debugging", icon='CHECKMARK')

        col = box.column(align=True)
        col.operator("bc.validate_ifc_alignment", text="Validate IFC", icon='FILE_TICK')
        col.operator("bc.list_all_ifc_objects", text="List All IFC Objects", icon='OUTLINER')


class BC_OT_test_maptiler_connection(bpy.types.Operator):
    """Test MapTiler API connection"""
    bl_idname = "bc.test_maptiler_connection"
    bl_label = "Test Connection"
    bl_description = "Test MapTiler API connection with your API key"

    def execute(self, context):
        preferences = context.preferences.addons[__package__].preferences
        api_key = preferences.maptiler_api_key

        if not api_key:
            self.report({'ERROR'}, "No API key set")
            return {'CANCELLED'}

        # Test the API with a simple search
        try:
            from .core.crs_searcher import CRSSearcher
            searcher = CRSSearcher(api_key=api_key)

            # Try searching for WGS84 (should always work)
            results = searcher.search("WGS84", limit=1)

            if results:
                self.report({'INFO'}, f"✓ Connection successful! Found: {results[0].name}")
            else:
                self.report({'WARNING'}, "API key works but no results returned")

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Connection failed: {str(e)}")
            return {'CANCELLED'}


# Registration
classes = (
    BlenderCivilPreferences,
    BC_OT_test_maptiler_connection,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
