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
            
            # Load cross-section assemblies from IFC
            assembly_count = self._load_cross_sections_from_ifc(context, ifc_file)

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
            if assembly_count > 0:
                logger.info("Cross-Section Assemblies: %s", assembly_count)
            logger.info("Check Blender outliner for visual hierarchy")
            logger.info("="*60)

            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open IFC file: {str(e)}")
            logger.error("Error opening IFC: %s", str(e))
            return {'CANCELLED'}

    def _load_cross_sections_from_ifc(self, context, ifc_file):
        """
        Load cross-section components from the IFC file.

        Per IFC 4.3, each component is stored as:
        - IfcPavement (lanes, shoulders)
        - IfcKerb (curbs)
        - Plus associated IfcOpenCrossProfileDef or IfcArbitraryClosedProfileDef

        Components are grouped by their parent IfcRoadPart into assemblies.

        Args:
            context: Blender context
            ifc_file: The loaded IFC file

        Returns:
            Number of assemblies loaded
        """
        from ..core.ifc_manager.manager import NativeIfcManager

        try:
            cs = context.scene.bc_cross_section

            # Clear existing assemblies
            cs.assemblies.clear()

            # Find all cross-section component entities
            pavements = ifc_file.by_type("IfcPavement") or []
            kerbs = ifc_file.by_type("IfcKerb") or []

            logger.info(f"Loading cross-sections: Found {len(pavements)} IfcPavement, {len(kerbs)} IfcKerb")

            # Group components by their parent (assembly name)
            assembly_components = {}  # name -> list of (entity, pset_data)

            for entity in pavements + kerbs:
                pset_data = self._get_component_pset(entity)
                if pset_data is None:
                    continue

                # Get assembly name from pset or parent
                assembly_name = pset_data.get('AssemblyName', 'Default Assembly')

                if assembly_name not in assembly_components:
                    assembly_components[assembly_name] = []

                assembly_components[assembly_name].append((entity, pset_data))
                logger.debug(f"  Found component: {entity.Name} -> assembly: {assembly_name}")

            # Create assemblies from grouped components
            loaded_count = 0
            for assembly_name, components in assembly_components.items():
                new_assembly = cs.assemblies.add()
                new_assembly.name = assembly_name
                new_assembly.assembly_type = 'CUSTOM'

                for entity, pset_data in components:
                    comp = new_assembly.components.add()
                    comp.name = entity.Name or "Unnamed Component"
                    comp.ifc_definition_id = entity.id()
                    comp.global_id = entity.GlobalId or ""

                    # Load component properties
                    if 'ComponentType' in pset_data:
                        comp.component_type = pset_data['ComponentType']
                    if 'Side' in pset_data:
                        comp.side = pset_data['Side']
                    if 'Width' in pset_data:
                        comp.width = float(pset_data['Width'])
                    if 'CrossSlope' in pset_data:
                        comp.cross_slope = float(pset_data['CrossSlope'])
                    if 'Offset' in pset_data:
                        comp.offset = float(pset_data['Offset'])

                    # Create Blender object for component
                    self._create_component_blender_object(context, comp, entity)

                # Calculate total width
                total_width = sum(c.width for c in new_assembly.components)
                new_assembly.total_width = total_width

                # Mark as valid
                new_assembly.is_valid = len(new_assembly.components) > 0
                new_assembly.validation_message = (
                    f"Loaded {len(new_assembly.components)} components from IFC"
                    if new_assembly.is_valid else "No components found"
                )

                loaded_count += 1
                logger.info(f"Loaded assembly '{assembly_name}' with {len(new_assembly.components)} components")

            if loaded_count == 0 and (pavements or kerbs):
                logger.warning("Found IFC components but no Pset_SaikeiCrossSection data")

            return loaded_count

        except Exception as e:
            logger.warning(f"Error loading cross-sections from IFC: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def _get_component_pset(self, entity):
        """
        Get cross-section component property set data from an IFC entity.

        Args:
            entity: IfcPavement, IfcKerb, or similar entity

        Returns:
            Dictionary of property values, or None if not a Saikei component
        """
        try:
            for rel in entity.IsDefinedBy or []:
                if not rel.is_a("IfcRelDefinesByProperties"):
                    continue

                pset = rel.RelatingPropertyDefinition
                if not pset or not pset.is_a("IfcPropertySet"):
                    continue

                # Look for our component-level property set
                if pset.Name != "Pset_SaikeiCrossSection":
                    continue

                # Extract property values
                data = {}
                for prop in pset.HasProperties or []:
                    if prop.is_a("IfcPropertySingleValue"):
                        value = prop.NominalValue
                        if value:
                            data[prop.Name] = value.wrappedValue
                return data

        except Exception as e:
            logger.warning(f"Error reading component pset: {e}")

        return None

    def _create_component_blender_object(self, context, comp, ifc_entity):
        """
        Create a Blender object to represent a component.

        Args:
            context: Blender context
            comp: BC_ComponentProperties instance
            ifc_entity: The IFC entity
        """
        from ..core.ifc_manager.manager import NativeIfcManager

        # Check if object already exists
        for obj in bpy.data.objects:
            if obj.get("ifc_definition_id") == ifc_entity.id():
                return obj

        # Determine display name based on IFC class
        ifc_class = ifc_entity.is_a()
        side_indicator = "L" if comp.side == "LEFT" else "R"
        display_name = f"{comp.name} [{side_indicator}] ({ifc_class})"

        # Create empty to represent component
        empty = bpy.data.objects.new(display_name, None)
        empty.empty_display_type = 'SINGLE_ARROW'
        empty.empty_display_size = 0.5

        # Link to IFC
        NativeIfcManager.link_object(empty, ifc_entity)

        # Add to project collection
        collection = NativeIfcManager.get_project_collection()
        if collection:
            collection.objects.link(empty)
        else:
            context.scene.collection.objects.link(empty)

        # Parent to the correct road part empty based on component type
        road_part_type = NativeIfcManager.COMPONENT_TO_ROAD_PART_TYPE.get(
            comp.component_type, 'ROADSEGMENT'
        )
        parent_empty = NativeIfcManager.get_road_part_empty(road_part_type)

        if parent_empty:
            empty.parent = parent_empty
            logger.debug(f"Parented {comp.name} to {parent_empty.name}")
        else:
            logger.warning(f"No parent empty found for {road_part_type}")

        return empty

    def _parse_component_data(self, assembly, comp_string):
        """
        Parse component data string and add components to assembly.

        Args:
            assembly: BC_AssemblyProperties instance
            comp_string: Semicolon-separated component data string
        """
        try:
            if not comp_string:
                return

            # Format: name|type|side|width|slope|offset;name|type|side|...
            comp_entries = comp_string.split(";")

            for entry in comp_entries:
                if not entry.strip():
                    continue

                parts = entry.split("|")
                if len(parts) < 6:
                    continue

                comp = assembly.components.add()
                comp.name = parts[0]
                comp.component_type = parts[1]
                comp.side = parts[2]
                comp.width = float(parts[3])
                comp.cross_slope = float(parts[4])
                comp.offset = float(parts[5])

        except Exception as e:
            logger.warning(f"Error parsing component data: {e}")

    def _create_assembly_blender_object(self, context, assembly, ifc_assembly):
        """
        Create a Blender empty to represent the assembly in the Outliner.

        Args:
            context: Blender context
            assembly: The PropertyGroup assembly data
            ifc_assembly: The IFC entity
        """
        from .. import tool

        try:
            # Check if a Blender object already exists for this assembly
            for obj in bpy.data.objects:
                if obj.get("ifc_definition_id") == assembly.ifc_definition_id:
                    # Already exists, just update name if needed
                    obj.name = f"{assembly.name} (IfcRoadPart)"
                    return obj

            # Create an empty object to represent the assembly
            empty = bpy.data.objects.new(f"{assembly.name} (IfcRoadPart)", None)
            empty.empty_display_type = 'PLAIN_AXES'
            empty.empty_display_size = 1.0

            # Link to IFC entity
            NativeIfcManager.link_object(empty, ifc_assembly)

            # Add to project collection
            project_coll_name = "Saikei Civil Project"
            if project_coll_name in bpy.data.collections:
                collection = bpy.data.collections[project_coll_name]
                collection.objects.link(empty)
            else:
                # Fallback to scene collection
                context.scene.collection.objects.link(empty)

            # Parent to Road object - use tool layer to find proper object
            road = tool.Spatial.get_road()
            road_obj = None
            if road:
                road_obj = tool.Ifc.get_object(road)
            if road_obj is None:
                # Fallback: try direct lookup by name
                from ..core.ifc_manager.blender_hierarchy import ROAD_EMPTY_NAME
                road_obj = bpy.data.objects.get(ROAD_EMPTY_NAME)

            if road_obj:
                empty.parent = road_obj

            logger.info(f"Created Blender representation for loaded assembly: {assembly.name}")
            return empty

        except Exception as e:
            logger.warning(f"Error creating Blender object for assembly: {e}")
            return None


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
            self.filepath = "Saikei Civil_Project.ifc"
        
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

            # Load cross-section assemblies from IFC (use open operator's method)
            assembly_count = BC_OT_open_ifc._load_cross_sections_from_ifc(
                BC_OT_open_ifc, context, ifc_file
            )

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
            if assembly_count > 0:
                logger.info("Cross-Section Assemblies: %s", assembly_count)
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
