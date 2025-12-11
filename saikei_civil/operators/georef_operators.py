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
Georeferencing Operators
=========================

Provides operators for georeferencing civil engineering projects using
coordinate reference systems (CRS).

This module connects the UI to backend georeferencing functionality, enabling
users to search for coordinate systems, configure false origins, and apply
georeferencing to IFC files. Supports EPSG codes and MapTiler API integration
for CRS lookups.

Operators:
    BC_OT_search_crs: Search for coordinate reference systems by name or EPSG code
    BC_OT_select_crs: Select a CRS from search results
    BC_OT_setup_georeferencing: Configure georeferencing with selected CRS
    BC_OT_preview_transform: Preview coordinate transformation calculations
    BC_OT_pick_false_origin: Set false origin from 3D cursor position
    BC_OT_validate_georeferencing: Check georeferencing configuration
    BC_OT_load_georeferencing: Load existing georeferencing from IFC file

Author: Saikei Civil Team
Date: November 2025
Sprint: 2 Day 3 - UI Integration
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty, FloatProperty
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Import backend modules (these will be from Sprint 2 Day 2)
try:
    from ..core.crs_searcher import CRSSearcher
    from ..core.native_ifc_georeferencing import NativeIfcGeoreferencing
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False
    logger.warning("Backend georeferencing modules not found")


class BC_OT_search_crs(Operator):
    """Search for Coordinate Reference Systems.

    Performs a search for coordinate reference systems using the MapTiler API.
    Users can search by name (e.g., "NAD83 California") or EPSG code.
    Results are stored in the scene's bc_georef.search_results collection.

    Properties:
        Uses scene.bc_georef.crs_search_query for the search term

    Requirements:
        - MapTiler API key must be configured in addon preferences
        - Backend georeferencing modules must be available

    Usage:
        Called when user enters a search term and clicks the search button.
        Results are displayed in the UI list for selection.

    Returns:
        {'FINISHED'} on successful search, {'CANCELLED'} on error or empty query
    """
    bl_idname = "bc.search_crs"
    bl_label = "Search CRS"
    bl_description = "Search for coordinate reference systems by name or EPSG code"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        georef = scene.bc_georef
        
        if not HAS_BACKEND:
            self.report({'ERROR'}, "Backend modules not available")
            return {'CANCELLED'}
        
        query = georef.crs_search_query.strip()
        
        if not query:
            self.report({'WARNING'}, "Please enter a search term")
            return {'CANCELLED'}
        
        try:
            # Get API key from preferences
            # In Blender 4.5+, extensions are registered with names like "bl_ext.user_default.saikei"
            # So we need to search for the correct addon key
            root_package = __package__.split('.')[0] if '.' in __package__ else __package__
            api_key = ""

            try:
                # Blender 4.5+ extension ID from blender_manifest.toml
                extension_id = "saikei_civil"

                # DEBUG: Log all available addon keys
                logger.debug("All registered addons:")
                for k in sorted(context.preferences.addons.keys()):
                    logger.debug("  - %s", k)

                # Try the standard Blender 4.5+ user extension naming first
                addon_keys_to_try = [
                    f"bl_ext.user_default.{extension_id}",  # Standard user extension
                    f"bl_ext.system_default.{extension_id}",  # System extension
                    extension_id,  # Direct ID
                ]

                logger.debug("Trying addon keys:")
                addon_key = None
                for key in addon_keys_to_try:
                    logger.debug("  - Checking: %s", key)
                    if key in context.preferences.addons:
                        addon_key = key
                        logger.debug("    FOUND!")
                        break

                # If not found, search for it
                if not addon_key:
                    logger.debug("Not found in standard locations, searching...")
                    for key in context.preferences.addons.keys():
                        if extension_id in key.lower():
                            addon_key = key
                            logger.debug("  Found via search: %s", key)
                            break

                if addon_key:
                    logger.debug("Using addon key: %s", addon_key)
                    preferences = context.preferences.addons[addon_key].preferences
                    logger.debug("Preferences type: %s", type(preferences).__name__)

                    if hasattr(preferences, 'maptiler_api_key'):
                        api_key = preferences.maptiler_api_key
                        logger.debug("API key retrieved: %s", 'Yes' if api_key else 'No (empty)')
                    else:
                        logger.error("maptiler_api_key attribute not found")
                        logger.error("Available attributes: %s", [a for a in dir(preferences) if not a.startswith('_')])
                        self.report({'ERROR'}, f"Preferences missing maptiler_api_key")
                        return {'CANCELLED'}
                else:
                    logger.error("Could not find extension '%s'", extension_id)
                    self.report({'ERROR'}, f"Could not find Saikei Civil extension")
                    return {'CANCELLED'}

            except Exception as e:
                logger.error("EXCEPTION: %s", e, exc_info=True)
                self.report({'ERROR'}, f"Error accessing API key: {str(e)}")
                return {'CANCELLED'}

            # Perform search
            searcher = CRSSearcher(api_key=api_key)
            results = searcher.search(query, limit=20)
            
            # Clear previous results
            georef.search_results.clear()
            
            # Add new results
            for crs_info in results:
                item = georef.search_results.add()
                item.epsg_code = crs_info.epsg_code
                item.name = crs_info.name
                item.area = crs_info.area
                item.kind = crs_info.kind
                item.unit = crs_info.unit
            
            # Reset selection
            georef.search_results_index = 0
            
            self.report({'INFO'}, f"Found {len(results)} coordinate reference systems")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Search failed: {str(e)}")
            return {'CANCELLED'}


