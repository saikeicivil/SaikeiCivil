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
Cross-Section Panel
UI panels for cross-section assembly design in Blender
"""

import bpy
from bpy.types import Panel, UIList
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class BC_UL_AssemblyList(UIList):
    """UI List for displaying assemblies"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        assembly = item
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(assembly, "name", text="", emboss=False, icon='PRESET')
            
            # Status icon
            if assembly.is_valid:
                row.label(text="", icon='CHECKMARK')
            else:
                row.label(text="", icon='ERROR')
            
            # Component count
            row.label(text=f"{len(assembly.components)}")
        
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='PRESET')


class BC_UL_ComponentList(UIList):
    """UI List for displaying components"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        component = item
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            
            # Icon based on type
            icon_map = {
                'LANE': 'MATSPHERE',
                'SHOULDER': 'MESH_PLANE',
                'CURB': 'MESH_CUBE',
                'DITCH': 'MESH_UVSPHERE',
                'MEDIAN': 'MESH_PLANE',
                'SIDEWALK': 'MESH_PLANE',
                'CUSTOM': 'QUESTION',
            }
            icon = icon_map.get(component.component_type, 'QUESTION')
            
            row.label(text="", icon=icon)
            row.prop(component, "name", text="", emboss=False)
            row.label(text=f"{component.width:.2f}m")
            
            # Side indicator
            if component.side == 'LEFT':
                row.label(text="L")
            elif component.side == 'RIGHT':
                row.label(text="R")
        
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MATSPHERE')


class BC_UL_ConstraintList(UIList):
    """UI List for displaying constraints"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        constraint = item
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.label(text=f"{constraint.station:.1f}m")
            row.label(text=constraint.component_name)
            row.label(text=constraint.parameter)
            row.label(text=f"{constraint.value:.2f}")
        
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='DRIVER')


class BC_PT_CrossSection_Main(Panel):
    """Main cross-section panel"""
    bl_label = "Cross-Section Design"
    bl_idname = "BC_PT_cross_section_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei Civil"
    bl_order = 8
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        cs = context.scene.bc_cross_section
        
        # Assembly list header
        box = layout.box()
        box.label(text="Assemblies", icon='PRESET')
        
        # Assembly list
        row = box.row()
        row.template_list(
            "BC_UL_AssemblyList", "",
            cs, "assemblies",
            cs, "active_assembly_index",
            rows=3
        )
        
        # Assembly operations
        col = row.column(align=True)
        col.operator("bc.create_assembly", text="", icon='ADD')
        col.operator("bc.delete_assembly", text="", icon='REMOVE')
        
        # Template creation
        if len(cs.assemblies) == 0:
            box = layout.box()
            box.label(text="Quick Start", icon='LIGHTPROBE_VOLUME')
            col = box.column(align=True)
            col.label(text="Create from template:")
            
            row = col.row(align=True)
            op = row.operator("bc.create_assembly", text="Two-Lane Rural")
            op.assembly_type = 'TWO_LANE_RURAL'
            op.name = "Two-Lane Rural Highway"
            
            row = col.row(align=True)
            op = row.operator("bc.create_assembly", text="Four-Lane Divided")
            op.assembly_type = 'FOUR_LANE_DIVIDED'
            op.name = "Four-Lane Divided Highway"


