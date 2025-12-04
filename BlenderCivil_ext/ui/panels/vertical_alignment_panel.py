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
Vertical Alignment UI Panels
Professional Blender interface for vertical alignment design

NOTE: Many sub-panels have been temporarily commented out to simplify the UI.
They can be re-enabled as needed by uncommenting the class definitions and
adding them back to the 'classes' tuple at the bottom of this file.
"""

import bpy
from bpy.types import Panel, UIList
from ...core.logging_config import get_logger

logger = get_logger(__name__)


# =============================================================================
# MAIN VERTICAL ALIGNMENT PANEL
# =============================================================================

class VIEW3D_PT_bc_vertical_alignment(Panel):
    """Main Vertical Alignment Panel"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_label = "Vertical Alignment"
    bl_idname = "VIEW3D_PT_bc_vertical_alignment"
    bl_order = 6
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        # Simplified header - sub-panels provide the functionality
        layout.label(text="Vertical alignment tools", icon='IPO_LINEAR')


# =============================================================================
# TERRAIN DATA SUB-PANEL (ACTIVE)
# =============================================================================

class VIEW3D_PT_bc_vertical_terrain(Panel):
    """Terrain Data Sub-Panel"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_label = "Terrain Data"
    bl_parent_id = "VIEW3D_PT_bc_vertical_alignment"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Check if profile view overlay exists
        from ...core.profile_view_overlay import get_profile_overlay
        overlay = get_profile_overlay()

        # Terrain sampling
        box = layout.box()
        box.label(text="Sample Terrain:", icon='IMPORT')

        col = box.column(align=True)
        col.operator("bc.sample_terrain_from_mesh", text="Sample from Mesh", icon='MESH_DATA')

        # Show terrain data status
        if overlay and len(overlay.data.terrain_points) > 0:
            col.separator()
            col.label(text=f"{len(overlay.data.terrain_points)} terrain points", icon='CHECKMARK')

            # Trace terrain as alignment button
            layout.separator()
            box = layout.box()
            box.label(text="Create Alignment from Terrain:", icon='EXPORT')
            col = box.column(align=True)
            col.operator("bc.trace_terrain_as_vertical", text="Trace as IFC Alignment", icon='CURVE_PATH')
            col.scale_y = 0.8
            col.label(text="Creates tangent-only vertical alignment", icon='INFO')
            col.label(text="tracing the sampled terrain data.")

            # Clear terrain button
            layout.separator()
            row = layout.row()
            row.operator("bc.clear_terrain_data", text="Clear Terrain", icon='X')
        else:
            col.label(text="No terrain data loaded", icon='INFO')

        # Info message
        layout.separator()
        box = layout.box()
        col = box.column(align=True)
        col.scale_y = 0.8
        col.label(text="Sample elevation from terrain mesh", icon='INFO')
        col.label(text="(OBJ/STL) along the active")
        col.label(text="horizontal alignment.")


# =============================================================================
# COMMENTED OUT PANELS - Re-enable as needed
# =============================================================================

# NOTE: The following panels have been temporarily disabled to simplify the UI.
# To re-enable a panel:
# 1. Uncomment the class definition
# 2. Add the class name to the 'classes' tuple at the bottom of this file

"""
class BC_UL_pvi_list(UIList):
    '''UIList for displaying PVIs'''

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # Custom drawing for each PVI
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            # Station
            row.label(text=f"{item.station:.1f}m", icon='EMPTY_SINGLE_ARROW')

            # Elevation
            row.label(text=f"Elev: {item.elevation:.2f}m")

            # Curve indicator
            if item.curve_length > 0:
                row.label(text=f"L={item.curve_length:.0f}m", icon='IPO_EASE_IN_OUT')
                if item.curve_type_display != "None":
                    row.label(text=item.curve_type_display, icon='DRIVER')

            # Validation status
            if not item.is_valid:
                row.label(text="", icon='ERROR')

        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=f"{item.station:.0f}m")


