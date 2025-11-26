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
Cross-Section Visualization Operators for Blender UI
Sprint 4 Day 4 - Interactive visualization from panels

These operators add one-click visualization buttons to the BlenderCivil UI,
making it easy to visualize cross-sections and corridors without scripting.

Operators:
- BLENDERCIVIL_OT_visualize_station: Visualize single cross-section
- BLENDERCIVIL_OT_create_corridor: Create full 3D corridor
- BLENDERCIVIL_OT_add_station_markers: Add station labels
- BLENDERCIVIL_OT_clear_visualization: Clear all visualization
- BLENDERCIVIL_OT_quick_preview: Quick preview at current station
"""

import bpy
from bpy.types import Operator
from bpy.props import FloatProperty, BoolProperty, StringProperty
import time
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class BLENDERCIVIL_OT_visualize_station(Operator):
    """Visualize cross-section at a specific station"""
    bl_idname = "blendercivil.visualize_station"
    bl_label = "Visualize Cross-Section"
    bl_description = "Create 3D geometry for cross-section at specified station"
    bl_options = {'REGISTER', 'UNDO'}
    
    station: FloatProperty(
        name="Station",
        description="Station to visualize",
        default=0.0,
        min=0.0
    )
    
    extrusion: FloatProperty(
        name="Extrusion Length",
        description="Length to extrude along alignment (meters)",
        default=2.0,
        min=0.1,
        max=20.0
    )
    
    show_materials: BoolProperty(
        name="Show Materials",
        description="Apply component materials (colors)",
        default=True
    )
    
    def execute(self, context):
        """Execute the operator."""
        scene = context.scene

        # Get alignment and assembly from scene properties
        # This assumes they're stored in the scene
        # TODO: Link to actual BlenderCivil data structures

        logger.info("Visualizing cross-section at station %.2f", self.station)
        
        try:
            # Import visualizer
            from cross_section_visualizer import CrossSectionVisualizer
            
            # TODO: Get actual alignment and assembly
            # For now, show error message
            self.report({'WARNING'}, 
                       "Visualization requires active alignment and cross-section assembly")
            return {'CANCELLED'}
            
            # Example code (when data available):
            # alignment_3d = scene.blendercivil.alignment_3d
            # assembly = scene.blendercivil.active_assembly
            # 
            # viz = CrossSectionVisualizer(alignment_3d, assembly)
            # obj = viz.visualize_station(
            #     self.station,
            #     extrusion=self.extrusion,
            #     show_materials=self.show_materials
            # )
            # 
            # self.report({'INFO'}, f"Cross-section created: {obj.name}")
            # return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Visualization failed: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Show dialog before executing."""
        return context.window_manager.invoke_props_dialog(self)


class BLENDERCIVIL_OT_create_corridor(Operator):
    """Create full 3D corridor from cross-sections"""
    bl_idname = "blendercivil.create_corridor"
    bl_label = "Create Corridor"
    bl_description = "Sweep cross-sections along alignment to create 3D road model"
    bl_options = {'REGISTER', 'UNDO'}
    
    start_station: FloatProperty(
        name="Start Station",
        description="Starting station for corridor",
        default=0.0,
        min=0.0
    )
    
    end_station: FloatProperty(
        name="End Station",
        description="Ending station for corridor",
        default=100.0,
        min=0.0
    )
    
    interval: FloatProperty(
        name="Station Interval",
        description="Distance between cross-sections (meters)",
        default=10.0,
        min=1.0,
        max=50.0
    )
    
    smooth_shading: BoolProperty(
        name="Smooth Shading",
        description="Use smooth shading for better appearance",
        default=True
    )
    
    show_materials: BoolProperty(
        name="Show Materials",
        description="Apply component materials",
        default=True
    )
    
    corridor_name: StringProperty(
        name="Name",
        description="Name for the corridor object",
        default="Corridor"
    )
    
    def execute(self, context):
        """Execute the operator."""
        logger.info("Creating corridor: %s", self.corridor_name)
        logger.info("From station %.2f to %.2f", self.start_station, self.end_station)
        logger.info("Interval: %.2f meters", self.interval)
        
        start_time = time.time()
        
        try:
            from cross_section_visualizer import CrossSectionVisualizer
            
            # TODO: Get actual data from scene
            self.report({'WARNING'}, 
                       "Corridor creation requires active alignment and assembly")
            return {'CANCELLED'}
            
            # Example code:
            # alignment_3d = context.scene.blendercivil.alignment_3d
            # assembly = context.scene.blendercivil.active_assembly
            # 
            # viz = CrossSectionVisualizer(alignment_3d, assembly)
            # corridor = viz.create_corridor(
            #     start_station=self.start_station,
            #     end_station=self.end_station,
            #     interval=self.interval,
            #     name=self.corridor_name,
            #     show_materials=self.show_materials,
            #     smooth=self.smooth_shading
            # )
            # 
            # elapsed = time.time() - start_time
            # 
            # self.report({'INFO'}, 
            #            f"Corridor created in {elapsed:.2f}s: {corridor.name}")
            # return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Corridor creation failed: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Show dialog with options."""
        return context.window_manager.invoke_props_dialog(self, width=400)


