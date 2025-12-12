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
Cross-Section View Overlay Manager (Tool Layer)
=================================================

Manages the viewport overlay system for cross-section view visualization.
Handles draw handler registration and coordinates with renderer.

Following the OpenRoads approach where cross-sections are visualized
in a dedicated viewer, not in the 3D model space.

Supports multiple anchor positions and drag-to-move functionality.

This module is part of Layer 2 (Tool) in the three-layer architecture,
containing Blender-specific overlay management.
"""

import bpy
import gpu
import blf
from gpu_extras.batch import batch_for_shader
from enum import Enum

from ..core.cross_section_view_data import CrossSectionViewData, ComponentType
from ..core.cross_section_view_renderer import CrossSectionViewRenderer
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class OverlayPosition(Enum):
    """Anchor positions for the overlay"""
    BOTTOM = "BOTTOM"      # Anchored to bottom edge (default)
    TOP = "TOP"            # Anchored to top edge
    LEFT = "LEFT"          # Anchored to left edge (vertical orientation)
    RIGHT = "RIGHT"        # Anchored to right edge (vertical orientation)
    FLOATING = "FLOATING"  # Free-floating, draggable


class ResizeEdge(Enum):
    """Which edge is being resized (for floating mode)"""
    NONE = "NONE"          # Not resizing
    RIGHT = "RIGHT"        # Right edge (horizontal resize)
    BOTTOM = "BOTTOM"      # Bottom edge (vertical resize)
    CORNER = "CORNER"      # Bottom-right corner (both dimensions)


class CrossSectionViewOverlay:
    """
    Manages the cross-section view as an overlay in the 3D viewport.

    Responsibilities:
        - Register/unregister draw handlers
        - Coordinate rendering with Blender's refresh cycle
        - Manage overlay state (enabled/disabled)
        - Define overlay dimensions and position
        - Handle resize and drag-to-move interaction

    This is the "glue" between the core rendering system and Blender's viewport.
    """

    # Title bar height for floating mode
    TITLE_BAR_HEIGHT = 24

    def __init__(self):
        """Initialize overlay manager"""
        self.data = CrossSectionViewData()
        self.renderer = CrossSectionViewRenderer()
        self.draw_handle = None
        self.enabled = False

        # Position and anchor
        self.position = OverlayPosition.BOTTOM
        self.floating_x = 50    # X position when floating (from left)
        self.floating_y = 50    # Y position when floating (from bottom)

        # Overlay dimensions
        self.overlay_width = 600   # Width (used for floating/left/right)
        self.overlay_height = 300  # Height (used for bottom/top/floating)

        # Resize interaction state
        self.is_resizing = False
        self.hover_resize_border = False
        self.resize_edge = ResizeEdge.NONE      # Which edge is being hovered/resized
        self.active_resize_edge = ResizeEdge.NONE  # Edge being actively resized
        self.resize_start_width = 0
        self.resize_start_height = 0
        self.resize_start_mouse_x = 0
        self.resize_start_mouse_y = 0
        self.resize_border_thickness = 8  # pixels to detect hover
        self.corner_size = 16  # Corner detection area size
        self.min_width = 300
        self.min_height = 150
        self.max_width = 1200
        self.max_height = 600

        # Drag interaction state (for floating mode)
        self.is_dragging = False
        self.hover_title_bar = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_start_overlay_x = 0
        self.drag_start_overlay_y = 0

    def enable(self, context):
        """
        Enable the cross-section view overlay.

        Args:
            context: Blender context
        """
        if not self.enabled:
            # Register draw handler for 3D viewport
            self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                self._draw_callback,
                (context,),
                'WINDOW',
                'POST_PIXEL'
            )
            self.enabled = True

            logger.info("Cross-section view overlay enabled")

            # Force viewport redraw
            if context.area:
                context.area.tag_redraw()

    def disable(self, context):
        """
        Disable the cross-section view overlay.

        Args:
            context: Blender context
        """
        if self.enabled and self.draw_handle:
            # Unregister draw handler
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'WINDOW')
            self.draw_handle = None
            self.enabled = False

            logger.info("Cross-section view overlay disabled")

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

    def set_position(self, position: OverlayPosition):
        """
        Set the overlay anchor position.

        Args:
            position: OverlayPosition enum value
        """
        self.position = position
        logger.info(f"Overlay position set to: {position.value}")

    def get_overlay_rect(self, region) -> tuple:
        """
        Calculate the overlay rectangle based on current position.

        Args:
            region: Blender region

        Returns:
            (x, y, width, height) tuple for overlay position
        """
        if self.position == OverlayPosition.BOTTOM:
            return (0, 0, region.width, self.overlay_height)

        elif self.position == OverlayPosition.TOP:
            y = region.height - self.overlay_height
            return (0, y, region.width, self.overlay_height)

        elif self.position == OverlayPosition.LEFT:
            return (0, 0, self.overlay_width, region.height)

        elif self.position == OverlayPosition.RIGHT:
            x = region.width - self.overlay_width
            return (x, 0, self.overlay_width, region.height)

        elif self.position == OverlayPosition.FLOATING:
            # Clamp to viewport bounds
            x = max(0, min(self.floating_x, region.width - self.overlay_width))
            y = max(0, min(self.floating_y, region.height - self.overlay_height - self.TITLE_BAR_HEIGHT))
            return (x, y, self.overlay_width, self.overlay_height)

        # Default to bottom
        return (0, 0, region.width, self.overlay_height)

    def _draw_callback(self, context):
        """
        Draw callback - invoked by Blender every frame.

        Args:
            context: Blender context
        """
        if not self.enabled:
            return

        # Get viewport dimensions
        area = context.area
        region = context.region

        if not region or not area:
            return

        # Calculate overlay position
        x, y, width, height = self.get_overlay_rect(region)

        # For floating mode, add title bar height to total
        total_height = height
        if self.position == OverlayPosition.FLOATING:
            total_height = height + self.TITLE_BAR_HEIGHT
            # Draw title bar first
            self._draw_title_bar(x, y + height, width)

        # Set renderer region
        self.renderer.set_view_region(x, y, width, height)

        # Render cross-section view
        self.renderer.render(self.data)

        # Draw resize border indicator when hovering or resizing
        if self.hover_resize_border or self.is_resizing:
            self._draw_resize_border_at_position(region, x, y, width, height)

        # Draw drag indicator when hovering title bar or dragging
        if self.position == OverlayPosition.FLOATING and (self.hover_title_bar or self.is_dragging):
            self._draw_drag_indicator(x, y + height, width)

    def _draw_title_bar(self, x: float, y: float, width: float):
        """
        Draw title bar for floating mode.

        Args:
            x, y: Bottom-left of title bar
            width: Width of title bar
        """
        # Title bar background
        vertices = [
            (x, y),
            (x + width, y),
            (x + width, y + self.TITLE_BAR_HEIGHT),
            (x, y + self.TITLE_BAR_HEIGHT)
        ]

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})

        shader.bind()
        # Darker background for title bar
        bg_color = (0.18, 0.18, 0.18, 0.98)
        shader.uniform_float("color", bg_color)

        gpu.state.blend_set('ALPHA')
        batch.draw(shader)

        # Title text
        font_id = 0
        blf.size(font_id, 12)
        blf.color(font_id, 1.0, 1.0, 1.0, 1.0)

        title = "Cross-Section Viewer"
        if self.data.assembly_name:
            title = f"Cross-Section: {self.data.assembly_name}"

        text_width, text_height = blf.dimensions(font_id, title)
        text_x = x + 10
        text_y = y + (self.TITLE_BAR_HEIGHT - text_height) / 2

        blf.position(font_id, text_x, text_y, 0)
        blf.draw(font_id, title)

        # Draw grip indicator (drag handle)
        grip_x = x + width - 30
        grip_y = y + self.TITLE_BAR_HEIGHT / 2
        self._draw_grip_icon(grip_x, grip_y)

        gpu.state.blend_set('NONE')

    def _draw_grip_icon(self, x: float, y: float):
        """Draw a grip/drag icon (three horizontal lines)"""
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        shader.bind()
        shader.uniform_float("color", (0.6, 0.6, 0.6, 0.8))

        gpu.state.blend_set('ALPHA')

        for i in range(3):
            line_y = y - 4 + (i * 4)
            vertices = [
                (x, line_y),
                (x + 20, line_y),
                (x + 20, line_y + 2),
                (x, line_y + 2)
            ]
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
            batch.draw(shader)

    def _draw_drag_indicator(self, x: float, y: float, width: float):
        """
        Draw indicator when title bar is hovered or being dragged.

        Args:
            x, y: Title bar position
            width: Title bar width
        """
        border_color = (0.3, 0.6, 1.0, 0.8) if self.is_dragging else (0.5, 0.7, 1.0, 0.5)

        # Draw border around title bar
        vertices = [
            (x, y),
            (x + width, y),
            (x + width, y + self.TITLE_BAR_HEIGHT),
            (x, y + self.TITLE_BAR_HEIGHT),
            (x, y)  # Close the loop
        ]

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": vertices})

        shader.bind()
        shader.uniform_float("color", border_color)

        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(2.0)
        batch.draw(shader)
        gpu.state.line_width_set(1.0)
        gpu.state.blend_set('NONE')

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
            return f"ENABLED - {len(self.data.components)} components"
        else:
            return "DISABLED"

    def load_from_assembly(self, assembly_props) -> bool:
        """
        Load cross-section data from Blender assembly properties.

        Args:
            assembly_props: BC_AssemblyProperties from Blender

        Returns:
            True if loaded successfully
        """
        result = self.data.load_from_assembly(assembly_props)
        if result:
            logger.info("Loaded assembly '%s' into cross-section viewer",
                       self.data.assembly_name)
        return result

    def is_mouse_over_resize_border(self, context, mouse_x: int, mouse_y: int) -> bool:
        """
        Check if mouse is hovering over the resize border.
        Also sets self.resize_edge to indicate which edge is being hovered.

        Args:
            context: Blender context
            mouse_x: Mouse X coordinate in region space
            mouse_y: Mouse Y coordinate in region space

        Returns:
            True if mouse is over resize border
        """
        if not self.enabled:
            self.resize_edge = ResizeEdge.NONE
            return False

        region = context.region
        if not region:
            self.resize_edge = ResizeEdge.NONE
            return False

        x, y, width, height = self.get_overlay_rect(region)

        # Check based on position mode
        if self.position == OverlayPosition.BOTTOM:
            # Resize border at top edge
            border_y = y + height
            if (0 <= mouse_x <= region.width and
                    abs(mouse_y - border_y) <= self.resize_border_thickness):
                self.resize_edge = ResizeEdge.BOTTOM  # Vertical resize
                return True

        elif self.position == OverlayPosition.TOP:
            # Resize border at bottom edge
            border_y = y
            if (0 <= mouse_x <= region.width and
                    abs(mouse_y - border_y) <= self.resize_border_thickness):
                self.resize_edge = ResizeEdge.BOTTOM  # Vertical resize
                return True

        elif self.position == OverlayPosition.LEFT:
            # Resize border at right edge
            border_x = x + width
            if (0 <= mouse_y <= region.height and
                    abs(mouse_x - border_x) <= self.resize_border_thickness):
                self.resize_edge = ResizeEdge.RIGHT  # Horizontal resize
                return True

        elif self.position == OverlayPosition.RIGHT:
            # Resize border at left edge
            border_x = x
            if (0 <= mouse_y <= region.height and
                    abs(mouse_x - border_x) <= self.resize_border_thickness):
                self.resize_edge = ResizeEdge.RIGHT  # Horizontal resize
                return True

        elif self.position == OverlayPosition.FLOATING:
            # Resize borders on right and bottom edges, plus corner
            right_border = x + width
            bottom_border = y

            # Check distances to edges
            dist_to_right = abs(mouse_x - right_border)
            dist_to_bottom = abs(mouse_y - bottom_border)

            near_right = dist_to_right <= self.resize_border_thickness
            near_bottom = dist_to_bottom <= self.resize_border_thickness

            # Check if in corner region (near both edges)
            in_corner_x = mouse_x >= right_border - self.corner_size
            in_corner_y = mouse_y <= bottom_border + self.corner_size

            if near_right and near_bottom and in_corner_x and in_corner_y:
                # Corner - resize both dimensions
                self.resize_edge = ResizeEdge.CORNER
                return True
            elif near_right and y <= mouse_y <= y + height:
                # Right edge only
                self.resize_edge = ResizeEdge.RIGHT
                return True
            elif near_bottom and x <= mouse_x <= right_border:
                # Bottom edge only
                self.resize_edge = ResizeEdge.BOTTOM
                return True

        self.resize_edge = ResizeEdge.NONE
        return False

    def is_mouse_over_title_bar(self, context, mouse_x: int, mouse_y: int) -> bool:
        """
        Check if mouse is hovering over the title bar (floating mode only).

        Args:
            context: Blender context
            mouse_x: Mouse X coordinate in region space
            mouse_y: Mouse Y coordinate in region space

        Returns:
            True if mouse is over title bar
        """
        if not self.enabled or self.position != OverlayPosition.FLOATING:
            return False

        region = context.region
        if not region:
            return False

        x, y, width, height = self.get_overlay_rect(region)

        # Title bar is above the content area
        title_y = y + height
        title_top = title_y + self.TITLE_BAR_HEIGHT

        return (x <= mouse_x <= x + width and
                title_y <= mouse_y <= title_top)

    def is_mouse_in_overlay(self, context, mouse_x: int, mouse_y: int) -> bool:
        """
        Check if mouse is inside the overlay region.

        Args:
            context: Blender context
            mouse_x: Mouse X coordinate in region space
            mouse_y: Mouse Y coordinate in region space

        Returns:
            True if mouse is inside overlay
        """
        if not self.enabled:
            return False

        region = context.region
        if not region:
            return False

        x, y, width, height = self.get_overlay_rect(region)

        # For floating mode, include title bar
        total_height = height
        if self.position == OverlayPosition.FLOATING:
            total_height = height + self.TITLE_BAR_HEIGHT

        return (x <= mouse_x <= x + width and
                y <= mouse_y <= y + total_height)

    def handle_mouse_move(self, context, event):
        """
        Handle mouse movement for resize, drag, and component hover.

        Args:
            context: Blender context
            event: Mouse event

        Returns:
            True if event was handled
        """
        if not self.enabled:
            return False

        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y
        region = context.region

        # Handle active dragging (floating mode)
        if self.is_dragging:
            delta_x = mouse_x - self.drag_start_x
            delta_y = mouse_y - self.drag_start_y

            new_x = self.drag_start_overlay_x + delta_x
            new_y = self.drag_start_overlay_y + delta_y

            # Clamp to viewport bounds
            if region:
                new_x = max(0, min(new_x, region.width - self.overlay_width))
                new_y = max(0, min(new_y, region.height - self.overlay_height - self.TITLE_BAR_HEIGHT))

            self.floating_x = new_x
            self.floating_y = new_y

            if context.area:
                context.area.tag_redraw()

            return True

        # Handle active resizing
        if self.is_resizing:
            # Resize height (BOTTOM edge or CORNER)
            if self.active_resize_edge in (ResizeEdge.BOTTOM, ResizeEdge.CORNER):
                delta_y = mouse_y - self.resize_start_mouse_y

                if self.position == OverlayPosition.TOP:
                    # TOP anchor: bottom edge moves, top stays fixed
                    delta_y = -delta_y
                    new_height = self.resize_start_height + delta_y
                    new_height = max(self.min_height, min(self.max_height, new_height))
                    self.overlay_height = new_height

                elif self.position == OverlayPosition.FLOATING:
                    # FLOATING: bottom edge follows mouse, top stays fixed
                    # delta_y is negative when dragging down (Y=0 at bottom)
                    # We need to move floating_y AND adjust height to keep top fixed
                    new_floating_y = self.drag_start_overlay_y + delta_y
                    height_change = -delta_y  # Opposite: height increases when y decreases

                    new_height = self.resize_start_height + height_change
                    new_height = max(self.min_height, min(self.max_height, new_height))

                    # Calculate actual height change after clamping
                    actual_height_change = new_height - self.resize_start_height
                    # Adjust floating_y by the opposite to keep top fixed
                    new_floating_y = self.drag_start_overlay_y - actual_height_change

                    # Clamp floating_y to viewport bounds
                    if region:
                        new_floating_y = max(0, min(new_floating_y,
                            region.height - new_height - self.TITLE_BAR_HEIGHT))

                    self.overlay_height = new_height
                    self.floating_y = new_floating_y

                else:
                    # BOTTOM anchor: top edge moves, bottom stays fixed
                    new_height = self.resize_start_height + delta_y
                    new_height = max(self.min_height, min(self.max_height, new_height))
                    self.overlay_height = new_height

            # Resize width (RIGHT edge or CORNER)
            if self.active_resize_edge in (ResizeEdge.RIGHT, ResizeEdge.CORNER):
                delta_x = mouse_x - self.resize_start_mouse_x
                if self.position == OverlayPosition.RIGHT:
                    delta_x = -delta_x  # Invert for right position
                new_width = self.resize_start_width + delta_x
                new_width = max(self.min_width, min(self.max_width, new_width))
                self.overlay_width = new_width

            if context.area:
                context.area.tag_redraw()

            return True

        # Update hover states
        self.hover_resize_border = self.is_mouse_over_resize_border(context, mouse_x, mouse_y)
        self.hover_title_bar = self.is_mouse_over_title_bar(context, mouse_x, mouse_y)

        # Handle component hover detection
        if self.is_mouse_in_overlay(context, mouse_x, mouse_y) and not self.hover_resize_border and not self.hover_title_bar:
            # Convert screen to world coordinates
            offset, elevation = self.renderer.screen_to_world(mouse_x, mouse_y, self.data)

            # Find component at point
            hover_index = self.data.get_component_at_point(offset, elevation)

            if hover_index != self.data.hover_component_index:
                self.data.hover_component_index = hover_index

                if context.area:
                    context.area.tag_redraw()

        # Update cursor
        if self.hover_title_bar:
            context.window.cursor_set('HAND')
            if context.area:
                context.area.tag_redraw()
            return True
        elif self.hover_resize_border:
            # Set cursor based on which edge is being hovered
            if self.resize_edge == ResizeEdge.CORNER:
                context.window.cursor_set('SCROLL_XY')  # Diagonal resize
            elif self.resize_edge == ResizeEdge.RIGHT:
                context.window.cursor_set('MOVE_X')     # Horizontal resize
            elif self.resize_edge == ResizeEdge.BOTTOM:
                context.window.cursor_set('MOVE_Y')     # Vertical resize
            else:
                context.window.cursor_set('DEFAULT')
            if context.area:
                context.area.tag_redraw()
            return True
        else:
            context.window.cursor_set('DEFAULT')

        return False

    def handle_mouse_press(self, context, event):
        """
        Handle mouse button press for starting resize, drag, or selecting component.

        Args:
            context: Blender context
            event: Mouse event

        Returns:
            True if event was handled
        """
        if not self.enabled:
            return False

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            mouse_x = event.mouse_region_x
            mouse_y = event.mouse_region_y

            # Check for title bar drag (floating mode)
            if self.hover_title_bar:
                self.is_dragging = True
                self.drag_start_x = mouse_x
                self.drag_start_y = mouse_y
                self.drag_start_overlay_x = self.floating_x
                self.drag_start_overlay_y = self.floating_y
                return True

            # Check for resize
            if self.hover_resize_border:
                self.is_resizing = True
                self.active_resize_edge = self.resize_edge  # Capture which edge is being resized
                self.resize_start_width = self.overlay_width
                self.resize_start_height = self.overlay_height
                self.resize_start_mouse_x = mouse_x
                self.resize_start_mouse_y = mouse_y
                # For floating mode, also capture starting position
                self.drag_start_overlay_x = self.floating_x
                self.drag_start_overlay_y = self.floating_y
                return True

            # Check for component selection
            if self.is_mouse_in_overlay(context, mouse_x, mouse_y):
                offset, elevation = self.renderer.screen_to_world(mouse_x, mouse_y, self.data)
                component_index = self.data.get_component_at_point(offset, elevation)

                if component_index >= 0:
                    self.data.select_component(component_index)
                    logger.info("Selected component: %s",
                               self.data.components[component_index].name)

                    if context.area:
                        context.area.tag_redraw()

                    return True

        return False

    def handle_mouse_release(self, context, event):
        """
        Handle mouse button release for ending resize or drag.

        Args:
            context: Blender context
            event: Mouse event

        Returns:
            True if event was handled
        """
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            handled = False

            if self.is_resizing:
                self.is_resizing = False
                self.active_resize_edge = ResizeEdge.NONE  # Clear active resize edge
                handled = True

            if self.is_dragging:
                self.is_dragging = False
                handled = True

            if handled:
                context.window.cursor_set('DEFAULT')
                return True

        return False

    def _draw_resize_border_at_position(self, region, x, y, width, height):
        """
        Draw resize border indicator based on current position mode.

        Args:
            region: Blender region
            x, y: Overlay position
            width, height: Overlay dimensions
        """
        border_color = (0.3, 0.6, 1.0, 0.8) if self.is_resizing else (0.5, 0.5, 0.5, 0.6)
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        gpu.state.blend_set('ALPHA')

        if self.position == OverlayPosition.BOTTOM:
            # Top edge
            vertices = [
                (x, y + height - 2),
                (x + width, y + height - 2),
                (x + width, y + height + 2),
                (x, y + height + 2)
            ]
        elif self.position == OverlayPosition.TOP:
            # Bottom edge
            vertices = [
                (x, y - 2),
                (x + width, y - 2),
                (x + width, y + 2),
                (x, y + 2)
            ]
        elif self.position == OverlayPosition.LEFT:
            # Right edge
            vertices = [
                (x + width - 2, y),
                (x + width + 2, y),
                (x + width + 2, y + height),
                (x + width - 2, y + height)
            ]
        elif self.position == OverlayPosition.RIGHT:
            # Left edge
            vertices = [
                (x - 2, y),
                (x + 2, y),
                (x + 2, y + height),
                (x - 2, y + height)
            ]
        elif self.position == OverlayPosition.FLOATING:
            # Right and bottom edges
            # Right edge
            vertices_right = [
                (x + width - 2, y),
                (x + width + 2, y),
                (x + width + 2, y + height),
                (x + width - 2, y + height)
            ]
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices_right})
            shader.bind()
            shader.uniform_float("color", border_color)
            batch.draw(shader)

            # Bottom edge
            vertices = [
                (x, y - 2),
                (x + width, y - 2),
                (x + width, y + 2),
                (x, y + 2)
            ]
        else:
            gpu.state.blend_set('NONE')
            return

        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
        shader.bind()
        shader.uniform_float("color", border_color)
        batch.draw(shader)

        gpu.state.blend_set('NONE')

    def _draw_resize_border(self, region, height):
        """
        Draw a visual indicator for the resize border.

        Args:
            region: Blender region
            height: Current overlay height
        """
        # Create a highlighted line at the top of the overlay
        border_y = height
        border_color = (0.3, 0.6, 1.0, 0.8) if self.is_resizing else (0.5, 0.5, 0.5, 0.6)

        # Draw a thick line across the top
        vertices = [
            (0, border_y - 2),
            (region.width, border_y - 2),
            (region.width, border_y + 2),
            (0, border_y + 2)
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
_cross_section_overlay_instance = None


def get_cross_section_overlay() -> CrossSectionViewOverlay:
    """
    Get or create the global cross-section overlay instance (singleton).

    Returns:
        CrossSectionViewOverlay instance

    Note:
        This ensures only one overlay exists at a time.
        Operators and UI can access this to interact with the overlay.
    """
    global _cross_section_overlay_instance

    if _cross_section_overlay_instance is None:
        _cross_section_overlay_instance = CrossSectionViewOverlay()

    return _cross_section_overlay_instance


def reset_cross_section_overlay():
    """
    Reset the global cross-section overlay instance.

    Note:
        Call this when Blender restarts or when you want to clear all data.
    """
    global _cross_section_overlay_instance

    # Disable if currently enabled
    if _cross_section_overlay_instance and _cross_section_overlay_instance.enabled:
        import bpy
        _cross_section_overlay_instance.disable(bpy.context)

    _cross_section_overlay_instance = None


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def load_assembly_to_overlay(context, assembly_index: int) -> bool:
    """
    Load an assembly from scene properties into the overlay.

    Args:
        context: Blender context
        assembly_index: Index of assembly in scene.bc_cross_section.assemblies

    Returns:
        True if loaded successfully
    """
    overlay = get_cross_section_overlay()

    if not hasattr(context.scene, 'bc_cross_section'):
        logger.warning("No bc_cross_section in scene")
        return False

    assemblies = context.scene.bc_cross_section.assemblies
    if assembly_index < 0 or assembly_index >= len(assemblies):
        logger.warning("Invalid assembly index: %d", assembly_index)
        return False

    assembly_props = assemblies[assembly_index]
    result = overlay.load_from_assembly(assembly_props)

    if result:
        # Enable overlay if not already
        if not overlay.enabled:
            overlay.enable(context)
        else:
            overlay.refresh(context)

    return result


def load_active_assembly_to_overlay(context) -> bool:
    """
    Load the active assembly from scene properties into the overlay.

    Args:
        context: Blender context

    Returns:
        True if loaded successfully
    """
    if not hasattr(context.scene, 'bc_cross_section'):
        return False

    active_index = context.scene.bc_cross_section.active_assembly_index

    if active_index < 0:
        return False

    return load_assembly_to_overlay(context, active_index)


__all__ = [
    "OverlayPosition",
    "ResizeEdge",
    "CrossSectionViewOverlay",
    "get_cross_section_overlay",
    "reset_cross_section_overlay",
    "load_assembly_to_overlay",
    "load_active_assembly_to_overlay",
]
