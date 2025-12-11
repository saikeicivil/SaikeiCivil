# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under the GNU General Public License v3
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
Visualizer tool implementation - Blender visualization operations.

This tool provides the standard interface for creating and updating Blender
objects from IFC data, including alignment curves, PI markers, and more.

Usage:
    from saikei_civil.tool import Visualizer

    # Create alignment curve
    curve_obj = Visualizer.create_alignment_curve(alignment_entity)

    # Create PI markers
    markers = Visualizer.create_pi_markers(alignment_entity)

    # Update visualization after changes
    Visualizer.update_alignment(alignment_entity)
"""
from typing import TYPE_CHECKING, Optional, List

import bpy

if TYPE_CHECKING:
    import ifcopenshell

try:
    import ifcopenshell
    HAS_IFCOPENSHELL = True
except ImportError:
    HAS_IFCOPENSHELL = False

from ..core import tool as core_tool


class Visualizer(core_tool.Visualizer):
    """
    Blender visualization operations.

    This class provides the standard interface for creating and updating
    Blender objects from IFC alignment data.
    """

    @classmethod
    def create_alignment_curve(
        cls,
        alignment: "ifcopenshell.entity_instance",
        resolution: int = 100
    ) -> Optional[bpy.types.Object]:
        """
        Create a Blender curve from alignment data.

        Args:
            alignment: The IfcAlignment entity
            resolution: Points per curve segment

        Returns:
            The curve object
        """
        if not HAS_IFCOPENSHELL:
            return None

        from ..core.alignment_visualizer import AlignmentVisualizer
        from ..core.alignment_registry import get_alignment_by_entity

        # Get the alignment wrapper
        alignment_obj = get_alignment_by_entity(alignment)
        if alignment_obj is None:
            return None

        # Create or get visualizer
        if hasattr(alignment_obj, 'visualizer') and alignment_obj.visualizer:
            visualizer = alignment_obj.visualizer
        else:
            visualizer = AlignmentVisualizer(alignment_obj)
            alignment_obj.visualizer = visualizer

        # Create curve
        return visualizer.create_centerline_curve(resolution=resolution)

    @classmethod
    def create_pi_markers(
        cls,
        alignment: "ifcopenshell.entity_instance"
    ) -> List[bpy.types.Object]:
        """
        Create PI marker empties for an alignment.

        Args:
            alignment: The IfcAlignment entity

        Returns:
            List of marker objects
        """
        if not HAS_IFCOPENSHELL:
            return []

        from ..core.alignment_visualizer import AlignmentVisualizer
        from ..core.alignment_registry import get_alignment_by_entity

        alignment_obj = get_alignment_by_entity(alignment)
        if alignment_obj is None:
            return []

        if hasattr(alignment_obj, 'visualizer') and alignment_obj.visualizer:
            visualizer = alignment_obj.visualizer
        else:
            visualizer = AlignmentVisualizer(alignment_obj)
            alignment_obj.visualizer = visualizer

        return visualizer.create_pi_markers()

    @classmethod
    def create_station_markers(
        cls,
        alignment: "ifcopenshell.entity_instance",
        interval: float = 100.0
    ) -> List[bpy.types.Object]:
        """
        Create station marker objects along alignment.

        Args:
            alignment: The IfcAlignment entity
            interval: Station interval in meters

        Returns:
            List of marker objects
        """
        if not HAS_IFCOPENSHELL:
            return []

        from ..core.alignment_visualizer import AlignmentVisualizer
        from ..core.alignment_registry import get_alignment_by_entity

        alignment_obj = get_alignment_by_entity(alignment)
        if alignment_obj is None:
            return []

        if hasattr(alignment_obj, 'visualizer') and alignment_obj.visualizer:
            visualizer = alignment_obj.visualizer
        else:
            visualizer = AlignmentVisualizer(alignment_obj)
            alignment_obj.visualizer = visualizer

        return visualizer.create_station_markers(interval=interval)

    @classmethod
    def update_alignment(cls, alignment: "ifcopenshell.entity_instance") -> None:
        """
        Update visualization after alignment changes.

        Args:
            alignment: The IfcAlignment entity
        """
        if not HAS_IFCOPENSHELL:
            return

        from ..core.alignment_registry import get_alignment_by_entity

        alignment_obj = get_alignment_by_entity(alignment)
        if alignment_obj is None:
            return

        if hasattr(alignment_obj, 'visualizer') and alignment_obj.visualizer:
            alignment_obj.visualizer.update_visualizations()

    @classmethod
    def hide_pi_markers(cls, alignment: "ifcopenshell.entity_instance") -> None:
        """
        Hide PI markers for an alignment.

        Args:
            alignment: The IfcAlignment entity
        """
        from ..core.alignment_registry import get_alignment_by_entity

        alignment_obj = get_alignment_by_entity(alignment)
        if alignment_obj and hasattr(alignment_obj, 'visualizer') and alignment_obj.visualizer:
            alignment_obj.visualizer.hide_pi_markers()

    @classmethod
    def show_pi_markers(cls, alignment: "ifcopenshell.entity_instance") -> None:
        """
        Show PI markers for an alignment.

        Args:
            alignment: The IfcAlignment entity
        """
        from ..core.alignment_registry import get_alignment_by_entity

        alignment_obj = get_alignment_by_entity(alignment)
        if alignment_obj and hasattr(alignment_obj, 'visualizer') and alignment_obj.visualizer:
            alignment_obj.visualizer.show_pi_markers()


__all__ = ["Visualizer"]
