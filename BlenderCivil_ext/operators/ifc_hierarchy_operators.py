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
IFC Hierarchy Operators
========================

Provides operators for IFC file management with visual hierarchy representation
in the Blender outliner.

This module handles the complete lifecycle of IFC file operations including
creating new files, loading existing files, saving modifications, and managing
the spatial hierarchy visualization in Blender.

Operators:
    BC_OT_new_ifc: Create a new IFC 4X3 file with spatial hierarchy
    BC_OT_open_ifc: Open and load existing IFC files
    BC_OT_save_ifc: Save current IFC file to disk
    BC_OT_reload_ifc: Reload IFC file from disk to refresh data
    BC_OT_clear_ifc: Clear current IFC data and Blender hierarchy
    BC_OT_show_ifc_info: Display current IFC file information
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

# Import the NativeIfcManager from the core module
from ..core.native_ifc_manager import NativeIfcManager
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class BC_OT_new_ifc(Operator):
    """Create new IFC file with complete spatial hierarchy.

    This operator creates a new IFC 4X3 file with the standard civil engineering
    spatial structure: IfcProject → IfcSite → IfcRoad. The hierarchy is
    automatically visualized in the Blender outliner using Empty objects.

    The operator also creates collections for Alignments and Geomodels to
    organize civil engineering elements.

    Usage:
        Called from the UI panel when user wants to start a new IFC project.
        No parameters required - creates a default structure.

    Returns:
        {'FINISHED'} on success, {'CANCELLED'} on error
    """
    bl_idname = "bc.new_ifc"
    bl_label = "Create New IFC"
    bl_description = "Create new IFC4X3 file with Project → Site → Road hierarchy"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """
        Create new IFC file and visualize hierarchy in Blender outliner.
        
        Creates:
        - IFC spatial structure: IfcProject → IfcSite → IfcRoad
        - Blender visualization with Empty objects
        - Collections for Alignments and Geomodels
        """
        
        try:
            # Create new IFC file with full hierarchy
            result = NativeIfcManager.new_file()
            
            # Report success
            self.report({'INFO'}, 
                f"Created IFC file: {result['project'].Name} "
                f"({result['ifc_file'].schema})")
            
            # Show info in console
            logger.info("="*60)
            logger.info("IFC SPATIAL HIERARCHY CREATED")
            logger.info("="*60)
            logger.info("Schema: %s", result['ifc_file'].schema)
            logger.info("Project: %s", result['project'].Name)
            logger.info("Site: %s", result['site'].Name)
            logger.info("Road: %s", result['road'].Name)
            logger.info("Check Blender outliner for visual hierarchy")
            logger.info("="*60)
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create IFC file: {str(e)}")
            logger.error("Error creating IFC: %s", str(e))
            return {'CANCELLED'}