class VIEW3D_PT_bc_vertical_pvi_list(Panel):
    '''PVI List Sub-Panel'''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_label = "PVI List"
    bl_parent_id = "VIEW3D_PT_bc_vertical_alignment"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        vertical = context.scene.bc_vertical
        layout.prop(vertical, "show_pvi_list", text="")

    def draw(self, context):
        layout = self.layout
        vertical = context.scene.bc_vertical

        layout.enabled = vertical.show_pvi_list

        # PVI List
        row = layout.row()
        row.template_list(
            "BC_UL_pvi_list", "",
            vertical, "pvis",
            vertical, "active_pvi_index",
            rows=5
        )

        # Add/Remove buttons
        col = row.column(align=True)
        col.operator("bc.add_pvi", text="", icon='ADD')
        col.operator("bc.remove_pvi", text="", icon='REMOVE')
        col.separator()
        col.operator("bc.edit_pvi", text="", icon='GREASEPENCIL')

        # PVI Details (if one selected)
        if len(vertical.pvis) > 0 and vertical.active_pvi_index < len(vertical.pvis):
            pvi = vertical.pvis[vertical.active_pvi_index]

            box = layout.box()
            box.label(text=f"PVI #{vertical.active_pvi_index + 1} Details:", icon='INFO')

            col = box.column(align=True)
            col.label(text=f"Station: {pvi.station:.3f}m")
            col.label(text=f"Elevation: {pvi.elevation:.3f}m")

            if pvi.curve_length > 0:
                col.separator()
                col.label(text=f"Curve Length: {pvi.curve_length:.1f}m")
                col.label(text=f"Curve Type: {pvi.curve_type_display}")
                col.label(text=f"K-Value: {pvi.k_value:.1f} m/%")

            # Grades
            if pvi.grade_in != 0 or pvi.grade_out != 0:
                col.separator()
                row = col.row(align=True)
                row.label(text=f"In: {pvi.grade_in*100:+.2f}%")
                row.label(text=f"Out: {pvi.grade_out*100:+.2f}%")

                if pvi.grade_change > 0:
                    col.label(text=f"Change: {pvi.grade_change*100:.2f}%")

        # Quick Actions
        layout.separator()
        row = layout.row(align=True)
        row.operator("bc.calculate_grades", icon='FILE_REFRESH')
        row.operator("bc.generate_segments", icon='MOD_ARRAY')

        layout.operator("bc.clear_vertical", icon='X')


class VIEW3D_PT_bc_vertical_grade_info(Panel):
    '''Grade Information Sub-Panel'''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_label = "Grade Analysis"
    bl_parent_id = "VIEW3D_PT_bc_vertical_alignment"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        vertical = context.scene.bc_vertical
        layout.prop(vertical, "show_grade_info", text="")

    def draw(self, context):
        layout = self.layout
        vertical = context.scene.bc_vertical

        layout.enabled = vertical.show_grade_info

        if len(vertical.pvis) < 2:
            layout.label(text="Add at least 2 PVIs", icon='INFO')
            return

        # Grade table
        box = layout.box()
        box.label(text="Grades Between PVIs:", icon='DRIVER')

        col = box.column(align=True)
        for i, pvi in enumerate(vertical.pvis):
            if i == 0:
                # First PVI - only outgoing grade
                if pvi.grade_out != 0:
                    col.label(text=f"PVI {i+1} → PVI {i+2}: {pvi.grade_out*100:+.2f}%")
            elif i == len(vertical.pvis) - 1:
                # Last PVI - only incoming grade
                if pvi.grade_in != 0:
                    col.label(text=f"PVI {i} → PVI {i+1}: {pvi.grade_in*100:+.2f}%")
            else:
                # Middle PVIs - show grade change
                col.separator()
                col.label(text=f"PVI {i+1}:")
                row = col.row(align=True)
                row.label(text=f"  In: {pvi.grade_in*100:+.2f}%")
                row.label(text=f"Out: {pvi.grade_out*100:+.2f}%")
                if pvi.grade_change > 0:
                    col.label(text=f"  ΔGrade: {pvi.grade_change*100:.2f}%")

        # Statistics
        layout.separator()
        box = layout.box()
        box.label(text="Grade Statistics:", icon='SORTSIZE')

        grades = []
        for pvi in vertical.pvis:
            if pvi.grade_in != 0:
                grades.append(pvi.grade_in * 100)
            if pvi.grade_out != 0:
                grades.append(pvi.grade_out * 100)

        if grades:
            col = box.column(align=True)
            col.label(text=f"Max Grade: {max(grades):+.2f}%")
            col.label(text=f"Min Grade: {min(grades):+.2f}%")
            col.label(text=f"Avg Grade: {sum(grades)/len(grades):+.2f}%")


