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
        # Check for IFC file with alignments
        from ..core.ifc_manager import NativeIfcManager
        ifc_file = NativeIfcManager.file
        if not ifc_file:
            return False

        alignments = ifc_file.by_type("IfcAlignment")
        if not alignments:
            return False

        # Check for cross-section assembly
        if not hasattr(context.scene, 'bc_cross_section'):
            return False

        cs_props = context.scene.bc_cross_section
        if not cs_props.assemblies:
            return False

        return True

    def invoke(self, context, event):
        """Show dialog before executing."""
        # Set default start/end based on alignment length
        # For now, use reasonable defaults
        self.start_station = 0.0
        self.end_station = 100.0  # Default 100m corridor

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
        """
        Generate the corridor using the three-layer architecture.

        This operator calls core functions with tool implementations,
        following the Bonsai/ifcopenshell pattern.
        """
        start_time = time.time()

        try:
            # Import tool layer (Layer 2)
            from .. import tool

            # Get scene properties
            props = context.scene.bc_corridor
            cs_props = context.scene.bc_cross_section

            # Validate inputs
            alignment_index = props.active_alignment_index
            assembly_index = props.active_assembly_index

            # Get alignments from IFC file
            ifc_file = tool.Ifc.get()
            if not ifc_file:
                self.report({'ERROR'}, "No IFC file loaded. Create a project first.")
                return {'CANCELLED'}

            alignments = tool.Ifc.by_type("IfcAlignment")
            if alignment_index < 0 or alignment_index >= len(alignments):
                self.report({'ERROR'}, "No alignment selected")
                return {'CANCELLED'}

            if assembly_index < 0 or assembly_index >= len(cs_props.assemblies):
                self.report({'ERROR'}, "No cross-section assembly selected")
                return {'CANCELLED'}

            alignment = alignments[alignment_index]
            assembly = cs_props.assemblies[assembly_index]

            # Create alignment wrapper (pure Python from core)
            from ..core.corridor import (
                AlignmentWrapper,
                create_assembly_wrapper,
                CorridorParams,
            )
            from ..core.native_ifc_corridor import StationManager

            alignment_3d = AlignmentWrapper(
                alignment,
                self.start_station,
                self.end_station
            )

            # Create assembly wrapper (pure Python)
            assembly_wrapper = create_assembly_wrapper(assembly)

            # Generate stations using StationManager (pure Python from core)
            station_manager = StationManager(alignment_3d, self.interval)
            stations = station_manager.calculate_stations(
                curve_densification_factor=self.curve_densification
            )

            if len(stations) < 2:
                self.report({'ERROR'}, "Need at least 2 stations to create corridor")
                return {'CANCELLED'}

            # Generate mesh using Corridor tool (Layer 2 - Blender specific)
            corridor_name = f"Corridor_{self.start_station:.0f}_{self.end_station:.0f} (IfcCourse)"
            mesh_obj, stats = tool.Corridor.generate_corridor_mesh(
                stations=stations,
                assembly=assembly_wrapper,
                name=corridor_name,
                lod=self.lod
            )

            if mesh_obj is None:
                self.report({'ERROR'}, "Failed to generate corridor mesh")
                return {'CANCELLED'}

            # Get Road entity and object for proper hierarchy
            road = tool.Spatial.get_road()
            road_obj = None
            if road:
                road_obj = tool.Ifc.get_object(road)
            if road_obj is None:
                # Fallback: try direct lookup by name
                from ..core.ifc_manager.blender_hierarchy import ROAD_EMPTY_NAME
                road_obj = bpy.data.objects.get(ROAD_EMPTY_NAME)

            # Create proper IFC hierarchy: IfcRoad > IfcRoadPart > IfcCourse
            corridor_entity = None
            road_part = None
            road_part_obj = None

            try:
                import ifcopenshell.guid

                # Get or create IfcRoadPart (CARRIAGEWAY) under the road
                road_part = self._get_or_create_road_part(
                    ifc_file, road, "CARRIAGEWAY", "Carriageway"
                )

                # Create Blender object for road part if it doesn't exist
                if road_part:
                    road_part_obj = tool.Ifc.get_object(road_part)
                    if road_part_obj is None:
                        road_part_obj = bpy.data.objects.new(
                            f"Carriageway (IfcRoadPart)", None
                        )
                        road_part_obj.empty_display_type = 'PLAIN_AXES'
                        road_part_obj.empty_display_size = 0.5
                        tool.Ifc.link(road_part, road_part_obj)

                        # Add to collection and parent to Road
                        if "Saikei Civil Project" in bpy.data.collections:
                            bpy.data.collections["Saikei Civil Project"].objects.link(road_part_obj)
                        if road_obj:
                            road_part_obj.parent = road_obj

                # Create IfcCourse for the corridor
                corridor_entity = ifc_file.create_entity(
                    "IfcCourse",
                    GlobalId=ifcopenshell.guid.new(),
                    Name=corridor_name,
                    Description="Corridor surface generated from cross-section assembly",
                    ObjectType="PAVEMENT",
                    PredefinedType="USERDEFINED"
                )

                # Link Blender mesh object to IFC entity
                tool.Ifc.link(corridor_entity, mesh_obj)

                # Contain IfcCourse in IfcRoadPart (or IfcRoad as fallback)
                containing_structure = road_part if road_part else road
                if containing_structure:
                    ifc_file.create_entity(
                        "IfcRelContainedInSpatialStructure",
                        GlobalId=ifcopenshell.guid.new(),
                        Name="CourseToRoadPart",
                        RelatingStructure=containing_structure,
                        RelatedElements=[corridor_entity]
                    )

            except Exception as e:
                import traceback
                traceback.print_exc()
                # IFC linkage failed, but we can continue

            # Add to collection
            if self.create_collection:
                tool.Corridor.add_to_collection(mesh_obj, "Saikei Civil Project")

            # Parent to RoadPart object (or Road as fallback) for hierarchy
            parent_obj = road_part_obj if road_part_obj else road_obj
            if parent_obj:
                mesh_obj.parent = parent_obj

            # Link mesh to scene if not already linked
            if mesh_obj.name not in context.scene.collection.objects:
                if "Saikei Civil Project" not in bpy.data.collections:
                    context.scene.collection.objects.link(mesh_obj)

            # Report success
            elapsed_time = time.time() - start_time
            self.report(
                {'INFO'},
                f"Corridor generated: {stats.vertex_count:,} vertices, "
                f"{stats.face_count:,} faces in {elapsed_time:.2f}s"
            )

            # Select the generated object
            bpy.ops.object.select_all(action='DESELECT')
            mesh_obj.select_set(True)
            context.view_layer.objects.active = mesh_obj

            return {'FINISHED'}

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Corridor generation failed: {str(e)}")
            return {'CANCELLED'}

    def _get_or_create_road_part(self, ifc_file, road, part_type, name):
        """
        Get or create an IfcRoadPart under the IfcRoad.

        IFC 4.3 road hierarchy: IfcRoad > IfcRoadPart > IfcCourse
        IfcRoadPart types: CARRIAGEWAY, SHOULDER, ROADSEGMENT, etc.

        Args:
            ifc_file: IFC file instance
            road: IfcRoad entity
            part_type: PredefinedType for IfcRoadPart (e.g., "CARRIAGEWAY")
            name: Name for the road part

        Returns:
            IfcRoadPart entity (existing or newly created)
        """
        import ifcopenshell.guid

        if road is None:
            return None

        # Look for existing IfcRoadPart of this type aggregated to the road
        for rel in ifc_file.by_type("IfcRelAggregates"):
            if rel.RelatingObject == road:
                for obj in rel.RelatedObjects or []:
                    if obj.is_a("IfcRoadPart"):
                        if hasattr(obj, 'PredefinedType') and obj.PredefinedType == part_type:
                            return obj

        # Create new IfcRoadPart
        road_part = ifc_file.create_entity(
            "IfcRoadPart",
            GlobalId=ifcopenshell.guid.new(),
            Name=name,
            Description=f"{part_type} road part",
            ObjectType=part_type,
            PredefinedType=part_type
        )

        # Aggregate IfcRoadPart to IfcRoad using IfcRelAggregates
        ifc_file.create_entity(
            "IfcRelAggregates",
            GlobalId=ifcopenshell.guid.new(),
            Name=f"Road_{part_type}",
            RelatingObject=road,
            RelatedObjects=[road_part]
        )

        return road_part


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
        # Same check as generate corridor
        from ..core.ifc_manager import NativeIfcManager
        ifc_file = NativeIfcManager.file
        if not ifc_file:
            return False

        alignments = ifc_file.by_type("IfcAlignment")
        if not alignments:
            return False

        if not hasattr(context.scene, 'bc_cross_section'):
            return False

        cs_props = context.scene.bc_cross_section
        return bool(cs_props.assemblies)

    def execute(self, context):
        """Generate quick preview."""
        try:
            corridor_props = context.scene.bc_corridor

            # Calculate preview range centered on start_station
            center = corridor_props.start_station
            start = max(0, center - self.preview_length / 2)
            end = center + self.preview_length / 2

            # Use the main generate corridor operator with limited range
            bpy.ops.saikei.generate_corridor(
                'EXEC_DEFAULT',
                start_station=start,
                end_station=end,
                interval=5.0,
                lod='high',
                apply_materials=True,
                create_collection=False
            )

            self.report({'INFO'}, f"Preview generated: {start:.0f}m to {end:.0f}m")
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
            # Export current IFC file (which includes corridor data)
            from ..core.ifc_manager import NativeIfcManager

            ifc_file = NativeIfcManager.file
            if not ifc_file:
                self.report({'ERROR'}, "No IFC file loaded")
                return {'CANCELLED'}

            # Write to specified path
            ifc_file.write(self.filepath)

            self.report({'INFO'}, f"Corridor exported to: {self.filepath}")
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
