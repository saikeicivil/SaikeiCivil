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
Saikei Civil - Corridor Properties

Blender scene properties for corridor generation and management.
"""

import bpy
from bpy.props import (
    IntProperty,
    FloatProperty,
    EnumProperty,
    BoolProperty,
    StringProperty,
    PointerProperty,
)
from bpy.types import PropertyGroup


def get_alignment_items(self, context):
    """Get available alignments from IFC file."""
    items = []

    try:
        from ..core.ifc_manager import NativeIfcManager
        ifc_file = NativeIfcManager.file

        if ifc_file:
            alignments = ifc_file.by_type("IfcAlignment")
            for i, alignment in enumerate(alignments):
                name = alignment.Name or f"Alignment #{alignment.id()}"
                items.append((str(i), name, f"Use {name} as corridor alignment", i))
    except Exception:
        pass

    if not items:
        items.append(('-1', "No Alignments", "Create an alignment first", 0))

    return items


def get_assembly_items(self, context):
    """Get available cross-section assemblies."""
    items = []

    try:
        if hasattr(context.scene, 'bc_cross_section'):
            cs_props = context.scene.bc_cross_section
            for i, assembly in enumerate(cs_props.assemblies):
                name = assembly.name or f"Assembly {i + 1}"
                items.append((str(i), name, f"Use {name} as corridor cross-section", i))
    except Exception:
        pass

    if not items:
        items.append(('-1', "No Assemblies", "Create a cross-section assembly first", 0))

    return items


class BC_CorridorProperties(PropertyGroup):
    """Properties for corridor generation."""

    # Active selections
    active_alignment_index: IntProperty(
        name="Active Alignment",
        description="Index of the alignment to use for corridor generation",
        default=0,
        min=0
    )

    active_assembly_index: IntProperty(
        name="Active Assembly",
        description="Index of the cross-section assembly to use",
        default=0,
        min=0
    )

    # Station range
    start_station: FloatProperty(
        name="Start Station",
        description="Starting station for corridor (meters)",
        default=0.0,
        min=0.0,
        unit='LENGTH'
    )

    end_station: FloatProperty(
        name="End Station",
        description="Ending station for corridor (meters)",
        default=100.0,
        min=0.0,
        unit='LENGTH'
    )

    # Generation settings
    station_interval: FloatProperty(
        name="Station Interval",
        description="Base interval between cross-sections (meters)",
        default=10.0,
        min=1.0,
        max=50.0,
        unit='LENGTH'
    )

    curve_densification: FloatProperty(
        name="Curve Densification",
        description="Multiplier for stations in curves (1.0 = same, 2.0 = twice as dense)",
        default=1.5,
        min=1.0,
        max=3.0
    )

    lod: EnumProperty(
        name="Level of Detail",
        description="Mesh detail level for corridor generation",
        items=[
            ('high', "High", "Best quality, slower generation"),
            ('medium', "Medium", "Balanced quality and speed"),
            ('low', "Low", "Fast preview, lower quality"),
        ],
        default='medium'
    )

    # Options
    apply_materials: BoolProperty(
        name="Apply Materials",
        description="Create and apply materials based on component types",
        default=True
    )

    create_collection: BoolProperty(
        name="Create Collection",
        description="Organize corridor in a dedicated collection",
        default=True
    )

    # Status tracking
    last_generation_time: FloatProperty(
        name="Last Generation Time",
        description="Time taken for last corridor generation (seconds)",
        default=0.0
    )

    last_vertex_count: IntProperty(
        name="Last Vertex Count",
        description="Number of vertices in last generated corridor",
        default=0
    )

    last_face_count: IntProperty(
        name="Last Face Count",
        description="Number of faces in last generated corridor",
        default=0
    )


# Registration
classes = (
    BC_CorridorProperties,
)


def register():
    """Register corridor properties."""
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.bc_corridor = PointerProperty(type=BC_CorridorProperties)


def unregister():
    """Unregister corridor properties."""
    del bpy.types.Scene.bc_corridor

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