class VIEW3D_PT_bc_vertical_curve_design(Panel):
    '''Curve Design Sub-Panel'''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_label = "Curve Design"
    bl_parent_id = "VIEW3D_PT_bc_vertical_alignment"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        vertical = context.scene.bc_vertical
        layout.prop(vertical, "show_curve_design", text="")

    def draw(self, context):
        layout = self.layout
        vertical = context.scene.bc_vertical

        layout.enabled = vertical.show_curve_design

        # Design standards
        box = layout.box()
        box.label(text="Design Standards:", icon='SETTINGS')

        col = box.column(align=True)
        col.prop(vertical, "design_speed")
        col.prop(vertical, "min_k_crest")
        col.prop(vertical, "min_k_sag")

        # Quick K-value presets
        layout.separator()
        box = layout.box()
        box.label(text="K-Value Presets (AASHTO):", icon='PRESET')

        col = box.column(align=True)

        # Crest curves
        col.label(text="Crest Curves:")
        row = col.row(align=True)
        row.scale_y = 0.8
        row.label(text="40km/h: K=11")
        row.label(text="60km/h: K=19")
        row = col.row(align=True)
        row.scale_y = 0.8
        row.label(text="80km/h: K=29")
        row.label(text="100km/h: K=43")

        col.separator()

        # Sag curves
        col.label(text="Sag Curves:")
        row = col.row(align=True)
        row.scale_y = 0.8
        row.label(text="40km/h: K=9")
        row.label(text="60km/h: K=13")
        row = col.row(align=True)
        row.scale_y = 0.8
        row.label(text="80km/h: K=17")
        row.label(text="100km/h: K=23")

        # Design tool
        layout.separator()
        box = layout.box()
        box.label(text="Curve Design Tool:", icon='TOOL_SETTINGS')

        if len(vertical.pvis) > 0 and vertical.active_pvi_index < len(vertical.pvis):
            pvi = vertical.pvis[vertical.active_pvi_index]

            col = box.column(align=True)
            col.label(text=f"Selected PVI: #{vertical.active_pvi_index + 1}")

            if pvi.grade_in != 0 and pvi.grade_out != 0:
                col.label(text=f"Grade Change: {pvi.grade_change*100:.2f}%")
                col.label(text=f"Curve Type: {pvi.curve_type_display}")

                col.separator()
                col.operator("bc.design_vertical_curve", icon='MOD_CURVE')
            else:
                col.label(text="Need adjacent PVIs", icon='INFO')
        else:
            box.label(text="Select a PVI from list", icon='INFO')


class VIEW3D_PT_bc_vertical_query(Panel):
    '''Station Query Sub-Panel'''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_label = "Station Query"
    bl_parent_id = "VIEW3D_PT_bc_vertical_alignment"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        vertical = context.scene.bc_vertical
        layout.prop(vertical, "show_query", text="")

    def draw(self, context):
        layout = self.layout
        vertical = context.scene.bc_vertical

        layout.enabled = vertical.show_query

        if len(vertical.pvis) < 2:
            layout.label(text="Need at least 2 PVIs", icon='INFO')
            return

        # Query input
        box = layout.box()
        box.label(text="Query Position:", icon='VIEWZOOM')

        col = box.column(align=True)
        col.prop(vertical, "query_station")
        col.operator("bc.query_station", icon='PLAY')

        # Results
        if vertical.query_elevation != 0 or vertical.query_grade != 0:
            layout.separator()
            box = layout.box()
            box.label(text="Results:", icon='INFO')

            col = box.column(align=True)
            col.label(text=f"Station: {vertical.query_station:.3f}m")
            col.separator()
            col.label(text=f"Elevation: {vertical.query_elevation:.3f}m")
            col.label(text=f"Grade: {vertical.query_grade_percent:+.2f}%")
            col.label(text=f"Decimal: {vertical.query_grade:+.4f}")


class VIEW3D_PT_bc_vertical_validation(Panel):
    '''Validation Sub-Panel'''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_label = "Validation"
    bl_parent_id = "VIEW3D_PT_bc_vertical_alignment"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        vertical = context.scene.bc_vertical
        layout.prop(vertical, "show_validation", text="")

    def draw(self, context):
        layout = self.layout
        vertical = context.scene.bc_vertical

        layout.enabled = vertical.show_validation

        # Validation button
        layout.operator("bc.validate_vertical", icon='CHECKMARK')

        # Status
        box = layout.box()
        if vertical.is_valid:
            box.label(text="All Checks Passed", icon='CHECKMARK')
        else:
            box.label(text="Issues Found", icon='ERROR')

        # Detailed message
        if vertical.validation_message:
            col = box.column(align=True)
            col.scale_y = 0.8

            # Split message by semicolon for multi-line display
            messages = vertical.validation_message.split(';')
            for msg in messages:
                col.label(text=msg.strip())

        # Validation criteria
        layout.separator()
        box = layout.box()
        box.label(text="Validation Checks:", icon='PROPERTIES')

        col = box.column(align=True)
        col.scale_y = 0.8
        col.label(text="• Minimum 2 PVIs")
        col.label(text="• Stations in order")
        col.label(text="• K-values ≥ minimums")
        col.label(text="• No duplicate stations")


