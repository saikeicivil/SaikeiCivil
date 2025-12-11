# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under the GNU General Public License v3
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
VerticalAlignment tool implementation - Blender-specific vertical alignment operations.

This tool wraps the core vertical_alignment package and provides the standard
interface for vertical alignment operations, plus Blender-specific functionality
like creating visualization empties.

Usage:
    from saikei_civil.tool import VerticalAlignment

    # Create a vertical alignment
    vertical = VerticalAlignment.create(horizontal_alignment, pvis)

    # Get elevation at a station
    elev = VerticalAlignment.get_elevation_at_station(alignment, station)

    # Create Blender visualization
    empty = VerticalAlignment.create_blender_empty(vertical_entity, horizontal_alignment)
"""
from typing import TYPE_CHECKING, Optional, List, Dict, Any

import bpy

if TYPE_CHECKING:
    import ifcopenshell

# Import will fail if ifcopenshell not installed - that's expected
try:
    import ifcopenshell
    HAS_IFCOPENSHELL = True
except ImportError:
    HAS_IFCOPENSHELL = False

from ..core import tool as core_tool


class VerticalAlignment(core_tool.VerticalAlignment):
    """
    Blender-specific vertical alignment operations.

    This class wraps the core vertical_alignment package and provides the
    standard interface for all vertical alignment operations in Saikei Civil.
    """

    @classmethod
    def create(
        cls,
        horizontal: "ifcopenshell.entity_instance",
        pvis: List[Dict]
    ) -> "ifcopenshell.entity_instance":
        """
        Create a vertical alignment for a horizontal alignment.

        Args:
            horizontal: The parent IfcAlignment entity
            pvis: List of PVI dictionaries with keys:
                - station: Station value
                - elevation: Elevation value
                - curve_length: Vertical curve length (0 for no curve)

        Returns:
            The IfcAlignmentVertical entity
        """
        if not HAS_IFCOPENSHELL:
            raise RuntimeError("ifcopenshell not installed")

        from ..core.ifc_manager import NativeIfcManager
        from ..core.vertical_alignment import VerticalAlignment as CoreVerticalAlignment

        ifc = NativeIfcManager.get_file()
        if ifc is None:
            raise RuntimeError("No IFC file loaded. Create or open a file first.")

        # Get alignment name
        name = horizontal.Name if hasattr(horizontal, 'Name') else "Vertical Alignment"

        # Create the core vertical alignment
        valign = CoreVerticalAlignment(name=f"{name} Profile")

        # Add PVIs
        for pvi in pvis:
            station = pvi.get('station', 0.0)
            elevation = pvi.get('elevation', 0.0)
            curve_length = pvi.get('curve_length', 0.0)
            valign.add_pvi(station, elevation, curve_length=curve_length)

        # Export to IFC
        vertical_entity = valign.to_ifc(ifc, horizontal)

        # Create Blender visualization
        cls.create_blender_empty(vertical_entity, horizontal)

        return vertical_entity

    @classmethod
    def get_pvis(cls, alignment: "ifcopenshell.entity_instance") -> List[Dict]:
        """
        Get PVI data from alignment.

        Args:
            alignment: The IfcAlignment entity (parent of vertical)

        Returns:
            List of PVI dictionaries
        """
        if not HAS_IFCOPENSHELL:
            return []

        from ..core.vertical_alignment import VerticalAlignment as CoreVerticalAlignment

        # Load vertical alignment from IFC
        valign = CoreVerticalAlignment.from_ifc(alignment)
        if valign is None:
            return []

        result = []
        for pvi in valign.pvis:
            result.append({
                'station': pvi.station,
                'elevation': pvi.elevation,
                'curve_length': pvi.curve_length,
                'grade_in': pvi.grade_in,
                'grade_out': pvi.grade_out,
            })

        return result

    @classmethod
    def set_pvis(
        cls,
        alignment: "ifcopenshell.entity_instance",
        pvis: List[Dict]
    ) -> None:
        """
        Update vertical alignment geometry from PVI data.

        Args:
            alignment: The IfcAlignment entity
            pvis: Updated PVI data
        """
        # This would require recreating the vertical alignment
        # For now, raise NotImplementedError
        raise NotImplementedError("PVI update not yet implemented. Recreate alignment.")

    @classmethod
    def get_vertical_segments(cls, alignment: "ifcopenshell.entity_instance") -> List[Dict]:
        """
        Get computed vertical segments.

        Args:
            alignment: The IfcAlignment entity

        Returns:
            List of segment dictionaries
        """
        if not HAS_IFCOPENSHELL:
            return []

        from ..core.vertical_alignment import VerticalAlignment as CoreVerticalAlignment

        valign = CoreVerticalAlignment.from_ifc(alignment)
        if valign is None:
            return []

        result = []
        for seg in valign.segments:
            result.append({
                'start_station': seg.start_station,
                'end_station': seg.end_station,
                'start_elevation': seg.start_elevation,
                'end_elevation': seg.end_elevation,
                'length': seg.length,
                'type': type(seg).__name__,
            })

        return result

    @classmethod
    def get_elevation_at_station(
        cls,
        alignment: "ifcopenshell.entity_instance",
        station: float
    ) -> Optional[float]:
        """
        Get elevation at a station.

        Args:
            alignment: The IfcAlignment entity
            station: Station value

        Returns:
            Elevation, or None if station is out of range
        """
        if not HAS_IFCOPENSHELL:
            return None

        from ..core.vertical_alignment import VerticalAlignment as CoreVerticalAlignment

        valign = CoreVerticalAlignment.from_ifc(alignment)
        if valign is None:
            return None

        try:
            return valign.get_elevation(station)
        except (ValueError, IndexError):
            return None

    @classmethod
    def get_grade_at_station(
        cls,
        alignment: "ifcopenshell.entity_instance",
        station: float
    ) -> Optional[float]:
        """
        Get grade (slope) at a station.

        Args:
            alignment: The IfcAlignment entity
            station: Station value

        Returns:
            Grade as decimal (e.g., 0.02 for 2%), or None if out of range
        """
        if not HAS_IFCOPENSHELL:
            return None

        from ..core.vertical_alignment import VerticalAlignment as CoreVerticalAlignment

        valign = CoreVerticalAlignment.from_ifc(alignment)
        if valign is None:
            return None

        try:
            return valign.get_grade(station)
        except (ValueError, IndexError):
            return None

    # =========================================================================
    # Blender-Specific Methods (not in core interface)
    # =========================================================================

    @classmethod
    def create_blender_empty(
        cls,
        vertical_entity: "ifcopenshell.entity_instance",
        horizontal_alignment: Optional["ifcopenshell.entity_instance"] = None
    ) -> bpy.types.Object:
        """
        Create a Blender Empty object to represent the vertical alignment.

        This is Blender-specific functionality that creates the visual
        representation of the vertical alignment in the 3D viewport.

        Args:
            vertical_entity: The IFC IfcAlignmentVertical entity
            horizontal_alignment: Optional parent horizontal alignment IFC entity

        Returns:
            Blender Empty object
        """
        from ..core.ifc_manager import NativeIfcManager

        # Get name from entity
        name = "Vertical Alignment"
        if hasattr(vertical_entity, 'Name') and vertical_entity.Name:
            name = vertical_entity.Name

        # Create Empty object
        empty_name = f"V: {name}"
        empty = bpy.data.objects.new(empty_name, None)
        empty.empty_display_type = 'SINGLE_ARROW'
        empty.empty_display_size = 1.0

        # Link to IFC entity
        NativeIfcManager.link_object(empty, vertical_entity)

        # Add to project collection
        project_collection = NativeIfcManager.get_project_collection()
        if project_collection:
            project_collection.objects.link(empty)

        # Parent to horizontal alignment if it exists
        if horizontal_alignment:
            horizontal_ifc_id = horizontal_alignment.id()

            for obj in bpy.data.objects:
                obj_ifc_id = obj.get("ifc_definition_id")
                obj_ifc_class = obj.get("ifc_class")
                if obj_ifc_id == horizontal_ifc_id and obj_ifc_class == "IfcAlignment":
                    empty.parent = obj
                    break

        return empty

    @classmethod
    def get_core_alignment(
        cls,
        alignment: "ifcopenshell.entity_instance"
    ) -> Optional[Any]:
        """
        Get the core VerticalAlignment object for an IFC entity.

        Args:
            alignment: The IfcAlignment entity

        Returns:
            Core VerticalAlignment object, or None if not found
        """
        if not HAS_IFCOPENSHELL:
            return None

        from ..core.vertical_alignment import VerticalAlignment as CoreVerticalAlignment

        return CoreVerticalAlignment.from_ifc(alignment)


__all__ = ["VerticalAlignment"]
