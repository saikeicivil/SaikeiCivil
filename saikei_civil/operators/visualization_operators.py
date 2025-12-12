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
Cross-Section Visualization Operators for Blender UI
Sprint 4 Day 4 - Interactive visualization from panels

These operators add one-click visualization buttons to the Saikei Civil UI,
making it easy to visualize cross-sections and corridors without scripting.

Operators:
- SAIKEI_OT_visualize_station: Visualize single cross-section
- SAIKEI_OT_create_corridor: Create full 3D corridor
- SAIKEI_OT_add_station_markers: Add station labels
- SAIKEI_OT_clear_visualization: Clear all visualization
- SAIKEI_OT_quick_preview: Quick preview at current station
"""

import bpy
from bpy.types import Operator
from bpy.props import FloatProperty, BoolProperty, StringProperty
import time
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class SAIKEI_OT_visualize_station(Operator):
    """Visualize cross-section at a specific station"""
    bl_idname = "saikei.visualize_station"
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
        # TODO: Link to actual Saikei Civil data structures

        logger.info("Visualizing cross-section at station %.2f", self.station)
        
        try:
            # Import visualizer
            from cross_section_visualizer import CrossSectionVisualizer
            
            # TODO: Implement when alignment and assembly data structures are available
            self.report({'WARNING'},
                       "Visualization requires active alignment and cross-section assembly")
            return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Visualization failed: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Show dialog before executing."""
        return context.window_manager.invoke_props_dialog(self)


class SAIKEI_OT_create_corridor(Operator):
    """Create full 3D corridor from cross-sections"""
    bl_idname = "saikei.create_corridor"
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
            
            # TODO: Implement when alignment and assembly data structures are available
            self.report({'WARNING'},
                       "Corridor creation requires active alignment and assembly")
            return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Corridor creation failed: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Show dialog with options."""
        return context.window_manager.invoke_props_dialog(self, width=400)


class SAIKEI_OT_add_station_markers(Operator):
    """Add station marker labels along alignment"""
    bl_idname = "saikei.add_station_markers"
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
            
            # TODO: Implement when alignment data structures are available
            self.report({'WARNING'},
                       "Station markers require active alignment")
            return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Marker creation failed: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Show dialog with options."""
        return context.window_manager.invoke_props_dialog(self)


class SAIKEI_OT_clear_visualization(Operator):
    """Clear all visualization objects"""
    bl_idname = "saikei.clear_visualization"
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


class SAIKEI_OT_quick_preview(Operator):
    """Quick preview of current cross-section"""
    bl_idname = "saikei.quick_preview"
    bl_label = "Quick Preview"
    bl_description = "Instantly preview cross-section at current station (fast mode)"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """Execute quick preview."""
        scene = context.scene

        logger.info("Quick preview")
        
        try:
            from cross_section_visualizer import visualize_cross_section_quick

            # TODO: Implement when alignment data structures are available
            self.report({'WARNING'}, "Quick preview requires active alignment")
            return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Preview failed: {str(e)}")
            return {'CANCELLED'}


class SAIKEI_OT_component_preview(Operator):
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
    bl_idname = "saikei.component_preview"
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
            
            # TODO: Implement when assembly data structures are available
            self.report({'WARNING'}, "Component preview requires active assembly")
            return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Component preview failed: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Show dialog."""
        return context.window_manager.invoke_props_dialog(self)


# Registration
classes = (
    SAIKEI_OT_visualize_station,
    SAIKEI_OT_create_corridor,
    SAIKEI_OT_add_station_markers,
    SAIKEI_OT_clear_visualization,
    SAIKEI_OT_quick_preview,
    SAIKEI_OT_component_preview,
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
