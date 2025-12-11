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
Saikei Civil - Alignment Property Groups

Property groups for storing alignment data and tracking the active alignment
in Blender scenes. This provides the scene-level data needed for operators
to work with alignments.

Author: Saikei Civil Team
Date: November 2025
Sprint: 5 - Interactive PI Placement
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    StringProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    BoolProperty,
    EnumProperty,
    CollectionProperty,
    PointerProperty,
)


class AlignmentItem(PropertyGroup):
    """Single alignment reference for tracking in scene."""
    
    ifc_global_id: StringProperty(
        name="IFC GlobalId",
        description="IFC GlobalId of the alignment",
        default=""
    )
    
    ifc_entity_id: IntProperty(
        name="IFC Entity ID",
        description="IFC entity ID for lookup",
        default=0
    )
    
    name: StringProperty(
        name="Alignment Name",
        description="Name of the alignment",
        default="Alignment"
    )
    
    collection_name: StringProperty(
        name="Collection Name",
        description="Name of the Blender collection containing this alignment",
        default=""
    )
    
    pi_count: IntProperty(
        name="PI Count",
        description="Number of PIs in this alignment",
        default=0,
        min=0
    )
    
    segment_count: IntProperty(
        name="Segment Count",
        description="Number of segments (tangents + curves) in this alignment",
        default=0,
        min=0
    )
    
    total_length: FloatProperty(
        name="Total Length",
        description="Total length of the alignment",
        default=0.0,
        min=0.0,
        unit='LENGTH',
        precision=3
    )


class AlignmentProperties(PropertyGroup):
    """Main alignment properties for the scene."""
    
    # ===== Alignment List =====
    alignments: CollectionProperty(
        type=AlignmentItem,
        name="Alignments",
        description="List of alignments in the scene"
    )
    
    active_alignment_index: IntProperty(
        name="Active Alignment Index",
        description="Index of the currently active alignment",
        default=-1,
        min=-1
    )
    
    # ===== Active Alignment Quick Access =====
    active_alignment_id: StringProperty(
        name="Active Alignment IFC ID",
        description="IFC GlobalId of the active alignment for quick lookup",
        default=""
    )
    
    active_alignment_name: StringProperty(
        name="Active Alignment Name",
        description="Name of the active alignment",
        default="None"
    )
    
    # ===== Alignment Creation Settings =====
    default_alignment_name: StringProperty(
        name="Default Name",
        description="Default name for new alignments",
        default="Alignment"
    )
    
    auto_visualize: BoolProperty(
        name="Auto-Visualize",
        description="Automatically create 3D visualization when creating alignments",
        default=True
    )
    
    auto_regenerate_segments: BoolProperty(
        name="Auto-Regenerate",
        description="Automatically regenerate segments when PIs are modified",
        default=True
    )
    
    # ===== PI Settings =====
    pi_display_size: FloatProperty(
        name="PI Display Size",
        description="Size of PI markers in viewport",
        default=3.0,
        min=0.1,
        max=100.0
    )
    
    pi_color_tangent: FloatVectorProperty(
        name="PI Color (Tangent)",
        description="Color for PI markers at tangent points (no curve)",
        default=(0.0, 1.0, 0.0, 1.0),
        size=4,
        min=0.0,
        max=1.0,
        subtype='COLOR'
    )
    
    # ===== Curve Settings =====
    default_curve_radius: FloatProperty(
        name="Default Curve Radius",
        description="Default radius for new curves",
        default=100.0,
        min=0.1,
        unit='LENGTH'
    )
    
    curve_color: FloatVectorProperty(
        name="Curve Color",
        description="Color for curve segments",
        default=(1.0, 0.3, 0.3, 1.0),
        size=4,
        min=0.0,
        max=1.0,
        subtype='COLOR'
    )
    
    # ===== Tangent Settings =====
    tangent_color: FloatVectorProperty(
        name="Tangent Color",
        description="Color for tangent line segments",
        default=(0.2, 0.6, 1.0, 1.0),
        size=4,
        min=0.0,
        max=1.0,
        subtype='COLOR'
    )
    
    # ===== Status =====
    alignment_count: IntProperty(
        name="Alignment Count",
        description="Total number of alignments in scene",
        default=0,
        min=0
    )
    
    status_message: StringProperty(
        name="Status",
        description="Current alignment system status message",
        default="No alignments"
    )
    
    # ===== Display Options =====
    show_pi_labels: BoolProperty(
        name="Show PI Labels",
        description="Display PI numbers/labels in viewport",
        default=True
    )
    
    show_station_labels: BoolProperty(
        name="Show Station Labels",
        description="Display station values along alignment",
        default=False
    )
    
    show_curve_data: BoolProperty(
        name="Show Curve Data",
        description="Display curve radius and other data in viewport",
        default=True
    )

    # ===== Station Marker Settings =====
    show_station_markers: BoolProperty(
        name="Show Station Markers",
        description="Display station tick marks and labels along alignment",
        default=False
    )

    station_major_interval: FloatProperty(
        name="Major Station Interval",
        description="Distance between major station markers (full stations)",
        default=1000.0,
        min=1.0,
        unit='LENGTH'
    )

    station_minor_interval: FloatProperty(
        name="Minor Station Interval",
        description="Distance between minor station markers (intermediate stations)",
        default=100.0,
        min=1.0,
        unit='LENGTH'
    )

    station_tick_size: FloatProperty(
        name="Station Tick Size",
        description="Size of station tick marks",
        default=5.0,
        min=0.1,
        max=50.0
    )

    station_label_size: FloatProperty(
        name="Station Label Size",
        description="Size of station text labels",
        default=2.0,
        min=0.1,
        max=20.0
    )


