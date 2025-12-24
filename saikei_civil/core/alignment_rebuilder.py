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
Alignment Rebuilder for IFC Undo/Redo

Rebuilds all alignment Python objects and Blender visualizations from the IFC file.
This is called after undo/redo to ensure Python/Blender state matches the (reverted) IFC.

Architecture:
    IFC File (reverted by undo)
        ↓
    Scan for IfcAlignment entities
        ↓
    Clear existing Python alignment objects + Blender visualizations
        ↓
    Reconstruct NativeIfcAlignment from each IFC entity
        (uses _reconstruct_pis_from_segments() to extract PIs from IFC geometry)
        ↓
    Create new AlignmentVisualizer for each alignment
        ↓
    Rebuild Blender PI objects and segment curves

This ensures IFC remains the single source of truth.
"""

from typing import Optional, List, Set
from .logging_config import get_logger

logger = get_logger(__name__)


def rebuild_alignments_from_ifc(ifc_file) -> int:
    """
    Rebuild all alignment state from the IFC file.

    This function:
    1. Clears all existing Blender visualization objects for alignments
    2. Clears the Python alignment and visualizer registries
    3. Scans the IFC file for IfcAlignment entities
    4. Reconstructs NativeIfcAlignment objects (extracting PIs from IFC geometry)
    5. Creates new visualizers and Blender objects

    Args:
        ifc_file: The IfcOpenShell file object

    Returns:
        Number of alignments rebuilt
    """
    import bpy
    from .alignment_registry import (
        get_all_alignments,
        get_all_visualizers,
        clear_registry,
        register_alignment,
        register_visualizer,
    )
    from .horizontal_alignment.manager import NativeIfcAlignment

    logger.info("=== REBUILDING ALIGNMENTS FROM IFC ===")

    if not ifc_file:
        logger.warning("No IFC file provided")
        return 0

    # Step 1: Collect all alignment GlobalIds and existing Blender objects to clean up
    existing_alignment_ids: Set[str] = set()
    objects_to_remove: List[bpy.types.Object] = []

    # Get existing alignments before clearing
    existing_alignments = get_all_alignments()
    existing_visualizers = get_all_visualizers()

    for alignment in existing_alignments:
        try:
            existing_alignment_ids.add(alignment.alignment.GlobalId)
        except Exception:
            pass

    # Collect Blender objects to remove from existing visualizers
    for visualizer in existing_visualizers:
        try:
            # Collect PI objects
            for pi_obj in visualizer.pi_objects:
                try:
                    if pi_obj and pi_obj.name in bpy.data.objects:
                        objects_to_remove.append(pi_obj)
                except (ReferenceError, AttributeError):
                    pass

            # Collect segment objects
            for seg_obj in visualizer.segment_objects:
                try:
                    if seg_obj and seg_obj.name in bpy.data.objects:
                        objects_to_remove.append(seg_obj)
                except (ReferenceError, AttributeError):
                    pass

            # Clear visualizer lists
            visualizer.pi_objects.clear()
            visualizer.segment_objects.clear()

        except Exception as e:
            logger.warning("Error collecting objects from visualizer: %s", e)

    # Also find orphaned PI objects by property
    # (handles case where visualizer reference was lost)
    for obj in list(bpy.data.objects):
        try:
            if 'bc_pi_id' in obj and 'bc_alignment_id' in obj:
                if obj not in objects_to_remove:
                    objects_to_remove.append(obj)
        except (ReferenceError, AttributeError):
            pass

    # Find orphaned segment curves by IFC class
    for obj in list(bpy.data.objects):
        try:
            if obj.get('ifc_class') == 'IfcAlignmentSegment':
                if obj not in objects_to_remove:
                    objects_to_remove.append(obj)
        except (ReferenceError, AttributeError):
            pass

    logger.info("Found %d Blender objects to clean up", len(objects_to_remove))

    # Step 2: Remove Blender objects
    removed_count = 0
    for obj in objects_to_remove:
        try:
            if obj and obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
                removed_count += 1
        except (ReferenceError, RuntimeError) as e:
            logger.debug("Could not remove object: %s", e)

    logger.info("Removed %d Blender objects", removed_count)

    # Step 3: Clear Python registries
    clear_registry()
    logger.info("Cleared alignment registries")

    # Also clear the complete_update_system registry
    try:
        from .complete_update_system import clear_alignments
        clear_alignments()
        logger.info("Cleared update system registry")
    except (ImportError, AttributeError):
        pass

    # Step 4: Scan IFC file for alignments
    ifc_alignments = ifc_file.by_type("IfcAlignment")
    logger.info("Found %d IfcAlignment entities in IFC file", len(ifc_alignments))

    # Step 5: Rebuild each alignment
    rebuilt_count = 0
    for ifc_alignment in ifc_alignments:
        try:
            global_id = ifc_alignment.GlobalId
            name = ifc_alignment.Name or f"Alignment_{global_id[:8]}"

            logger.info("Rebuilding alignment: %s (%s)", name, global_id)

            # Create NativeIfcAlignment by loading from existing IFC entity
            # This calls _load_from_ifc() which runs _reconstruct_pis_from_segments()
            alignment_obj = NativeIfcAlignment(
                ifc_file,
                name=name,
                alignment_entity=ifc_alignment
            )

            # Alignment registers itself with alignment_registry in __init__

            # Create visualizer
            from ..tool.alignment_visualizer import AlignmentVisualizer
            visualizer = AlignmentVisualizer(alignment_obj)

            # Store visualizer reference on alignment
            alignment_obj.visualizer = visualizer

            # Register visualizer
            register_visualizer(visualizer, global_id)

            # Create Blender visualizations
            visualizer.update_visualizations()

            logger.info(
                "Rebuilt '%s': %d PIs, %d segments, %d PI objects, %d segment objects",
                name,
                len(alignment_obj.pis),
                len(alignment_obj.segments),
                len(visualizer.pi_objects),
                len(visualizer.segment_objects)
            )

            rebuilt_count += 1

        except Exception as e:
            logger.error("Error rebuilding alignment %s: %s",
                        getattr(ifc_alignment, 'Name', 'unknown'), e)
            import traceback
            logger.debug(traceback.format_exc())

    logger.info("=== REBUILD COMPLETE: %d alignments rebuilt ===", rebuilt_count)

    return rebuilt_count


def register_alignment_rebuilder():
    """Register the alignment rebuilder with the IfcRebuilderRegistry."""
    from .ifc_manager.rebuilder_registry import IfcRebuilderRegistry

    IfcRebuilderRegistry.register(
        name="alignment",
        rebuilder_func=rebuild_alignments_from_ifc,
        priority=50,  # Alignments before corridors (100) but after project (10)
        description="Rebuilds all alignment Python objects and Blender visualizations from IFC"
    )

    logger.info("Registered alignment rebuilder with priority 50")


def unregister_alignment_rebuilder():
    """Unregister the alignment rebuilder."""
    from .ifc_manager.rebuilder_registry import IfcRebuilderRegistry

    IfcRebuilderRegistry.unregister("alignment")
    logger.debug("Unregistered alignment rebuilder")


__all__ = [
    "rebuild_alignments_from_ifc",
    "register_alignment_rebuilder",
    "unregister_alignment_rebuilder",
]
