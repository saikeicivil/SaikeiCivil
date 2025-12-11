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
Vertical Alignment Properties
Property groups for vertical alignment data storage in Blender scenes
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
)

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class PVIProperties(PropertyGroup):
    """Properties for a single PVI (Point of Vertical Intersection)"""
    
    # Core data
    station: FloatProperty(
        name="Station",
        description="Location along alignment (m)",
        default=0.0,
        min=0.0,
        precision=3,
        unit='LENGTH',
    )
    
    elevation: FloatProperty(
        name="Elevation",
        description="Height at this location (m)",
        default=0.0,
        precision=3,
        unit='LENGTH',
    )
    
    # Curve properties
    curve_length: FloatProperty(
        name="Curve Length",
        description="Vertical curve length (m), 0 = no curve",
        default=0.0,
        min=0.0,
        precision=2,
        unit='LENGTH',
    )
    
    # Calculated properties (read-only in UI)
    grade_in: FloatProperty(
        name="Grade In",
        description="Incoming grade (decimal)",
        default=0.0,
        precision=4,
    )
    
    grade_out: FloatProperty(
        name="Grade Out",
        description="Outgoing grade (decimal)",
        default=0.0,
        precision=4,
    )
    
    grade_change: FloatProperty(
        name="Grade Change",
        description="Algebraic difference in grades (A-value)",
        default=0.0,
        precision=4,
    )
    
    k_value: FloatProperty(
        name="K-Value",
        description="Curve parameter (m/%)",
        default=0.0,
        min=0.0,
        precision=2,
    )
    
    curve_type_display: StringProperty(
        name="Curve Type",
        description="Crest or Sag curve",
        default="None",
    )
    
    # Design parameters
    design_speed: FloatProperty(
        name="Design Speed",
        description="Design speed for this curve (km/h)",
        default=80.0,
        min=20.0,
        max=120.0,
        precision=0,
    )
    
    # Validation status
    is_valid: BoolProperty(
        name="Valid",
        description="PVI passes validation checks",
        default=True,
    )
    
    validation_message: StringProperty(
        name="Validation",
        description="Validation status message",
        default="OK",
    )


class VerticalSegmentProperties(PropertyGroup):
    """Properties for a vertical segment (tangent or curve)"""
    
    segment_type: StringProperty(
        name="Type",
        description="Segment type (TANGENT or CURVE)",
        default="TANGENT",
    )
    
    start_station: FloatProperty(
        name="Start Station",
        description="Segment start station (m)",
        default=0.0,
        precision=3,
    )
    
    end_station: FloatProperty(
        name="End Station",
        description="Segment end station (m)",
        default=0.0,
        precision=3,
    )
    
    length: FloatProperty(
        name="Length",
        description="Segment length (m)",
        default=0.0,
        precision=3,
    )
    
    start_elevation: FloatProperty(
        name="Start Elevation",
        description="Elevation at start (m)",
        default=0.0,
        precision=3,
    )
    
    end_elevation: FloatProperty(
        name="End Elevation",
        description="Elevation at end (m)",
        default=0.0,
        precision=3,
    )
    
    grade: FloatProperty(
        name="Grade",
        description="Segment grade (decimal)",
        default=0.0,
        precision=4,
    )


