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
Saikei Civil - Georeferencing Property Groups

Property groups for storing georeferencing data in Blender scenes.
This module defines the data structures that hold CRS information,
false origin settings, and georeferencing status.

Author: Saikei Civil Team
Date: November 2025
Sprint: 2 Day 3 - UI Integration
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    StringProperty,
    IntProperty,
    FloatProperty,
    BoolProperty,
    FloatVectorProperty,
    EnumProperty,
    CollectionProperty,
)


class CRSSearchResult(PropertyGroup):
    """Single CRS search result for display in UI list."""
    
    epsg_code: IntProperty(
        name="EPSG Code",
        description="EPSG code number",
        default=0
    )
    
    name: StringProperty(
        name="CRS Name",
        description="Human-readable CRS name",
        default=""
    )
    
    area: StringProperty(
        name="Area of Use",
        description="Geographic area where this CRS is applicable",
        default=""
    )
    
    kind: StringProperty(
        name="CRS Type",
        description="Type of coordinate reference system",
        default=""
    )
    
    unit: StringProperty(
        name="Unit",
        description="Unit of measurement (metre, foot, etc.)",
        default=""
    )


class GeoreferencingProperties(PropertyGroup):
    """Main georeferencing properties for the scene."""
    
    # ===== CRS Search =====
    crs_search_query: StringProperty(
        name="Search",
        description="Search for coordinate reference systems by name or EPSG code",
        default=""
    )
    
    search_results: CollectionProperty(
        type=CRSSearchResult,
        name="Search Results",
        description="List of CRS search results"
    )
    
    search_results_index: IntProperty(
        name="Selected Result",
        description="Currently selected search result",
        default=0
    )
    
    # ===== Selected CRS =====
    selected_epsg_code: IntProperty(
        name="EPSG Code",
        description="Selected EPSG code for georeferencing",
        default=0,
        min=0
    )
    
    selected_crs_name: StringProperty(
        name="CRS Name",
        description="Name of the selected CRS",
        default="Not Set"
    )
    
    selected_crs_area: StringProperty(
        name="Area of Use",
        description="Geographic area of the selected CRS",
        default=""
    )
    
    selected_crs_unit: StringProperty(
        name="Unit",
        description="Unit of measurement for the selected CRS",
        default=""
    )
    
    # ===== False Origin =====
    false_origin_easting: FloatProperty(
        name="Easting (X)",
        description="Easting coordinate of the false origin in map coordinates",
        default=0.0,
        precision=3,
        unit='LENGTH'
    )
    
    false_origin_northing: FloatProperty(
        name="Northing (Y)",
        description="Northing coordinate of the false origin in map coordinates",
        default=0.0,
        precision=3,
        unit='LENGTH'
    )
    
    false_origin_elevation: FloatProperty(
        name="Elevation (Z)",
        description="Elevation of the false origin in map coordinates",
        default=0.0,
        precision=3,
        unit='LENGTH'
    )
    
    # ===== Rotation =====
    grid_rotation: FloatProperty(
        name="Grid Rotation",
        description="Rotation of the local grid relative to map north (degrees)",
        default=0.0,
        min=-180.0,
        max=180.0,
        precision=4,
        unit='ROTATION'
    )
    
    # ===== Scale =====
    map_scale: FloatProperty(
        name="Scale Factor",
        description="Scale factor for coordinate transformation (typically 1.0)",
        default=1.0,
        min=0.0001,
        max=10.0,
        precision=6
    )
    
    # ===== Status =====
    is_georeferenced: BoolProperty(
        name="Georeferenced",
        description="Whether the project is currently georeferenced",
        default=False
    )
    
    georef_status_message: StringProperty(
        name="Status",
        description="Current georeferencing status message",
        default="Not configured"
    )
    
    # ===== Preview =====
    show_coordinate_preview: BoolProperty(
        name="Show Coordinate Preview",
        description="Display coordinate transformation preview in viewport",
        default=False
    )
    
    preview_local_x: FloatProperty(
        name="Local X",
        description="Local X coordinate for preview",
        default=0.0,
        precision=3
    )
    
    preview_local_y: FloatProperty(
        name="Local Y",
        description="Local Y coordinate for preview",
        default=0.0,
        precision=3
    )
    
    preview_local_z: FloatProperty(
        name="Local Z",
        description="Local Z coordinate for preview",
        default=0.0,
        precision=3
    )
    
    preview_map_easting: FloatProperty(
        name="Map Easting",
        description="Computed map easting for preview point",
        default=0.0,
        precision=3
    )
    
    preview_map_northing: FloatProperty(
        name="Map Northing",
        description="Computed map northing for preview point",
        default=0.0,
        precision=3
    )
    
    preview_map_elevation: FloatProperty(
        name="Map Elevation",
        description="Computed map elevation for preview point",
        default=0.0,
        precision=3
    )
    
    # ===== Advanced =====
    show_advanced_settings: BoolProperty(
        name="Show Advanced",
        description="Show advanced georeferencing settings",
        default=False
    )
    
    ifc_file_path: StringProperty(
        name="IFC File",
        description="Path to the IFC file for this project",
        default="",
        subtype='FILE_PATH'
    )
    
    auto_update_transforms: BoolProperty(
        name="Auto-Update Transforms",
        description="Automatically update coordinate transformations when false origin changes",
        default=True
    )


# Registration
classes = (
    CRSSearchResult,
    GeoreferencingProperties,
)


def register():
    """Register property groups."""
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Add georeferencing properties to Scene
    bpy.types.Scene.bc_georef = bpy.props.PointerProperty(
        type=GeoreferencingProperties,
        name="Saikei Civil Georeferencing",
        description="Georeferencing properties for this scene"
    )


def unregister():
    """Unregister property groups."""
    # Remove from Scene
    del bpy.types.Scene.bc_georef
    
    # Unregister classes in reverse order
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