class BC_OT_select_crs(Operator):
    """Select a CRS from search results.

    Selects a coordinate reference system from the search results and loads
    its detailed information. The selected CRS is stored in the scene's
    bc_georef properties for later use in georeferencing setup.

    Properties:
        epsg_code: Optional EPSG code to select directly (default: 0 = use UI selection)

    Usage:
        Called when user clicks on a CRS in the search results list or when
        programmatically selecting a CRS by EPSG code.

    Returns:
        {'FINISHED'} on success, {'CANCELLED'} if no results or invalid selection
    """
    bl_idname = "bc.select_crs"
    bl_label = "Select CRS"
    bl_description = "Select this coordinate reference system for georeferencing"
    bl_options = {'REGISTER', 'UNDO'}
    
    epsg_code: IntProperty(name="EPSG Code", default=0)
    
    def execute(self, context):
        scene = context.scene
        georef = scene.bc_georef
        
        if self.epsg_code == 0:
            # Use currently selected search result
            if not georef.search_results:
                self.report({'WARNING'}, "No search results available")
                return {'CANCELLED'}
            
            if georef.search_results_index >= len(georef.search_results):
                self.report({'WARNING'}, "Invalid selection")
                return {'CANCELLED'}
            
            selected = georef.search_results[georef.search_results_index]
            self.epsg_code = selected.epsg_code
        
        try:
            # Get CRS details
            if HAS_BACKEND:
                # Get API key from preferences (Blender 4.5+ extension)
                extension_id = "saikei_civil"
                api_key = ""

                try:
                    addon_keys_to_try = [
                        f"bl_ext.user_default.{extension_id}",
                        f"bl_ext.system_default.{extension_id}",
                        extension_id,
                    ]

                    addon_key = None
                    for key in addon_keys_to_try:
                        if key in context.preferences.addons:
                            addon_key = key
                            break

                    if not addon_key:
                        for key in context.preferences.addons.keys():
                            if extension_id in key.lower():
                                addon_key = key
                                break

                    if addon_key and hasattr(context.preferences.addons[addon_key].preferences, 'maptiler_api_key'):
                        api_key = context.preferences.addons[addon_key].preferences.maptiler_api_key
                except Exception as e:
                    pass  # Continue with empty API key

                searcher = CRSSearcher(api_key=api_key)
                crs_info = searcher.get_crs(self.epsg_code)
                
                # Update properties
                georef.selected_epsg_code = crs_info.epsg_code
                georef.selected_crs_name = crs_info.name
                georef.selected_crs_area = crs_info.area
                georef.selected_crs_unit = crs_info.unit
            else:
                # Fallback if backend not available
                selected = georef.search_results[georef.search_results_index]
                georef.selected_epsg_code = selected.epsg_code
                georef.selected_crs_name = selected.name
                georef.selected_crs_area = selected.area
                georef.selected_crs_unit = selected.unit
            
            georef.georef_status_message = "CRS selected - configure false origin"
            
            self.report({'INFO'}, f"Selected: {georef.selected_crs_name}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to select CRS: {str(e)}")
            return {'CANCELLED'}