class VerticalAlignmentProperties(PropertyGroup):
    """Main vertical alignment properties"""
    
    # Alignment info
    name: StringProperty(
        name="Name",
        description="Vertical alignment name",
        default="Vertical Alignment",
        maxlen=64,
    )
    
    description: StringProperty(
        name="Description",
        description="Alignment description",
        default="",
        maxlen=256,
    )
    
    # PVI collection
    pvis: CollectionProperty(
        type=PVIProperties,
        name="PVIs",
        description="Point of Vertical Intersections",
    )
    
    active_pvi_index: IntProperty(
        name="Active PVI",
        description="Currently selected PVI",
        default=0,
        min=0,
    )
    
    # Segments collection (generated)
    segments: CollectionProperty(
        type=VerticalSegmentProperties,
        name="Segments",
        description="Generated vertical segments",
    )
    
    active_segment_index: IntProperty(
        name="Active Segment",
        description="Currently selected segment",
        default=0,
        min=0,
    )
    
    # Design standards
    design_speed: FloatProperty(
        name="Design Speed",
        description="Default design speed for curves (km/h)",
        default=80.0,
        min=20.0,
        max=120.0,
        precision=0,
    )
    
    min_k_crest: FloatProperty(
        name="Min K (Crest)",
        description="Minimum K-value for crest curves (m/%)",
        default=29.0,
        min=0.0,
        precision=1,
    )
    
    min_k_sag: FloatProperty(
        name="Min K (Sag)",
        description="Minimum K-value for sag curves (m/%)",
        default=17.0,
        min=0.0,
        precision=1,
    )
    
    # Status and validation
    is_valid: BoolProperty(
        name="Valid",
        description="Alignment passes all validation checks",
        default=False,
    )
    
    validation_message: StringProperty(
        name="Validation Status",
        description="Overall validation status",
        default="No PVIs defined",
    )
    
    total_length: FloatProperty(
        name="Total Length",
        description="Total alignment length (m)",
        default=0.0,
        precision=3,
    )
    
    elevation_min: FloatProperty(
        name="Min Elevation",
        description="Minimum elevation (m)",
        default=0.0,
        precision=3,
    )
    
    elevation_max: FloatProperty(
        name="Max Elevation",
        description="Maximum elevation (m)",
        default=0.0,
        precision=3,
    )
    
    # Query properties
    query_station: FloatProperty(
        name="Query Station",
        description="Station for elevation/grade query (m)",
        default=0.0,
        min=0.0,
        precision=3,
    )
    
    query_elevation: FloatProperty(
        name="Elevation",
        description="Elevation at query station (m)",
        default=0.0,
        precision=3,
    )
    
    query_grade: FloatProperty(
        name="Grade",
        description="Grade at query station (decimal)",
        default=0.0,
        precision=4,
    )
    
    query_grade_percent: FloatProperty(
        name="Grade %",
        description="Grade at query station (%)",
        default=0.0,
        precision=2,
    )
    
    # UI state
    show_pvi_list: BoolProperty(
        name="Show PVI List",
        description="Show/hide PVI list",
        default=True,
    )
    
    show_grade_info: BoolProperty(
        name="Show Grade Info",
        description="Show/hide grade information",
        default=True,
    )
    
    show_curve_design: BoolProperty(
        name="Show Curve Design",
        description="Show/hide curve design tools",
        default=False,
    )
    
    show_validation: BoolProperty(
        name="Show Validation",
        description="Show/hide validation panel",
        default=False,
    )
    
    show_query: BoolProperty(
        name="Show Query",
        description="Show/hide station query panel",
        default=False,
    )
    
    # IFC export
    ifc_file_path: StringProperty(
        name="IFC File",
        description="Path to IFC file for export",
        default="",
        subtype='FILE_PATH',
    )
    
    # Linked horizontal alignment
    linked_horizontal_alignment: StringProperty(
        name="Horizontal Alignment",
        description="Name of linked horizontal alignment",
        default="",
    )


# Registration
classes = (
    PVIProperties,
    VerticalSegmentProperties,
    VerticalAlignmentProperties,
)


def register():
    """Register property classes and add to Scene"""
    for cls in classes:
        bpy.utils.register_class(cls)

    # Add vertical alignment properties to Scene
    bpy.types.Scene.bc_vertical = bpy.props.PointerProperty(
        type=VerticalAlignmentProperties,
        name="Vertical Alignment",
        description="Vertical alignment properties",
    )

    logger.debug("Vertical alignment properties registered")


def unregister():
    """Unregister property classes"""
    # Remove from Scene
    del bpy.types.Scene.bc_vertical

    # Unregister classes
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    logger.debug("Vertical alignment properties unregistered")


if __name__ == "__main__":
    register()
