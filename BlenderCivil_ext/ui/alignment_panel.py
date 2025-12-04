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
Alignment Panel - REVISED
Separate PI and Curve tools following professional civil engineering practice
"""

import bpy
from bpy.props import StringProperty, FloatProperty, IntProperty, BoolProperty

# Import from parent ui module
from . import NativeIfcManager


class VIEW3D_PT_native_ifc_alignment(bpy.types.Panel):
    """Native IFC Alignment Tools"""
    bl_label = "Horizontal Alignment"
    bl_idname = "VIEW3D_PT_native_ifc_alignment"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei Civil"
    bl_order = 4
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        # IFC File Status
        box = layout.box()
        box.label(text="IFC File", icon='FILE')
        
        ifc = NativeIfcManager.file
        if ifc:
            col = box.column(align=True)
            col.label(text=f"Schema: {ifc.schema}")
            
            # Count entities
            alignments = ifc.by_type("IfcAlignment")
            col.label(text=f"Alignments: {len(alignments)}")
        else:
            box.label(text="No IFC file loaded")
            box.operator("bc.new_ifc_file", text="Create New IFC")
        
        # Alignment Tools
        box = layout.box()
        box.label(text="Alignment", icon='CURVE_DATA')
        
        col = box.column(align=True)
        col.operator("bc.create_native_alignment", text="New Alignment", icon='ADD')
        
        # Active Alignment Info
        props = context.scene.bc_alignment
        if props.active_alignment_id:
            col.separator()
            
            # Active alignment indicator
            row = col.row()
            row.label(text=f"Active: {props.active_alignment_name}", icon='RADIOBUT_ON')
            
            # Refresh button
            row.operator("bc.refresh_alignment_list", text="", icon='FILE_REFRESH')
            
            # Show alignment stats if available
            active_item = None
            if props.active_alignment_index >= 0 and props.active_alignment_index < len(props.alignments):
                active_item = props.alignments[props.active_alignment_index]
            
            if active_item:
                sub = col.column(align=True)
                sub.scale_y = 0.8
                sub.label(text=f"  PIs: {active_item.pi_count}")
                sub.label(text=f"  Segments: {active_item.segment_count}")
                if active_item.total_length > 0:
                    sub.label(text=f"  Length: {active_item.total_length:.2f}m")
        else:
            col.separator()
            col.label(text="No active alignment", icon='ERROR')
        
        # Active object info (if selected)
        if context.active_object and "ifc_definition_id" in context.active_object:
            col.separator()
            col.label(text="Selected: " + context.active_object.name, icon='OBJECT_DATA')
            
            entity = NativeIfcManager.get_entity(context.active_object)
            if entity:
                col.label(text=f"Type: {entity.is_a()}")
                col.label(text=f"GlobalId: {entity.GlobalId[:8]}...")
        
        # ==================== PI TOOLS ====================
        box = layout.box()
        box.label(text="PI Tools (Tangent Points)", icon='EMPTY_DATA')
        
        col = box.column(align=True)
        
        # PRIMARY: Interactive PI placement
        row = col.row(align=True)
        row.scale_y = 1.3
        op = row.operator("bc.add_pi_interactive", text="Click to Place PIs", icon='HAND')
        
        col.separator()
        
        # Secondary PI tools
        col.label(text="Edit PIs:", icon='PREFERENCES')
        row = col.row(align=True)
        row.operator("bc.add_native_pi", text="Add at Cursor", icon='CURSOR')
        row.operator("bc.delete_native_pi", text="Delete", icon='X')
        
        col.separator()
        col.operator("bc.update_pi_from_location", text="Update from Location", icon='FILE_REFRESH')
        
        # Display PI info if selected
        if context.active_object and "ifc_pi_id" in context.active_object:
            pi_box = box.box()
            obj = context.active_object
            
            col = pi_box.column(align=True)
            col.label(text=f"Selected: {obj.name}", icon='DECORATE_KEYFRAME')
            
            if "ifc_point_id" in obj:
                ifc = NativeIfcManager.get_file()
                if ifc:
                    point = ifc.by_id(obj["ifc_point_id"])
                    coords = point.Coordinates
                    col.label(text=f"Location: ({coords[0]:.2f}, {coords[1]:.2f})")
                    col.label(text=f"PI Index: {obj['ifc_pi_id']}")
        
        # ==================== CURVE TOOLS ====================
        box = layout.box()
        box.label(text="Curve Tools", icon='SPHERECURVE')
        
        col = box.column(align=True)
        
        # PRIMARY: Interactive curve insertion
        row = col.row(align=True)
        row.scale_y = 1.3
        op = row.operator("bc.add_curve_interactive", text="Add Curve", icon='HAND')
        
        col.separator()
        
        # Secondary curve tools
        col.label(text="Edit Curves:", icon='PREFERENCES')
        row = col.row(align=True)
        row.operator("bc.edit_curve_radius", text="Edit Radius", icon='DRIVER_DISTANCE')
        row.operator("bc.delete_curve", text="Delete", icon='X')
        
        # Display curve info if selected
        if context.active_object and context.active_object.type == 'CURVE':
            if "Curve" in context.active_object.name:
                curve_box = box.box()
                obj = context.active_object

                col = curve_box.column(align=True)
                col.label(text=f"Selected: {obj.name}", icon='CURVE_DATA')

                # Show curve parameters if available from IFC
                if "ifc_definition_id" in obj:
                    ifc = NativeIfcManager.get_file()
                    if ifc:
                        entity = ifc.by_id(obj["ifc_definition_id"])
                        if entity:
                            params = entity.DesignParameters
                            if params:
                                col.label(text=f"Radius: {abs(params.StartRadiusOfCurvature):.2f}m")
                                col.label(text=f"Length: {params.SegmentLength:.2f}m")

                                # Determine turn direction
                                if params.StartRadiusOfCurvature > 0:
                                    col.label(text="Turn: LEFT (CCW)", icon='LOOP_BACK')
                                else:
                                    col.label(text="Turn: RIGHT (CW)", icon='LOOP_FORWARDS')

        # ==================== STATIONING TOOLS ====================
        box = layout.box()
        box.label(text="Stationing", icon='DRIVER_DISTANCE')

        col = box.column(align=True)

        # Show current starting station if available
        if props.active_alignment_id:
            # Try to get alignment object from registry to show stationing
            from ..core import alignment_registry
            from ..core.station_formatting import format_station_short
            from .alignment_properties import get_active_alignment_ifc

            active_alignment_ifc = get_active_alignment_ifc(context)
            if active_alignment_ifc:
                alignment_obj = alignment_registry.get_alignment(active_alignment_ifc.GlobalId)

                if alignment_obj and alignment_obj.referents:
                    # Find starting station
                    for ref in alignment_obj.referents:
                        if ref['distance_along'] == 0.0:
                            info_box = col.box()
                            # Format station properly
                            formatted_station = format_station_short(ref['station'])
                            info_box.label(text=f"Start: {formatted_station}", icon='TRACKING')
                            break

                    # Show station equations if any
                    equations = [r for r in alignment_obj.referents if r['incoming_station'] is not None]
                    if equations:
                        info_box.label(text=f"Equations: {len(equations)}", icon='PREFERENCES')

        col.separator()

        # Stationing tools
        col.label(text="Setup:", icon='PREFERENCES')
        col.operator("bc.set_starting_station", text="Set Starting Station", icon='TRACKING')

        col.separator()
        col.label(text="Station Equations:", icon='PREFERENCES')
        row = col.row(align=True)
        row.operator("bc.add_station_equation", text="Add Equation", icon='ADD')
        row.operator("bc.remove_station_equation", text="Remove", icon='X')

        col.separator()
        col.label(text="Utilities:", icon='PROPERTIES')
        col.operator("bc.calculate_station", text="Calculate Station", icon='PIVOT_CURSOR')

        # ==================== STATION MARKERS (Visual) ====================
        col.separator()
        col.label(text="Display:", icon='HIDE_OFF')

        # Show/hide toggle
        col.prop(props, "show_station_markers", text="Show Station Markers")

        # Settings (only show when markers are enabled)
        if props.show_station_markers:
            sub = col.column(align=True)
            sub.scale_y = 0.9
            sub.prop(props, "station_major_interval", text="Major Interval")
            sub.prop(props, "station_minor_interval", text="Minor Interval")

            sub.separator()
            sub.prop(props, "station_tick_size", text="Tick Size")
            sub.prop(props, "station_label_size", text="Label Size")

            sub.separator()
            # Button to refresh markers
            sub.operator("bc.update_station_markers", text="Update Markers", icon='FILE_REFRESH')


# Registration
classes = (
    VIEW3D_PT_native_ifc_alignment,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
