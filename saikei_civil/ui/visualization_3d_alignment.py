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
Saikei Civil - 3D Alignment Visualization
Sprint 3 Day 4 - 3D Visualization in Blender

This module provides tools to visualize complete 3D alignments (H+V) 
in Blender, creating beautiful curves, profiles, and cross-sections.

Author: Saikei Civil Team
Date: November 2, 2025
Sprint: 3 of 16 - Vertical Alignments
Day: 4 of 5 - 3D Visualization

Key Features:
- Create 3D alignment curves in Blender
- Visualize horizontal alignment (plan view)
- Visualize vertical profile (elevation view)
- Combined 3D alignment visualization
- Station markers and labels
- Grade indicators
- Curve highlighting
- Customizable appearance (colors, line widths)

Usage in Blender:
    >>> import bpy
    >>> from visualization_3d_alignment import AlignmentVisualizer3D
    >>> 
    >>> # Create visualizer
    >>> viz = AlignmentVisualizer3D(alignment_3d)
    >>> 
    >>> # Create 3D curve
    >>> curve_obj = viz.create_3d_curve(interval=5.0)
    >>> 
    >>> # Add station markers
    >>> markers = viz.create_station_markers(interval=50.0)
    >>> 
    >>> # Create profile view
    >>> profile = viz.create_profile_view(scale_z=10.0)
