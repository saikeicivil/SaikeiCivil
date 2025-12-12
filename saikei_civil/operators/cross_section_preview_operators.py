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
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================

"""
Cross-Section Preview Operators
================================

Operators for generating 2D cross-section preview meshes in the 3D viewport.
These create visual representations of assemblies without requiring an alignment.

Operators:
    BC_OT_GenerateCrossSectionPreview: Generate a 2D preview mesh
    BC_OT_ClearCrossSectionPreview: Clear preview objects from scene
"""

import bpy
from bpy.types import Operator
from ..core.logging_config import get_logger

logger = get_logger(__name__)


def update_assembly_total_width(assembly):
    """
    Calculate and update the total width of an assembly.

    Args:
        assembly: BC_AssemblyProperties instance
    """
    left_width = 0.0
    right_width = 0.0

    for comp in assembly.components:
        if comp.side == 'LEFT':
            left_width += comp.width
        elif comp.side == 'RIGHT':
            right_width += comp.width
        else:  # CENTER
            left_width += comp.width / 2
            right_width += comp.width / 2

    assembly.total_width = left_width + right_width


class BC_OT_GenerateCrossSectionPreview(Operator):
    """
    Generate a 2D cross-section preview mesh.

    Creates a flat 2D visualization of the cross-section assembly in the 3D view,
    allowing users to see the component layout while building the assembly. This
    preview does not require an alignment - it shows the cross-section shape at
    the world origin.

    The preview mesh is color-coded by component type:
    - Lanes: Dark gray
    - Shoulders: Light gray
    - Curbs: White
    - Ditches: Brown

    Usage:
        Called from the cross-section panel to visualize the assembly shape.
        Updates the existing preview if one exists.
    """
    bl_idname = "bc.generate_cross_section_preview"
    bl_label = "Generate Preview"
    bl_description = "Generate a 2D preview of the cross-section assembly"
    bl_options = {'REGISTER', 'UNDO'}

    # Component type colors (R, G, B, A)
    COMPONENT_COLORS = {
        'LANE': (0.3, 0.3, 0.3, 1.0),
        'SHOULDER': (0.5, 0.5, 0.45, 1.0),
        'CURB': (0.8, 0.8, 0.8, 1.0),
        'DITCH': (0.4, 0.3, 0.2, 1.0),
        'MEDIAN': (0.2, 0.6, 0.2, 1.0),
        'SIDEWALK': (0.7, 0.7, 0.7, 1.0),
        'CUSTOM': (0.6, 0.6, 0.6, 1.0),
    }

    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return len(assembly.components) > 0

    def execute(self, context):
        import bmesh

        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]

        # Collection for preview objects
        collection_name = "Cross-Section Preview"
        if collection_name in bpy.data.collections:
            collection = bpy.data.collections[collection_name]
            # Clear existing preview objects
            for obj in list(collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
        else:
            collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(collection)

        # Calculate cross-section points for all components
        all_points = []

        # Sort components by side and offset for proper layout
        left_components = []
        right_components = []

        for comp in assembly.components:
            if comp.side == 'LEFT':
                left_components.append(comp)
            else:
                right_components.append(comp)

        # Process LEFT components (negative X direction)
        current_x = 0.0
        for comp in left_components:
            points = self._calculate_component_points(comp, current_x, direction=-1)
            if points:
                all_points.append((comp.component_type, points))
                current_x = points[-1][0]  # Update position for next component

        # Process RIGHT components (positive X direction)
        current_x = 0.0
        for comp in right_components:
            points = self._calculate_component_points(comp, current_x, direction=1)
            if points:
                all_points.append((comp.component_type, points))
                current_x = points[-1][0]

        # Create mesh objects for each component
        for idx, (comp_type, points) in enumerate(all_points):
            if len(points) < 2:
                continue

            # Create mesh
            mesh_name = f"Preview_{comp_type}_{idx}"
            mesh = bpy.data.meshes.new(mesh_name)
            obj = bpy.data.objects.new(mesh_name, mesh)
            collection.objects.link(obj)

            # Build geometry
            bm = bmesh.new()

            # Create vertices for the profile (as a line with thickness)
            thickness = 0.1  # Visual thickness for the preview

            # Top edge vertices
            top_verts = []
            for x, z in points:
                vert = bm.verts.new((x, 0.0, z))
                top_verts.append(vert)

            # Bottom edge vertices (for closed cross-section)
            bottom_verts = []
            for x, z in reversed(points):
                vert = bm.verts.new((x, 0.0, z - thickness))
                bottom_verts.append(vert)

            # Create face
            all_verts = top_verts + bottom_verts
            if len(all_verts) >= 3:
                try:
                    bm.faces.new(all_verts)
                except ValueError:
                    # Face creation failed, use edges instead
                    for i in range(len(top_verts) - 1):
                        bm.edges.new((top_verts[i], top_verts[i + 1]))

            bm.to_mesh(mesh)
            bm.free()

            # Apply material
            mat = self._get_or_create_material(comp_type)
            if mat:
                obj.data.materials.append(mat)

        # Also create a centerline marker
        centerline_mesh = bpy.data.meshes.new("Preview_Centerline")
        centerline_obj = bpy.data.objects.new("Preview_Centerline", centerline_mesh)
        collection.objects.link(centerline_obj)

        # Simple vertical line at origin
        verts = [(0, 0, -0.5), (0, 0, 0.5)]
        edges = [(0, 1)]
        centerline_mesh.from_pydata(verts, edges, [])

        # Frame the view on the preview
        try:
            # Select all preview objects
            for obj in collection.objects:
                obj.select_set(True)
                context.view_layer.objects.active = obj

            # Frame selected in view
            bpy.ops.view3d.view_selected(use_all_regions=False)
        except Exception:
            pass  # May fail if no 3D view is active

        # Ensure total width is updated
        update_assembly_total_width(assembly)

        self.report({'INFO'}, f"Generated preview with {len(all_points)} components")
        return {'FINISHED'}

    def _calculate_component_points(self, comp, start_x, direction=1):
        """
        Calculate 2D points for a component.

        Args:
            comp: Component properties
            start_x: Starting X position
            direction: 1 for right, -1 for left

        Returns:
            List of (x, z) tuples
        """
        points = []

        if comp.component_type == 'LANE':
            # Simple sloped lane
            points.append((start_x, 0.0))
            end_x = start_x + direction * comp.width
            end_z = comp.width * comp.cross_slope * direction
            points.append((end_x, end_z))

        elif comp.component_type == 'SHOULDER':
            # Similar to lane but with steeper slope
            points.append((start_x, 0.0))
            end_x = start_x + direction * comp.width
            end_z = comp.width * comp.cross_slope * direction
            points.append((end_x, end_z))

        elif comp.component_type == 'CURB':
            # Curb with vertical face
            points.append((start_x, 0.0))
            points.append((start_x, comp.curb_height))
            end_x = start_x + direction * comp.width
            points.append((end_x, comp.curb_height))
            points.append((end_x, 0.0))

        elif comp.component_type == 'DITCH':
            # Trapezoidal ditch
            start_z = 0.0  # Top of foreslope
            foreslope_width = comp.depth * comp.foreslope
            backslope_width = comp.depth * comp.backslope

            # Foreslope start
            points.append((start_x, start_z))
            # Bottom of foreslope
            fore_x = start_x + direction * foreslope_width
            points.append((fore_x, start_z - comp.depth))
            # Across bottom
            bottom_end_x = fore_x + direction * comp.bottom_width
            points.append((bottom_end_x, start_z - comp.depth))
            # Top of backslope
            back_x = bottom_end_x + direction * backslope_width
            points.append((back_x, start_z))

        elif comp.component_type == 'MEDIAN':
            # Raised or flush median
            points.append((start_x, 0.0))
            points.append((start_x, 0.15))  # Default raised height
            end_x = start_x + direction * comp.width
            points.append((end_x, 0.15))
            points.append((end_x, 0.0))

        elif comp.component_type == 'SIDEWALK':
            # Flat sidewalk
            points.append((start_x, 0.0))
            end_x = start_x + direction * comp.width
            end_z = comp.width * comp.cross_slope * direction
            points.append((end_x, end_z))

        else:
            # Generic component
            points.append((start_x, 0.0))
            end_x = start_x + direction * comp.width
            points.append((end_x, 0.0))

        return points

    def _get_or_create_material(self, component_type):
        """Get or create a material for a component type."""
        mat_name = f"Preview_{component_type}"

        if mat_name in bpy.data.materials:
            return bpy.data.materials[mat_name]

        # Create new material
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True

        color = self.COMPONENT_COLORS.get(component_type, (0.6, 0.6, 0.6, 1.0))

        if mat.node_tree:
            bsdf = mat.node_tree.nodes.get('Principled BSDF')
            if bsdf:
                bsdf.inputs['Base Color'].default_value = color
                bsdf.inputs['Roughness'].default_value = 0.8

        return mat


class BC_OT_ClearCrossSectionPreview(Operator):
    """
    Clear the cross-section preview from the 3D view.

    Removes all preview objects created by Generate Preview, cleaning up
    the scene when the preview is no longer needed.

    Usage:
        Called from the cross-section panel to clear the preview.
    """
    bl_idname = "bc.clear_cross_section_preview"
    bl_label = "Clear Preview"
    bl_description = "Clear the cross-section preview from the 3D view"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return "Cross-Section Preview" in bpy.data.collections

    def execute(self, context):
        collection_name = "Cross-Section Preview"

        if collection_name in bpy.data.collections:
            collection = bpy.data.collections[collection_name]
            # Remove all objects in the collection
            for obj in list(collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            # Remove the collection itself
            bpy.data.collections.remove(collection)

        self.report({'INFO'}, "Cleared cross-section preview")
        return {'FINISHED'}


# Registration
classes = (
    BC_OT_GenerateCrossSectionPreview,
    BC_OT_ClearCrossSectionPreview,
)


def register():
    """Register operator classes"""
    for cls in classes:
        bpy.utils.register_class(cls)

    logger.info("Cross-section preview operators registered")


def unregister():
    """Unregister operator classes"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    logger.info("Cross-section preview operators unregistered")