class BC_OT_open_ifc(Operator, ImportHelper):
    """Open existing IFC file and visualize hierarchy.

    Loads an IFC file from disk and creates a visual representation of its
    spatial hierarchy in the Blender outliner. Automatically detects and
    visualizes alignments, geomodels, and other civil engineering elements.

    Properties:
        filename_ext: File extension filter (.ifc)
        filter_glob: Glob pattern for file browser

    Usage:
        Opens a file browser for the user to select an IFC file. Once selected,
        the file is loaded and its structure is visualized in Blender.

    Returns:
        {'FINISHED'} on success, {'CANCELLED'} on error
    """
    bl_idname = "bc.open_ifc"
    bl_label = "Open IFC File"
    bl_description = "Open existing IFC file and create Blender visualization"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".ifc"
    filter_glob: StringProperty(
        default="*.ifc",
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        """
        Load IFC file and create Blender visualization.
        """
        
        try:
            # Load IFC file
            ifc_file = NativeIfcManager.open_file(self.filepath)
            
            # Get info
            info = NativeIfcManager.get_info()
            
            # Report success
            self.report({'INFO'}, 
                f"Loaded: {info['project']} ({info['entities']} entities)")
            
            # Show info in console
            logger.info("="*60)
            logger.info("IFC FILE LOADED")
            logger.info("="*60)
            logger.info("File: %s", self.filepath)
            logger.info("Schema: %s", info['schema'])
            logger.info("Entities: %s", info['entities'])
            logger.info("Alignments: %s", info['alignments'])
            logger.info("Geomodels: %s", info['geomodels'])
            logger.info("Check Blender outliner for visual hierarchy")
            logger.info("="*60)
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open IFC file: {str(e)}")
            logger.error("Error opening IFC: %s", str(e))
            return {'CANCELLED'}


class BC_OT_save_ifc(Operator, ExportHelper):
    """Save IFC file to disk.

    Writes the current in-memory IFC file to disk. Opens a file browser with
    a default filename based on either the current file path or the project name.

    Properties:
        filename_ext: File extension (.ifc)
        filter_glob: Glob pattern for file browser

    Usage:
        Called when user wants to save their IFC data. Presents a file browser
        with the last saved location or a default filename.

    Returns:
        {'FINISHED'} on success, {'CANCELLED'} if no file loaded or error
    """
    bl_idname = "bc.save_ifc"
    bl_label = "Save IFC File"
    bl_description = "Save current IFC file to disk"
    bl_options = {'REGISTER'}
    
    filename_ext = ".ifc"
    filter_glob: StringProperty(
        default="*.ifc",
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        """
        Save IFC file to selected location.
        """
        
        try:
            # Check if file exists
            if NativeIfcManager.file is None:
                self.report({'ERROR'}, "No IFC file to save")
                return {'CANCELLED'}
            
            # Save file
            NativeIfcManager.save_file(self.filepath)
            
            # Get info
            info = NativeIfcManager.get_info()
            
            # Report success
            self.report({'INFO'}, 
                f"Saved: {self.filepath} ({info['entities']} entities)")
            
            # Show info in console
            logger.info("="*60)
            logger.info("IFC FILE SAVED")
            logger.info("="*60)
            logger.info("File: %s", self.filepath)
            logger.info("Entities: %s", info['entities'])
            logger.info("Alignments: %s", info['alignments'])
            logger.info("Geomodels: %s", info['geomodels'])
            logger.info("="*60)
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to save IFC file: {str(e)}")
            logger.error("Error saving IFC: %s", str(e))
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Open file browser with default filename"""
        # Set default filename
        if NativeIfcManager.filepath:
            self.filepath = NativeIfcManager.filepath
        else:
            self.filepath = "BlenderCivil_Project.ifc"
        
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class BC_OT_clear_ifc(Operator):
    """Clear current IFC file and Blender hierarchy.

    Clears all IFC data from memory and removes the visual hierarchy
    representation from the Blender outliner. This is a destructive operation
    that removes all IFC-related objects and collections.

    Usage:
        Called when user wants to close the current IFC project and start fresh.
        Should be used before opening a different IFC file or starting a new one.

    Returns:
        {'FINISHED'} on success, {'CANCELLED'} on error
    """
    bl_idname = "bc.clear_ifc"
    bl_label = "Clear IFC"
    bl_description = "Clear current IFC file and remove Blender visualization"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """Clear IFC data and Blender hierarchy"""
        
        try:
            NativeIfcManager.clear()

            self.report({'INFO'}, "Cleared IFC file and hierarchy")
            logger.info("IFC data cleared")

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to clear IFC: {str(e)}")
            logger.error("Error clearing IFC: %s", str(e))
            return {'CANCELLED'}


class BC_OT_reload_ifc(Operator):
    """Reload IFC file from disk.

    Reloads the current IFC file from its saved location on disk. This is
    useful when the file has been modified externally or when you want to
    refresh the data after making changes.

    The file must have been previously saved - this operator will fail if
    the IFC file only exists in memory without a saved path.

    Usage:
        Called when user needs to refresh the IFC data from disk. Commonly used
        after external tools have modified the IFC file or to reset changes.

    Returns:
        {'FINISHED'} on success, {'CANCELLED'} if no file loaded or not saved
    """
    bl_idname = "bc.reload_ifc"
    bl_label = "Reload IFC"
    bl_description = "Reload IFC file from disk to refresh alignment and geometry data"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Reload IFC file from disk"""

        try:
            # Check if file is loaded and has a filepath
            if NativeIfcManager.file is None:
                self.report({'ERROR'}, "No IFC file loaded")
                return {'CANCELLED'}

            if not NativeIfcManager.filepath:
                self.report({'ERROR'}, "IFC file has not been saved yet - use 'Save' first")
                return {'CANCELLED'}

            # Store filepath
            filepath = NativeIfcManager.filepath

            # Reload the file
            ifc_file = NativeIfcManager.open_file(filepath)

            # Get info
            info = NativeIfcManager.get_info()

            # Report success
            self.report({'INFO'},
                f"Reloaded: {info['project']} ({info['entities']} entities)")

            # Show info in console
            logger.info("="*60)
            logger.info("IFC FILE RELOADED")
            logger.info("="*60)
            logger.info("File: %s", filepath)
            logger.info("Entities: %s", info['entities'])
            logger.info("Alignments: %s", info['alignments'])
            logger.info("Geomodels: %s", info['geomodels'])
            logger.info("="*60)

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to reload IFC file: {str(e)}")
            logger.error("Error reloading IFC: %s", str(e))
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class BC_OT_show_ifc_info(Operator):
    """Show current IFC file information.

    Displays detailed information about the currently loaded IFC file including
    schema version, entity counts, spatial structure, and civil engineering
    elements (alignments, geomodels).

    The information is printed to both the console logger and shown in the
    Blender info area.

    Usage:
        Called when user wants to inspect the current IFC file details.
        No parameters required.

    Returns:
        {'FINISHED'} always (displays 'No IFC file loaded' if none loaded)
    """
    bl_idname = "bc.show_ifc_info"
    bl_label = "Show IFC Info"
    bl_description = "Display current IFC file information in console"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        """Display IFC file information"""
        
        info = NativeIfcManager.get_info()
        
        if not info['loaded']:
            self.report({'INFO'}, "No IFC file loaded")
            return {'FINISHED'}
        
        # Display in console
        logger.info("="*60)
        logger.info("IFC FILE INFORMATION")
        logger.info("="*60)
        logger.info("File: %s", info['filepath'] or 'Not saved')
        logger.info("Schema: %s", info['schema'])
        logger.info("Total Entities: %s", info['entities'])
        logger.info("Spatial Structure:")
        logger.info("  Project: %s", info['project'])
        logger.info("  Site: %s", info['site'])
        logger.info("  Road: %s", info['road'])
        logger.info("Civil Elements:")
        logger.info("  Alignments: %s", info['alignments'])
        logger.info("  Geomodels: %s", info['geomodels'])
        logger.info("="*60)
        
        self.report({'INFO'}, 
            f"IFC Info: {info['entities']} entities, "
            f"{info['alignments']} alignments")
        
        return {'FINISHED'}


# ============================================================================
# Registration
# ============================================================================

classes = (
    BC_OT_new_ifc,
    BC_OT_open_ifc,
    BC_OT_save_ifc,
    BC_OT_reload_ifc,
    BC_OT_clear_ifc,
    BC_OT_show_ifc_info,
)


def register():
    """Register operators"""
    for cls in classes:
        bpy.utils.register_class(cls)
    logger.info("Registered IFC operators")


def unregister():
    """Unregister operators"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    logger.info("Unregistered IFC operators")


if __name__ == "__main__":
    register()
