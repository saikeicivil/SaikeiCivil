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
Saikei Civil - Corridor Generation Operators
Sprint 5 Day 3 - Blender UI Integration

Operators for corridor mesh generation from the Saikei Civil UI panels.
Provides user-friendly interface for creating 3D corridor models.

Author: Saikei Civil Team
Date: November 5, 2025
Sprint: 5 of 16 - Corridor Modeling
Day: 3 of 5 - UI Integration

Operators:
- SAIKEI_OT_generate_corridor: Main corridor generation
- SAIKEI_OT_corridor_quick_preview: Fast preview at current station
- SAIKEI_OT_update_corridor_lod: Change LOD of existing corridor
- SAIKEI_OT_export_corridor_ifc: Export corridor to IFC format
- SAIKEI_OT_clear_corridor: Clear corridor visualization
"""

import bpy
from bpy.types import Operator
from bpy.props import (
    FloatProperty,
    EnumProperty,
    BoolProperty,
    IntProperty,
    StringProperty
)
import time


class SAIKEI_OT_generate_corridor(Operator):
    """
    Generate 3D corridor mesh from alignment and cross-section.
    
    Creates a complete corridor model by sweeping the cross-section
    assembly along the 3D alignment with intelligent station management.
    """
    bl_idname = "saikei.generate_corridor"
    bl_label = "Generate Corridor"
    bl_description = "Create 3D corridor mesh from alignment and cross-section"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Properties
    start_station: FloatProperty(
        name="Start Station",
        description="Starting station along alignment (m)",
        default=0.0,
        min=0.0
    )
    
    end_station: FloatProperty(
        name="End Station",
        description="Ending station along alignment (m)",
        default=1000.0,
        min=0.0
    )
    
    interval: FloatProperty(
        name="Station Interval",
        description="Base interval between stations (m)",
        default=10.0,
        min=1.0,
        max=50.0
    )
    
    lod: EnumProperty(
        name="Level of Detail",
        description="Mesh detail level",
        items=[
            ('high', "High", "Best quality, slower generation (< 5s for 1km)", 0),
            ('medium', "Medium", "Balanced quality and speed (< 2s for 1km)", 1),
            ('low', "Low", "Fast preview, lower quality (< 1s for 1km)", 2),
        ],
        default='medium'
    )
    
    curve_densification: FloatProperty(
        name="Curve Densification",
        description="Additional stations at curves (1.0 = minimal, 2.0 = dense)",
        default=1.5,
        min=1.0,
        max=3.0
    )
    
    apply_materials: BoolProperty(
        name="Apply Materials",
        description="Create and apply materials to corridor",
        default=True
    )
    
    create_collection: BoolProperty(
        name="Create Collection",
        description="Organize corridor in collection",
        default=True
    )
    
    @classmethod
    def poll(cls, context):
        """Check if operator can run."""
        props = context.scene.bc_alignment
        
        # Need active alignment and cross-section
        has_alignment = hasattr(props, 'active_alignment') and props.active_alignment
        has_cross_section = hasattr(props, 'active_assembly') and props.active_assembly
        
        return has_alignment and has_cross_section
    
    def invoke(self, context, event):
        """Show dialog before executing."""
        # Set default start/end from alignment
        props = context.scene.bc_alignment
        
        if hasattr(props, 'alignment_start_station'):
            self.start_station = props.alignment_start_station
        if hasattr(props, 'alignment_end_station'):
            self.end_station = props.alignment_end_station
        
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        """Draw operator properties in dialog."""
        layout = self.layout
        
        # Station range
        box = layout.box()
        box.label(text="Station Range:", icon='DRIVER_DISTANCE')
        col = box.column(align=True)
        col.prop(self, "start_station")
        col.prop(self, "end_station")
        
        # Generation settings
        box = layout.box()
        box.label(text="Generation Settings:", icon='SETTINGS')
        col = box.column(align=True)
        col.prop(self, "interval")
        col.prop(self, "curve_densification")
        col.prop(self, "lod", expand=False)
        
        # Options
        box = layout.box()
        box.label(text="Options:", icon='PREFERENCES')
        col = box.column(align=True)
        col.prop(self, "apply_materials")
        col.prop(self, "create_collection")
        
        # Estimated generation time
        layout.separator()
        length = self.end_station - self.start_station
        
        if self.lod == 'high':
            est_time = length / 200.0  # ~200m/s
        elif self.lod == 'medium':
            est_time = length / 500.0  # ~500m/s
        else:
            est_time = length / 1000.0  # ~1000m/s
        
        info_box = layout.box()
        info_box.label(text=f"Corridor Length: {length:.0f}m", icon='INFO')
        info_box.label(text=f"Estimated Time: {est_time:.1f}s")
    
    def execute(self, context):
        """Generate the corridor."""
        start_time = time.time()
        
        try:
            # Get scene properties
            props = context.scene.bc_alignment
            
            # Import modules
            from .native_ifc_corridor import CorridorModeler
            from .corridor_mesh_generator import CorridorMeshGenerator
            from .native_ifc_alignment import Alignment3D
            
            # Get alignment and cross-section
            alignment = props.active_alignment  # Alignment3D instance
            assembly = props.active_assembly  # RoadAssembly instance
            
            # Create corridor modeler
            modeler = CorridorModeler(
                alignment_3d=alignment,
                assembly=assembly,
                name=f"Corridor_{self.start_station:.0f}_{self.end_station:.0f}"
            )
            
            # Generate stations
            modeler.generate_stations(
                interval=self.interval,
                curve_densification=self.curve_densification
            )
            
            # Create mesh generator
            generator = CorridorMeshGenerator(
                modeler=modeler,
                name=f"Corridor_{self.start_station:.0f}_{self.end_station:.0f}"
            )
            
            # Generate mesh
            mesh_obj = generator.generate_mesh(
                lod=self.lod,
                apply_materials=self.apply_materials,
                create_collection=self.create_collection
            )
            
            # Get statistics
            stats = generator.get_statistics()
            
            # Report success
            elapsed_time = time.time() - start_time
            self.report(
                {'INFO'},
                f"Corridor generated: {stats['vertex_count']:,} vertices, "
                f"{stats['face_count']:,} faces in {elapsed_time:.2f}s"
            )
            
            # Select the generated object
            bpy.ops.object.select_all(action='DESELECT')
            mesh_obj.select_set(True)
            context.view_layer.objects.active = mesh_obj
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Corridor generation failed: {str(e)}")
            return {'CANCELLED'}


class SAIKEI_OT_corridor_quick_preview(Operator):
    """
    Quick corridor preview at current station.
    
    Generates a short section of corridor for rapid design validation.
    """
    bl_idname = "saikei.corridor_quick_preview"
    bl_label = "Quick Corridor Preview"
    bl_description = "Generate quick preview of corridor at current station"
    bl_options = {'REGISTER', 'UNDO'}
    
    preview_length: FloatProperty(
        name="Preview Length",
        description="Length of preview section (m)",
        default=50.0,
        min=10.0,
        max=200.0
    )
    
    @classmethod
    def poll(cls, context):
        """Check if operator can run."""
        props = context.scene.bc_alignment
        return (
            hasattr(props, 'active_alignment') and props.active_alignment and
            hasattr(props, 'active_assembly') and props.active_assembly and
            hasattr(props, 'current_station')
        )
    
    def execute(self, context):
        """Generate quick preview."""
        try:
            props = context.scene.bc_alignment
            current_station = props.current_station
            
            # Calculate preview range
            start = max(0, current_station - self.preview_length / 2)
            end = current_station + self.preview_length / 2
            
            # Import modules
            from .native_ifc_corridor import CorridorModeler
            from .corridor_mesh_generator import CorridorMeshGenerator
            
            # Get alignment and assembly
            alignment = props.active_alignment
            assembly = props.active_assembly
            
            # Create modeler
            modeler = CorridorModeler(
                alignment_3d=alignment,
                assembly=assembly,
                name="Corridor_Preview"
            )
            
            # Generate stations (denser for preview)
            modeler.generate_stations(interval=5.0)
            
            # Filter to preview range
            modeler.stations = [
                s for s in modeler.stations
                if start <= s.station <= end
            ]
            
            # Generate preview mesh
            generator = CorridorMeshGenerator(
                modeler=modeler,
                name="Corridor_Preview"
            )
            
            mesh_obj = generator.generate_mesh(
                lod='high',  # High quality for preview
                apply_materials=True,
                create_collection=False
            )
            
            # Add to scene
            bpy.context.collection.objects.link(mesh_obj)
            
            # Report success
            self.report(
                {'INFO'},
                f"Preview generated at station {current_station:.2f}m"
            )
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Preview failed: {str(e)}")
            return {'CANCELLED'}


class SAIKEI_OT_update_corridor_lod(Operator):
    """
    Update LOD of existing corridor mesh.
    
    Regenerates corridor with different detail level without
    changing other parameters.
    """
    bl_idname = "saikei.update_corridor_lod"
    bl_label = "Update Corridor LOD"
    bl_description = "Change level of detail of existing corridor"
    bl_options = {'REGISTER', 'UNDO'}
    
    lod: EnumProperty(
        name="New LOD",
        description="New level of detail",
        items=[
            ('high', "High", "Best quality", 0),
            ('medium', "Medium", "Balanced", 1),
            ('low', "Low", "Fast preview", 2),
        ],
        default='medium'
    )
    
    @classmethod
    def poll(cls, context):
        """Check if there's an active corridor object."""
        return (
            context.active_object and
            context.active_object.type == 'MESH' and
            'Corridor' in context.active_object.name
        )
    
    def invoke(self, context, event):
        """Show confirmation dialog."""
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        """Update corridor LOD."""
        # This would require storing corridor parameters
        # For now, show information message
        self.report(
            {'INFO'},
            f"LOD update to '{self.lod}' - Regenerate corridor to apply"
        )
        return {'FINISHED'}


