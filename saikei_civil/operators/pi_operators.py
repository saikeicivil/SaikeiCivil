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
Interactive PI Operations
==========================

Provides interactive operators for adding and managing Point of Intersections (PIs)
in horizontal alignments. PIs represent pure tangent intersection points without
radius properties - curves are added separately between adjacent tangents.

Creates IFC entities and Blender visualizations in real-time as the user clicks
in the viewport, providing immediate visual feedback for alignment design.

Operators:
    BC_OT_add_pi_interactive: Add PIs by clicking in viewport with real-time visualization
    BC_OT_add_native_pi: Add PI at 3D cursor location (classic method)
    BC_OT_delete_native_pi: Delete the selected PI marker from scene and IFC
"""

import bpy
import gpu
import blf
import math
from bpy.props import StringProperty, FloatProperty, IntProperty, BoolProperty
from mathutils import Vector
from gpu_extras.batch import batch_for_shader
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class BC_OT_add_pi_interactive(bpy.types.Operator):
    """Add PIs by clicking in the viewport with real-time visualization.

    Modal operator that allows users to place Point of Intersections (PIs) by clicking
    directly in the 3D viewport. Each click creates an IFC entity and visual marker
    immediately. Tangent lines are automatically created between consecutive PIs and
    visualized in real-time.

    Modal States:
        - RUNNING_MODAL: Tracking mouse movement and waiting for user input
        - Mouse move: Updates cursor feedback and crosshair position
        - Left click: Places PI at mouse position on XY plane (Z=0)
        - Right click/Enter: Finishes placement and exits modal mode
        - ESC: Cancels operation

    Internal State:
        _handle: Drawing handler for HUD overlay
        _alignment_obj: Active NativeIfcAlignment instance
        _visualizer: AlignmentVisualizer for real-time updates
        _last_mouse_pos: Current mouse position for cursor feedback

    Usage:
        Requires an active alignment. Enters modal mode with on-screen instructions.
        Each PI is immediately added to IFC and visualized. Tangent segments are
        created between consecutive PIs automatically.
    """
    bl_idname = "bc.add_pi_interactive"
    bl_label = "Add PI (Click to Place)"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Internal state
    _handle = None
    _alignment_obj = None  # NativeIfcAlignment instance
    _visualizer = None     # AlignmentVisualizer instance
    _last_mouse_pos = None
    
    def modal(self, context, event):
        context.area.tag_redraw()
        
        # Track mouse position for visual feedback
        if event.type == 'MOUSEMOVE':
            self._last_mouse_pos = (event.mouse_region_x, event.mouse_region_y)
            return {'RUNNING_MODAL'}
        
        # Left click - Place PI (immediate placement with visualization!)
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Get 3D location from mouse click
            location = self.get_3d_location_from_mouse(context, event)
            if location:
                # Add PI immediately with visualization
                self.add_pi_at_location(location)
            return {'RUNNING_MODAL'}
        
        # Right click or ENTER - Finish
        if event.type in {'RIGHTMOUSE', 'RET'} and event.value == 'PRESS':
            self.finish(context)
            return {'FINISHED'}
        
        # ESC - Cancel
        if event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}
        
        return {'RUNNING_MODAL'}
    
    def invoke(self, context, event):
        # Validate prerequisites
        from . import NativeIfcManager
        from ..ui.alignment_properties import get_active_alignment_ifc, refresh_alignment_list
        from ..core.alignment_registry import get_or_create_alignment, get_or_create_visualizer
        
        # Check for IFC file
        ifc = NativeIfcManager.get_file()
        if not ifc:
            self.report({'ERROR'}, "No IFC file. Create an IFC file first.")
            return {'CANCELLED'}
        
        # Refresh alignment list
        refresh_alignment_list(context)
        
        # Check for active alignment
        active_alignment = get_active_alignment_ifc(context)
        if not active_alignment:
            # Try to get any alignment
            alignments = ifc.by_type("IfcAlignment")
            if not alignments:
                self.report({'ERROR'}, "No alignment found. Create an alignment first.")
                return {'CANCELLED'}
            
            # Set first alignment as active
            from ..ui.alignment_properties import set_active_alignment
            set_active_alignment(context, alignments[0])
            active_alignment = alignments[0]
            self.report({'INFO'}, f"Set {active_alignment.Name} as active alignment")
        
        # Get or create the Python alignment instance and visualizer
        self._alignment_obj, was_created = get_or_create_alignment(active_alignment)
        self._visualizer, vis_created = get_or_create_visualizer(self._alignment_obj)

        # CRITICAL: Store visualizer on alignment so update handler can access it!
        self._alignment_obj.visualizer = self._visualizer

        if was_created:
            logger.info("Created new alignment instance")
        if vis_created:
            logger.info("Created new visualizer")
        
        # Setup drawing handler for HUD
        args = (self, context)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
        
        context.window_manager.modal_handler_add(self)
        
        align_name = context.scene.bc_alignment.active_alignment_name
        self.report({'INFO'}, f"Interactive PI Mode [{align_name}] - Click to place, Enter/RMB to finish, ESC to cancel")
        return {'RUNNING_MODAL'}
    
    def get_3d_location_from_mouse(self, context, event):
        """Convert mouse position to 3D coordinates on XY plane (Z=0)"""
        region = context.region
        rv3d = context.region_data
        
        # Get mouse position in region coordinates
        coord = (event.mouse_region_x, event.mouse_region_y)
        
        # Use view3d_utils for proper 3D projection
        from bpy_extras import view3d_utils
        
        # Get ray from mouse
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        
        # Intersect with Z=0 plane
        if abs(view_vector.z) > 0.0001:  # Avoid division by zero
            t = -ray_origin.z / view_vector.z
            if t >= 0:  # Only forward intersections
                intersection = ray_origin + t * view_vector
                return Vector((intersection.x, intersection.y, 0))
        
        return None
    
    def add_pi_at_location(self, location):
        """Add PI at location with immediate visualization but deferred IFC geometry.

        OPTIMIZATION: We defer segment regeneration until the user finishes placing
        all PIs. This prevents creating thousands of intermediate entities that would
        be deleted and recreated with each PI placement.
        """

        if not self._alignment_obj or not self._visualizer:
            self.report({'ERROR'}, "Alignment or visualizer not initialized")
            return

        # Add PI to alignment WITHOUT regenerating segments (deferred to finish())
        # This avoids creating/deleting thousands of intermediate entities
        pi_data = self._alignment_obj.add_pi(location.x, location.y, regenerate=False)

        # Create visual marker immediately (just the PI point, not geometry)
        pi_marker = self._visualizer.create_pi_object(pi_data)

        # Note: We don't visualize tangent segments during placement anymore
        # because regenerate_segments() is deferred. The tangents will appear
        # when the user finishes placement.

        pi_count = len(self._alignment_obj.pis)
        self.report({'INFO'}, f"[+] PI {pi_count} at ({location.x:.2f}, {location.y:.2f})")

        logger.debug("Added PI %d at (%.2f, %.2f)", pi_count, location.x, location.y)
        logger.debug("Total segments: %d", len(self._alignment_obj.segments))
    
    def draw_callback_px(self, operator, context):
        """Draw on-screen instructions, preview tangent lines, and visual feedback.

        PREVIEW LINES: We draw tangent lines using GPU primitives instead of
        creating IFC/Blender geometry. This provides real-time visual feedback
        without creating thousands of intermediate entities.
        """
        from bpy_extras import view3d_utils

        font_id = 0
        region = context.region
        rv3d = context.region_data

        # Draw instructions box
        blf.position(font_id, 15, 80, 0)
        blf.size(font_id, 22)
        blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
        blf.draw(font_id, "[PI] Place Tangent Points (PIs)")

        blf.position(font_id, 15, 55, 0)
        blf.size(font_id, 14)
        blf.color(font_id, 0.9, 0.9, 0.9, 1.0)
        blf.draw(font_id, "Left Click: Place PI (immediate!)")

        blf.position(font_id, 15, 38, 0)
        blf.draw(font_id, "[OK] Enter / Right Click: Finish")

        blf.position(font_id, 15, 21, 0)
        blf.draw(font_id, "[X] ESC: Cancel")

        # Show point count if any points placed
        if self._alignment_obj and len(self._alignment_obj.pis) > 0:
            pi_count = len(self._alignment_obj.pis)
            blf.position(font_id, context.region.width - 180, 45, 0)
            blf.size(font_id, 18)
            blf.color(font_id, 0.3, 1.0, 0.4, 1.0)
            blf.draw(font_id, f"PIs Placed: {pi_count}")

            # Show last PI coordinates
            last_pi = self._alignment_obj.pis[-1]
            blf.position(font_id, context.region.width - 180, 25, 0)
            blf.size(font_id, 13)
            blf.color(font_id, 0.8, 0.8, 0.8, 1.0)
            blf.draw(font_id, f"Last: ({last_pi['position'].x:.1f}, {last_pi['position'].y:.1f})")

        # ============================================================
        # PREVIEW TANGENT LINES - GPU drawing, no IFC entities!
        # ============================================================
        if self._alignment_obj and len(self._alignment_obj.pis) >= 1:
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            shader.bind()

            gpu.state.blend_set('ALPHA')
            gpu.state.line_width_set(2.5)

            # Convert PI 3D positions to 2D screen coordinates
            pi_screen_coords = []
            for pi in self._alignment_obj.pis:
                pos_3d = Vector((pi['position'].x, pi['position'].y, 0.0))
                pos_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, pos_3d)
                if pos_2d:
                    pi_screen_coords.append(pos_2d)

            # Draw tangent lines between consecutive PIs (yellow preview)
            if len(pi_screen_coords) >= 2:
                shader.uniform_float("color", (1.0, 0.9, 0.2, 0.8))  # Yellow for tangents
                line_vertices = []
                for i in range(len(pi_screen_coords) - 1):
                    line_vertices.append((pi_screen_coords[i].x, pi_screen_coords[i].y))
                    line_vertices.append((pi_screen_coords[i + 1].x, pi_screen_coords[i + 1].y))

                batch = batch_for_shader(shader, 'LINES', {"pos": line_vertices})
                batch.draw(shader)

            # Draw "rubber band" line from last PI to current mouse position
            if pi_screen_coords and self._last_mouse_pos:
                shader.uniform_float("color", (1.0, 0.9, 0.2, 0.5))  # Dimmer yellow
                last_pi_2d = pi_screen_coords[-1]
                rubber_band = [
                    (last_pi_2d.x, last_pi_2d.y),
                    self._last_mouse_pos
                ]
                batch = batch_for_shader(shader, 'LINES', {"pos": rubber_band})
                batch.draw(shader)

            # Draw PI markers (circles at each PI position)
            shader.uniform_float("color", (0.3, 1.0, 0.4, 0.9))  # Green for PIs
            for pos_2d in pi_screen_coords:
                circle_segments = 16
                circle_radius = 6
                circle_vertices = []
                for i in range(circle_segments + 1):
                    angle = 2 * math.pi * i / circle_segments
                    circle_vertices.append((
                        pos_2d.x + circle_radius * math.cos(angle),
                        pos_2d.y + circle_radius * math.sin(angle)
                    ))
                batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": circle_vertices})
                batch.draw(shader)

            gpu.state.blend_set('NONE')

        # Draw crosshair cursor at mouse position
        if self._last_mouse_pos:
            x, y = self._last_mouse_pos

            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            shader.bind()
            shader.uniform_float("color", (0.3, 1.0, 0.4, 0.9))  # Green for PIs

            gpu.state.blend_set('ALPHA')
            gpu.state.line_width_set(2.0)

            # Draw crosshair
            size = 15
            vertices = [
                (x - size, y), (x + size, y),  # Horizontal
                (x, y - size), (x, y + size)   # Vertical
            ]
            batch = batch_for_shader(shader, 'LINES', {"pos": vertices})
            batch.draw(shader)

            # Draw circle at cursor
            circle_segments = 24
            circle_vertices = []
            circle_radius = 8
            for i in range(circle_segments + 1):
                angle = 2 * math.pi * i / circle_segments
                circle_vertices.append((
                    x + circle_radius * math.cos(angle),
                    y + circle_radius * math.sin(angle)
                ))

            batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": circle_vertices})
            batch.draw(shader)

            gpu.state.blend_set('NONE')
    
    def finish(self, context):
        """Finish interactive mode - regenerate segments ONCE at the end."""
        # Remove drawing handler
        if self._handle:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')

        if self._alignment_obj:
            pi_count = len(self._alignment_obj.pis)

            if pi_count >= 2:
                # NOW regenerate segments - only once for all PIs!
                # This is the key optimization - instead of regenerating N times
                # (once per PI), we regenerate once at the end.
                self._alignment_obj.regenerate_segments()

                # Update visualization for all segments
                if self._visualizer:
                    self._visualizer.update_all()

                segment_count = len(self._alignment_obj.segments)
                self.report({'INFO'}, f"[OK] Placed {pi_count} PIs, created {segment_count} segments")
                logger.info("Finished: %d PIs, %d segments in IFC", pi_count, segment_count)
            elif pi_count == 1:
                self.report({'INFO'}, f"[OK] Placed 1 PI (need 2+ for segments)")
            else:
                self.report({'WARNING'}, "No PIs placed")

        context.area.tag_redraw()
    
    def cancel(self, context):
        """Cancel interactive mode"""
        if self._handle:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
        
        # TODO: Could implement undo here - remove PIs added during this session
        
        self.report({'INFO'}, "PI placement cancelled")
        context.area.tag_redraw()


# Keep original operator for backward compatibility
class BC_OT_add_native_pi(bpy.types.Operator):
    """Add PI at 3D cursor location (classic method).

    Non-interactive operator that places a Point of Intersection at the current
    3D cursor position. Creates IFC entity and visualization marker, then updates
    tangent segments if multiple PIs exist.

    This is the traditional placement method, as opposed to the interactive click-to-place
    mode. Useful for precise placement when cursor position is set programmatically
    or snapped to specific locations.

    Requirements:
        - Active alignment must be set
        - 3D cursor position determines PI location (X, Y coordinates used)

    Usage:
        Position 3D cursor at desired location, then invoke this operator to
        place PI. Tangent visualization updates automatically if 2+ PIs exist.
    """
    bl_idname = "bc.add_native_pi"
    bl_label = "Add PI at Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    
    # NO RADIUS PROPERTY!
    
    def execute(self, context):
        from . import NativeIfcManager
        from ..ui.alignment_properties import get_active_alignment_ifc
        from ..core.alignment_registry import get_or_create_alignment, get_or_create_visualizer
        
        cursor = context.scene.cursor.location
        
        # Get active alignment
        active_alignment = get_active_alignment_ifc(context)
        if not active_alignment:
            self.report({'ERROR'}, "No active alignment. Create an alignment first.")
            return {'CANCELLED'}
        
        # Get alignment instance
        alignment_obj, _ = get_or_create_alignment(active_alignment)
        visualizer, _ = get_or_create_visualizer(alignment_obj)
        
        # Add PI - no radius!
        pi_data = alignment_obj.add_pi(cursor.x, cursor.y)
        
        # Create visualization
        visualizer.create_pi_object(pi_data)
        
        # Update tangent visualization if we have 2+ PIs
        # Note: segments[-1] is the zero-length Endpoint (BSI ALB015),
        # so get second-to-last for the actual tangent
        if len(alignment_obj.pis) >= 2 and len(alignment_obj.segments) >= 2:
            tangent_segment = alignment_obj.segments[-2]
            visualizer.create_segment_curve(tangent_segment)
        
        self.report({'INFO'}, f"Added PI at ({cursor.x:.2f}, {cursor.y:.2f})")
        return {'FINISHED'}


class BC_OT_delete_native_pi(bpy.types.Operator):
    """Delete the selected PI marker from scene and IFC.

    Removes a Point of Intersection marker object from the Blender scene. The operator
    validates that the selected object is a PI marker by checking for the "ifc_pi_id"
    custom property.

    Requirements:
        - Active object must be a PI marker with "ifc_pi_id" custom property

    Note:
        Current implementation removes the Blender object but does not fully update
        the IFC alignment structure. Full implementation should regenerate segments
        and update visualization after PI removal.

    Usage:
        Select a PI marker object in the viewport and invoke to delete it.
    """
    bl_idname = "bc.delete_native_pi"
    bl_label = "Delete PI"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or "ifc_pi_id" not in obj:
            self.report({'ERROR'}, "Select a PI marker")
            return {'CANCELLED'}
        
        # Remove from scene
        bpy.data.objects.remove(obj, do_unlink=True)
        
        # Note: Full implementation needs to update IFC alignment
        self.report({'INFO'}, "Deleted PI")
        return {'FINISHED'}


# Registration
classes = (
    BC_OT_add_pi_interactive,
    BC_OT_add_native_pi,
    BC_OT_delete_native_pi,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
