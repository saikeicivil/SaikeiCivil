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
Cross-Section Properties
Property groups for cross-section assembly data storage in Blender scenes
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    FloatProperty,
    IntProperty,
    StringProperty,
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    PointerProperty,
)

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class BC_ComponentProperties(PropertyGroup):
    """Properties for a single cross-section component (lane, shoulder, etc.)"""
    
    # Component identification
    name: StringProperty(
        name="Name",
        description="Component name",
        default="Component",
        maxlen=64,
    )
    
    component_type: EnumProperty(
        name="Type",
        description="Component type",
        items=[
            ('LANE', "Lane", "Travel lane, parking lane, or turn lane"),
            ('SHOULDER', "Shoulder", "Paved or gravel shoulder"),
            ('CURB', "Curb", "Vertical or mountable curb"),
            ('DITCH', "Ditch", "Roadside drainage ditch"),
            ('MEDIAN', "Median", "Center median or divider"),
            ('SIDEWALK', "Sidewalk", "Pedestrian walkway"),
            ('CUSTOM', "Custom", "Custom component"),
        ],
        default='LANE',
    )
    
    # Geometric properties
    width: FloatProperty(
        name="Width",
        description="Component width (m)",
        default=3.6,
        min=0.1,
        max=20.0,
        precision=3,
        unit='LENGTH',
    )
    
    cross_slope: FloatProperty(
        name="Cross Slope",
        description="Cross slope (decimal, positive = down right)",
        default=0.02,
        min=-0.20,
        max=0.20,
        precision=4,
    )
    
    offset: FloatProperty(
        name="Offset",
        description="Offset from centerline (m)",
        default=0.0,
        precision=3,
        unit='LENGTH',
    )
    
    side: EnumProperty(
        name="Side",
        description="Side of alignment",
        items=[
            ('CENTER', "Center", "Centered on alignment"),
            ('LEFT', "Left", "Left side of alignment"),
            ('RIGHT', "Right", "Right side of alignment"),
        ],
        default='CENTER',
    )
    
    # Material layers (simplified)
    surface_material: StringProperty(
        name="Surface",
        description="Surface material",
        default="HMA",
        maxlen=64,
    )
    
    surface_thickness: FloatProperty(
        name="Surface Thickness",
        description="Surface layer thickness (m)",
        default=0.15,
        min=0.01,
        max=1.0,
        precision=3,
        unit='LENGTH',
    )
    
    # Component-specific properties
    # For lanes
    lane_type: EnumProperty(
        name="Lane Type",
        description="Type of lane",
        items=[
            ('TRAVEL', "Travel", "Standard travel lane"),
            ('PARKING', "Parking", "Parking lane"),
            ('TURN', "Turn", "Turn lane"),
            ('BIKE', "Bike", "Bicycle lane"),
        ],
        default='TRAVEL',
    )
    
    # For shoulders
    shoulder_type: EnumProperty(
        name="Shoulder Type",
        description="Type of shoulder",
        items=[
            ('PAVED', "Paved", "Paved shoulder"),
            ('GRAVEL', "Gravel", "Gravel shoulder"),
        ],
        default='PAVED',
    )
    
    # For curbs
    curb_type: EnumProperty(
        name="Curb Type",
        description="Type of curb",
        items=[
            ('VERTICAL', "Vertical", "Vertical curb (90° face)"),
            ('MOUNTABLE', "Mountable", "Mountable curb (2:1 slope)"),
            ('GUTTER', "Curb & Gutter", "Curb with integral gutter"),
        ],
        default='VERTICAL',
    )
    
    curb_height: FloatProperty(
        name="Curb Height",
        description="Curb height (m)",
        default=0.15,
        min=0.05,
        max=0.30,
        precision=3,
        unit='LENGTH',
    )
    
    # For ditches
    foreslope: FloatProperty(
        name="Foreslope",
        description="Foreslope ratio (H:V, e.g., 4:1 = 4.0)",
        default=4.0,
        min=2.0,
        max=6.0,
        precision=1,
    )
    
    backslope: FloatProperty(
        name="Backslope",
        description="Backslope ratio (H:V, e.g., 3:1 = 3.0)",
        default=3.0,
        min=2.0,
        max=4.0,
        precision=1,
    )
    
    bottom_width: FloatProperty(
        name="Bottom Width",
        description="Ditch bottom width (m)",
        default=1.2,
        min=0.5,
        max=3.0,
        precision=2,
        unit='LENGTH',
    )
    
    depth: FloatProperty(
        name="Depth",
        description="Ditch depth (m)",
        default=0.45,
        min=0.2,
        max=1.5,
        precision=2,
        unit='LENGTH',
    )
    
    # Status
    is_valid: BoolProperty(
        name="Valid",
        description="Component passes validation",
        default=True,
    )


class BC_ConstraintProperties(PropertyGroup):
    """Properties for a parametric constraint"""
    
    station: FloatProperty(
        name="Station",
        description="Station where constraint applies (m)",
        default=0.0,
        min=0.0,
        precision=3,
        unit='LENGTH',
    )
    
    component_name: StringProperty(
        name="Component",
        description="Name of component to modify",
        default="",
        maxlen=64,
    )
    
    parameter: EnumProperty(
        name="Parameter",
        description="Parameter to modify",
        items=[
            ('width', "Width", "Component width"),
            ('cross_slope', "Cross Slope", "Cross slope"),
            ('offset', "Offset", "Offset from centerline"),
        ],
        default='width',
    )
    
    value: FloatProperty(
        name="Value",
        description="Parameter value at this station",
        default=3.6,
        precision=3,
    )


