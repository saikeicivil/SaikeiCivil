# ==============================================================================
# Saikei Civil - Civil Engineering Tools for Blender
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
UI for checking and installing Saikei Civil dependencies
"""

import bpy
from bpy.types import Panel, Operator

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class SAIKEI_OT_install_dependencies(Operator):
    """Install missing Saikei Civil dependencies"""
    bl_idname = "saikei.install_dependencies"
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


class SAIKEI_OT_check_dependencies(Operator):
    """Check Saikei Civil dependency status"""
    bl_idname = "saikei.check_dependencies"
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


# NOTE: The Dependencies panel UI has been moved to Edit > Preferences > Extensions
# The operators below are still needed and are called from the preferences panel


# Registration
classes = (
    SAIKEI_OT_install_dependencies,
    SAIKEI_OT_check_dependencies,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