class BC_PT_CrossSection_Assembly(Panel):
    """Assembly properties panel"""
    bl_label = "Assembly"
    bl_idname = "BC_PT_cross_section_assembly"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei Civil"
    bl_parent_id = "BC_PT_cross_section_main"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        return len(cs.assemblies) > 0
    
    def draw(self, context):
        layout = self.layout
        cs = context.scene.bc_cross_section
        
        if cs.active_assembly_index >= len(cs.assemblies):
            layout.label(text="No active assembly", icon='ERROR')
            return
        
        assembly = cs.assemblies[cs.active_assembly_index]
        
        # Assembly properties
        box = layout.box()
        box.label(text="Properties", icon='PROPERTIES')
        
        col = box.column(align=True)
        col.prop(assembly, "name")
        col.prop(assembly, "description")
        col.prop(assembly, "assembly_type")
        col.prop(assembly, "design_speed")
        
        # Validation status
        box = layout.box()
        row = box.row()
        if assembly.is_valid:
            row.label(text="Status: Valid", icon='CHECKMARK')
        else:
            row.label(text="Status: Invalid", icon='ERROR')
        
        if assembly.validation_message:
            col = box.column()
            col.label(text=assembly.validation_message)
        
        row = box.row()
        row.operator("bc.validate_assembly", text="Validate", icon='CHECKMARK')

        # IFC Save section
        box = layout.box()
        box.label(text="IFC Storage", icon='FILE_3D')
        col = box.column(align=True)

        # Show IFC linkage status
        if assembly.ifc_definition_id > 0:
            col.label(text=f"IFC ID: {assembly.ifc_definition_id}", icon='CHECKMARK')
        else:
            col.label(text="Not saved to IFC", icon='INFO')

        # Save to IFC button
        row = col.row()
        row.scale_y = 1.2
        row.operator("bc.save_assembly_to_ifc", text="Save to IFC", icon='EXPORT')

        # Statistics
        box = layout.box()
        box.label(text="Statistics", icon='INFO')
        col = box.column(align=True)
        col.label(text=f"Components: {len(assembly.components)}")
        col.label(text=f"Constraints: {len(assembly.constraints)}")
        col.label(text=f"Total Width: {assembly.total_width:.2f}m")


class BC_PT_CrossSection_Components(Panel):
    """Components panel"""
    bl_label = "Components"
    bl_idname = "BC_PT_cross_section_components"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei Civil"
    bl_parent_id = "BC_PT_cross_section_main"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        return len(cs.assemblies) > 0
    
    def draw(self, context):
        layout = self.layout
        cs = context.scene.bc_cross_section
        
        if cs.active_assembly_index >= len(cs.assemblies):
            return
        
        assembly = cs.assemblies[cs.active_assembly_index]
        
        # Component list
        row = layout.row()
        row.template_list(
            "BC_UL_ComponentList", "",
            assembly, "components",
            assembly, "active_component_index",
            rows=4
        )
        
        # Component operations
        col = row.column(align=True)
        col.operator("bc.add_component", text="", icon='ADD')
        col.operator("bc.remove_component", text="", icon='REMOVE')
        col.separator()
        col.operator("bc.move_component_up", text="", icon='TRIA_UP')
        col.operator("bc.move_component_down", text="", icon='TRIA_DOWN')
        
        # Active component properties
        if len(assembly.components) > 0 and assembly.active_component_index < len(assembly.components):
            comp = assembly.components[assembly.active_component_index]
            
            box = layout.box()
            box.label(text=f"Properties: {comp.name}", icon='PROPERTIES')
            
            col = box.column(align=True)
            col.prop(comp, "component_type")
            col.prop(comp, "side")
            col.separator()
            col.prop(comp, "width")
            col.prop(comp, "cross_slope")
            col.prop(comp, "offset")
            col.prop(comp, "surface_thickness")

            # Type-specific properties
            if comp.component_type == 'LANE':
                col.separator()
                col.prop(comp, "lane_type")
            elif comp.component_type == 'SHOULDER':
                col.separator()
                col.prop(comp, "shoulder_type")
            elif comp.component_type == 'CURB':
                col.separator()
                col.prop(comp, "curb_type")
                col.prop(comp, "curb_height")
            elif comp.component_type == 'DITCH':
                col.separator()
                col.prop(comp, "foreslope")
                col.prop(comp, "backslope")
                col.prop(comp, "bottom_width")
                col.prop(comp, "depth")


class BC_PT_CrossSection_Materials(Panel):
    """Materials panel"""
    bl_label = "Materials"
    bl_idname = "BC_PT_cross_section_materials"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei Civil"
    bl_parent_id = "BC_PT_cross_section_main"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return len(assembly.components) > 0
    
    def draw(self, context):
        layout = self.layout
        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]
        
        if len(assembly.components) > 0 and assembly.active_component_index < len(assembly.components):
            comp = assembly.components[assembly.active_component_index]
            
            box = layout.box()
            box.label(text=f"Materials: {comp.name}", icon='MATERIAL')
            
            col = box.column(align=True)
            col.prop(comp, "surface_material")
            col.prop(comp, "surface_thickness")
            
            # TODO: Add support for multiple material layers