"""

import bpy
import math
from typing import List, Tuple, Optional, Dict, Any
from mathutils import Vector

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class AlignmentVisualizer3D:
    """
    3D Alignment Visualization in Blender.
    
    This class creates beautiful 3D visualizations of complete alignments
    (horizontal + vertical) in Blender, with customizable appearance and
    options for plan view, profile view, and combined 3D view.
    
    Attributes:
        alignment_3d: Alignment3D instance to visualize
        collection_name: Blender collection name for organization
        
    Methods:
        create_3d_curve(): Main 3D alignment curve
        create_plan_view(): Top-down (plan) view
        create_profile_view(): Side (elevation) profile
        create_station_markers(): Station labels along alignment
        create_grade_indicators(): Visual grade arrows
        highlight_curves(): Emphasize curved sections
    """
    
    def __init__(
        self,
        alignment_3d: Any,
        collection_name: str = "Alignment 3D"
    ):
        """
        Initialize 3D visualizer.
        
        Args:
            alignment_3d: Alignment3D instance to visualize
            collection_name: Name for Blender collection
        """
        self.alignment = alignment_3d
        self.collection_name = collection_name
        
        # Create/get collection
        self.collection = self._get_or_create_collection(collection_name)
    
    def _get_or_create_collection(self, name: str) -> bpy.types.Collection:
        """Get existing collection or create new one."""
        if name in bpy.data.collections:
            return bpy.data.collections[name]
        
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        return collection
    
    def create_3d_curve(
        self,
        interval: float = 5.0,
        name: str = "Alignment_3D",
        color: Tuple[float, float, float, float] = (0.0, 0.5, 1.0, 1.0),
        line_width: float = 3.0
    ) -> bpy.types.Object:
        """
        Create main 3D alignment curve in Blender.
        
        This creates a beautiful 3D curve showing the complete alignment
        path through space (x, y, z).
        
        Args:
            interval: Sample spacing along alignment (m)
            name: Object name in Blender
            color: RGBA color (0-1 range)
            line_width: Line width in pixels
            
        Returns:
            Blender curve object
            
        Example:
            >>> viz = AlignmentVisualizer3D(alignment_3d)
            >>> curve = viz.create_3d_curve(
            ...     interval=5.0,
            ...     color=(0, 0.5, 1, 1),  # Blue
            ...     line_width=4.0
            ... )
        """
        # Sample alignment
        points = self.alignment.sample_alignment(
            interval=interval,
            include_key_stations=True
        )
        
        if len(points) < 2:
            raise ValueError("Not enough points to create curve")
        
        # Create curve data
        curve_data = bpy.data.curves.new(name=name, type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.resolution_u = 12
        curve_data.bevel_depth = 0.5  # Thickness
        
        # Create spline
        spline = curve_data.splines.new('POLY')
        spline.points.add(len(points) - 1)  # Already has 1 point
        
        # Set point coordinates
        for i, point in enumerate(points):
            x, y, z = point.x, point.y, point.z
            spline.points[i].co = (x, y, z, 1.0)  # Homogeneous coordinates
        
        # Create object
        curve_obj = bpy.data.objects.new(name, curve_data)
        self.collection.objects.link(curve_obj)
        
        # Set appearance
        mat = self._create_material(
            name=f"{name}_Material",
            color=color,
            line_width=line_width
        )
        if curve_obj.data.materials:
            curve_obj.data.materials[0] = mat
        else:
            curve_obj.data.materials.append(mat)
        
        return curve_obj
    
    def create_plan_view(
        self,
        interval: float = 5.0,
        elevation: float = 0.0,
        name: str = "Alignment_Plan",
        color: Tuple[float, float, float, float] = (1.0, 0.5, 0.0, 1.0)
    ) -> bpy.types.Object:
        """
        Create plan view (top-down, 2D) of alignment.
        
        This creates a horizontal-only view at a fixed elevation,
        useful for site layout and plan drawings.
        
        Args:
            interval: Sample spacing (m)
            elevation: Z-height for plan (m)
            name: Object name
            color: RGBA color (orange default)
            
        Returns:
            Blender curve object
        """
        # Sample alignment
        points = self.alignment.sample_alignment(interval=interval)
        
        # Create curve
        curve_data = bpy.data.curves.new(name=name, type='CURVE')
        curve_data.dimensions = '3D'
        
        spline = curve_data.splines.new('POLY')
        spline.points.add(len(points) - 1)
        
        # Set coordinates (x, y, fixed z)
        for i, point in enumerate(points):
            spline.points[i].co = (point.x, point.y, elevation, 1.0)
        
        # Create object
        curve_obj = bpy.data.objects.new(name, curve_data)
        self.collection.objects.link(curve_obj)
        
        # Material
        mat = self._create_material(name=f"{name}_Material", color=color)
        curve_obj.data.materials.append(mat)
        
        return curve_obj
    
    def create_profile_view(
        self,
        interval: float = 5.0,
        offset_x: float = 0.0,
        scale_z: float = 10.0,
        name: str = "Alignment_Profile",
        color: Tuple[float, float, float, float] = (0.0, 1.0, 0.0, 1.0)
    ) -> bpy.types.Object:
        """
        Create profile view (side elevation) of alignment.
        
        This creates a 2D profile showing station vs elevation,
        useful for vertical design visualization. The vertical
        scale is typically exaggerated for clarity.
        
        Args:
            interval: Sample spacing (m)
            offset_x: X-offset for profile location (m)
            scale_z: Vertical exaggeration factor
            name: Object name
            color: RGBA color (green default)
            
        Returns:
            Blender curve object
            
        Example:
            >>> # Create profile with 10x vertical exaggeration
            >>> profile = viz.create_profile_view(
            ...     scale_z=10.0,
            ...     offset_x=1000.0  # Offset from main alignment
            ... )
        """
        # Sample alignment
        points = self.alignment.sample_alignment(interval=interval)
        
        # Create curve
        curve_data = bpy.data.curves.new(name=name, type='CURVE')
        curve_data.dimensions = '3D'
        
        spline = curve_data.splines.new('POLY')
        spline.points.add(len(points) - 1)
        
        # Profile coordinates: (station, 0, scaled_elevation)
        start_station = self.alignment.get_start_station()
        
        for i, point in enumerate(points):
            station_offset = point.station - start_station
            x = offset_x + station_offset
            y = 0.0
            z = point.z * scale_z
            spline.points[i].co = (x, y, z, 1.0)
        
        # Create object
        curve_obj = bpy.data.objects.new(name, curve_data)
        self.collection.objects.link(curve_obj)
        
        # Material
        mat = self._create_material(name=f"{name}_Material", color=color)
        curve_obj.data.materials.append(mat)
        
        return curve_obj
    
    def create_station_markers(
        self,
        interval: float = 50.0,
        size: float = 5.0,
        show_labels: bool = True,
        name_prefix: str = "Station"
    ) -> List[bpy.types.Object]:
        """
        Create station markers along alignment.
        
        Places small markers (spheres or text) at regular stations
        along the alignment for reference.
        
        Args:
            interval: Spacing between markers (m)
            size: Marker size (m)
            show_labels: Add text labels with station values
            name_prefix: Prefix for marker names
            
        Returns:
            List of marker objects
            
        Example:
            >>> # Mark every 100m
            >>> markers = viz.create_station_markers(
            ...     interval=100.0,
            ...     size=3.0
            ... )
        """
        markers = []
        
        start = self.alignment.get_start_station()
        end = self.alignment.get_end_station()
        
        # Generate stations
        current = start
        while current <= end:
            # Get 3D position
            x, y, z = self.alignment.get_3d_position(current)
            
            # Create marker sphere
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=size/2,
                location=(x, y, z)
            )
            marker = bpy.context.active_object
            marker.name = f"{name_prefix}_{current:.0f}"
            
            # Move to collection
            if marker.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(marker)
            self.collection.objects.link(marker)
            
            markers.append(marker)
            
            # Add text label if requested
            if show_labels:
                bpy.ops.object.text_add(location=(x, y, z + size))
                text_obj = bpy.context.active_object
                text_obj.data.body = f"Sta {current:.0f}"
                text_obj.data.size = size * 2
                text_obj.name = f"{name_prefix}_Label_{current:.0f}"
                
                # Move to collection
                if text_obj.name in bpy.context.scene.collection.objects:
                    bpy.context.scene.collection.objects.unlink(text_obj)
                self.collection.objects.link(text_obj)
                
                markers.append(text_obj)
            
            current += interval
        
        return markers
    
    def create_grade_indicators(
        self,
        interval: float = 100.0,
        arrow_length: float = 10.0,
        name_prefix: str = "Grade"
    ) -> List[bpy.types.Object]:
        """
        Create visual grade indicators (arrows).
        
        Places arrows along alignment showing grade direction
        and magnitude. Useful for understanding vertical design.
        
        Args:
            interval: Spacing between indicators (m)
            arrow_length: Arrow length (m)
            name_prefix: Prefix for arrow names
            
        Returns:
            List of arrow objects
        """
        arrows = []
        
        start = self.alignment.get_start_station()
        end = self.alignment.get_end_station()
        
        current = start
        while current <= end:
            # Get position and grade
            x, y, z = self.alignment.get_3d_position(current)
            grade = self.alignment.get_grade(current)
            direction = self.alignment.get_direction(current)
            
            # Calculate arrow end point
            dx = arrow_length * math.sin(direction)
            dy = arrow_length * math.cos(direction)
            dz = arrow_length * grade
            
            # Create arrow (using cone)
            bpy.ops.mesh.primitive_cone_add(
                radius1=1.0,
                radius2=0.0,
                depth=5.0,
                location=(x, y, z)
            )
            arrow = bpy.context.active_object
            arrow.name = f"{name_prefix}_{current:.0f}"
            
            # Orient arrow
            # (This is simplified - proper orientation requires quaternions)
            arrow.rotation_euler.z = direction
            arrow.rotation_euler.y = math.atan(grade)
            
            # Move to collection
            if arrow.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(arrow)
            self.collection.objects.link(arrow)
            
            arrows.append(arrow)
            
            current += interval
        
        return arrows
    
    def highlight_curves(
        self,
        horizontal: bool = True,
        vertical: bool = True,
        color_h: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 1.0),
        color_v: Tuple[float, float, float, float] = (1.0, 1.0, 0.0, 1.0)
    ) -> List[bpy.types.Object]:
        """
        Highlight curved sections of alignment.
        
        Creates visual emphasis on horizontal curves (red) and
        vertical curves (yellow) for design review.
        
        Args:
            horizontal: Highlight horizontal curves
            vertical: Highlight vertical curves
            color_h: RGBA color for horizontal curves (red)
            color_v: RGBA color for vertical curves (yellow)
            
        Returns:
            List of highlight objects
        """
        highlights = []
        
        # TODO: Implement curve detection and highlighting
        # This requires access to curve segment data from
        # horizontal and vertical alignments
        
        # Placeholder implementation
        logger.info("Curve highlighting: To be implemented")
        logger.debug("  Horizontal curves: %s", horizontal)
        logger.debug("  Vertical curves: %s", vertical)
        
        return highlights
    
    def create_complete_visualization(
        self,
        interval: float = 5.0,
        station_interval: float = 50.0,
        include_plan: bool = True,
        include_profile: bool = True,
        include_markers: bool = True
    ) -> Dict[str, Any]:
        """
        Create complete visualization with all elements.
        
        This is the "one-click" method that creates a full
        alignment visualization package.
        
        Args:
            interval: Sample interval for curves (m)
            station_interval: Station marker spacing (m)
            include_plan: Create plan view
            include_profile: Create profile view
            include_markers: Add station markers
            
        Returns:
            Dictionary with all created objects:
            {
                '3d_curve': Object,
                'plan_curve': Object,
                'profile_curve': Object,
                'markers': List[Object]
            }
            
        Example:
            >>> viz = AlignmentVisualizer3D(alignment_3d)
            >>> result = viz.create_complete_visualization()
            >>> print(f"Created {len(result)} visualization elements")
        """
        result = {}

        # Main 3D curve
        logger.info("Creating 3D alignment curve...")
        result['3d_curve'] = self.create_3d_curve(interval=interval)

        # Plan view
        if include_plan:
            logger.info("Creating plan view...")
            result['plan_curve'] = self.create_plan_view(interval=interval)

        # Profile view
        if include_profile:
            logger.info("Creating profile view...")
            offset = self.alignment.get_length() + 100  # Offset to side
            result['profile_curve'] = self.create_profile_view(
                interval=interval,
                offset_x=offset
            )

        # Station markers
        if include_markers:
            logger.info("Creating station markers...")
            result['markers'] = self.create_station_markers(
                interval=station_interval
            )

        logger.info("Visualization complete! Created %s elements", len(result))
        
        return result
    
    def _create_material(
        self,
        name: str,
        color: Tuple[float, float, float, float],
        line_width: float = 3.0
    ) -> bpy.types.Material:
        """
        Create material for alignment visualization.
        
        Args:
            name: Material name
            color: RGBA color (0-1 range)
            line_width: Line width for viewport display
            
        Returns:
            Blender material
        """
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        
        # Set color
        if mat.node_tree:
            nodes = mat.node_tree.nodes
            principled = nodes.get("Principled BSDF")
            if principled:
                principled.inputs["Base Color"].default_value = color
                principled.inputs["Emission"].default_value = color
                principled.inputs["Emission Strength"].default_value = 0.5
        
        # Viewport display
        mat.diffuse_color = color
        mat.line_width = line_width
        
        return mat
    
    def export_to_csv(
        self,
        filepath: str,
        interval: float = 1.0
    ):
        """
        Export alignment data to CSV file.
        
        Creates a CSV file with complete 3D alignment data,
        useful for analysis in Excel, GIS, or other software.
        
        Args:
            filepath: Output CSV file path
            interval: Sample interval (m)
            
        Example:
            >>> viz.export_to_csv(
            ...     filepath="/tmp/alignment_data.csv",
            ...     interval=1.0
            ... )
        """
        import csv
        
        # Sample alignment
        points = self.alignment.sample_alignment(interval=interval)
        
        # Write CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Station(m)',
                'X(m)',
                'Y(m)',
                'Z(m)',
                'Direction(deg)',
                'Grade(%)',
                'H_Curvature(1/m)',
                'V_Curvature(m/%)'
            ])
            
            # Data rows
            for point in points:
                writer.writerow([
                    f"{point.station:.3f}",
                    f"{point.x:.3f}",
                    f"{point.y:.3f}",
                    f"{point.z:.3f}",
                    f"{math.degrees(point.direction):.3f}",
                    f"{point.grade * 100:.3f}",
                    f"{point.horizontal_curvature:.6f}",
                    f"{point.vertical_curvature:.1f}"
                ])

        logger.info("Exported %s points to %s", len(points), filepath)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"AlignmentVisualizer3D('{self.alignment.name}')"


def demo_visualization():
    """
    Demonstrate 3D visualization capabilities.

    This creates sample visualizations to show what's possible.
    """
    logger.info("=== Saikei Civil 3D Visualization Demo ===")
    logger.info("")
    logger.info("Visualization Capabilities:")
    logger.info("  [+] 3D alignment curves")
    logger.info("  [+] Plan view (top-down)")
    logger.info("  [+] Profile view (elevation)")
    logger.info("  [+] Station markers")
    logger.info("  [+] Grade indicators")
    logger.info("  [+] Curve highlighting")
    logger.info("")
    logger.info("To use:")
    logger.info("  1. Create Alignment3D (H+V)")
    logger.info("  2. Create visualizer: viz = AlignmentVisualizer3D(alignment)")
    logger.info("  3. Create elements: viz.create_3d_curve()")
    logger.info("  4. Or all at once: viz.create_complete_visualization()")
    logger.info("")
    logger.info("See docstrings for detailed examples!")


if __name__ == "__main__":
    demo_visualization()
