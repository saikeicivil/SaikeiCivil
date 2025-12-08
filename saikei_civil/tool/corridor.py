# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under Apache License 2.0
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
Corridor tool implementation - Blender-specific corridor operations.

This tool wraps the core corridor functionality and provides the standard
interface for 3D corridor generation from alignments and cross-sections.

Usage:
    from saikei_civil.tool import Corridor

    # Create a corridor
    corridor = Corridor.create(
        name="Main Road Corridor",
        alignment=alignment_entity,
        assembly=road_assembly,
        start_station=10000.0,
        end_station=11000.0,
        interval=10.0
    )

    # Generate mesh
    mesh_obj = Corridor.generate_mesh(corridor)
"""
from typing import TYPE_CHECKING, Optional, List, Any

import bpy

if TYPE_CHECKING:
    import ifcopenshell

try:
    import ifcopenshell
    HAS_IFCOPENSHELL = True
except ImportError:
    HAS_IFCOPENSHELL = False

from ..core import tool as core_tool


class Corridor(core_tool.Corridor):
    """
    Blender-specific corridor operations.

    This class wraps the core corridor functionality and provides
    the standard interface for 3D corridor generation in Saikei Civil.
    """

    # In-memory storage for corridors
    _corridors: dict = {}

    @classmethod
    def create(
        cls,
        name: str,
        alignment: "ifcopenshell.entity_instance",
        assembly: Any,
        start_station: float,
        end_station: float,
        interval: float = 10.0
    ) -> Any:
        """
        Create a corridor from alignment and assembly.

        Args:
            name: Corridor name
            alignment: The IfcAlignment entity
            assembly: The road assembly
            start_station: Starting station
            end_station: Ending station
            interval: Sampling interval for cross-sections

        Returns:
            The corridor object
        """
        from ..core.native_ifc_corridor import NativeIfcCorridor

        corridor = NativeIfcCorridor(
            name=name,
            alignment=alignment,
            assembly=assembly,
            start_station=start_station,
            end_station=end_station,
            interval=interval
        )

        cls._corridors[name] = corridor
        return corridor

    @classmethod
    def get_corridor(cls, name: str) -> Optional[Any]:
        """
        Get a corridor by name.

        Args:
            name: Corridor name

        Returns:
            The corridor, or None if not found
        """
        return cls._corridors.get(name)

    @classmethod
    def list_corridors(cls) -> List[str]:
        """
        List all corridor names.

        Returns:
            List of corridor names
        """
        return list(cls._corridors.keys())

    @classmethod
    def generate_mesh(
        cls,
        corridor: Any,
        lod: int = 1
    ) -> Optional[bpy.types.Object]:
        """
        Generate Blender mesh for corridor.

        Args:
            corridor: The corridor object
            lod: Level of detail (0=low, 1=medium, 2=high)

        Returns:
            The mesh object
        """
        from ..core.corridor_mesh_generator import CorridorMeshGenerator
        from ..core.ifc_manager import NativeIfcManager

        if corridor is None:
            return None

        generator = CorridorMeshGenerator(corridor)
        mesh_obj = generator.generate(lod=lod)

        if mesh_obj:
            # Link to IFC if corridor has an entity
            if hasattr(corridor, 'ifc_entity') and corridor.ifc_entity:
                NativeIfcManager.link_object(mesh_obj, corridor.ifc_entity)

        return mesh_obj

    @classmethod
    def update_mesh(cls, corridor: Any) -> None:
        """
        Update existing mesh after corridor changes.

        Args:
            corridor: The corridor object
        """
        if hasattr(corridor, 'update_mesh'):
            corridor.update_mesh()

    @classmethod
    def export_to_ifc(cls, corridor: Any) -> Optional["ifcopenshell.entity_instance"]:
        """
        Export corridor to IFC entities.

        Args:
            corridor: The corridor object

        Returns:
            The IfcSectionedSolidHorizontal or equivalent entity
        """
        if not HAS_IFCOPENSHELL:
            return None

        from ..core.ifc_manager import NativeIfcManager

        ifc = NativeIfcManager.get_file()
        if ifc is None:
            return None

        if hasattr(corridor, 'to_ifc'):
            return corridor.to_ifc(ifc)

        return None


__all__ = ["Corridor"]
