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
Saikei Civil - Profile View GPU Renderer (Core)
================================================

GPU-based 2D rendering for profile view visualization.
Uses Blender's GPU module but contains no operators or UI.

This follows Saikei Civil's architecture pattern:
- Minimal Blender dependencies (only gpu module for drawing)
- No operators or UI code
- Pure rendering logic

Author: Saikei Civil Development Team
Date: November 2025
License: GPL v3
"""

import gpu
import numpy as np
from gpu_extras.batch import batch_for_shader
from typing import Tuple, List
import blf  # Blender Font library for text
import bpy

# Import our core data model
from .profile_view_data import ProfileViewData, ProfilePoint

# Import stationing utilities
from .station_formatting import format_station_short
from . import alignment_registry
from .logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# COLOR SCHEME
# ============================================================================

COLORS = {
    'background': (0.15, 0.15, 0.15, 0.9),  # Dark gray, semi-transparent
    'grid_major': (0.3, 0.3, 0.3, 0.8),      # Medium gray
    'grid_minor': (0.25, 0.25, 0.25, 0.4),   # Light gray, transparent
    'terrain_fill': (0.6, 0.5, 0.4, 0.3),    # Brown, transparent
    'terrain_line': (0.4, 0.3, 0.2, 1.0),    # Dark brown
    'alignment': (1.0, 0.2, 0.2, 1.0),       # Red
    'vertical_alignment': (0.2, 1.0, 0.4, 1.0),  # Bright green for vertical alignments
    'vertical_pvi': (0.6, 1.0, 0.6, 1.0),    # Light green for vertical PVIs
    'pvi_normal': (0.2, 0.8, 1.0, 1.0),      # Light blue
    'pvi_selected': (1.0, 1.0, 0.0, 1.0),    # Yellow
    'pvi_hover': (0.4, 1.0, 1.0, 1.0),       # Cyan
    'grade_line': (0.5, 0.5, 0.5, 0.5),      # Gray, transparent
    'text': (1.0, 1.0, 1.0, 1.0),            # White
    'axes': (0.0, 0.0, 0.0, 1.0),            # Black
}


# ============================================================================
# PROFILE VIEW RENDERER
# ============================================================================

class ProfileViewRenderer:
    """
    GPU-based 2D renderer for profile view.
    
    Responsibilities:
        - Transform world coordinates to screen pixels
        - Render all visual elements (grid, terrain, alignment, PVIs)
        - Handle text labels
        - Manage GPU shaders and batches
    
    This is pure rendering logic - no operators or UI.
    """
    
    def __init__(self):
        """Initialize renderer with shaders"""
        self.shader_2d = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.shader_smooth = gpu.shader.from_builtin('SMOOTH_COLOR')
        
        # View region (screen coordinates)
        self.view_region = (0, 0, 800, 200)  # x, y, width, height in pixels
        self.margin_left = 60    # Space for elevation labels
        self.margin_right = 20
        self.margin_top = 20
        self.margin_bottom = 40  # Space for station labels
        
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
        
        return (draw_x, draw_y, draw_w, draw_h)
    
    def world_to_screen(self, station: float, elevation: float, 
                       data: ProfileViewData) -> Tuple[float, float]:
        """
        Convert world coordinates (station, elevation) to screen pixels.
        
        Args:
            station: Station coordinate (m)
            elevation: Elevation coordinate (m)
            data: ProfileViewData with view extents
            
        Returns:
            (screen_x, screen_y) in pixels
        """
        draw_x, draw_y, draw_w, draw_h = self.get_drawable_region()
        
        # Normalize to 0-1
        norm_x = (station - data.station_min) / (data.station_max - data.station_min)
        norm_y = (elevation - data.elevation_min) / (data.elevation_max - data.elevation_min)
        
        # Clamp to prevent overflow
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))
        
        # Map to screen
        screen_x = draw_x + norm_x * draw_w
        screen_y = draw_y + norm_y * draw_h
        
        return screen_x, screen_y
    
    def screen_to_world(self, screen_x: float, screen_y: float,
                       data: ProfileViewData) -> Tuple[float, float]:
        """
        Convert screen pixels to world coordinates.
        
        Args:
            screen_x, screen_y: Screen coordinates (pixels)
            data: ProfileViewData with view extents
            
        Returns:
            (station, elevation) in meters
        """
        draw_x, draw_y, draw_w, draw_h = self.get_drawable_region()
        
        # Normalize to 0-1
        norm_x = (screen_x - draw_x) / draw_w
        norm_y = (screen_y - draw_y) / draw_h
        
        # Map to world
        station = data.station_min + norm_x * (data.station_max - data.station_min)
        elevation = data.elevation_min + norm_y * (data.elevation_max - data.elevation_min)
        
        return station, elevation
    
    def is_point_in_drawable_region(self, screen_x: float, screen_y: float) -> bool:
        """Check if screen point is inside drawable region"""
        draw_x, draw_y, draw_w, draw_h = self.get_drawable_region()
        return (draw_x <= screen_x <= draw_x + draw_w and
                draw_y <= screen_y <= draw_y + draw_h)

    def _get_active_alignment(self):
        """
        Get the active horizontal alignment from the scene.

        Returns:
            Active alignment object with stationing, or None if no active alignment
        """
        try:
            # Import here to avoid circular dependency
            from ..ui.alignment_properties import get_active_alignment_ifc

            # Get active alignment IFC entity
            active_alignment_ifc = get_active_alignment_ifc(bpy.context)
            if not active_alignment_ifc:
                return None

            # Get alignment object from registry
            alignment_obj = alignment_registry.get_alignment(active_alignment_ifc.GlobalId)
            return alignment_obj

        except Exception as e:
            # Silently fail if alignment not available
            return None

    def draw_background(self):
        """Draw semi-transparent background for profile view area"""
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
    
    def draw_grid(self, data: ProfileViewData):
        """
        Draw grid lines with station and elevation intervals.
        
        Args:
            data: ProfileViewData with grid settings
        """
        if not data.show_grid:
            return
        
        vertices = []
        
        # Vertical grid lines (station intervals)
        station = data.station_min
        while station <= data.station_max:
            x1, y1 = self.world_to_screen(station, data.elevation_min, data)
            x2, y2 = self.world_to_screen(station, data.elevation_max, data)
            vertices.extend([(x1, y1), (x2, y2)])
            station += data.station_grid_spacing
        
        # Horizontal grid lines (elevation intervals)
        elevation = data.elevation_min
        while elevation <= data.elevation_max:
            x1, y1 = self.world_to_screen(data.station_min, elevation, data)
            x2, y2 = self.world_to_screen(data.station_max, elevation, data)
            vertices.extend([(x1, y1), (x2, y2)])
            elevation += data.elevation_grid_spacing
        
        # Draw lines
        if vertices:
            batch = batch_for_shader(self.shader_2d, 'LINES', {"pos": vertices})
            self.shader_2d.uniform_float("color", COLORS['grid_major'])
            batch.draw(self.shader_2d)
    
    def draw_terrain_profile(self, data: ProfileViewData):
        """
        Draw terrain profile with fill using proper triangulation.

        Uses vertical strips to create triangles that work correctly
        for any terrain shape (convex or non-convex).

        Args:
            data: ProfileViewData with terrain points
        """
        if not data.show_terrain or not data.terrain_points:
            return

        # Sort terrain points by station
        terrain_sorted = sorted(data.terrain_points, key=lambda p: p.station)

        if len(terrain_sorted) < 2:
            return

        # Convert terrain points to screen coordinates
        terrain_screen = []
        for pt in terrain_sorted:
            x, y = self.world_to_screen(pt.station, pt.elevation, data)
            terrain_screen.append((x, y))

        # Get bottom of view for fill
        _, y_bottom = self.world_to_screen(0, data.elevation_min, data)

        # Create triangles using vertical strips
        # For each pair of consecutive points, create two triangles forming a vertical strip
        triangles = []
        for i in range(len(terrain_screen) - 1):
            x1, y1 = terrain_screen[i]
            x2, y2 = terrain_screen[i + 1]

            # Create two triangles for this vertical strip:
            # Triangle 1: (x1,y1) -> (x2,y2) -> (x2,y_bottom)
            triangles.extend([(x1, y1), (x2, y2), (x2, y_bottom)])
            # Triangle 2: (x1,y1) -> (x2,y_bottom) -> (x1,y_bottom)
            triangles.extend([(x1, y1), (x2, y_bottom), (x1, y_bottom)])

        # Draw fill triangles
        if triangles:
            batch = batch_for_shader(self.shader_2d, 'TRIS', {"pos": triangles})
            self.shader_2d.uniform_float("color", COLORS['terrain_fill'])
            batch.draw(self.shader_2d)

        # Draw terrain outline
        batch = batch_for_shader(self.shader_2d, 'LINE_STRIP', {"pos": terrain_screen})
        self.shader_2d.uniform_float("color", COLORS['terrain_line'])
        gpu.state.line_width_set(2.0)
        batch.draw(self.shader_2d)
        gpu.state.line_width_set(1.0)
    
    def draw_alignment_profile(self, data: ProfileViewData):
        """
        Draw vertical alignment profile.
        
        Args:
            data: ProfileViewData with alignment points
        """
        if not data.show_alignment or not data.alignment_points:
            return
        
        # Sort alignment points by station
        alignment_sorted = sorted(data.alignment_points, key=lambda p: p.station)
        
        vertices = []
        for pt in alignment_sorted:
            x, y = self.world_to_screen(pt.station, pt.elevation, data)
            vertices.append((x, y))
        
        # Draw line
        if len(vertices) >= 2:
            batch = batch_for_shader(self.shader_2d, 'LINE_STRIP', {"pos": vertices})
            self.shader_2d.uniform_float("color", COLORS['alignment'])
            gpu.state.line_width_set(3.0)
            batch.draw(self.shader_2d)
            gpu.state.line_width_set(1.0)
    
    def draw_pvis(self, data: ProfileViewData):
        """
        Draw PVIs as editable control points.
        
        Args:
            data: ProfileViewData with PVIs
        """
        if not data.show_pvis or not data.pvis:
            return
        
        for i, pvi in enumerate(data.pvis):
            x, y = self.world_to_screen(pvi.station, pvi.elevation, data)
            
            # Determine color and size based on selection
            if i == data.selected_pvi_index:
                color = COLORS['pvi_selected']
                size = 10.0
            else:
                color = COLORS['pvi_normal']
                size = 7.0
            
            # Draw circle
            self._draw_circle(x, y, size, color)
            
            # Draw grade lines if enabled
            if data.show_grades and i < len(data.pvis) - 1:
                next_pvi = data.pvis[i + 1]
                x2, y2 = self.world_to_screen(next_pvi.station, next_pvi.elevation, data)
                
                # Dashed line for grade
                vertices = [(x, y), (x2, y2)]
                batch = batch_for_shader(self.shader_2d, 'LINES', {"pos": vertices})
                self.shader_2d.uniform_float("color", COLORS['grade_line'])
                batch.draw(self.shader_2d)
    
    def _draw_circle(self, x: float, y: float, radius: float, color: Tuple):
        """
        Helper to draw a filled circle.
        
        Args:
            x, y: Center coordinates (pixels)
            radius: Circle radius (pixels)
            color: RGBA color tuple
        """
        segments = 16
        vertices = []
        for i in range(segments):
            angle = 2.0 * np.pi * i / segments
            vertices.append((
                x + radius * np.cos(angle),
                y + radius * np.sin(angle)
            ))
        
        batch = batch_for_shader(self.shader_2d, 'TRI_FAN', {"pos": vertices})
        self.shader_2d.uniform_float("color", color)
        batch.draw(self.shader_2d)

    def draw_vertical_alignments(self, data: ProfileViewData):
        """
        Draw vertical alignment profiles from IFC.

        This draws vertical alignments loaded from IFC files or created
        from terrain tracing. Each vertical alignment is drawn as a green line
        with PVI markers.

        Args:
            data: ProfileViewData with vertical alignments
        """
        if not data.vertical_alignments:
            return

        # Draw each vertical alignment
        for valign_idx, valign in enumerate(data.vertical_alignments):
            # Determine if this is the selected vertical alignment
            is_selected = (valign_idx == data.selected_vertical_index)

            # Sample points along the vertical alignment by querying at regular intervals
            vertices = []

            # Get station range from PVIs
            if len(valign.pvis) >= 2:
                start_station = valign.pvis[0].station
                end_station = valign.pvis[-1].station

                # Sample at regular intervals along the entire alignment
                num_samples = 100  # More samples for smooth display
                for i in range(num_samples):
                    t = i / (num_samples - 1)
                    station = start_station + t * (end_station - start_station)

                    # Query elevation at this station
                    try:
                        elevation = valign.get_elevation(station)
                        if elevation is not None:
                            x, y = self.world_to_screen(station, elevation, data)
                            vertices.append((x, y))
                    except Exception as e:
                        # Log error for debugging but continue
                        logger.warning("Could not query elevation at station %s: %s", station, e)

            # Draw vertical alignment line
            if len(vertices) >= 2:
                batch = batch_for_shader(self.shader_2d, 'LINE_STRIP', {"pos": vertices})
                # Use brighter green if selected, dimmer if not
                if is_selected:
                    self.shader_2d.uniform_float("color", COLORS['vertical_alignment'])
                    gpu.state.line_width_set(3.0)
                else:
                    color_dimmed = (0.2, 0.7, 0.3, 0.6)  # Dimmer green
                    self.shader_2d.uniform_float("color", color_dimmed)
                    gpu.state.line_width_set(2.0)
                batch.draw(self.shader_2d)
                gpu.state.line_width_set(1.0)
                logger.debug("Drew vertical alignment with %s vertices", len(vertices))
            else:
                logger.debug("No vertices to draw for vertical alignment %s", valign.name)

            # Draw PVIs for this vertical alignment
            if is_selected:  # Only show PVIs for selected alignment
                for pvi in valign.pvis:
                    x, y = self.world_to_screen(pvi.station, pvi.elevation, data)

                    # Draw PVI marker (diamond shape for vertical alignment PVIs)
                    size = 6.0
                    diamond_vertices = [
                        (x, y + size),      # Top
                        (x + size, y),      # Right
                        (x, y - size),      # Bottom
                        (x - size, y),      # Left
                    ]

                    batch = batch_for_shader(self.shader_2d, 'TRI_FAN', {"pos": diamond_vertices})
                    self.shader_2d.uniform_float("color", COLORS['vertical_pvi'])
                    batch.draw(self.shader_2d)

    def draw_axes(self, data: ProfileViewData):
        """
        Draw X and Y axes.
        
        Args:
            data: ProfileViewData for extent information
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
    
    def draw_labels(self, data: ProfileViewData):
        """
        Draw station and elevation labels using BLF.
        
        Args:
            data: ProfileViewData with view extents
        """
        blf.size(self.font_id, 11)
        blf.color(self.font_id, *COLORS['text'])
        
        draw_x, draw_y, draw_w, draw_h = self.get_drawable_region()
        
        # Station labels (X-axis)
        # Note: data.station_min/max are ALREADY in station units (meters along alignment)
        # They represent actual station values, not distances to be converted

        station = data.station_min
        while station <= data.station_max:
            x, y = self.world_to_screen(station, data.elevation_min, data)

            # Format station value directly (no conversion needed)
            # Station values are in meters, format them in XX+XXX notation
            text = format_station_short(station)

            text_width, text_height = blf.dimensions(self.font_id, text)

            # Draw below axis
            blf.position(self.font_id, x - text_width / 2, y - 25, 0)
            blf.draw(self.font_id, text)

            station += data.station_grid_spacing
        
        # Elevation labels (Y-axis)
        elevation = data.elevation_min
        while elevation <= data.elevation_max:
            x, y = self.world_to_screen(data.station_min, elevation, data)
            
            text = f"{elevation:.1f}m"
            text_width, text_height = blf.dimensions(self.font_id, text)
            
            # Draw to left of axis
            blf.position(self.font_id, x - text_width - 10, y - text_height / 2, 0)
            blf.draw(self.font_id, text)
            
            elevation += data.elevation_grid_spacing
        
        # Axis titles
        # X-axis title: Always "Station" since we're working with alignment stations
        title_x = draw_x + draw_w / 2
        title_y = draw_y - 35
        blf.size(self.font_id, 12)
        title = "Station"
        text_width, _ = blf.dimensions(self.font_id, title)
        blf.position(self.font_id, title_x - text_width / 2, title_y, 0)
        blf.draw(self.font_id, title)
        
        # Y-axis title: "Elevation (m)" (rotated would be nice, but complex)
        blf.size(self.font_id, 12)
        title = "Elev (m)"
        blf.position(self.font_id, draw_x - 55, draw_y + draw_h / 2, 0)
        blf.draw(self.font_id, title)
    
    def render(self, data: ProfileViewData):
        """
        Main render function - draws complete profile view.
        
        Args:
            data: ProfileViewData to visualize
        """
        # Enable alpha blending for transparency
        gpu.state.blend_set('ALPHA')
        
        # Draw in order (back to front for proper layering)
        self.draw_background()
        self.draw_grid(data)
        self.draw_axes(data)
        self.draw_labels(data)
        self.draw_terrain_profile(data)
        self.draw_alignment_profile(data)
        self.draw_vertical_alignments(data)  # Draw IFC vertical alignments
        self.draw_pvis(data)
        
        # Restore state
        gpu.state.blend_set('NONE')


if __name__ == "__main__":
    logger.info("ProfileViewRenderer - Core rendering module")
    logger.info("This module requires Blender's GPU context to run tests.")
    logger.info("Use from within Blender for testing.")