class VIEW3D_PT_bc_vertical_segments(Panel):
    '''Segments Sub-Panel'''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_label = "Segments"
    bl_parent_id = "VIEW3D_PT_bc_vertical_alignment"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        vertical = context.scene.bc_vertical

        if len(vertical.segments) == 0:
            layout.label(text="No segments generated", icon='INFO')
            layout.operator("bc.generate_segments", icon='MOD_ARRAY')
            return

        # Segments list
        box = layout.box()
        box.label(text=f"Generated Segments: {len(vertical.segments)}", icon='MOD_ARRAY')

        for i, seg in enumerate(vertical.segments):
            col = box.column(align=True)

            # Segment header
            row = col.row()
            if seg.segment_type == "TANGENT":
                row.label(text=f"Seg {i+1}: Tangent", icon='CURVE_PATH')
            else:
                row.label(text=f"Seg {i+1}: Curve", icon='IPO_EASE_IN_OUT')

            # Details
            row = col.row(align=True)
            row.scale_y = 0.7
            row.label(text=f"{seg.start_station:.1f} → {seg.end_station:.1f}m")
            row.label(text=f"L={seg.length:.1f}m")

            row = col.row(align=True)
            row.scale_y = 0.7
            row.label(text=f"Grade: {seg.grade*100:+.2f}%")

            if i < len(vertical.segments) - 1:
                col.separator()


class VIEW3D_PT_bc_vertical_ifc_alignments(Panel):
    '''IFC Vertical Alignments Sub-Panel'''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_label = "IFC Vertical Alignments"
    bl_parent_id = "VIEW3D_PT_bc_vertical_alignment"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Get profile view overlay
        from ...core.profile_view_overlay import get_profile_overlay
        overlay = get_profile_overlay()

        if not overlay:
            layout.label(text="Profile view not available", icon='INFO')
            return

        vertical_alignments = overlay.data.vertical_alignments
        selected_index = overlay.data.selected_vertical_index

        if not vertical_alignments:
            box = layout.box()
            box.label(text="No vertical alignments loaded", icon='INFO')
            box.separator()
            col = box.column(align=True)
            col.scale_y = 0.8
            col.label(text="Create a vertical alignment from")
            col.label(text="terrain data, or reload an IFC")
            col.label(text="file with vertical alignments.")
            return

        # Show list of vertical alignments
        box = layout.box()
        box.label(text=f"Loaded Alignments: {len(vertical_alignments)}", icon='CURVE_DATA')

        for i, valign in enumerate(vertical_alignments):
            is_selected = (i == selected_index)

            # Alignment item
            row = box.row(align=True)

            # Selection indicator
            if is_selected:
                row.alert = False  # Green highlight
                icon = 'RADIOBUT_ON'
            else:
                icon = 'RADIOBUT_OFF'

            # Create a button to select this alignment
            op = row.operator("bc.select_vertical_alignment", text="", icon=icon)
            op.alignment_index = i

            # Alignment info
            col = row.column()
            col.scale_y = 0.9
            info_row = col.row(align=True)
            info_row.label(text=f"{valign.name}", icon='IPO_LINEAR')

            # PVI count
            sub_row = col.row(align=True)
            sub_row.scale_y = 0.7
            sub_row.label(text=f"  {len(valign.pvis)} PVIs")

            # Highlight selected alignment
            if is_selected:
                box.separator(factor=0.3)

        # Info about displaying in profile view
        layout.separator()
        info_box = layout.box()
        info_col = info_box.column(align=True)
        info_col.scale_y = 0.8
        info_col.label(text="Selected alignment displays", icon='INFO')
        info_col.label(text="in green in the profile viewer.")
"""


# =============================================================================
# REGISTRATION - Only active panels are registered
# =============================================================================

classes = (
    VIEW3D_PT_bc_vertical_alignment,
    VIEW3D_PT_bc_vertical_terrain,
    # Profile View panel is in profile_view_panel.py
)


def register():
    """Register UI panels"""
    for cls in classes:
        bpy.utils.register_class(cls)

    logger.info("Vertical alignment UI panels registered (simplified)")


def unregister():
    """Unregister UI panels"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    logger.info("Vertical alignment UI panels unregistered")


if __name__ == "__main__":
    register()