class BC_AssemblyProperties(PropertyGroup):
    """Properties for a cross-section assembly"""
    
    # Assembly identification
    name: StringProperty(
        name="Name",
        description="Assembly name",
        default="Road Assembly",
        maxlen=64,
    )
    
    description: StringProperty(
        name="Description",
        description="Assembly description",
        default="",
        maxlen=256,
    )
    
    assembly_type: EnumProperty(
        name="Type",
        description="Assembly type",
        items=[
            ('CUSTOM', "Custom", "Custom assembly"),
            ('TWO_LANE_RURAL', "Two-Lane Rural", "Standard two-lane rural highway"),
            ('FOUR_LANE_DIVIDED', "Four-Lane Divided", "Four-lane divided highway"),
            ('URBAN_ARTERIAL', "Urban Arterial", "Urban arterial with curbs"),
        ],
        default='CUSTOM',
    )
    
    # Components collection
    components: CollectionProperty(
        type=BC_ComponentProperties,
        name="Components",
        description="Assembly components",
    )
    
    active_component_index: IntProperty(
        name="Active Component",
        description="Currently selected component",
        default=0,
        min=0,
    )
    
    # Constraints collection
    constraints: CollectionProperty(
        type=BC_ConstraintProperties,
        name="Constraints",
        description="Parametric constraints",
    )
    
    active_constraint_index: IntProperty(
        name="Active Constraint",
        description="Currently selected constraint",
        default=0,
        min=0,
    )
    
    # Design standards
    design_speed: FloatProperty(
        name="Design Speed",
        description="Design speed (km/h)",
        default=80.0,
        min=20.0,
        max=120.0,
        precision=0,
    )
    
    # Status
    is_valid: BoolProperty(
        name="Valid",
        description="Assembly passes validation",
        default=False,
    )
    
    validation_message: StringProperty(
        name="Validation",
        description="Validation status message",
        default="No components defined",
    )
    
    total_width: FloatProperty(
        name="Total Width",
        description="Total assembly width (m)",
        default=0.0,
        precision=3,
        unit='LENGTH',
    )
    
    # Query properties
    query_station: FloatProperty(
        name="Query Station",
        description="Station for section query (m)",
        default=0.0,
        min=0.0,
        precision=3,
        unit='LENGTH',
    )
    
    # UI state
    show_component_list: BoolProperty(
        name="Show Components",
        description="Show/hide component list",
        default=True,
    )
    
    show_constraints: BoolProperty(
        name="Show Constraints",
        description="Show/hide constraints",
        default=False,
    )
    
    show_materials: BoolProperty(
        name="Show Materials",
        description="Show/hide material properties",
        default=False,
    )
    
    show_validation: BoolProperty(
        name="Show Validation",
        description="Show/hide validation panel",
        default=False,
    )
    
    # IFC export
    ifc_file_path: StringProperty(
        name="IFC File",
        description="Path to IFC file for export",
        default="",
        subtype='FILE_PATH',
    )


class BC_CrossSectionGlobalProperties(PropertyGroup):
    """Global cross-section properties (stored on Scene)"""
    
    # Assembly list
    assemblies: CollectionProperty(
        type=BC_AssemblyProperties,
        name="Assemblies",
        description="Available assemblies",
    )
    
    active_assembly_index: IntProperty(
        name="Active Assembly",
        description="Currently selected assembly",
        default=0,
        min=0,
    )
    
    # Template library
    template_to_create: EnumProperty(
        name="Template",
        description="Template to create",
        items=[
            ('TWO_LANE_RURAL', "Two-Lane Rural", "Standard two-lane rural highway"),
            ('FOUR_LANE_DIVIDED', "Four-Lane Divided", "Four-lane divided highway"),
            ('URBAN_ARTERIAL', "Urban Arterial", "Urban arterial with curbs"),
        ],
        default='TWO_LANE_RURAL',
    )
    
    # Display settings
    show_3d_preview: BoolProperty(
        name="3D Preview",
        description="Show 3D preview of cross-section",
        default=True,
    )
    
    preview_station: FloatProperty(
        name="Preview Station",
        description="Station for 3D preview (m)",
        default=0.0,
        min=0.0,
        precision=3,
        unit='LENGTH',
    )
    
    # Component library - for adding new components
    new_component_type: EnumProperty(
        name="Component Type",
        description="Type of component to add",
        items=[
            ('LANE', "Lane", "Travel lane"),
            ('SHOULDER', "Shoulder", "Shoulder"),
            ('CURB', "Curb", "Curb"),
            ('DITCH', "Ditch", "Ditch"),
        ],
        default='LANE',
    )
    
    new_component_side: EnumProperty(
        name="Side",
        description="Side to add component",
        items=[
            ('LEFT', "Left", "Left side"),
            ('RIGHT', "Right", "Right side"),
        ],
        default='RIGHT',
    )


# Registration
classes = (
    BC_ComponentProperties,
    BC_ConstraintProperties,
    BC_AssemblyProperties,
    BC_CrossSectionGlobalProperties,
)


def register():
    """Register property classes and add to Scene"""
    for cls in classes:
        bpy.utils.register_class(cls)

    # Add cross-section properties to Scene
    bpy.types.Scene.bc_cross_section = PointerProperty(
        type=BC_CrossSectionGlobalProperties,
        name="Cross-Section",
        description="Cross-section assembly properties",
    )

    logger.debug("Cross-section properties registered")


def unregister():
    """Unregister property classes"""
    # Remove from Scene
    del bpy.types.Scene.bc_cross_section

    # Unregister classes
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    logger.debug("Cross-section properties unregistered")


if __name__ == "__main__":
    register()