class SAIKEI_OT_export_corridor_ifc(Operator):
    """
    Export corridor to IFC 4.3 format.
    
    Creates IFC file with IfcSectionedSolidHorizontal representing
    the corridor geometry.
    """
    bl_idname = "saikei.export_corridor_ifc"
    bl_label = "Export Corridor to IFC"
    bl_description = "Export corridor as IFC 4.3 file"
    bl_options = {'REGISTER'}
    
    filepath: StringProperty(
        name="File Path",
        description="Output IFC file path",
        default="corridor.ifc",
        subtype='FILE_PATH'
    )
    
    @classmethod
    def poll(cls, context):
        """Check if there's a corridor to export."""
        return (
            context.active_object and
            context.active_object.type == 'MESH' and
            'Corridor' in context.active_object.name
        )
    
    def invoke(self, context, event):
        """Open file browser."""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        """Export corridor to IFC."""
        try:
            # Import corridor modeler
            from .native_ifc_corridor import CorridorModeler
            
            # Get corridor data from scene
            props = context.scene.bc_alignment
            
            if not hasattr(props, 'active_corridor_modeler'):
                self.report(
                    {'WARNING'},
                    "No corridor data found. Generate corridor first."
                )
                return {'CANCELLED'}
            
            modeler = props.active_corridor_modeler
            
            # Export to IFC
            ifc_file = modeler.export_to_ifc()
            ifc_file.write(self.filepath)
            
            self.report(
                {'INFO'},
                f"Corridor exported to: {self.filepath}"
            )
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}