class BC_PT_CrossSection_Constraints(Panel):
    """Parametric constraints panel"""
    bl_label = "Parametric Constraints"
    bl_idname = "BC_PT_cross_section_constraints"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei Civil"
    bl_parent_id = "BC_PT_cross_section_main"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return len(assembly.components) > 0
    
    def draw(self, context):
        layout = self.layout
        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]
        
        # Info box
        box = layout.box()
        box.label(text="Parametric Variation", icon='DRIVER')
        col = box.column()
        col.label(text="Constraints allow components to vary")
        col.label(text="along the alignment (widening, etc.)")
        
        # Constraint list
        row = layout.row()
        row.template_list(
            "BC_UL_ConstraintList", "",
            assembly, "constraints",
            assembly, "active_constraint_index",
            rows=3
        )
        
        # Constraint operations
        col = row.column(align=True)
        col.operator("bc.add_constraint", text="", icon='ADD')
        col.operator("bc.remove_constraint", text="", icon='REMOVE')
        
        # Examples
        if len(assembly.constraints) == 0:
            box = layout.box()
            box.label(text="Examples:", icon='INFO')
            col = box.column(align=True)
            col.label(text="• Lane widening")
            col.label(text="• Superelevation transition")
            col.label(text="• Shoulder width changes")


class BC_PT_CrossSection_Query(Panel):
    """Section query panel"""
    bl_label = "Section Query"
    bl_idname = "BC_PT_cross_section_query"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei Civil"
    bl_parent_id = "BC_PT_cross_section_main"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return len(assembly.components) > 0
    
    def draw(self, context):
        layout = self.layout
        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]
        
        # Query input
        box = layout.box()
        box.label(text="Calculate Section", icon='VIEWZOOM')
        
        col = box.column(align=True)
        col.prop(assembly, "query_station")
        col.operator("bc.calculate_section", text="Calculate", icon='PLAY')
        
        # Results
        if assembly.total_width > 0:
            box = layout.box()
            box.label(text="Results", icon='INFO')
            col = box.column(align=True)
            col.label(text=f"Total Width: {assembly.total_width:.2f}m")


