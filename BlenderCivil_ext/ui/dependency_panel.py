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
Dependency Panel
UI for checking and installing BlenderCivil dependencies
"""

import bpy
from bpy.types import Panel, Operator

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class BLENDERCIVIL_OT_install_dependencies(Operator):
    """Install missing BlenderCivil dependencies"""
    bl_idname = "blendercivil.install_dependencies"
    bl_label = "Install Dependencies"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    def execute(self, context):
        from ..core import dependency_manager
        
        # Install all dependencies
        success, message = dependency_manager.DependencyManager.install_all_dependencies()
        
        if success:
            self.report({'INFO'}, "Dependencies installed! Please restart Blender.")
            # Show popup
            def draw(self, context):
                self.layout.label(text="Installation successful!")
                self.layout.label(text="Please restart Blender to use all features.")
            context.window_manager.popup_menu(draw, title="Success", icon='INFO')
        else:
            self.report({'ERROR'}, "Installation failed. Check console for details.")
            # Show error popup
            def draw_error(self, context):
                self.layout.label(text="Installation failed!")
                self.layout.label(text="Check the console for details.")
            context.window_manager.popup_menu(draw_error, title="Error", icon='ERROR')
        
        return {'FINISHED'}


class BLENDERCIVIL_OT_check_dependencies(Operator):
    """Check BlenderCivil dependency status"""
    bl_idname = "blendercivil.check_dependencies"
    bl_label = "Check Dependencies"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    def execute(self, context):
        from ..core import dependency_manager

        report = dependency_manager.DependencyManager.get_status_report()
        logger.info("=" * 60)
        logger.info("%s", report)
        logger.info("=" * 60)

        self.report({'INFO'}, "Dependency status printed to console")
        return {'FINISHED'}


class VIEW3D_PT_blendercivil_dependencies(bpy.types.Panel):
    """Panel for dependency management"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_label = 'Dependencies'
    bl_order = 1
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        # Import here to avoid circular import
        from ..core import dependency_manager
        
        # Check dependencies
        results = dependency_manager.DependencyManager.check_all_dependencies()
        has_missing = dependency_manager.DependencyManager.has_missing_dependencies()
        
        if has_missing:
            # Show warning
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Missing dependencies:", icon='ERROR')
            col.separator(factor=0.5)

            # List missing dependencies
            for dep_key, (available, version) in results.items():
                if not available:
                    dep_info = dependency_manager.DependencyManager.DEPENDENCIES[dep_key]
                    row = col.row()
                    row.label(text=f"[-] {dep_info['display_name']}")
                    
                    # Show description
                    desc_row = col.row()
                    desc_row.label(text=f"   {dep_info['description']}", icon='BLANK1')
            
            col.separator()
            
            # Install button
            col.operator("blendercivil.install_dependencies", icon='IMPORT')
            
            # Help text
            col.separator()
            help_box = col.box()
            help_col = help_box.column(align=True)
            help_col.label(text="Installation will:", icon='INFO')
            help_col.label(text="  • Use Blender's Python pip", icon='BLANK1')
            help_col.label(text="  • Install IfcOpenShell 0.8+", icon='BLANK1')
            help_col.label(text="  • Take 30-60 seconds", icon='BLANK1')
            help_col.label(text="  • Require restart after", icon='BLANK1')
            
        else:
            # All dependencies available
            box = layout.box()
            col = box.column(align=True)
            col.label(text="All dependencies installed", icon='CHECKMARK')
            col.separator(factor=0.5)
            
            # List installed dependencies
            for dep_key, (available, version) in results.items():
                dep_info = dependency_manager.DependencyManager.DEPENDENCIES[dep_key]
                row = col.row()
                version_str = f" ({version})" if version != "unknown" else ""
                row.label(text=f"  {dep_info['display_name']}{version_str}", icon='BLANK1')
        
        # Check status button
        layout.separator()
        layout.operator("blendercivil.check_dependencies", icon='VIEWZOOM')


# Registration
classes = (
    BLENDERCIVIL_OT_install_dependencies,
    BLENDERCIVIL_OT_check_dependencies,
    VIEW3D_PT_blendercivil_dependencies,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