class SAIKEI_OT_clear_corridor(Operator):
    """
    Clear corridor visualization from scene.
    
    Removes corridor mesh and associated objects.
    """
    bl_idname = "saikei.clear_corridor"
    bl_label = "Clear Corridor"
    bl_description = "Remove corridor visualization from scene"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        """Check if there are corridor objects."""
        return 'Corridor Visualization' in bpy.data.collections
    
    def invoke(self, context, event):
        """Show confirmation dialog."""
        return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, context):
        """Clear corridor objects."""
        try:
            count = 0
            
            # Remove objects in corridor collection
            if 'Corridor Visualization' in bpy.data.collections:
                coll = bpy.data.collections['Corridor Visualization']
                
                # Remove all objects in collection
                for obj in coll.objects:
                    bpy.data.objects.remove(obj, do_unlink=True)
                    count += 1
                
                # Remove collection
                bpy.data.collections.remove(coll)
            
            self.report({'INFO'}, f"Cleared {count} corridor objects")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Clear failed: {str(e)}")
            return {'CANCELLED'}


# Registration
classes = (
    SAIKEI_OT_generate_corridor,
    SAIKEI_OT_corridor_quick_preview,
    SAIKEI_OT_update_corridor_lod,
    SAIKEI_OT_export_corridor_ifc,
    SAIKEI_OT_clear_corridor,
)


def register():
    """Register operators."""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister operators."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