class BLENDERCIVIL_OT_add_station_markers(Operator):
    """Add station marker labels along alignment"""
    bl_idname = "blendercivil.add_station_markers"
    bl_label = "Add Station Markers"
    bl_description = "Create station labels and markers along the alignment"
    bl_options = {'REGISTER', 'UNDO'}
    
    start_station: FloatProperty(
        name="Start Station",
        description="Starting station",
        default=0.0,
        min=0.0
    )
    
    end_station: FloatProperty(
        name="End Station",
        description="Ending station",
        default=100.0,
        min=0.0
    )
    
    interval: FloatProperty(
        name="Marker Interval",
        description="Distance between markers (meters)",
        default=50.0,
        min=10.0,
        max=200.0
    )
    
    marker_height: FloatProperty(
        name="Marker Height",
        description="Height of marker posts (meters)",
        default=2.0,
        min=0.5,
        max=10.0
    )
    
    def execute(self, context):
        """Execute the operator."""
        logger.info("Adding station markers")
        logger.info("Interval: %.2f meters", self.interval)
        
        try:
            from cross_section_visualizer import CrossSectionVisualizer
            
            # TODO: Get actual data
            self.report({'WARNING'}, 
                       "Station markers require active alignment")
            return {'CANCELLED'}
            
            # Example code:
            # alignment_3d = context.scene.blendercivil.alignment_3d
            # assembly = context.scene.blendercivil.active_assembly
            # 
            # viz = CrossSectionVisualizer(alignment_3d, assembly)
            # markers = viz.create_station_markers(
            #     start_station=self.start_station,
            #     end_station=self.end_station,
            #     interval=self.interval,
            #     height=self.marker_height
            # )
            # 
            # self.report({'INFO'}, f"Created {len(markers)} station markers")
            # return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Marker creation failed: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Show dialog with options."""
        return context.window_manager.invoke_props_dialog(self)


