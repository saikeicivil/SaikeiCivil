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
BlenderCivil - Corridor UI Panel
Sprint 5 Day 3 - User Interface

Panel for corridor generation and management in Blender's 3D View sidebar.
Provides intuitive controls for creating 3D corridor models.

Author: BlenderCivil Team
Date: November 5, 2025
Sprint: 5 of 16 - Corridor Modeling
Day: 3 of 5 - UI Integration

Panels:
- BLENDERCIVIL_PT_corridor_generation: Main corridor controls
- BLENDERCIVIL_PT_corridor_settings: Advanced settings
- BLENDERCIVIL_PT_corridor_info: Statistics and information
"""

import bpy
from bpy.types import Panel


class BLENDERCIVIL_PT_corridor_generation(Panel):
    """
    Main corridor generation panel.

    Provides primary controls for creating 3D corridors from
    alignments and cross-sections.
    """
    bl_label = "Corridor Generation"
    bl_idname = "BLENDERCIVIL_PT_corridor_generation"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_order = 9
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        """Draw the panel."""
        layout = self.layout
        props = context.scene.bc_alignment
        
        # Header with icon
        box = layout.box()
        row = box.row()
        row.label(text="3D Corridor Modeling", icon='OUTLINER_OB_CURVE')
        
        # Prerequisites check
        has_alignment = hasattr(props, 'active_alignment') and props.active_alignment
        has_assembly = hasattr(props, 'active_assembly') and props.active_assembly
        
        if not has_alignment or not has_assembly:
            box = layout.box()
            box.label(text="Prerequisites Required:", icon='ERROR')
            
            if not has_alignment:
                box.label(text="[-] Create Alignment (H+V)", icon='BLANK1')
            else:
                box.label(text="[+] Alignment Ready", icon='BLANK1')
            
            if not has_assembly:
                box.label(text="[-] Design Cross-Section", icon='BLANK1')
            else:
                box.label(text="[+] Cross-Section Ready", icon='BLANK1')
            
            return
        
        # Status - all ready
        box = layout.box()
        box.label(text="[+] Ready to Generate", icon='CHECKMARK')
        col = box.column(align=True)
        
        if hasattr(props, 'alignment_name'):
            col.label(text=f"Alignment: {props.alignment_name}", icon='CURVE_PATH')
        if hasattr(props, 'assembly_name'):
            col.label(text=f"Assembly: {props.assembly_name}", icon='MESH_DATA')
        
        layout.separator()
        
        # Quick actions
        box = layout.box()
        box.label(text="Quick Actions", icon='PLAY')
        col = box.column(align=True)
        
        # Quick preview
        row = col.row(align=True)
        row.scale_y = 1.3
        row.operator(
            "blendercivil.corridor_quick_preview",
            text="⚡ Quick Preview",
            icon='HIDE_OFF'
        )
        
        # Main generation
        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator(
            "blendercivil.generate_corridor",
            text="🏗️ Generate Corridor",
            icon='MOD_BUILD'
        )
        
        layout.separator()
        
        # Management
        box = layout.box()
        box.label(text="Management", icon='TOOL_SETTINGS')
        col = box.column(align=True)
        
        # Export
        col.operator(
            "blendercivil.export_corridor_ifc",
            text="Export to IFC",
            icon='EXPORT'
        )
        
        # Clear
        col.operator(
            "blendercivil.clear_corridor",
            text="Clear Corridor",
            icon='TRASH'
        )


class BLENDERCIVIL_PT_corridor_settings(Panel):
    """
    Corridor generation settings panel.
    
    Advanced settings and parameters for corridor generation.
    """
    bl_label = "Corridor Settings"
    bl_idname = "BLENDERCIVIL_PT_corridor_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_parent_id = "BLENDERCIVIL_PT_corridor_generation"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        """Draw settings panel."""
        layout = self.layout
        props = context.scene.bc_alignment
        
        # Station settings
        box = layout.box()
        box.label(text="Station Settings", icon='DRIVER_DISTANCE')
        col = box.column(align=True)
        
        # These would be properties added to the scene
        # For now, showing as info
        col.label(text="Base Interval: 10.0m")
        col.label(text="Curve Densification: 1.5x")
        
        layout.separator()
        
        # LOD settings
        box = layout.box()
        box.label(text="Level of Detail", icon='SHADING_RENDERED')
        col = box.column(align=True)
        
        col.label(text="High: Best quality (<5s/km)")
        col.label(text="Medium: Balanced (<2s/km)")
        col.label(text="Low: Fast preview (<1s/km)")
        
        # LOD selector (would be a property)
        row = col.row(align=True)
        row.label(text="Current: Medium")
        
        layout.separator()
        
        # Material settings
        box = layout.box()
        box.label(text="Materials", icon='MATERIAL')
        col = box.column(align=True)
        
        col.label(text="[+] Auto-apply materials")
        col.label(text="[+] Component-based colors")
        
        layout.separator()
        
        # Performance info
        box = layout.box()
        box.label(text="Performance Tips", icon='INFO')
        col = box.column(align=True)
        col.label(text="• Use Medium LOD for general work")
        col.label(text="• High LOD for final renders")
        col.label(text="• Low LOD for quick checks")
        col.label(text="• Larger intervals = faster")


class BLENDERCIVIL_PT_corridor_info(Panel):
    """
    Corridor information and statistics panel.
    
    Shows information about the current corridor or last generation.
    """
    bl_label = "Corridor Info"
    bl_idname = "BLENDERCIVIL_PT_corridor_info"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_parent_id = "BLENDERCIVIL_PT_corridor_generation"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        """Draw info panel."""
        layout = self.layout
        props = context.scene.bc_alignment
        
        # Check if there's an active corridor
        active_obj = context.active_object
        
        if active_obj and active_obj.type == 'MESH' and 'Corridor' in active_obj.name:
            # Show corridor statistics
            box = layout.box()
            box.label(text="Active Corridor", icon='MESH_DATA')
            col = box.column(align=True)
            
            mesh = active_obj.data
            col.label(text=f"Name: {active_obj.name}")
            col.label(text=f"Vertices: {len(mesh.vertices):,}")
            col.label(text=f"Faces: {len(mesh.polygons):,}")
            col.label(text=f"Materials: {len(mesh.materials)}")
            
            layout.separator()
            
            # Show object info
            box = layout.box()
            box.label(text="Object Info", icon='OBJECT_DATA')
            col = box.column(align=True)
            
            loc = active_obj.location
            col.label(text=f"Location: ({loc.x:.1f}, {loc.y:.1f}, {loc.z:.1f})")
            col.label(text=f"Collection: {active_obj.users_collection[0].name if active_obj.users_collection else 'None'}")
            
        else:
            # No active corridor
            box = layout.box()
            box.label(text="No Active Corridor", icon='INFO')
            col = box.column(align=True)
            col.label(text="Generate a corridor to see")
            col.label(text="statistics and information")
        
        layout.separator()
        
        # General info
        box = layout.box()
        box.label(text="About Corridors", icon='QUESTION')
        col = box.column(align=True)
        col.label(text="Corridors are 3D models created")
        col.label(text="by sweeping cross-sections")
        col.label(text="along 3D alignments")
        col.label(text="")
        col.label(text="IFC Standard: IfcSectionedSolidHorizontal")


class BLENDERCIVIL_PT_corridor_workflow(Panel):
    """
    Corridor workflow guide panel.
    
    Provides step-by-step workflow guidance for users.
    """
    bl_label = "Corridor Workflow"
    bl_idname = "BLENDERCIVIL_PT_corridor_workflow"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BlenderCivil'
    bl_parent_id = "BLENDERCIVIL_PT_corridor_generation"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        """Draw workflow guide."""
        layout = self.layout
        
        # Workflow steps
        box = layout.box()
        box.label(text="Complete Workflow", icon='PREFERENCES')
        
        # Step 1
        col = box.column(align=False)
        row = col.row()
        row.label(text="1️⃣ Create Alignment", icon='CURVE_PATH')
        row = col.row()
        row.label(text="   • Horizontal (PI method)")
        row = col.row()
        row.label(text="   • Vertical (PVI method)")
        row = col.row()
        row.label(text="   • Combine for 3D")
        
        col.separator()
        
        # Step 2
        row = col.row()
        row.label(text="2️⃣ Design Cross-Section", icon='MESH_DATA')
        row = col.row()
        row.label(text="   • Choose template or")
        row = col.row()
        row.label(text="   • Create custom assembly")
        row = col.row()
        row.label(text="   • Add components")
        
        col.separator()
        
        # Step 3
        row = col.row()
        row.label(text="3️⃣ Generate Corridor", icon='MOD_BUILD')
        row = col.row()
        row.label(text="   • Set station range")
        row = col.row()
        row.label(text="   • Choose LOD")
        row = col.row()
        row.label(text="   • Generate mesh")
        
        col.separator()
        
        # Step 4
        row = col.row()
        row.label(text="4️⃣ Review & Export", icon='EXPORT')
        row = col.row()
        row.label(text="   • Check geometry")
        row = col.row()
        row.label(text="   • Adjust if needed")
        row = col.row()
        row.label(text="   • Export to IFC")
        
        layout.separator()
        
        # Tips
        box = layout.box()
        box.label(text="Pro Tips", icon='LIGHT')
        col = box.column(align=True)
        col.label(text="💡 Use Quick Preview to test")
        col.label(text="💡 Start with Medium LOD")
        col.label(text="💡 Smaller intervals = smoother")
        col.label(text="💡 Curves auto-densify")


# Registration
classes = (
    BLENDERCIVIL_PT_corridor_generation,
    BLENDERCIVIL_PT_corridor_settings,
    BLENDERCIVIL_PT_corridor_info,
    BLENDERCIVIL_PT_corridor_workflow,
)


def register():
    """Register panels."""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister panels."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
