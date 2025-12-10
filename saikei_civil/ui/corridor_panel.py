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
Saikei Civil - Corridor UI Panel
Sprint 5 Day 3 - User Interface

Panel for corridor generation and management in Blender's 3D View sidebar.
Provides intuitive controls for creating 3D corridor models.

Author: Saikei Civil Team
Date: November 5, 2025
Sprint: 5 of 16 - Corridor Modeling
Day: 3 of 5 - UI Integration

Panels:
- SAIKEI_PT_corridor_generation: Main corridor controls
- SAIKEI_PT_corridor_settings: Advanced settings
- SAIKEI_PT_corridor_info: Statistics and information
"""

import bpy
from bpy.types import Panel


class SAIKEI_PT_corridor_generation(Panel):
    """
    Main corridor generation panel.

    Provides primary controls for creating 3D corridors from
    alignments and cross-sections.
    """
    bl_label = "Corridor Generation"
    bl_idname = "SAIKEI_PT_corridor_generation"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Saikei Civil'
    bl_order = 9
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        """Draw the panel."""
        layout = self.layout

        # Get corridor properties
        corridor_props = context.scene.bc_corridor if hasattr(context.scene, 'bc_corridor') else None

        # Header with icon
        box = layout.box()
        row = box.row()
        row.label(text="3D Corridor Modeling", icon='OUTLINER_OB_CURVE')

        # Check for IFC file and alignments
        from ..core.ifc_manager import NativeIfcManager
        ifc_file = NativeIfcManager.file
        alignments = ifc_file.by_type("IfcAlignment") if ifc_file else []

        # Check for cross-section assemblies
        cs_props = context.scene.bc_cross_section if hasattr(context.scene, 'bc_cross_section') else None
        assemblies = cs_props.assemblies if cs_props else []

        has_alignment = len(alignments) > 0
        has_assembly = len(assemblies) > 0

        # Prerequisites check
        if not has_alignment or not has_assembly:
            box = layout.box()
            box.label(text="Prerequisites Required:", icon='ERROR')

            if not has_alignment:
                box.label(text="• Create Alignment (Horizontal + Vertical)")
            else:
                box.label(text="✓ Alignment Ready", icon='CHECKMARK')

            if not has_assembly:
                box.label(text="• Design Cross-Section Assembly")
            else:
                box.label(text="✓ Cross-Section Ready", icon='CHECKMARK')

            return

        # Input Selection
        box = layout.box()
        box.label(text="Input Selection", icon='IMPORT')
        col = box.column(align=True)

        # Alignment selector
        row = col.row(align=True)
        row.label(text="Alignment:", icon='CURVE_PATH')
        if corridor_props and len(alignments) > 0:
            # Show alignment name
            idx = min(corridor_props.active_alignment_index, len(alignments) - 1)
            align_name = alignments[idx].Name if idx >= 0 else "None"
            row.label(text=align_name)

            # Navigation buttons if multiple alignments
            if len(alignments) > 1:
                row = col.row(align=True)
                row.prop(corridor_props, "active_alignment_index", text="Index")

        # Assembly selector
        row = col.row(align=True)
        row.label(text="Assembly:", icon='MESH_DATA')
        if corridor_props and len(assemblies) > 0:
            idx = min(corridor_props.active_assembly_index, len(assemblies) - 1)
            asm_name = assemblies[idx].name if idx >= 0 else "None"
            row.label(text=asm_name)

            if len(assemblies) > 1:
                row = col.row(align=True)
                row.prop(corridor_props, "active_assembly_index", text="Index")

        layout.separator()

        # Station Range
        box = layout.box()
        box.label(text="Station Range", icon='DRIVER_DISTANCE')
        col = box.column(align=True)

        if corridor_props:
            col.prop(corridor_props, "start_station")
            col.prop(corridor_props, "end_station")

            # Show length
            length = corridor_props.end_station - corridor_props.start_station
            col.label(text=f"Length: {length:.1f}m")

        layout.separator()

        # Generation Settings
        box = layout.box()
        box.label(text="Generation Settings", icon='SETTINGS')
        col = box.column(align=True)

        if corridor_props:
            col.prop(corridor_props, "station_interval")
            col.prop(corridor_props, "curve_densification")
            col.prop(corridor_props, "lod")
            col.separator()
            col.prop(corridor_props, "apply_materials")
            col.prop(corridor_props, "create_collection")

        layout.separator()

        # Generate Button
        box = layout.box()
        col = box.column(align=True)

        row = col.row(align=True)
        row.scale_y = 1.8
        row.operator(
            "saikei.generate_corridor",
            text="Generate Corridor",
            icon='MOD_BUILD'
        )

        layout.separator()

        # Management
        box = layout.box()
        box.label(text="Management", icon='TOOL_SETTINGS')
        col = box.column(align=True)

        col.operator(
            "saikei.export_corridor_ifc",
            text="Export to IFC",
            icon='EXPORT'
        )

        col.operator(
            "saikei.clear_corridor",
            text="Clear Corridor",
            icon='TRASH'
        )

        # Show last generation stats if available
        if corridor_props and corridor_props.last_vertex_count > 0:
            layout.separator()
            box = layout.box()
            box.label(text="Last Generation", icon='INFO')
            col = box.column(align=True)
            col.label(text=f"Vertices: {corridor_props.last_vertex_count:,}")
            col.label(text=f"Faces: {corridor_props.last_face_count:,}")
            col.label(text=f"Time: {corridor_props.last_generation_time:.2f}s")


class SAIKEI_PT_corridor_settings(Panel):
    """
    Corridor generation settings panel.
    
    Advanced settings and parameters for corridor generation.
    """
    bl_label = "Corridor Settings"
    bl_idname = "SAIKEI_PT_corridor_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Saikei Civil'
    bl_parent_id = "SAIKEI_PT_corridor_generation"
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


class SAIKEI_PT_corridor_info(Panel):
    """
    Corridor information and statistics panel.
    
    Shows information about the current corridor or last generation.
    """
    bl_label = "Corridor Info"
    bl_idname = "SAIKEI_PT_corridor_info"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Saikei Civil'
    bl_parent_id = "SAIKEI_PT_corridor_generation"
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


class SAIKEI_PT_corridor_workflow(Panel):
    """
    Corridor workflow guide panel.
    
    Provides step-by-step workflow guidance for users.
    """
    bl_label = "Corridor Workflow"
    bl_idname = "SAIKEI_PT_corridor_workflow"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Saikei Civil'
    bl_parent_id = "SAIKEI_PT_corridor_generation"
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
    SAIKEI_PT_corridor_generation,
    SAIKEI_PT_corridor_settings,
    SAIKEI_PT_corridor_info,
    SAIKEI_PT_corridor_workflow,
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