class BC_OT_setup_georeferencing(Operator):
    """Setup georeferencing for the project.

    Applies georeferencing configuration to the IFC file using the selected
    coordinate reference system and false origin. Creates IfcMapConversion and
    IfcProjectedCRS entities in the IFC file.

    Properties:
        Uses scene.bc_georef properties:
            - selected_epsg_code: The chosen coordinate system
            - false_origin_easting/northing/elevation: Local origin offset
            - grid_rotation: Optional grid rotation angle
            - map_scale: Optional map scale factor

    Requirements:
        - CRS must be selected first
        - Backend georeferencing modules must be available

    Usage:
        Called after user has selected a CRS and configured the false origin.
        Creates or updates georeferencing in the IFC file.

    Returns:
        {'FINISHED'} on success, {'CANCELLED'} if validation fails or error
    """
    bl_idname = "bc.setup_georeferencing"
    bl_label = "Setup Georeferencing"
    bl_description = "Configure georeferencing with selected CRS and false origin"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        georef = scene.bc_georef
        
        # Validation
        if georef.selected_epsg_code == 0:
            self.report({'ERROR'}, "Please select a coordinate reference system first")
            return {'CANCELLED'}
        
        if not HAS_BACKEND:
            self.report({'ERROR'}, "Backend modules not available")
            return {'CANCELLED'}
        
        try:
            # Get or create IFC file path
            if not georef.ifc_file_path:
                import os
                blend_filepath = bpy.data.filepath
                if blend_filepath:
                    base_path = os.path.splitext(blend_filepath)[0]
                    georef.ifc_file_path = base_path + ".ifc"
                else:
                    georef.ifc_file_path = "/tmp/saikei_project.ifc"
            
            # Create georeferencing
            georef_manager = NativeIfcGeoreferencing(georef.ifc_file_path)
            
            false_origin = (
                georef.false_origin_easting,
                georef.false_origin_northing,
                georef.false_origin_elevation
            )
            
            # Setup with rotation if specified
            x_axis_abscissa = 1.0
            x_axis_ordinate = 0.0
            
            if georef.grid_rotation != 0.0:
                import math
                rad = math.radians(georef.grid_rotation)
                x_axis_abscissa = math.cos(rad)
                x_axis_ordinate = math.sin(rad)
            
            georef_manager.setup_georeferencing(
                epsg_code=georef.selected_epsg_code,
                false_origin=false_origin,
                x_axis_abscissa=x_axis_abscissa,
                x_axis_ordinate=x_axis_ordinate,
                scale=georef.map_scale
            )
            
            # Save IFC file
            georef_manager.save()
            
            # Update status
            georef.is_georeferenced = True
            georef.georef_status_message = f"Georeferenced: EPSG:{georef.selected_epsg_code}"
            
            self.report({'INFO'}, f"Georeferencing configured successfully")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Setup failed: {str(e)}")
            logger.error("Setup georeferencing failed: %s", e, exc_info=True)
            return {'CANCELLED'}


