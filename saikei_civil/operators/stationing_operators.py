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
Stationing Operators
====================

Operators for managing IFC stationing referents (IfcReferent with Pset_Stationing).

This module provides Blender operators for working with alignment stationing,
including setting starting stations, managing station equations (chainage breaks),
and calculating station values. All operations conform to IFC 4.3 standards
for civil infrastructure.

Operators:
    BC_OT_set_starting_station: Set the starting station of the active alignment
    BC_OT_add_station_equation: Add a station equation (chainage break) to the alignment
    BC_OT_remove_station_equation: Remove a station equation from the alignment
    BC_OT_calculate_station: Calculate station value at a given distance along the alignment
    BC_OT_update_station_markers: Update station markers along the alignment
"""

import bpy
from bpy.props import FloatProperty, StringProperty
from ..core import alignment_registry
from ..core.station_formatting import parse_station, format_station, format_station_short
from ..ui.alignment_properties import get_active_alignment_ifc


class BC_OT_set_starting_station(bpy.types.Operator):
    """
    Set the starting station of the active alignment.

    Defines the initial station value at the beginning of the alignment
    (distance_along = 0). This is fundamental for all station calculations
    along the alignment.

    Properties:
        station_input: String input for station value, accepts formats like:
            - "10+000" (formatted with plus sign)
            - "10000" (plain numeric)
            - "5+50.25" (with decimal precision)

    The operator presents a dialog showing both the formatted input and
    the parsed metric value. The starting station is stored as an IFC
    referent with Pset_Stationing properties.

    Usage context: Called when establishing the initial station reference
    for a new alignment or updating an existing one.
    """
    bl_idname = "bc.set_starting_station"
    bl_label = "Set Starting Station"
    bl_options = {'REGISTER', 'UNDO'}

    station_input: StringProperty(
        name="Starting Station",
        description="Station value at start (e.g., '10+000', '0+000', or '10000')",
        default="10+000"
    )

    _parsed_value: FloatProperty(default=10000.0)

    def execute(self, context):
        # Parse station input
        try:
            station_value = parse_station(self.station_input)
            self._parsed_value = station_value
        except ValueError as e:
            self.report({'ERROR'}, f"Invalid station format: {e}")
            return {'CANCELLED'}

        # Get active alignment
        active_alignment_ifc = get_active_alignment_ifc(context)
        if not active_alignment_ifc:
            self.report({'ERROR'}, "No active alignment")
            return {'CANCELLED'}

        # Get alignment object from registry
        alignment_obj = alignment_registry.get_alignment(active_alignment_ifc.GlobalId)
        if not alignment_obj:
            self.report({'ERROR'}, "Alignment not found in registry")
            return {'CANCELLED'}

        # Set starting station
        alignment_obj.set_starting_station(station_value)

        # Format output message
        formatted_station = format_station_short(station_value)
        self.report({'INFO'}, f"Set starting station to {formatted_station}")
        return {'FINISHED'}

    def invoke(self, context, event):
        # Get current starting station if it exists
        active_alignment_ifc = get_active_alignment_ifc(context)
        if active_alignment_ifc:
            alignment_obj = alignment_registry.get_alignment(active_alignment_ifc.GlobalId)
            if alignment_obj and alignment_obj.referents:
                # Find starting station (distance_along = 0)
                for ref in alignment_obj.referents:
                    if ref['distance_along'] == 0.0:
                        # Display in formatted notation
                        self.station_input = format_station_short(ref['station'])
                        self._parsed_value = ref['station']
                        break

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "station_input")

        # Show parsed value if valid
        try:
            parsed = parse_station(self.station_input)
            layout.separator()
            layout.label(text=f"= {parsed:.2f} meters", icon='INFO')
        except ValueError:
            pass  # Invalid input, don't show parsed value


class BC_OT_add_station_equation(bpy.types.Operator):
    """
    Add a station equation (chainage break) to the alignment.

    Creates a station equation where the stationing changes abruptly,
    typically used when:
    - Joining alignments from different projects with different stationing
    - Adjusting stationing to match existing roadway conventions
    - Creating logical breaks in station numbering

    Properties:
        distance_along: Physical distance along alignment where equation occurs (m)
        incoming_station_input: Station value approaching the equation point
        outgoing_station_input: Station value leaving the equation point
        description: Optional descriptive text for the equation

    Example: At distance 500m along alignment, station changes from
    "10+500" (incoming) to "15+000" (outgoing), creating a +4500m jump.

    The operator automatically calculates the incoming station based on
    current stationing and suggests reasonable defaults for the outgoing
    station.

    Usage context: Called when managing complex stationing scenarios or
    matching existing project conventions.
    """
    bl_idname = "bc.add_station_equation"
    bl_label = "Add Station Equation"
    bl_options = {'REGISTER', 'UNDO'}

    distance_along: FloatProperty(
        name="Distance Along",
        description="Distance along alignment where equation occurs (meters)",
        default=500.0,
        min=0.0,
        unit='LENGTH'
    )

    incoming_station_input: StringProperty(
        name="Incoming Station",
        description="Station value approaching (e.g., '10+500', '5+00')",
        default="10+500"
    )

    outgoing_station_input: StringProperty(
        name="Outgoing Station",
        description="Station value leaving (e.g., '15+000', '10+00')",
        default="15+000"
    )

    description: StringProperty(
        name="Description",
        description="Optional description of the station equation",
        default="Station Equation"
    )

    def execute(self, context):
        # Parse station inputs
        try:
            incoming_value = parse_station(self.incoming_station_input)
            outgoing_value = parse_station(self.outgoing_station_input)
        except ValueError as e:
            self.report({'ERROR'}, f"Invalid station format: {e}")
            return {'CANCELLED'}

        # Get active alignment
        active_alignment_ifc = get_active_alignment_ifc(context)
        if not active_alignment_ifc:
            self.report({'ERROR'}, "No active alignment")
            return {'CANCELLED'}

        # Get alignment object from registry
        alignment_obj = alignment_registry.get_alignment(active_alignment_ifc.GlobalId)
        if not alignment_obj:
            self.report({'ERROR'}, "Alignment not found in registry")
            return {'CANCELLED'}

        # Add station equation
        alignment_obj.add_station_equation(
            self.distance_along,
            incoming_value,
            outgoing_value,
            self.description
        )

        # Format output message
        incoming_fmt = format_station_short(incoming_value)
        outgoing_fmt = format_station_short(outgoing_value)
        self.report({'INFO'},
                   f"Added equation at {self.distance_along:.2f}m: {incoming_fmt} → {outgoing_fmt}")
        return {'FINISHED'}

    def invoke(self, context, event):
        # Auto-calculate incoming station based on current stationing
        active_alignment_ifc = get_active_alignment_ifc(context)
        if active_alignment_ifc:
            alignment_obj = alignment_registry.get_alignment(active_alignment_ifc.GlobalId)
            if alignment_obj:
                # Calculate what the incoming station would be at this distance
                incoming_calc = alignment_obj.get_station_at_distance(self.distance_along)
                self.incoming_station_input = format_station_short(incoming_calc)

                # Set outgoing to a reasonable default (e.g., +5000m ahead)
                self.outgoing_station_input = format_station_short(incoming_calc + 5000.0)

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "distance_along")
        layout.separator()
        layout.label(text="Station Equation:")

        # Incoming station
        row = layout.row()
        row.prop(self, "incoming_station_input", text="Back")
        try:
            parsed = parse_station(self.incoming_station_input)
            row.label(text=f"({parsed:.2f}m)")
        except:
            pass

        layout.label(text="→", icon='FORWARD')

        # Outgoing station
        row = layout.row()
        row.prop(self, "outgoing_station_input", text="Ahead")
        try:
            parsed = parse_station(self.outgoing_station_input)
            row.label(text=f"({parsed:.2f}m)")
        except:
            pass

        layout.separator()
        layout.prop(self, "description")


class BC_OT_remove_station_equation(bpy.types.Operator):
    """
    Remove a station equation from the alignment.

    Deletes a previously created station equation, returning the
    stationing to continuous calculation from the starting station.

    Properties:
        distance_along: Distance where the equation to be removed exists (m)

    The operator searches for a station equation at the specified
    distance and removes it if found. If no equation exists at that
    location, a warning is reported.

    Usage context: Called when correcting stationing or simplifying
    alignment station management.
    """
    bl_idname = "bc.remove_station_equation"
    bl_label = "Remove Station Equation"
    bl_options = {'REGISTER', 'UNDO'}

    distance_along: FloatProperty(
        name="Distance Along",
        description="Distance where the equation exists",
        default=0.0,
        unit='LENGTH'
    )

    def execute(self, context):
        # Get active alignment
        active_alignment_ifc = get_active_alignment_ifc(context)
        if not active_alignment_ifc:
            self.report({'ERROR'}, "No active alignment")
            return {'CANCELLED'}

        # Get alignment object from registry
        alignment_obj = alignment_registry.get_alignment(active_alignment_ifc.GlobalId)
        if not alignment_obj:
            self.report({'ERROR'}, "Alignment not found in registry")
            return {'CANCELLED'}

        # Remove station equation
        if alignment_obj.remove_station_equation(self.distance_along):
            self.report({'INFO'}, f"Removed station equation at {self.distance_along:.2f}m")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, f"No station equation found at {self.distance_along:.2f}m")
            return {'CANCELLED'}


class BC_OT_calculate_station(bpy.types.Operator):
    """
    Calculate station value at a given distance along the alignment.

    Computes the station value at any point along the alignment,
    accounting for starting station and all station equations.
    This is a query operation that does not modify the alignment.

    Properties:
        distance_along: Physical distance along alignment (m)

    The operator displays results in both formatted notation
    (e.g., "10+234.56") and raw metric values. The dialog updates
    in real-time as the user adjusts the distance value.

    This calculation respects:
    - Starting station offset
    - All station equations (forward and backward)
    - Proper ordering of equations along alignment

    Usage context: Called when determining station values for
    design features, cross-sections, or reporting purposes.
    """
    bl_idname = "bc.calculate_station"
    bl_label = "Calculate Station"
    bl_options = {'REGISTER'}

    distance_along: FloatProperty(
        name="Distance Along",
        description="Distance along alignment (meters)",
        default=0.0,
        unit='LENGTH'
    )

    _calculated_station: FloatProperty(default=0.0)
    _calculated_station_formatted: StringProperty(default="")

    def execute(self, context):
        # Get active alignment
        active_alignment_ifc = get_active_alignment_ifc(context)
        if not active_alignment_ifc:
            self.report({'ERROR'}, "No active alignment")
            return {'CANCELLED'}

        # Get alignment object from registry
        alignment_obj = alignment_registry.get_alignment(active_alignment_ifc.GlobalId)
        if not alignment_obj:
            self.report({'ERROR'}, "Alignment not found in registry")
            return {'CANCELLED'}

        # Calculate station
        self._calculated_station = alignment_obj.get_station_at_distance(self.distance_along)
        self._calculated_station_formatted = format_station_short(self._calculated_station)

        self.report({'INFO'},
                   f"At {self.distance_along:.2f}m → Station {self._calculated_station_formatted}")
        return {'FINISHED'}

    def invoke(self, context, event):
        # Pre-calculate if alignment is available
        active_alignment_ifc = get_active_alignment_ifc(context)
        if active_alignment_ifc:
            alignment_obj = alignment_registry.get_alignment(active_alignment_ifc.GlobalId)
            if alignment_obj:
                self._calculated_station = alignment_obj.get_station_at_distance(self.distance_along)
                self._calculated_station_formatted = format_station_short(self._calculated_station)

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "distance_along")

        # Show calculated result
        if self._calculated_station_formatted:
            layout.separator()
            box = layout.box()
            col = box.column(align=True)
            col.label(text=f"Station: {self._calculated_station_formatted}", icon='TRACKING')
            col.label(text=f"= {self._calculated_station:.2f} meters")


class BC_OT_update_station_markers(bpy.types.Operator):
    """
    Update station markers along the alignment.

    Creates or updates visual station markers (tick marks and labels)
    along the alignment geometry in the 3D viewport. These markers help
    visualize station positions and are useful for design review.

    The operator reads settings from scene properties:
        - show_station_markers: Whether markers should be visible
        - station_major_interval: Spacing for major (labeled) tick marks
        - station_minor_interval: Spacing for minor (unlabeled) tick marks
        - station_tick_size: Visual size of tick marks
        - station_label_size: Text size for station labels

    If markers are disabled in settings, this operator clears all
    existing markers. Otherwise, it regenerates them with current
    settings and station values.

    Usage context: Called when:
    - Toggling station marker visibility
    - Changing marker display settings
    - After modifying stationing or alignment geometry
    """
    bl_idname = "bc.update_station_markers"
    bl_label = "Update Station Markers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Get active alignment
        active_alignment_ifc = get_active_alignment_ifc(context)
        if not active_alignment_ifc:
            self.report({'ERROR'}, "No active alignment")
            return {'CANCELLED'}

        # Get alignment object from registry
        alignment_obj = alignment_registry.get_alignment(active_alignment_ifc.GlobalId)
        if not alignment_obj:
            self.report({'ERROR'}, "Alignment not found in registry")
            return {'CANCELLED'}

        # Get settings from scene properties
        props = context.scene.bc_alignment

        # Check if markers should be shown
        if not props.show_station_markers:
            # Remove existing markers
            if hasattr(alignment_obj, 'visualizer') and alignment_obj.visualizer:
                alignment_obj.visualizer.clear_station_markers()
            self.report({'INFO'}, "Station markers hidden")
            return {'FINISHED'}

        # Update markers
        if hasattr(alignment_obj, 'visualizer') and alignment_obj.visualizer:
            alignment_obj.visualizer.update_station_markers(
                major_interval=props.station_major_interval,
                minor_interval=props.station_minor_interval,
                tick_size=props.station_tick_size,
                label_size=props.station_label_size
            )
            self.report({'INFO'}, "Updated station markers")
        else:
            self.report({'WARNING'}, "No visualizer found for alignment")
            return {'CANCELLED'}

        return {'FINISHED'}


# Registration
classes = (
    BC_OT_set_starting_station,
    BC_OT_add_station_equation,
    BC_OT_remove_station_equation,
    BC_OT_calculate_station,
    BC_OT_update_station_markers,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()