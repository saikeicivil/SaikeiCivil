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
Alignment Instance Registry

Maintains references to NativeIfcAlignment and AlignmentVisualizer instances
so that operators can access and modify them.

This solves the problem of operators needing to work with alignment Python objects,
not just IFC entities.
"""

from typing import Optional, Dict, Tuple
from .logging_config import get_logger

logger = get_logger(__name__)


# Global registries - use regular dicts to keep alignments alive
# These persist as long as the IFC file is loaded
_alignment_instances: Dict[str, 'NativeIfcAlignment'] = {}
_visualizer_instances: Dict[str, 'AlignmentVisualizer'] = {}


def register_alignment(alignment_obj):
    """Register a NativeIfcAlignment instance.

    Args:
        alignment_obj: NativeIfcAlignment instance
    """
    global_id = alignment_obj.alignment.GlobalId
    _alignment_instances[global_id] = alignment_obj
    logger.debug("Registered alignment: %s", global_id)


def register_visualizer(visualizer_obj, alignment_global_id):
    """Register an AlignmentVisualizer instance.

    Args:
        visualizer_obj: AlignmentVisualizer instance
        alignment_global_id: GlobalId of the alignment this visualizes
    """
    _visualizer_instances[alignment_global_id] = visualizer_obj
    logger.debug("Registered visualizer for: %s", alignment_global_id)


def get_alignment(alignment_global_id) -> Optional['NativeIfcAlignment']:
    """Get NativeIfcAlignment instance by GlobalId.
    
    Args:
        alignment_global_id: IFC GlobalId of the alignment
        
    Returns:
        NativeIfcAlignment instance or None
    """
    return _alignment_instances.get(alignment_global_id)


def get_visualizer(alignment_global_id) -> Optional['AlignmentVisualizer']:
    """Get AlignmentVisualizer instance by alignment GlobalId.
    
    Args:
        alignment_global_id: IFC GlobalId of the alignment
        
    Returns:
        AlignmentVisualizer instance or None
    """
    return _visualizer_instances.get(alignment_global_id)


def get_or_create_alignment(ifc_entity) -> Tuple['NativeIfcAlignment', bool]:
    """Get existing alignment instance or create new one.

    Args:
        ifc_entity: IFC alignment entity

    Returns:
        Tuple of (NativeIfcAlignment instance, was_created: bool)
    """
    from .native_ifc_alignment import NativeIfcAlignment

    global_id = ifc_entity.GlobalId

    # Check if already exists
    existing = get_alignment(global_id)
    if existing:
        # CRITICAL: Ensure alignment is registered with update system!
        # The update system registry might have been cleared (module reload, etc.)
        # We must always ensure the alignment is registered for real-time updates.
        _ensure_update_system_registration(existing)
        return existing, False

    # Create new instance by wrapping existing IFC entity
    # This is tricky - we need to reconstruct from IFC
    alignment_obj = reconstruct_alignment_from_ifc(ifc_entity)

    # Register it
    register_alignment(alignment_obj)

    return alignment_obj, True


def _ensure_update_system_registration(alignment_obj):
    """Ensure alignment is registered with the update system for real-time PI movement.

    The update system uses Python object IDs as keys, which may become stale after
    module reloads or if the alignment wasn't properly registered initially.

    Args:
        alignment_obj: NativeIfcAlignment instance
    """
    from ..operators.update_system_operators import _alignment_registry, register_alignment as update_register

    alignment_id = id(alignment_obj)
    if alignment_id not in _alignment_registry:
        update_register(alignment_obj)
        logger.debug("Re-registered alignment with update system: %s", alignment_obj.alignment.Name)


def get_or_create_visualizer(alignment_obj) -> Tuple['AlignmentVisualizer', bool]:
    """Get existing visualizer or create new one.

    Args:
        alignment_obj: NativeIfcAlignment instance

    Returns:
        Tuple of (AlignmentVisualizer instance, was_created: bool)
    """
    from .alignment_visualizer import AlignmentVisualizer

    global_id = alignment_obj.alignment.GlobalId

    # Check if already exists
    existing = get_visualizer(global_id)
    if existing:
        # CRITICAL: Always ensure visualizer is linked to alignment object!
        # The update handler needs alignment.visualizer to update curves in real-time.
        alignment_obj.visualizer = existing

        # CRITICAL: Ensure segment_objects is populated for fast updates!
        # If visualizer was created before segments were ready, populate now.
        if alignment_obj.segments and not existing.segment_objects:
            logger.info("Existing visualizer had no segment_objects, populating now")
            existing.update_visualizations()

        return existing, False

    # Create new visualizer
    visualizer = AlignmentVisualizer(alignment_obj)

    # CRITICAL: Store visualizer on alignment for update handler access
    alignment_obj.visualizer = visualizer

    # CRITICAL: Populate segment_objects from existing IFC segments!
    # Without this, update_segment_curves_fast() has nothing to update,
    # and preview lines won't appear during PI movement.
    if alignment_obj.segments:
        logger.info("Populating visualizer with %d existing segments", len(alignment_obj.segments))
        visualizer.update_visualizations()

    # Register it
    register_visualizer(visualizer, global_id)

    return visualizer, True


def reconstruct_alignment_from_ifc(ifc_entity) -> 'NativeIfcAlignment':
    """Reconstruct a NativeIfcAlignment instance from an existing IFC entity.

    This is used when we have an IFC alignment entity but no Python object.
    Also reconstructs PIs from existing Blender objects if available.

    Args:
        ifc_entity: IFC IfcAlignment entity

    Returns:
        NativeIfcAlignment instance
    """
    from .native_ifc_alignment import NativeIfcAlignment, StationingManager, SimpleVector
    from .native_ifc_manager import NativeIfcManager

    ifc_file = NativeIfcManager.get_file()
    global_id = ifc_entity.GlobalId

    # Create a new alignment object with all required attributes
    alignment_obj = NativeIfcAlignment.__new__(NativeIfcAlignment)
    alignment_obj.ifc = ifc_file
    alignment_obj.alignment = ifc_entity
    alignment_obj.horizontal = None
    alignment_obj.pis = []
    alignment_obj.segments = []
    alignment_obj.curve_segments = []  # Will be populated from IFC representation
    alignment_obj.auto_update = True

    # Find horizontal alignment and load segments
    for rel in ifc_entity.IsNestedBy or []:
        for obj in rel.RelatedObjects:
            if obj.is_a('IfcAlignmentHorizontal'):
                alignment_obj.horizontal = obj
                # Load existing segments from horizontal alignment
                for seg_rel in obj.IsNestedBy or []:
                    for seg in seg_rel.RelatedObjects:
                        if seg.is_a('IfcAlignmentSegment'):
                            alignment_obj.segments.append(seg)
                break

    # ========================================================================
    # CRITICAL: Load existing curve_segments from IFC representation
    # Without this, cleanup_old_geometry() won't remove old entities,
    # causing entity ID explosion during regeneration!
    # ========================================================================
    if hasattr(ifc_entity, 'Representation') and ifc_entity.Representation:
        rep = ifc_entity.Representation
        if rep.is_a("IfcProductDefinitionShape"):
            for shape_rep in rep.Representations or []:
                if shape_rep.is_a("IfcShapeRepresentation"):
                    for item in shape_rep.Items or []:
                        if item.is_a("IfcCompositeCurve"):
                            # Found the composite curve - extract its segments
                            if hasattr(item, 'Segments') and item.Segments:
                                alignment_obj.curve_segments = list(item.Segments)
                                logger.info(
                                    "Loaded %d curve segments from IFC for alignment '%s'",
                                    len(alignment_obj.curve_segments),
                                    ifc_entity.Name
                                )
                            break

    # Initialize stationing manager
    alignment_obj.stationing = StationingManager(ifc_file, ifc_entity)
    alignment_obj.stationing.load_from_ifc()

    # ========================================================================
    # CRITICAL: Reconstruct PIs from existing Blender objects
    # Without this, the update handler won't find any PIs to update!
    # ========================================================================
    try:
        import bpy

        # Find all PI objects that belong to this alignment
        pi_objects = []
        for obj in bpy.data.objects:
            if 'bc_pi_id' in obj and 'bc_alignment_id' in obj:
                # Check if this PI belongs to our alignment (by GlobalId)
                obj_alignment_id = obj.get('bc_alignment_id')
                if obj_alignment_id == global_id:
                    pi_objects.append((obj.get('bc_pi_id'), obj))

        # Sort by PI ID and reconstruct pis list
        pi_objects.sort(key=lambda x: x[0])

        for pi_id, obj in pi_objects:
            pi_data = {
                'id': pi_id,
                'position': SimpleVector(obj.location.x, obj.location.y),
                'blender_object': obj,
                'ifc_point': None,  # Will be set when IFC is regenerated
            }
            alignment_obj.pis.append(pi_data)

        logger.info(
            "Reconstructed %d PIs from Blender objects for alignment '%s'",
            len(alignment_obj.pis),
            ifc_entity.Name
        )

    except ImportError:
        # bpy not available (testing environment)
        logger.debug("Cannot reconstruct PIs - bpy not available")
    except Exception as e:
        logger.warning("Error reconstructing PIs from Blender: %s", e)

    # Register with update system
    from .complete_update_system import register_alignment
    register_alignment(alignment_obj)

    logger.debug(
        "Reconstructed alignment '%s': horizontal=%s, segments=%d, pis=%d",
        ifc_entity.Name,
        alignment_obj.horizontal is not None,
        len(alignment_obj.segments),
        len(alignment_obj.pis)
    )

    return alignment_obj


def clear_registry():
    """Clear all registered instances. Use for cleanup or reset."""
    global _alignment_instances, _visualizer_instances
    _alignment_instances.clear()
    _visualizer_instances.clear()
    logger.info("Cleared all registrations")


def list_registered():
    """List all registered alignments for debugging."""
    logger.info("Registered alignments: %s", len(_alignment_instances))
    for global_id in _alignment_instances.keys():
        logger.info("  - %s", global_id)

    logger.info("Registered visualizers: %s", len(_visualizer_instances))
    for global_id in _visualizer_instances.keys():
        logger.info("  - %s", global_id)
