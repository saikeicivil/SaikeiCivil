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
Saikei Civil - Cross-Section View GPU Renderer (Core)
======================================================

GPU-based 2D rendering for cross-section view visualization.
Uses Blender's GPU module but contains no operators or UI.

Following the OpenRoads approach where cross-sections are visualized
in a dedicated viewer, not in the 3D model space.

Author: Saikei Civil Development Team
Date: December 2025
"""

import gpu
import numpy as np
from gpu_extras.batch import batch_for_shader
from typing import Tuple, List
import blf  # Blender Font library for text

# Import our core data model
from .cross_section_view_data import (
    CrossSectionViewData,
    CrossSectionComponent,
    ComponentType
)
from .logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# COLOR SCHEME
# ============================================================================

COLORS = {
    'background': (0.12, 0.12, 0.12, 0.95),     # Dark gray, semi-transparent
    'grid_major': (0.25, 0.25, 0.25, 0.8),       # Medium gray
    'grid_minor': (0.2, 0.2, 0.2, 0.4),          # Light gray, transparent
    'centerline': (1.0, 0.0, 0.0, 1.0),          # Red centerline
    'centerline_dashed': (1.0, 0.0, 0.0, 0.5),   # Red dashed
    'axes': (0.0, 0.0, 0.0, 1.0),                # Black axes
    'text': (1.0, 1.0, 1.0, 1.0),                # White text
    'text_dim': (0.7, 0.7, 0.7, 1.0),            # Dimmed text
    'selection': (1.0, 0.8, 0.0, 1.0),           # Yellow/gold selection
    'hover': (0.5, 0.8, 1.0, 0.8),               # Cyan hover

    # Component colors by type
    'lane': (0.35, 0.35, 0.35, 0.9),             # Dark gray asphalt
    'shoulder': (0.5, 0.48, 0.42, 0.9),          # Light gray/tan
    'curb': (0.65, 0.65, 0.65, 0.9),             # Concrete gray
    'ditch': (0.45, 0.38, 0.28, 0.9),            # Brown earth
    'median': (0.3, 0.55, 0.3, 0.9),             # Green
    'sidewalk': (0.6, 0.58, 0.55, 0.9),          # Concrete
    'custom': (0.5, 0.5, 0.5, 0.9),              # Generic gray
}

# Component type to color mapping
COMPONENT_COLORS = {
    ComponentType.LANE: COLORS['lane'],
    ComponentType.SHOULDER: COLORS['shoulder'],
    ComponentType.CURB: COLORS['curb'],
    ComponentType.DITCH: COLORS['ditch'],
    ComponentType.MEDIAN: COLORS['median'],
    ComponentType.SIDEWALK: COLORS['sidewalk'],
    ComponentType.CUSTOM: COLORS['custom'],
}


# ============================================================================
# CROSS-SECTION VIEW RENDERER
# ============================================================================

class CrossSectionViewRenderer:
    """
    GPU-based 2D renderer for cross-section view.

    Responsibilities:
        - Transform world coordinates to screen pixels
        - Render all visual elements (grid, components, centerline)
        - Handle text labels
        - Manage GPU shaders and batches

    This is pure rendering logic - no operators or UI.
    """

    def __init__(self):
        """Initialize renderer with shaders"""
        self.shader_2d = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.shader_smooth = gpu.shader.from_builtin('SMOOTH_COLOR')

        # View region (screen coordinates)
        self.view_region = (0, 0, 800, 300)  # x, y, width, height in pixels
        self.margin_left = 60     # Space for elevation labels
        self.margin_right = 20
        self.margin_top = 30      # Space for title
        self.margin_bottom = 40   # Space for offset labels

        # Font ID for text rendering
        self.font_id = 0

    def set_view_region(self, x: int, y: int, width: int, height: int):
        """
        Set the screen region for drawing.

        Args:
            x, y: Bottom-left corner (pixels)
            width, height: Region dimensions (pixels)
        """
        self.view_region = (x, y, width, height)

    def get_drawable_region(self) -> Tuple[int, int, int, int]:
        """
        Get the drawable region (excluding margins).

        Returns:
            (x, y, width, height) of drawable area
        """
        x, y, w, h = self.view_region

        draw_x = x + self.margin_left
        draw_y = y + self.margin_bottom
        draw_w = w - self.margin_left - self.margin_right
        draw_h = h - self.margin_bottom - self.margin_top

        return (draw_x, draw_y, max(1, draw_w), max(1, draw_h))

    def world_to_screen(self, offset: float, elevation: float,
                        data: CrossSectionViewData) -> Tuple[float, float]:
        """
        Convert world coordinates (offset, elevation) to screen pixels.

        Args:
            offset: Horizontal offset from centerline (m)
            elevation: Elevation relative to centerline (m)
            data: CrossSectionViewData with view extents

        Returns:
            (screen_x, screen_y) in pixels
        """
        draw_x, draw_y, draw_w, draw_h = self.get_drawable_region()

        # Normalize to 0-1
        offset_range = data.offset_max - data.offset_min
        elevation_range = data.elevation_max - data.elevation_min

        if offset_range == 0:
            offset_range = 1.0
        if elevation_range == 0:
            elevation_range = 1.0

        norm_x = (offset - data.offset_min) / offset_range
        norm_y = (elevation - data.elevation_min) / elevation_range

        # Clamp to prevent overflow
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        # Map to screen
        screen_x = draw_x + norm_x * draw_w
        screen_y = draw_y + norm_y * draw_h

        return screen_x, screen_y

    def screen_to_world(self, screen_x: float, screen_y: float,
                        data: CrossSectionViewData) -> Tuple[float, float]:
        """
        Convert screen pixels to world coordinates.

        Args:
            screen_x, screen_y: Screen coordinates (pixels)
            data: CrossSectionViewData with view extents

        Returns:
            (offset, elevation) in meters
        """
        draw_x, draw_y, draw_w, draw_h = self.get_drawable_region()

        if draw_w == 0 or draw_h == 0:
            return 0.0, 0.0

        # Normalize to 0-1
        norm_x = (screen_x - draw_x) / draw_w
        norm_y = (screen_y - draw_y) / draw_h

        # Map to world
        offset = data.offset_min + norm_x * (data.offset_max - data.offset_min)
        elevation = data.elevation_min + norm_y * (data.elevation_max - data.elevation_min)

        return offset, elevation

    def is_point_in_drawable_region(self, screen_x: float, screen_y: float) -> bool:
        """Check if screen point is inside drawable region"""
        draw_x, draw_y, draw_w, draw_h = self.get_drawable_region()
        return (draw_x <= screen_x <= draw_x + draw_w and
                draw_y <= screen_y <= draw_y + draw_h)

    def draw_background(self):
        """Draw semi-transparent background for cross-section view area"""
        x, y, w, h = self.view_region

        vertices = [
            (x, y),
            (x + w, y),
            (x + w, y + h),
            (x, y + h)
        ]

        batch = batch_for_shader(self.shader_2d, 'TRI_FAN', {"pos": vertices})
        self.shader_2d.uniform_float("color", COLORS['background'])

        gpu.state.blend_set('ALPHA')
        batch.draw(self.shader_2d)
        gpu.state.blend_set('NONE')

    def draw_grid(self, data: CrossSectionViewData):
        """
        Draw grid lines with offset and elevation intervals.

        Args:
            data: CrossSectionViewData with grid settings
        """
        if not data.show_grid:
            return

        vertices = []

        # Vertical grid lines (offset intervals)
        offset = data.offset_min
        while offset <= data.offset_max:
            x1, y1 = self.world_to_screen(offset, data.elevation_min, data)
            x2, y2 = self.world_to_screen(offset, data.elevation_max, data)
            vertices.extend([(x1, y1), (x2, y2)])
            offset += data.offset_grid_spacing

        # Horizontal grid lines (elevation intervals)
        elevation = data.elevation_min
        while elevation <= data.elevation_max:
            x1, y1 = self.world_to_screen(data.offset_min, elevation, data)
            x2, y2 = self.world_to_screen(data.offset_max, elevation, data)
            vertices.extend([(x1, y1), (x2, y2)])
            elevation += data.elevation_grid_spacing

        # Draw lines
        if vertices:
            batch = batch_for_shader(self.shader_2d, 'LINES', {"pos": vertices})
            self.shader_2d.uniform_float("color", COLORS['grid_major'])
            batch.draw(self.shader_2d)

    def draw_centerline(self, data: CrossSectionViewData):
        """
        Draw vertical centerline reference.

        Args:
            data: CrossSectionViewData
        """
        if not data.show_centerline:
            return

        # Draw vertical line at offset = 0
        x1, y1 = self.world_to_screen(0, data.elevation_min, data)
        x2, y2 = self.world_to_screen(0, data.elevation_max, data)

        vertices = [(x1, y1), (x2, y2)]

        batch = batch_for_shader(self.shader_2d, 'LINES', {"pos": vertices})
        self.shader_2d.uniform_float("color", COLORS['centerline'])
        gpu.state.line_width_set(2.0)
        batch.draw(self.shader_2d)
        gpu.state.line_width_set(1.0)

        # Draw horizontal reference at elevation = 0
        x1, y1 = self.world_to_screen(data.offset_min, 0, data)
        x2, y2 = self.world_to_screen(data.offset_max, 0, data)

        vertices = [(x1, y1), (x2, y2)]

        batch = batch_for_shader(self.shader_2d, 'LINES', {"pos": vertices})
        self.shader_2d.uniform_float("color", COLORS['centerline_dashed'])
        batch.draw(self.shader_2d)

    def draw_component(self, component: CrossSectionComponent, data: CrossSectionViewData,
                       is_selected: bool = False, is_hovered: bool = False):
        """
        Draw a single cross-section component.

        Args:
            component: Component to draw
            data: CrossSectionViewData for coordinate transformation
            is_selected: Whether component is selected
            is_hovered: Whether mouse is hovering over component
        """
        if len(component.points) < 2:
            return

        # Get screen coordinates for component surface points (top edge)
        screen_points_top = []
        for pt in component.points:
            sx, sy = self.world_to_screen(pt.offset, pt.elevation, data)
            screen_points_top.append((sx, sy))

        # Get screen coordinates for component bottom points (surface - thickness)
        # Use the component's thickness property
        thickness = component.thickness if component.thickness > 0 else 0.15
        screen_points_bottom = []
        for pt in component.points:
            sx, sy = self.world_to_screen(pt.offset, pt.elevation - thickness, data)
            screen_points_bottom.append((sx, sy))

        # Create filled polygon (triangulate for fill)
        # Draw the component as a closed shape with proper thickness
        if len(screen_points_top) >= 2:
            triangles = []
            for i in range(len(screen_points_top) - 1):
                # Top edge points
                x1_top, y1_top = screen_points_top[i]
                x2_top, y2_top = screen_points_top[i + 1]
                # Bottom edge points
                x1_bot, y1_bot = screen_points_bottom[i]
                x2_bot, y2_bot = screen_points_bottom[i + 1]

                # Create two triangles for the quad between top and bottom
                triangles.extend([(x1_top, y1_top), (x2_top, y2_top), (x2_bot, y2_bot)])
                triangles.extend([(x1_top, y1_top), (x2_bot, y2_bot), (x1_bot, y1_bot)])

            # Get color for component type
            base_color = COMPONENT_COLORS.get(component.component_type, COLORS['custom'])

            # Modify color for selection/hover
            if is_selected:
                color = COLORS['selection']
            elif is_hovered:
                color = (*base_color[:3], 1.0)  # Full opacity for hover
            else:
                color = base_color

            # Draw fill
            if triangles:
                batch = batch_for_shader(self.shader_2d, 'TRIS', {"pos": triangles})
                self.shader_2d.uniform_float("color", color)
                batch.draw(self.shader_2d)

        # Draw outline
        outline_color = COLORS['selection'] if is_selected else (0.0, 0.0, 0.0, 1.0)
        line_width = 2.0 if is_selected else 1.0

        # Create closed polygon outline (top -> right side -> bottom reversed -> left side)
        outline_points = list(screen_points_top)
        # Add right edge (from last top to last bottom)
        outline_points.append(screen_points_bottom[-1])
        # Add bottom edge in reverse
        outline_points.extend(reversed(screen_points_bottom[:-1]))
        # Close back to start
        outline_points.append(screen_points_top[0])

        if len(outline_points) >= 2:
            batch = batch_for_shader(self.shader_2d, 'LINE_STRIP', {"pos": outline_points})
            self.shader_2d.uniform_float("color", outline_color)
            gpu.state.line_width_set(line_width)
            batch.draw(self.shader_2d)
            gpu.state.line_width_set(1.0)

    def draw_components(self, data: CrossSectionViewData):
        """
        Draw all cross-section components.

        Args:
            data: CrossSectionViewData with components
        """
        for i, component in enumerate(data.components):
            is_selected = (i == data.selected_component_index)
            is_hovered = (i == data.hover_component_index)
            self.draw_component(component, data, is_selected, is_hovered)

    def draw_component_labels(self, data: CrossSectionViewData):
        """
        Draw labels for each component.

        Args:
            data: CrossSectionViewData with components
        """
        if not data.show_labels:
            return

        blf.size(self.font_id, 10)

        for i, component in enumerate(data.components):
            if len(component.points) < 2:
                continue

            # Calculate center of component
            offsets = [pt.offset for pt in component.points]
            elevations = [pt.elevation for pt in component.points]

            center_offset = (min(offsets) + max(offsets)) / 2
            center_elevation = (min(elevations) + max(elevations)) / 2

            x, y = self.world_to_screen(center_offset, center_elevation, data)

            # Determine text color
            is_selected = (i == data.selected_component_index)
            if is_selected:
                blf.color(self.font_id, *COLORS['selection'])
            else:
                blf.color(self.font_id, *COLORS['text'])

            # Draw component name
            text = component.name
            text_width, text_height = blf.dimensions(self.font_id, text)

            blf.position(self.font_id, x - text_width / 2, y + 5, 0)
            blf.draw(self.font_id, text)

            # Draw width below name
            if data.show_dimensions and component.width > 0:
                dim_text = f"{component.width:.2f}m"
                blf.color(self.font_id, *COLORS['text_dim'])
                blf.size(self.font_id, 9)
                dim_width, _ = blf.dimensions(self.font_id, dim_text)
                blf.position(self.font_id, x - dim_width / 2, y - 10, 0)
                blf.draw(self.font_id, dim_text)
                blf.size(self.font_id, 10)

    def draw_axes(self, data: CrossSectionViewData):
        """
        Draw X and Y axes.

        Args:
            data: CrossSectionViewData for extent information
        """
        draw_x, draw_y, draw_w, draw_h = self.get_drawable_region()

        vertices = [
            # X-axis (bottom)
            (draw_x, draw_y),
            (draw_x + draw_w, draw_y),
            # Y-axis (left)
            (draw_x, draw_y),
            (draw_x, draw_y + draw_h)
        ]

        batch = batch_for_shader(self.shader_2d, 'LINES', {"pos": vertices})
        self.shader_2d.uniform_float("color", COLORS['axes'])
        gpu.state.line_width_set(2.0)
        batch.draw(self.shader_2d)
        gpu.state.line_width_set(1.0)

    def draw_labels(self, data: CrossSectionViewData):
        """
        Draw offset and elevation labels using BLF.

        Args:
            data: CrossSectionViewData with view extents
        """
        blf.size(self.font_id, 11)
        blf.color(self.font_id, *COLORS['text'])

        draw_x, draw_y, draw_w, draw_h = self.get_drawable_region()

        # Offset labels (X-axis)
        offset = data.offset_min
        while offset <= data.offset_max:
            x, y = self.world_to_screen(offset, data.elevation_min, data)

            # Format offset with sign for left/right
            if offset > 0:
                text = f"+{offset:.1f}"
            elif offset < 0:
                text = f"{offset:.1f}"
            else:
                text = "CL"  # Centerline

            text_width, text_height = blf.dimensions(self.font_id, text)

            # Draw below axis
            blf.position(self.font_id, x - text_width / 2, y - 20, 0)
            blf.draw(self.font_id, text)

            offset += data.offset_grid_spacing

        # Elevation labels (Y-axis)
        elevation = data.elevation_min
        while elevation <= data.elevation_max:
            x, y = self.world_to_screen(data.offset_min, elevation, data)

            text = f"{elevation:.2f}m"
            text_width, text_height = blf.dimensions(self.font_id, text)

            # Draw to left of axis
            blf.position(self.font_id, x - text_width - 8, y - text_height / 2, 0)
            blf.draw(self.font_id, text)

            elevation += data.elevation_grid_spacing

        # Axis titles
        # X-axis title
        blf.size(self.font_id, 12)
        title_x = draw_x + draw_w / 2
        title_y = draw_y - 35
        title = "Offset (m)"
        text_width, _ = blf.dimensions(self.font_id, title)
        blf.position(self.font_id, title_x - text_width / 2, title_y, 0)
        blf.draw(self.font_id, title)

        # Y-axis title
        title = "Elev (m)"
        blf.position(self.font_id, draw_x - 55, draw_y + draw_h / 2, 0)
        blf.draw(self.font_id, title)

    def draw_title(self, data: CrossSectionViewData):
        """
        Draw title bar with assembly name and info.

        Args:
            data: CrossSectionViewData
        """
        x, y, w, h = self.view_region

        blf.size(self.font_id, 14)
        blf.color(self.font_id, *COLORS['text'])

        # Title text
        title = data.get_status_text()
        text_width, text_height = blf.dimensions(self.font_id, title)

        # Draw at top of view region
        blf.position(self.font_id, x + 10, y + h - 20, 0)
        blf.draw(self.font_id, title)

    def render(self, data: CrossSectionViewData):
        """
        Main render function - draws complete cross-section view.

        Args:
            data: CrossSectionViewData to visualize
        """
        # Enable alpha blending for transparency
        gpu.state.blend_set('ALPHA')

        # Draw in order (back to front for proper layering)
        self.draw_background()
        self.draw_grid(data)
        self.draw_centerline(data)
        self.draw_components(data)
        self.draw_axes(data)
        self.draw_labels(data)
        self.draw_component_labels(data)
        self.draw_title(data)

        # Restore state
        gpu.state.blend_set('NONE')


if __name__ == "__main__":
    logger.info("CrossSectionViewRenderer - Core rendering module")
    logger.info("This module requires Blender's GPU context to run tests.")
    logger.info("Use from within Blender for testing.")