class BLENDERCIVIL_OT_clear_visualization(Operator):
    """Clear all visualization objects"""
    bl_idname = "blendercivil.clear_visualization"
    bl_label = "Clear Visualization"
    bl_description = "Remove all cross-section visualization objects from the scene"
    bl_options = {'REGISTER', 'UNDO'}
    
    collection_name: StringProperty(
        name="Collection",
        description="Name of collection to clear",
        default="Cross-Section Visualization"
    )
    
    def execute(self, context):
        """Execute the operator."""
        logger.info("Clearing visualization: %s", self.collection_name)
        
        try:
            # Find and clear collection
            if self.collection_name in bpy.data.collections:
                collection = bpy.data.collections[self.collection_name]
                
                # Delete all objects in collection
                obj_count = len(collection.objects)
                for obj in list(collection.objects):
                    bpy.data.objects.remove(obj, do_unlink=True)
                
                self.report({'INFO'}, f"Cleared {obj_count} objects")
                return {'FINISHED'}
            else:
                self.report({'INFO'}, "No visualization to clear")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Clear failed: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Confirm before clearing."""
        return context.window_manager.invoke_confirm(self, event)


class BLENDERCIVIL_OT_quick_preview(Operator):
    """Quick preview of current cross-section"""
    bl_idname = "blendercivil.quick_preview"
    bl_label = "Quick Preview"
    bl_description = "Instantly preview cross-section at current station (fast mode)"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """Execute quick preview."""
        scene = context.scene

        logger.info("Quick preview")
        
        try:
            # TODO: Get current station from scene properties
            # current_station = scene.blendercivil.current_station
            current_station = 0.0
            
            from cross_section_visualizer import visualize_cross_section_quick
            
            # TODO: Get actual data
            self.report({'WARNING'}, "Quick preview requires active alignment")
            return {'CANCELLED'}
            
            # Example code:
            # alignment_3d = scene.blendercivil.alignment_3d
            # assembly = scene.blendercivil.active_assembly
            # 
            # obj = visualize_cross_section_quick(
            #     alignment_3d,
            #     assembly,
            #     current_station,
            #     collection_name="Quick Preview"
            # )
            # 
            # self.report({'INFO'}, f"Preview created at STA {current_station:.2f}")
            # return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Preview failed: {str(e)}")
            return {'CANCELLED'}


class BLENDERCIVIL_OT_component_preview(Operator):
    """
    Preview a single cross-section component in isolation.

    This operator creates a 3D visualization of a single component from
    the active assembly, useful for inspecting individual elements like
    lanes, shoulders, or ditches without the full cross-section.

    Properties:
        component_name: Name of the component to preview
        station: Station location for the preview
        extrusion: Length to extrude the component (for 3D depth)

    Usage:
        Invoked from UI panels to preview individual assembly components.
        Helps verify component geometry before creating full corridor.
    """
    bl_idname = "blendercivil.component_preview"
    bl_label = "Preview Component"
    bl_description = "Visualize a single cross-section component"
    bl_options = {'REGISTER', 'UNDO'}
    
    component_name: StringProperty(
        name="Component",
        description="Name of component to preview",
        default=""
    )
    
    station: FloatProperty(
        name="Station",
        description="Station for preview",
        default=0.0,
        min=0.0
    )
    
    extrusion: FloatProperty(
        name="Extrusion",
        description="Extrusion length (meters)",
        default=5.0,
        min=0.1,
        max=20.0
    )
    
    def execute(self, context):
        """Execute component preview."""
        logger.info("Previewing component: %s", self.component_name)
        
        try:
            from cross_section_visualizer import CrossSectionVisualizer
            
            # TODO: Get actual data
            self.report({'WARNING'}, "Component preview requires active assembly")
            return {'CANCELLED'}
            
            # Example code:
            # alignment_3d = context.scene.blendercivil.alignment_3d
            # assembly = context.scene.blendercivil.active_assembly
            # 
            # component = assembly.get_component_by_name(self.component_name)
            # if not component:
            #     self.report({'ERROR'}, f"Component not found: {self.component_name}")
            #     return {'CANCELLED'}
            # 
            # viz = CrossSectionVisualizer(alignment_3d, assembly)
            # obj = viz.create_component_preview(
            #     component=component,
            #     station=self.station,
            #     extrusion=self.extrusion
            # )
            # 
            # self.report({'INFO'}, f"Component preview: {obj.name}")
            # return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Component preview failed: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Show dialog."""
        return context.window_manager.invoke_props_dialog(self)


# Registration
classes = (
    BLENDERCIVIL_OT_visualize_station,
    BLENDERCIVIL_OT_create_corridor,
    BLENDERCIVIL_OT_add_station_markers,
    BLENDERCIVIL_OT_clear_visualization,
    BLENDERCIVIL_OT_quick_preview,
    BLENDERCIVIL_OT_component_preview,
)


def register():
    """Register operators."""
    for cls in classes:
        bpy.utils.register_class(cls)
    logger.info("Cross-section visualization operators registered")


def unregister():
    """Unregister operators."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    logger.info("Cross-section visualization operators unregistered")


if __name__ == "__main__":
    register()
