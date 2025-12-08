# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under Apache License 2.0
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
CrossSection tool implementation - Blender-specific cross-section operations.

This tool wraps the core cross-section functionality and provides the standard
interface for road assembly creation and cross-section profile generation.

Usage:
    from saikei_civil.tool import CrossSection

    # Create an assembly
    assembly = CrossSection.create_assembly("Main Road")

    # Add components
    CrossSection.add_component(assembly, 'LANE', 'RIGHT', width=3.6)

    # Get profile at station
    profile = CrossSection.get_profile_at_station(assembly, 10500.0)
"""
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Tuple

import bpy

if TYPE_CHECKING:
    import ifcopenshell

try:
    import ifcopenshell
    HAS_IFCOPENSHELL = True
except ImportError:
    HAS_IFCOPENSHELL = False

from ..core import tool as core_tool


class CrossSection(core_tool.CrossSection):
    """
    Blender-specific cross-section operations.

    This class wraps the core cross-section functionality and provides
    the standard interface for road assembly operations in Saikei Civil.
    """

    # In-memory storage for assemblies (will be persisted to IFC)
    _assemblies: Dict[str, Any] = {}

    @classmethod
    def create_assembly(cls, name: str) -> Any:
        """
        Create a new road assembly.

        Args:
            name: Assembly name

        Returns:
            The assembly object
        """
        from ..core.native_ifc_cross_section import CrossSectionAssembly

        assembly = CrossSectionAssembly(name)
        cls._assemblies[name] = assembly
        return assembly

    @classmethod
    def get_assembly(cls, name: str) -> Optional[Any]:
        """
        Get an existing assembly by name.

        Args:
            name: Assembly name

        Returns:
            The assembly, or None if not found
        """
        return cls._assemblies.get(name)

    @classmethod
    def list_assemblies(cls) -> List[str]:
        """
        List all assembly names.

        Returns:
            List of assembly names
        """
        return list(cls._assemblies.keys())

    @classmethod
    def add_component(
        cls,
        assembly: Any,
        component_type: str,
        side: str,
        **kwargs
    ) -> Any:
        """
        Add a component to an assembly.

        Args:
            assembly: The road assembly
            component_type: Type of component (LANE, SHOULDER, CURB, DITCH, etc.)
            side: LEFT or RIGHT
            **kwargs: Component-specific parameters (width, cross_slope, etc.)

        Returns:
            The created component
        """
        if hasattr(assembly, 'add_component'):
            return assembly.add_component(component_type, side, **kwargs)
        return None

    @classmethod
    def get_profile_at_station(
        cls,
        assembly: Any,
        station: float,
        alignment: "ifcopenshell.entity_instance" = None
    ) -> List[Tuple[float, float]]:
        """
        Get cross-section profile points at a station.

        Args:
            assembly: The road assembly
            station: Station value
            alignment: Optional alignment for superelevation, etc.

        Returns:
            List of (offset, elevation) tuples from centerline
        """
        if hasattr(assembly, 'get_profile_at_station'):
            return assembly.get_profile_at_station(station, alignment)
        return []

    @classmethod
    def apply_template(cls, assembly: Any, template_name: str) -> None:
        """
        Apply a standard template to an assembly.

        Args:
            assembly: The road assembly
            template_name: Name of template (e.g., "AASHTO_2LANE_RURAL")
        """
        if hasattr(assembly, 'apply_template'):
            assembly.apply_template(template_name)

    # =========================================================================
    # Blender-Specific Methods
    # =========================================================================

    @classmethod
    def create_blender_visualization(
        cls,
        assembly: Any,
        station: float = 0.0
    ) -> Optional[bpy.types.Object]:
        """
        Create a Blender mesh visualization of a cross-section.

        Args:
            assembly: The road assembly
            station: Station for the cross-section view

        Returns:
            Blender mesh object, or None
        """
        from ..core.ifc_manager import NativeIfcManager

        profile = cls.get_profile_at_station(assembly, station)
        if not profile:
            return None

        # Create mesh from profile points
        verts = [(p[0], 0, p[1]) for p in profile]
        edges = [(i, i + 1) for i in range(len(verts) - 1)]

        mesh = bpy.data.meshes.new(f"{assembly.name}_XS_{station:.0f}")
        mesh.from_pydata(verts, edges, [])
        mesh.update()

        obj = bpy.data.objects.new(f"{assembly.name} XS @{station:.0f}", mesh)

        # Add to collection
        collection = NativeIfcManager.get_project_collection()
        if collection:
            collection.objects.link(obj)

        return obj


__all__ = ["CrossSection"]
