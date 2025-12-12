# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under the GNU General Public License v3
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
Alignment Operators v2 - Three-Layer Architecture
===================================================

New-style operators using the three-layer architecture:
    - Core: Pure business logic (core/alignment.py)
    - Tool: Blender-specific (tool/alignment.py)
    - Operators: UI integration (this file)

These operators demonstrate the new pattern and run alongside existing
operators during the migration period.

Usage:
    # In Blender's 3D View, these appear alongside existing operators
    # They can be called via:
    bpy.ops.saikei.create_alignment_v2()
    bpy.ops.saikei.query_alignment_v2()

The key differences from v1 operators:
    1. Inherit from tool.Ifc.Operator mixin
    2. Use tool interfaces instead of direct IFC manipulation
    3. Call core functions for business logic
    4. Cleaner separation of concerns
"""
import logging

import bpy
from bpy.props import StringProperty, FloatProperty, IntProperty, BoolProperty

from .. import tool
from ..core import alignment as core_alignment

logger = logging.getLogger(__name__)


class SAIKEI_OT_create_alignment_v2(bpy.types.Operator, tool.Ifc.Operator):
    """Create a new horizontal alignment using the three-layer architecture"""
    bl_idname = "saikei.create_alignment_v2"
    bl_label = "Create Alignment (v2)"
    bl_description = "Create a new horizontal alignment using the new architecture"
    bl_options = {"REGISTER", "UNDO"}

    name: StringProperty(
        name="Name",
        default="New Alignment",
        description="Name for the new alignment"
    )

    use_selection: BoolProperty(
        name="Use Selection",
        default=True,
        description="Use selected objects as PI locations"
    )

    def _execute(self, context):
        """Execute using the new pattern."""
        # Check for IFC file
        if not tool.Ifc.has_file():
            self.report({'ERROR'}, "No IFC file loaded. Create or open a file first.")
            return {'CANCELLED'}

        # Get PI locations
        pis = self._get_pi_data(context)

        if len(pis) < 2:
            self.report({'ERROR'}, "At least 2 points required for alignment")
            return {'CANCELLED'}

        try:
            # Create alignment using tool interface
            alignment = tool.Alignment.create(self.name, pis)

            # Select the alignment object
            obj = tool.Ifc.get_object(alignment)
            if obj:
                tool.Blender.select_object(obj)

            self.report(
                {'INFO'},
                f"Created alignment '{self.name}' with {len(pis)} PIs"
            )
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to create alignment: {str(e)}")
            return {'CANCELLED'}

    def _get_pi_data(self, context) -> list:
        """Get PI data from selection or scene properties."""
        pis = []

        if self.use_selection:
            # Use selected objects as PI locations
            selected = tool.Blender.get_selected_objects()

            # Sort by name for consistent ordering
            selected.sort(key=lambda o: o.name)

            for obj in selected:
                loc = obj.location
                pis.append({
                    'x': loc.x,
                    'y': loc.y,
                })
        else:
            # Use scene alignment properties (existing UI)
            try:
                props = context.scene.bc_alignment
                if hasattr(props, 'alignment_list'):
                    for item in props.alignment_list:
                        pis.append({
                            'x': getattr(item, 'x', 0.0),
                            'y': getattr(item, 'y', 0.0),
                        })
            except AttributeError:
                pass

        return pis

    def invoke(self, context, event):
        """Show dialog for name input."""
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        """Draw the operator dialog."""
        layout = self.layout
        layout.prop(self, "name")
        layout.prop(self, "use_selection")

        if self.use_selection:
            selected = tool.Blender.get_selected_objects()
            layout.label(text=f"Selected: {len(selected)} objects")


class SAIKEI_OT_query_alignment_v2(bpy.types.Operator, tool.Ifc.Operator):
    """Query alignment information at a station"""
    bl_idname = "saikei.query_alignment_v2"
    bl_label = "Query Alignment (v2)"
    bl_description = "Get position and direction at a station along the alignment"
    bl_options = {"REGISTER"}

    station: FloatProperty(
        name="Station",
        default=10000.0,
        description="Station value to query",
        unit='LENGTH'
    )

    def _execute(self, context):
        """Query the alignment."""
        obj = tool.Blender.get_active_object()
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}

        alignment = tool.Ifc.get_entity(obj)
        if not alignment or not alignment.is_a("IfcAlignment"):
            self.report({'ERROR'}, "Active object is not an alignment")
            return {'CANCELLED'}

        # Query using tool interface
        result = tool.Alignment.get_point_at_station(alignment, self.station)

        if result:
            import math
            deg = math.degrees(result['direction'])
            self.report(
                {'INFO'},
                f"Station {self.station:.2f}: "
                f"X={result['x']:.3f}, Y={result['y']:.3f}, "
                f"Dir={deg:.2f}°"
            )

            # Optionally place 3D cursor at position
            tool.Blender.set_cursor_location((result['x'], result['y'], 0.0))

            return {'FINISHED'}
        else:
            self.report({'WARNING'}, f"Station {self.station:.2f} is out of range")
            return {'CANCELLED'}

    def invoke(self, context, event):
        """Show dialog for station input."""
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        """Draw the operator dialog."""
        layout = self.layout
        layout.prop(self, "station")


class SAIKEI_OT_insert_curve_v2(bpy.types.Operator, tool.Ifc.Operator):
    """Insert a curve at a PI using the new architecture"""
    bl_idname = "saikei.insert_curve_v2"
    bl_label = "Insert Curve (v2)"
    bl_description = "Insert a horizontal curve at the selected PI"
    bl_options = {"REGISTER", "UNDO"}

    pi_index: IntProperty(
        name="PI Index",
        default=1,
        min=1,
        description="Index of interior PI (1 to n-2)"
    )

    radius: FloatProperty(
        name="Radius",
        default=100.0,
        min=1.0,
        description="Curve radius in meters",
        unit='LENGTH'
    )

    def _execute(self, context):
        """Insert curve at PI."""
        obj = tool.Blender.get_active_object()
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}

        alignment = tool.Ifc.get_entity(obj)
        if not alignment or not alignment.is_a("IfcAlignment"):
            self.report({'ERROR'}, "Active object is not an alignment")
            return {'CANCELLED'}

        # Get current PIs
        pis = tool.Alignment.get_pis(alignment)

        if self.pi_index <= 0 or self.pi_index >= len(pis) - 1:
            self.report(
                {'ERROR'},
                f"PI index must be between 1 and {len(pis) - 2}"
            )
            return {'CANCELLED'}

        # Insert curve using core function
        curve_data = core_alignment.insert_curve(pis, self.pi_index, self.radius)

        if not curve_data:
            self.report({'WARNING'}, "Could not create curve (PIs may be collinear)")
            return {'CANCELLED'}

        # Update alignment
        tool.Alignment.set_pis(alignment, pis)

        self.report(
            {'INFO'},
            f"Inserted R={self.radius:.1f}m curve at PI {self.pi_index}"
        )
        return {'FINISHED'}

    def invoke(self, context, event):
        """Show dialog."""
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        """Draw the operator dialog."""
        layout = self.layout
        layout.prop(self, "pi_index")
        layout.prop(self, "radius")


class SAIKEI_OT_get_alignment_info_v2(bpy.types.Operator, tool.Ifc.Operator):
    """Get comprehensive alignment information"""
    bl_idname = "saikei.get_alignment_info_v2"
    bl_label = "Alignment Info (v2)"
    bl_description = "Display detailed information about the selected alignment"
    bl_options = {"REGISTER"}

    def _execute(self, context):
        """Get alignment info."""
        obj = tool.Blender.get_active_object()
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}

        alignment = tool.Ifc.get_entity(obj)
        if not alignment or not alignment.is_a("IfcAlignment"):
            self.report({'ERROR'}, "Active object is not an alignment")
            return {'CANCELLED'}

        # Get info using core function
        info = core_alignment.get_alignment_info(tool.Alignment, alignment)

        # Report to user
        self.report({'INFO'}, f"Alignment: {info['name']}")
        self.report({'INFO'}, f"  PIs: {info['pi_count']}")
        self.report({'INFO'}, f"  Segments: {info['segment_count']}")
        self.report({'INFO'}, f"  Length: {info['total_length']:.2f}m")

        # Log detailed info using logger
        logger.info(f"Alignment: {info['name']}")
        logger.info(f"PIs: {info['pi_count']}")
        for pi in info['pis']:
            curve_info = ""
            if 'curve' in pi:
                curve_info = f" (R={pi['curve'].get('radius', 0):.1f}m)"
            logger.info(f"  PI {pi['id']}: ({pi['x']:.3f}, {pi['y']:.3f}){curve_info}")

        logger.info(f"Segments: {info['segment_count']}")
        for seg in info['segments']:
            logger.info(f"  {seg['name']}: {seg['type']} L={seg['length']:.2f}m")

        logger.info(f"Total Length: {info['total_length']:.2f}m")

        return {'FINISHED'}


# =============================================================================
# Registration
# =============================================================================

classes = [
    SAIKEI_OT_create_alignment_v2,
    SAIKEI_OT_query_alignment_v2,
    SAIKEI_OT_insert_curve_v2,
    SAIKEI_OT_get_alignment_info_v2,
]


def register():
    """Register v2 operators."""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister v2 operators."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


__all__ = [
    "SAIKEI_OT_create_alignment_v2",
    "SAIKEI_OT_query_alignment_v2",
    "SAIKEI_OT_insert_curve_v2",
    "SAIKEI_OT_get_alignment_info_v2",
    "register",
    "unregister",
]