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
IFC Rebuilder Registry

Provides a global registry for functions that rebuild Python/Blender state from IFC entities.
This is the core mechanism for ensuring IFC remains the single source of truth.

Architecture:
    IFC File (reverted by undo) → Rebuilder Functions → Python State → Blender Visualization

Each domain module (alignments, cross-sections, corridors, etc.) registers its own rebuilder
function that knows how to scan the IFC file and recreate all Python objects and Blender
visualizations from the IFC entities.

Usage:
    # In alignment module initialization:
    from .ifc_manager.rebuilder_registry import IfcRebuilderRegistry
    IfcRebuilderRegistry.register("alignment", rebuild_alignments_from_ifc)

    # After undo/redo:
    IfcRebuilderRegistry.rebuild_all(ifc_file)
"""

from typing import Dict, Callable, Optional, List, Any
from dataclasses import dataclass
from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RebuilderInfo:
    """Information about a registered rebuilder function."""
    name: str
    rebuilder_func: Callable
    priority: int  # Lower = runs first (useful for dependencies)
    description: str


class IfcRebuilderRegistry:
    """
    Central registry for IFC-to-Python/Blender rebuilder functions.

    Each module registers a function that can scan the IFC file and rebuild
    all its Python objects and Blender visualizations from the IFC entities.

    This ensures IFC remains the single source of truth - after undo/redo,
    we rebuild everything from the (now-reverted) IFC file.
    """

    # Registry of rebuilder functions: name -> RebuilderInfo
    _rebuilders: Dict[str, RebuilderInfo] = {}

    # Track if a rebuild is in progress to prevent recursion
    _rebuilding: bool = False

    @classmethod
    def register(
        cls,
        name: str,
        rebuilder_func: Callable,
        priority: int = 100,
        description: str = ""
    ) -> None:
        """
        Register a rebuilder function for a specific domain.

        Args:
            name: Unique name for this rebuilder (e.g., "alignment", "cross_section")
            rebuilder_func: Function that takes (ifc_file) and rebuilds state
            priority: Execution order (lower = first). Use for dependencies.
                     Example: 10=project, 50=alignments, 100=corridors
            description: Human-readable description for debugging
        """
        if name in cls._rebuilders:
            logger.warning("Overwriting existing rebuilder: %s", name)

        cls._rebuilders[name] = RebuilderInfo(
            name=name,
            rebuilder_func=rebuilder_func,
            priority=priority,
            description=description or f"Rebuilder for {name}"
        )

        logger.debug(
            "Registered rebuilder '%s' with priority %d",
            name, priority
        )

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Unregister a rebuilder function.

        Args:
            name: Name of the rebuilder to remove

        Returns:
            True if removed, False if not found
        """
        if name in cls._rebuilders:
            del cls._rebuilders[name]
            logger.debug("Unregistered rebuilder: %s", name)
            return True
        return False

    @classmethod
    def rebuild_all(cls, ifc_file: Any) -> Dict[str, bool]:
        """
        Execute all registered rebuilders to rebuild state from IFC.

        This is called after undo/redo to ensure Python/Blender state
        matches the (reverted) IFC file.

        Args:
            ifc_file: The IfcOpenShell file object

        Returns:
            Dict mapping rebuilder names to success status
        """
        if cls._rebuilding:
            logger.warning("Rebuild already in progress, skipping")
            return {}

        if not ifc_file:
            logger.warning("No IFC file provided for rebuild")
            return {}

        cls._rebuilding = True
        results: Dict[str, bool] = {}

        try:
            # Sort rebuilders by priority
            sorted_rebuilders = sorted(
                cls._rebuilders.values(),
                key=lambda r: r.priority
            )

            logger.info(
                "Rebuilding state from IFC with %d rebuilders",
                len(sorted_rebuilders)
            )

            for rebuilder in sorted_rebuilders:
                try:
                    logger.debug(
                        "Running rebuilder '%s' (priority %d)",
                        rebuilder.name, rebuilder.priority
                    )

                    rebuilder.rebuilder_func(ifc_file)
                    results[rebuilder.name] = True

                    logger.debug("Rebuilder '%s' completed", rebuilder.name)

                except Exception as e:
                    logger.error(
                        "Rebuilder '%s' failed: %s",
                        rebuilder.name, e
                    )
                    results[rebuilder.name] = False

            success_count = sum(1 for v in results.values() if v)
            logger.info(
                "Rebuild complete: %d/%d rebuilders succeeded",
                success_count, len(results)
            )

        finally:
            cls._rebuilding = False

        return results

    @classmethod
    def rebuild_one(cls, name: str, ifc_file: Any) -> bool:
        """
        Execute a single named rebuilder.

        Args:
            name: Name of the rebuilder to run
            ifc_file: The IfcOpenShell file object

        Returns:
            True if successful, False if failed or not found
        """
        if name not in cls._rebuilders:
            logger.warning("Rebuilder not found: %s", name)
            return False

        try:
            cls._rebuilders[name].rebuilder_func(ifc_file)
            return True
        except Exception as e:
            logger.error("Rebuilder '%s' failed: %s", name, e)
            return False

    @classmethod
    def list_rebuilders(cls) -> List[str]:
        """Get list of registered rebuilder names."""
        return list(cls._rebuilders.keys())

    @classmethod
    def get_info(cls, name: str) -> Optional[RebuilderInfo]:
        """Get info about a specific rebuilder."""
        return cls._rebuilders.get(name)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered rebuilders. Use for testing/reset."""
        cls._rebuilders.clear()
        logger.debug("Cleared all rebuilders")