class BC_OT_preview_transform(Operator):
    """Preview coordinate transformation.

    Transforms local Blender coordinates to real-world map coordinates using
    the configured georeferencing. Useful for verifying the georeferencing
    setup before applying it to actual geometry.

    Properties:
        Uses scene.bc_georef properties:
            - preview_local_x/y/z: Input local coordinates
            - preview_map_easting/northing/elevation: Output map coordinates

    Requirements:
        - Project must be georeferenced
        - Backend georeferencing modules must be available

    Usage:
        Called when user wants to test the coordinate transformation.
        Enter local coordinates and see the corresponding map coordinates.

    Returns:
        {'FINISHED'} on success, {'CANCELLED'} if not georeferenced or error
    """
    bl_idname = "bc.preview_transform"
    bl_label = "Preview Transform"
    bl_description = "Preview coordinate transformation at a point"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        scene = context.scene
        georef = scene.bc_georef
        
        if not georef.is_georeferenced:
            self.report({'WARNING'}, "Project is not georeferenced")
            return {'CANCELLED'}
        
        if not HAS_BACKEND:
            self.report({'ERROR'}, "Backend modules not available")
            return {'CANCELLED'}
        
        try:
            # Load georeferencing
            georef_manager = NativeIfcGeoreferencing(georef.ifc_file_path)
            georef_manager.load_existing_georeferencing()
            
            # Transform local to map
            local_coords = (
                georef.preview_local_x,
                georef.preview_local_y,
                georef.preview_local_z
            )
            
            map_coords = georef_manager.local_to_map(local_coords)
            
            # Update preview properties
            georef.preview_map_easting = map_coords[0]
            georef.preview_map_northing = map_coords[1]
            georef.preview_map_elevation = map_coords[2]
            
            self.report({'INFO'}, f"Transformed: Local {local_coords} → Map {map_coords}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Transform failed: {str(e)}")
            return {'CANCELLED'}


class BC_OT_pick_false_origin(Operator):
    """Pick false origin from 3D cursor.

    Sets the georeferencing false origin based on the current 3D cursor location.
    The coordinates are automatically rounded to the nearest specified value
    for cleaner numbers.

    Properties:
        round_to_meters: Round false origin to nearest N meters (default: 100)

    Usage:
        Position the 3D cursor at the desired false origin location and call
        this operator. The cursor coordinates will be rounded and set as the
        false origin for georeferencing.

    Returns:
        {'FINISHED'} always
    """
    bl_idname = "bc.pick_false_origin"
    bl_label = "Pick from 3D Cursor"
    bl_description = "Set false origin from current 3D cursor location"
    bl_options = {'REGISTER', 'UNDO'}
    
    round_to_meters: IntProperty(
        name="Round To",
        description="Round false origin to nearest N meters",
        default=100,
        min=1,
        max=10000
    )
    
    def execute(self, context):
        scene = context.scene
        georef = scene.bc_georef
        cursor = scene.cursor.location
        
        # Round coordinates
        def round_to_nearest(value, nearest):
            return round(value / nearest) * nearest
        
        georef.false_origin_easting = round_to_nearest(cursor.x, self.round_to_meters)
        georef.false_origin_northing = round_to_nearest(cursor.y, self.round_to_meters)
        georef.false_origin_elevation = round_to_nearest(cursor.z, self.round_to_meters)
        
        self.report({'INFO'}, 
            f"False origin set to ({georef.false_origin_easting:.1f}, "
            f"{georef.false_origin_northing:.1f}, {georef.false_origin_elevation:.1f})")
        
        return {'FINISHED'}


