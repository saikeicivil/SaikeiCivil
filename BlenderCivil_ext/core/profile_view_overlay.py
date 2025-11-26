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
BlenderCivil - Profile View Overlay Manager (Core)
===================================================

Manages the viewport overlay system for profile view visualization.
Handles draw handler registration and coordinates with renderer.

This follows BlenderCivil's architecture pattern:
- Core logic for overlay management
- Minimal Blender dependencies

Author: BlenderCivil Development Team
Date: November 2025
License: GPL v3
"""

import bpy

from .profile_view_data import ProfileViewData
from .profile_view_renderer import ProfileViewRenderer
from .logging_config import get_logger

logger = get_logger(__name__)


class ProfileViewOverlay:
    """
    Manages the profile view as an overlay at the bottom of the 3D viewport.
    
    Responsibilities:
        - Register/unregister draw handlers
        - Coordinate rendering with Blender's refresh cycle
        - Manage overlay state (enabled/disabled)
        - Define overlay dimensions
    
    This is the "glue" between the core rendering system and Blender's viewport.
    """
    
    def __init__(self):
        """Initialize overlay manager"""
        self.data = ProfileViewData()
        self.renderer = ProfileViewRenderer()
        self.draw_handle = None
        self.enabled = False

        # Overlay dimensions
        self.overlay_height = 200  # pixels (resizable from bottom of viewport)

        # Resize interaction state
        self.is_resizing = False
        self.hover_resize_border = False
        self.resize_start_height = 0
        self.resize_start_mouse_y = 0
        self.resize_border_thickness = 8  # pixels to detect hover
        self.min_height = 100  # minimum overlay height
        self.max_height = 600  # maximum overlay height
    
    def enable(self, context):
        """
        Enable the profile view overlay.
        
        Args:
            context: Blender context
        """
        if not self.enabled:
            # Register draw handler for 3D viewport
            # This will be called every time the viewport refreshes
            self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                self._draw_callback,
                (context,),
                'WINDOW',
                'POST_PIXEL'
            )
            self.enabled = True

            # Load vertical alignments if any were loaded from IFC
            self._load_vertical_alignments_from_manager()

            # Force viewport redraw
            if context.area:
                context.area.tag_redraw()
    
    def disable(self, context):
        """
        Disable the profile view overlay.
        
        Args:
            context: Blender context
        """
        if self.enabled and self.draw_handle:
            # Unregister draw handler
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'WINDOW')
            self.draw_handle = None
            self.enabled = False
            
            # Force viewport redraw
            if context.area:
                context.area.tag_redraw()
    
    def toggle(self, context):
        """
        Toggle overlay on/off.
        
        Args:
            context: Blender context
        """
        if self.enabled:
            self.disable(context)
        else:
            self.enable(context)
    
    def _draw_callback(self, context):
        """
        Draw callback - invoked by Blender every frame.

        Args:
            context: Blender context

        Note:
            This is called automatically by Blender's draw handler system.
            Do not call directly.
        """
        if not self.enabled:
            return

        # Get viewport dimensions
        area = context.area
        region = context.region

        if not region or not area:
            return

        # Set renderer region (bottom strip of viewport)
        x = 0
        y = 0
        width = region.width
        height = self.overlay_height

        self.renderer.set_view_region(x, y, width, height)

        # Render profile view
        self.renderer.render(self.data)

        # Draw resize border indicator when hovering or resizing
        if self.hover_resize_border or self.is_resizing:
            self._draw_resize_border(region, height)
    
    def refresh(self, context):
        """
        Force a viewport refresh.
        
        Args:
            context: Blender context
        """
        if context.area:
            context.area.tag_redraw()
    
    def get_status(self) -> str:
        """
        Get overlay status as string.

        Returns:
            Status description
        """
        if self.enabled:
            return f"ENABLED - {len(self.data.pvis)} PVIs, " \
                   f"{len(self.data.terrain_points)} terrain pts"
        else:
            return "DISABLED"

    def _load_vertical_alignments_from_manager(self):
        """
        Load vertical alignments from NativeIfcManager into profile view.

        This is called when the profile view is enabled, to check if
        any vertical alignments were loaded from an IFC file.
        """
        try:
            from .native_ifc_manager import NativeIfcManager

            if NativeIfcManager.vertical_alignments:
                logger.info("Loading %s vertical alignments from IFC...", len(NativeIfcManager.vertical_alignments))

                # Clear existing vertical alignments
                self.data.clear_vertical_alignments()

                # Add each vertical alignment
                for valign in NativeIfcManager.vertical_alignments:
                    self.data.add_vertical_alignment(valign)
                    logger.info("  Added %s", valign.name)

                # Auto-select first vertical alignment
                if len(NativeIfcManager.vertical_alignments) > 0:
                    self.data.select_vertical_alignment(0)
                    logger.info("  Selected %s as active", NativeIfcManager.vertical_alignments[0].name)

                # Update view extents
                self.data.update_view_extents()

                logger.info("Loaded vertical alignments into profile view")

        except Exception as e:
            logger.debug("Note: Could not load vertical alignments: %s", e)

    def is_mouse_over_resize_border(self, context, mouse_x: int, mouse_y: int) -> bool:
        """
        Check if mouse is hovering over the resize border (top edge of overlay).

        Args:
            context: Blender context
            mouse_x: Mouse X coordinate in region space
            mouse_y: Mouse Y coordinate in region space

        Returns:
            True if mouse is over resize border
        """
        if not self.enabled:
            return False

        # The resize border is at the top edge of the overlay
        border_y = self.overlay_height

        # Check if mouse Y is within the border thickness zone
        return abs(mouse_y - border_y) <= self.resize_border_thickness

    def handle_mouse_move(self, context, event):
        """
        Handle mouse movement for resize interaction.

        Args:
            context: Blender context
            event: Mouse event
        """
        if not self.enabled:
            return False

        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y

        # Update hover state
        self.hover_resize_border = self.is_mouse_over_resize_border(context, mouse_x, mouse_y)

        # Handle active resizing
        if self.is_resizing:
            # Calculate new height based on mouse movement
            delta_y = mouse_y - self.resize_start_mouse_y
            new_height = self.resize_start_height + delta_y

            # Clamp to min/max
            new_height = max(self.min_height, min(self.max_height, new_height))

            self.overlay_height = new_height

            # Update property if available
            if hasattr(context.scene, 'bc_profile_view_props'):
                context.scene.bc_profile_view_props.overlay_height = int(new_height)

            # Force redraw
            if context.area:
                context.area.tag_redraw()

            return True

        # Change cursor when hovering over border
        if self.hover_resize_border:
            context.window.cursor_set('MOVE_Y')
            return True
        else:
            context.window.cursor_set('DEFAULT')

        return False

    def handle_mouse_press(self, context, event):
        """
        Handle mouse button press for starting resize.

        Args:
            context: Blender context
            event: Mouse event

        Returns:
            True if event was handled
        """
        if not self.enabled:
            return False

        if self.hover_resize_border and event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Start resizing
            self.is_resizing = True
            self.resize_start_height = self.overlay_height
            self.resize_start_mouse_y = event.mouse_region_y
            return True

        return False

    def handle_mouse_release(self, context, event):
        """
        Handle mouse button release for ending resize.

        Args:
            context: Blender context
            event: Mouse event

        Returns:
            True if event was handled
        """
        if self.is_resizing and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            # End resizing
            self.is_resizing = False
            context.window.cursor_set('DEFAULT')
            return True

        return False

    def _draw_resize_border(self, region, height):
        """
        Draw a visual indicator for the resize border.

        Args:
            region: Blender region
            height: Current overlay height
        """
        import gpu
        from gpu_extras.batch import batch_for_shader

        # Create a highlighted line at the top of the overlay
        border_y = height
        border_color = (0.3, 0.6, 1.0, 0.8) if self.is_resizing else (0.5, 0.5, 0.5, 0.6)

        # Draw a thick line across the top
        vertices = [
            (0, border_y - 1),
            (region.width, border_y - 1),
            (region.width, border_y + 1),
            (0, border_y + 1)
        ]

        indices = [(0, 1, 2), (0, 2, 3)]

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)

        shader.bind()
        shader.uniform_float("color", border_color)

        gpu.state.blend_set('ALPHA')
        batch.draw(shader)
        gpu.state.blend_set('NONE')


# ============================================================================
# GLOBAL OVERLAY INSTANCE
# ============================================================================

# Singleton pattern - one overlay per Blender session
_profile_overlay_instance = None


def get_profile_overlay() -> ProfileViewOverlay:
    """
    Get or create the global profile overlay instance (singleton).
    
    Returns:
        ProfileViewOverlay instance
    
    Note:
        This ensures only one overlay exists at a time.
        Operators and UI can access this to interact with the overlay.
    """
    global _profile_overlay_instance
    
    if _profile_overlay_instance is None:
        _profile_overlay_instance = ProfileViewOverlay()
    
    return _profile_overlay_instance


def reset_profile_overlay():
    """
    Reset the global profile overlay instance.
    
    Note:
        Call this when Blender restarts or when you want to clear all data.
    """
    global _profile_overlay_instance
    
    # Disable if currently enabled
    if _profile_overlay_instance and _profile_overlay_instance.enabled:
        import bpy
        _profile_overlay_instance.disable(bpy.context)
    
    _profile_overlay_instance = None


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def load_from_sprint3_vertical(context) -> bool:
    """
    Load profile data from Sprint 3 vertical alignment properties.
    
    Args:
        context: Blender context
        
    Returns:
        True if loaded successfully, False otherwise
    """
    overlay = get_profile_overlay()
    
    # Check if Sprint 3 vertical alignment exists
    if not hasattr(context.scene, 'bc_vertical'):
        return False
    
    v_props = context.scene.bc_vertical
    
    # Clear existing data
    overlay.data.clear_alignment()
    
    # Load PVIs from Sprint 3
    for pvi_prop in v_props.pvis:
        metadata = {
            'curve_length': pvi_prop.curve_length,
            'incoming_grade': pvi_prop.incoming_grade,
            'outgoing_grade': pvi_prop.outgoing_grade,
        }
        
        if hasattr(pvi_prop, 'k_value'):
            metadata['k_value'] = pvi_prop.k_value
        
        overlay.data.add_pvi(
            pvi_prop.station,
            pvi_prop.elevation,
            metadata
        )
    
    # Load segments to create smooth alignment profile
    for segment_prop in v_props.segments:
        # Sample points along segment for smooth display
        import numpy as np
        
        num_points = 20 if segment_prop.segment_type == 'CURVE' else 2
        stations = np.linspace(
            segment_prop.start_station,
            segment_prop.end_station,
            num_points
        )
        
        for station in stations:
            # Linear interpolation (Sprint 3 has better elevation calculator)
            t = (station - segment_prop.start_station) / segment_prop.length
            elevation = (
                segment_prop.start_elevation * (1 - t) +
                segment_prop.end_elevation * t
            )
            
            overlay.data.add_alignment_point(station, elevation)
    
    # Update view extents
    overlay.data.update_view_extents()
    
    return True


def sync_to_sprint3_vertical(context) -> bool:
    """
    Write profile data back to Sprint 3 vertical alignment properties.
    
    Args:
        context: Blender context
        
    Returns:
        True if synced successfully, False otherwise
    """
    overlay = get_profile_overlay()
    
    # Check if Sprint 3 vertical alignment exists
    if not hasattr(context.scene, 'bc_vertical'):
        return False
    
    v_props = context.scene.bc_vertical
    
    # Clear existing PVIs
    v_props.pvis.clear()
    
    # Add updated PVIs
    for pvi in overlay.data.pvis:
        pvi_prop = v_props.pvis.add()
        pvi_prop.station = pvi.station
        pvi_prop.elevation = pvi.elevation
        
        # Transfer metadata
        if 'curve_length' in pvi.metadata:
            pvi_prop.curve_length = pvi.metadata['curve_length']
        
        # Note: incoming/outgoing grades will be recalculated by Sprint 3
    
    # Trigger Sprint 3 segment regeneration
    # (This operator should exist from Sprint 3)
    if hasattr(bpy.ops.blendercivil, 'generate_vertical_segments'):
        bpy.ops.blendercivil.generate_vertical_segments()
    
    return True


if __name__ == "__main__":
    logger.info("ProfileViewOverlay - Core overlay manager")
    logger.info("Use from within Blender for testing.")