class BC_PT_CrossSection_Preview(Panel):
    """Cross-Section Viewer panel (OpenRoads-style overlay)"""
    bl_label = "Cross-Section Viewer"
    bl_idname = "BC_PT_cross_section_preview"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei Civil"
    bl_parent_id = "BC_PT_cross_section_main"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return len(assembly.components) > 0

    def draw(self, context):
        layout = self.layout

        # Get overlay status
        try:
            from ...core.cross_section_view_overlay import get_cross_section_overlay
            overlay = get_cross_section_overlay()
            is_enabled = overlay.enabled
        except ImportError:
            is_enabled = False

        # Overlay Viewer controls (OpenRoads-style)
        box = layout.box()
        box.label(text="Overlay Viewer", icon='OVERLAY')

        col = box.column(align=True)

        # Toggle button with status indication
        if is_enabled:
            col.operator("bc.toggle_cross_section_view",
                        text="Disable Viewer", icon='HIDE_ON')
            col.operator("bc.load_assembly_to_view",
                        text="Refresh Data", icon='FILE_REFRESH')
            col.operator("bc.fit_cross_section_view",
                        text="Fit to Data", icon='FULLSCREEN_ENTER')

            # Position controls
            box2 = layout.box()
            box2.label(text="Position", icon='ORIENTATION_GLOBAL')
            row = box2.row(align=True)
            row.scale_x = 0.9

            # Position buttons
            op = row.operator("bc.set_cross_section_view_position",
                             text="", icon='TRIA_DOWN')
            op.position = 'BOTTOM'

            op = row.operator("bc.set_cross_section_view_position",
                             text="", icon='TRIA_UP')
            op.position = 'TOP'

            op = row.operator("bc.set_cross_section_view_position",
                             text="", icon='TRIA_LEFT')
            op.position = 'LEFT'

            op = row.operator("bc.set_cross_section_view_position",
                             text="", icon='TRIA_RIGHT')
            op.position = 'RIGHT'

            op = row.operator("bc.set_cross_section_view_position",
                             text="Float", icon='WINDOW')
            op.position = 'FLOATING'

            # Current position display
            from ...core.cross_section_view_overlay import OverlayPosition
            pos_names = {
                OverlayPosition.BOTTOM: "Bottom",
                OverlayPosition.TOP: "Top",
                OverlayPosition.LEFT: "Left",
                OverlayPosition.RIGHT: "Right",
                OverlayPosition.FLOATING: "Floating",
            }
            current_pos = pos_names.get(overlay.position, "Unknown")
            box2.label(text=f"Current: {current_pos}")

            # Status info
            box3 = layout.box()
            box3.label(text="Viewer Status", icon='INFO')
            col3 = box3.column(align=True)
            col3.scale_y = 0.8
            col3.label(text=f"Components: {len(overlay.data.components)}")
            if overlay.data.assembly_name:
                col3.label(text=f"Assembly: {overlay.data.assembly_name}")

            # Interaction hints
            if overlay.position == OverlayPosition.FLOATING:
                col3.label(text="Drag title bar to move")
                col3.label(text="Drag edges to resize")
            else:
                col3.label(text="Drag edge to resize")
        else:
            col.operator("bc.toggle_cross_section_view",
                        text="Enable Viewer", icon='HIDE_OFF')

            # Help text
            box2 = layout.box()
            box2.label(text="Viewer Info", icon='INFO')
            col2 = box2.column(align=True)
            col2.scale_y = 0.8
            col2.label(text="OpenRoads-style cross-section")
            col2.label(text="viewer as viewport overlay.")
            col2.label(text="Shows components, grid, labels.")

        # Legacy 3D Preview (collapsible section)
        box = layout.box()
        box.label(text="3D Mesh Preview (Legacy)", icon='MESH_DATA')

        col = box.column(align=True)
        col.scale_y = 0.9
        col.operator("bc.generate_cross_section_preview",
                    text="Generate 3D Preview", icon='PLAY')
        col.operator("bc.clear_cross_section_preview",
                    text="Clear 3D Preview", icon='X')


class BC_PT_CrossSection_Export(Panel):
    """IFC export panel"""
    bl_label = "IFC Export"
    bl_idname = "BC_PT_cross_section_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei Civil"
    bl_parent_id = "BC_PT_cross_section_main"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return assembly.is_valid and len(assembly.components) > 0
    
    def draw(self, context):
        layout = self.layout
        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]
        
        # Export options
        box = layout.box()
        box.label(text="Export to IFC 4.3", icon='EXPORT')
        
        col = box.column(align=True)
        col.prop(assembly, "ifc_file_path", text="")
        
        row = col.row(align=True)
        row.operator("bc.export_assembly_ifc", text="Export IFC", icon='EXPORT')
        
        # Info
        box = layout.box()
        box.label(text="IFC Entities", icon='INFO')
        col = box.column(align=True)
        col.label(text="• IfcOpenCrossProfileDef")
        col.label(text="• IfcCompositeProfileDef")
        col.label(text="• IfcMaterialProfileSet")
        
        # Template save
        box = layout.box()
        box.label(text="Template", icon='FILE')
        box.operator("bc.save_assembly_template", text="Save as Template", icon='FILE_TICK')


# Registration
classes = (
    BC_UL_AssemblyList,
    BC_UL_ComponentList,
    BC_UL_ConstraintList,
    BC_PT_CrossSection_Main,
    BC_PT_CrossSection_Assembly,
    BC_PT_CrossSection_Components,
    BC_PT_CrossSection_Materials,
    BC_PT_CrossSection_Constraints,
    BC_PT_CrossSection_Query,
    BC_PT_CrossSection_Preview,
    BC_PT_CrossSection_Export,
)


def register():
    """Register panel classes"""
    for cls in classes:
        bpy.utils.register_class(cls)

    logger.info("Cross-section panels registered")


def unregister():
    """Unregister panel classes"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    logger.info("Cross-section panels unregistered")


if __name__ == "__main__":
    register()
