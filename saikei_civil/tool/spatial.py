# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under the GNU General Public License v3
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
Spatial tool implementation - IFC spatial structure operations.

This tool wraps the NativeIfcManager and provides the standard interface
for managing the IFC spatial hierarchy: Project > Site > Road.

Usage:
    from saikei_civil.tool import Spatial

    # Ensure spatial structure exists
    project, site, road = Spatial.ensure_spatial_structure()

    # Assign an alignment to the road
    Spatial.assign_to_road(alignment_entity)
"""
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    import ifcopenshell

try:
    import ifcopenshell
    HAS_IFCOPENSHELL = True
except ImportError:
    HAS_IFCOPENSHELL = False

from ..core import tool as core_tool


class Spatial(core_tool.Spatial):
    """
    IFC spatial structure operations.

    This class wraps NativeIfcManager and provides the standard interface
    for managing the IFC spatial hierarchy in Saikei Civil.
    """

    @classmethod
    def get_project(cls) -> Optional["ifcopenshell.entity_instance"]:
        """Get the IfcProject entity."""
        if not HAS_IFCOPENSHELL:
            return None

        from ..core.ifc_manager import NativeIfcManager
        return NativeIfcManager.get_project()

    @classmethod
    def get_site(cls) -> Optional["ifcopenshell.entity_instance"]:
        """Get the IfcSite entity."""
        if not HAS_IFCOPENSHELL:
            return None

        from ..core.ifc_manager import NativeIfcManager
        return NativeIfcManager.get_site()

    @classmethod
    def get_road(cls) -> Optional["ifcopenshell.entity_instance"]:
        """Get the IfcRoad entity."""
        if not HAS_IFCOPENSHELL:
            return None

        from ..core.ifc_manager import NativeIfcManager
        return NativeIfcManager.get_road()

    @classmethod
    def ensure_spatial_structure(cls) -> Tuple[
        Optional["ifcopenshell.entity_instance"],
        Optional["ifcopenshell.entity_instance"],
        Optional["ifcopenshell.entity_instance"]
    ]:
        """
        Ensure the spatial structure exists (Project > Site > Road).

        Creates missing entities as needed.

        Returns:
            Tuple of (project, site, road) entities
        """
        if not HAS_IFCOPENSHELL:
            return (None, None, None)

        from ..core.ifc_manager import NativeIfcManager
        from ..core import ifc_api

        ifc = NativeIfcManager.get_file()
        if ifc is None:
            # Create new file with spatial structure
            result = NativeIfcManager.new_file()
            return (result['project'], result['site'], result['road'])

        # Get or create entities
        project = NativeIfcManager.get_project()
        if project is None:
            project = ifc_api.create_project(ifc)

        site = NativeIfcManager.get_site()
        if site is None:
            site = ifc_api.create_site(ifc, project)

        road = NativeIfcManager.get_road()
        if road is None:
            road = ifc_api.create_road(ifc, site)

        # Update manager references
        NativeIfcManager.project = project
        NativeIfcManager.site = site
        NativeIfcManager.road = road

        return (project, site, road)

    @classmethod
    def assign_to_road(cls, entity: "ifcopenshell.entity_instance") -> None:
        """
        Assign an entity to the road container.

        Args:
            entity: Entity to assign (e.g., IfcAlignment)
        """
        if not HAS_IFCOPENSHELL:
            return

        from ..core.ifc_manager import NativeIfcManager

        NativeIfcManager.contain_alignment_in_road(entity)

    @classmethod
    def get_spatial_info(cls) -> dict:
        """
        Get information about the current spatial structure.

        Returns:
            Dictionary with project, site, road names and entity counts
        """
        from ..core.ifc_manager import NativeIfcManager

        return NativeIfcManager.get_info()


__all__ = ["Spatial"]