# Helper functions for working with active alignment
def get_active_alignment_item(context):
    """Get the active AlignmentItem from scene properties.
    
    Returns:
        AlignmentItem or None: The active alignment item, or None if none active
    """
    props = context.scene.bc_alignment
    
    if props.active_alignment_index >= 0 and props.active_alignment_index < len(props.alignments):
        return props.alignments[props.active_alignment_index]
    
    return None


def get_active_alignment_ifc(context):
    """Get the IFC alignment entity for the active alignment.
    
    Returns:
        IFC entity or None: The IFC alignment entity, or None if not found
    """
    from . import NativeIfcManager
    
    props = context.scene.bc_alignment
    
    if not props.active_alignment_id:
        return None
    
    ifc = NativeIfcManager.get_file()
    if not ifc:
        return None
    
    # Find alignment by GlobalId
    alignments = ifc.by_type("IfcAlignment")
    for alignment in alignments:
        if alignment.GlobalId == props.active_alignment_id:
            return alignment
    
    return None


def set_active_alignment(context, alignment_ifc_entity):
    """Set the active alignment from an IFC entity.
    
    Args:
        context: Blender context
        alignment_ifc_entity: IFC alignment entity to set as active
    """
    props = context.scene.bc_alignment
    
    # Update quick access properties
    props.active_alignment_id = alignment_ifc_entity.GlobalId
    props.active_alignment_name = alignment_ifc_entity.Name or "Unnamed"
    
    # Find and set index
    for i, item in enumerate(props.alignments):
        if item.ifc_global_id == alignment_ifc_entity.GlobalId:
            props.active_alignment_index = i
            return
    
    # If not found in list, add it
    add_alignment_to_list(context, alignment_ifc_entity)


def add_alignment_to_list(context, alignment_ifc_entity):
    """Add an alignment to the scene's alignment list.
    
    Args:
        context: Blender context
        alignment_ifc_entity: IFC alignment entity to add
    """
    props = context.scene.bc_alignment
    
    # Check if already exists
    for item in props.alignments:
        if item.ifc_global_id == alignment_ifc_entity.GlobalId:
            return  # Already in list
    
    # Add new item
    item = props.alignments.add()
    item.ifc_global_id = alignment_ifc_entity.GlobalId
    item.ifc_entity_id = alignment_ifc_entity.id()
    item.name = alignment_ifc_entity.Name or "Unnamed"
    
    # Try to find collection
    for collection in bpy.data.collections:
        if "ifc_definition_id" in collection:
            if collection["ifc_definition_id"] == alignment_ifc_entity.id():
                item.collection_name = collection.name
                break
    
    # Update count
    props.alignment_count = len(props.alignments)
    
    # If this is the first alignment, make it active
    if len(props.alignments) == 1:
        set_active_alignment(context, alignment_ifc_entity)


def refresh_alignment_list(context):
    """Refresh the alignment list from IFC file.
    
    Args:
        context: Blender context
    """
    from . import NativeIfcManager
    
    props = context.scene.bc_alignment
    
    # Clear existing list
    props.alignments.clear()
    
    # Get IFC file
    ifc = NativeIfcManager.get_file()
    if not ifc:
        props.alignment_count = 0
        props.status_message = "No IFC file loaded"
        return
    
    # Get all alignments
    alignments = ifc.by_type("IfcAlignment")
    
    # Add each to list
    for alignment in alignments:
        add_alignment_to_list(context, alignment)
    
    # Update status
    count = len(props.alignments)
    props.alignment_count = count
    
    if count == 0:
        props.status_message = "No alignments found"
    else:
        props.status_message = f"{count} alignment(s) loaded"


# Registration
classes = (
    AlignmentItem,
    AlignmentProperties,
)


def register():
    """Register property groups."""
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Add alignment properties to Scene
    bpy.types.Scene.bc_alignment = PointerProperty(
        type=AlignmentProperties,
        name="Saikei Civil Alignment",
        description="Alignment properties for this scene"
    )


def unregister():
    """Unregister property groups."""
    # Remove from Scene
    del bpy.types.Scene.bc_alignment
    
    # Unregister classes in reverse order
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