class BC_OT_validate_georeferencing(Operator):
    """Validate georeferencing setup.

    Performs validation checks on the georeferencing configuration to ensure
    all required elements are present and properly configured. Reports any
    issues found.

    Validation checks:
        - CRS has been selected
        - False origin is configured
        - IFC file path is set
        - Georeferencing has been applied to IFC

    Usage:
        Called to verify georeferencing setup before proceeding with
        coordinate-dependent operations.

    Returns:
        {'FINISHED'} always (reports validation results via messages)
    """
    bl_idname = "bc.validate_georeferencing"
    bl_label = "Validate Georeferencing"
    bl_description = "Check if georeferencing is correctly configured"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        scene = context.scene
        georef = scene.bc_georef
        
        if not HAS_BACKEND:
            self.report({'ERROR'}, "Backend modules not available")
            return {'CANCELLED'}
        
        issues = []
        
        # Check CRS selection
        if georef.selected_epsg_code == 0:
            issues.append("No CRS selected")
        
        # Check false origin
        if (georef.false_origin_easting == 0.0 and 
            georef.false_origin_northing == 0.0):
            issues.append("False origin not configured")
        
        # Check IFC file
        if not georef.ifc_file_path:
            issues.append("No IFC file path specified")
        elif not georef.is_georeferenced:
            issues.append("Georeferencing not applied to IFC file")
        
        # Report results
        if issues:
            message = "Validation issues: " + ", ".join(issues)
            self.report({'WARNING'}, message)
            georef.georef_status_message = "Validation failed"
        else:
            self.report({'INFO'}, "Georeferencing validation passed")
            georef.georef_status_message = "Validated successfully"
        
        return {'FINISHED'}


class BC_OT_load_georeferencing(Operator):
    """Load georeferencing from IFC file.

    Loads existing georeferencing data from an IFC file that already contains
    IfcMapConversion and IfcProjectedCRS entities. Populates the scene's
    georeferencing properties with the loaded values.

    Properties:
        filepath: Optional path to IFC file (uses scene.bc_georef.ifc_file_path if not set)

    Requirements:
        - IFC file must exist and contain georeferencing data
        - Backend georeferencing modules must be available

    Usage:
        Called when user wants to load georeferencing from an existing IFC file.
        Opens file browser if no filepath is set.

    Returns:
        {'FINISHED'} on success, {'CANCELLED'} if no georeferencing found or error
    """
    bl_idname = "bc.load_georeferencing"
    bl_label = "Load from IFC"
    bl_description = "Load existing georeferencing from IFC file"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(
        name="IFC File",
        description="Path to IFC file",
        subtype='FILE_PATH'
    )
    
    def execute(self, context):
        scene = context.scene
        georef = scene.bc_georef
        
        if not HAS_BACKEND:
            self.report({'ERROR'}, "Backend modules not available")
            return {'CANCELLED'}
        
        filepath = self.filepath or georef.ifc_file_path
        
        if not filepath:
            self.report({'ERROR'}, "No IFC file specified")
            return {'CANCELLED'}
        
        try:
            # Load georeferencing
            georef_manager = NativeIfcGeoreferencing(filepath)
            success = georef_manager.load_existing_georeferencing()
            
            if not success:
                self.report({'WARNING'}, "No georeferencing found in IFC file")
                return {'CANCELLED'}
            
            # Update properties
            georef_data = georef_manager.get_georeferencing_data()
            
            georef.selected_epsg_code = georef_data['epsg_code']
            georef.selected_crs_name = georef_data['crs_name']
            georef.false_origin_easting = georef_data['eastings']
            georef.false_origin_northing = georef_data['northings']
            georef.false_origin_elevation = georef_data['orthogonal_height']
            georef.map_scale = georef_data.get('scale', 1.0)
            georef.is_georeferenced = True
            georef.ifc_file_path = filepath
            georef.georef_status_message = f"Loaded: EPSG:{georef.selected_epsg_code}"
            
            self.report({'INFO'}, f"Loaded georeferencing from {filepath}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load: {str(e)}")
            logger.error("Failed to load georeferencing: %s", e, exc_info=True)
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# Registration
classes = (
    BC_OT_search_crs,
    BC_OT_select_crs,
    BC_OT_setup_georeferencing,
    BC_OT_preview_transform,
    BC_OT_pick_false_origin,
    BC_OT_validate_georeferencing,
    BC_OT_load_georeferencing,
)


def register():
    """Register operators."""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister operators."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
