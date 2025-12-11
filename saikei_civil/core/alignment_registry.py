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
        return existing, False
    
    # Create new instance by wrapping existing IFC entity
    # This is tricky - we need to reconstruct from IFC
    alignment_obj = reconstruct_alignment_from_ifc(ifc_entity)
    
    # Register it
    register_alignment(alignment_obj)
    
    return alignment_obj, True


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
        return existing, False
    
    # Create new visualizer
    visualizer = AlignmentVisualizer(alignment_obj)
    
    # Register it
    register_visualizer(visualizer, global_id)
    
    return visualizer, True


def reconstruct_alignment_from_ifc(ifc_entity) -> 'NativeIfcAlignment':
    """Reconstruct a NativeIfcAlignment instance from an existing IFC entity.

    This is used when we have an IFC alignment entity but no Python object.

    Args:
        ifc_entity: IFC IfcAlignment entity

    Returns:
        NativeIfcAlignment instance
    """
    from .native_ifc_alignment import NativeIfcAlignment
    from .native_ifc_manager import NativeIfcManager
    
    ifc_file = NativeIfcManager.get_file()
    
    # Create a new alignment object
    alignment_obj = NativeIfcAlignment.__new__(NativeIfcAlignment)
    alignment_obj.ifc = ifc_file
    alignment_obj.alignment = ifc_entity
    alignment_obj.pis = []
    alignment_obj.segments = []
    
    # Find horizontal alignment
    for rel in ifc_entity.IsNestedBy or []:
        for obj in rel.RelatedObjects:
            if obj.is_a('IfcAlignmentHorizontal'):
                alignment_obj.horizontal = obj
                break
    
    # TODO: Reconstruct PIs from IFC if needed
    # For now, assume it's empty or will be populated
    
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
