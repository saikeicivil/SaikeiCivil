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
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================

"""
Blender Hierarchy Module (Tool Layer)
======================================

Creates and manages Blender objects/collections that mirror the IFC hierarchy.
Provides functions for creating the project structure in Blender's outliner.

This module is part of Layer 2 (Tool) in the three-layer architecture,
containing Blender-specific implementations.
"""

import logging
from typing import Optional, Tuple, Callable, Any

import bpy

logger = logging.getLogger(__name__)

# Object names used in hierarchy
PROJECT_COLLECTION_NAME = "Saikei Civil Project"
PROJECT_EMPTY_NAME = "Project (IfcProject)"
SITE_EMPTY_NAME = "Site (IfcSite)"
ROAD_EMPTY_NAME = "Road (IfcRoad)"
ALIGNMENTS_EMPTY_NAME = "Alignments"
GEOMODELS_EMPTY_NAME = "Geomodels"


def create_blender_hierarchy(
    project: Any,
    site: Any,
    road: Any,
    link_func: Callable[[bpy.types.Object, Any], None]
) -> Tuple[bpy.types.Collection, bpy.types.Object, bpy.types.Object]:
    """Create Blender objects/collections mirroring IFC hierarchy.

    Structure created:
        [Collection] Saikei Civil Project
            [Empty] Project
            └── [Empty] Site
                ├── [Empty] Road
                ├── [Empty] Alignments
                └── [Empty] Geomodels

    Args:
        project: IfcProject entity
        site: IfcSite entity
        road: IfcRoad entity
        link_func: Function to link Blender object to IFC entity

    Returns:
        Tuple of (project_collection, alignments_empty, geomodels_empty)
    """
    # Create main project collection
    project_collection = bpy.data.collections.new(PROJECT_COLLECTION_NAME)
    bpy.context.scene.collection.children.link(project_collection)

    # Project Empty
    project_empty = bpy.data.objects.new(PROJECT_EMPTY_NAME, None)
    project_empty.empty_display_type = 'CUBE'
    project_empty.empty_display_size = 5.0
    project_collection.objects.link(project_empty)
    link_func(project_empty, project)

    # Site Empty (child of Project)
    site_empty = bpy.data.objects.new(SITE_EMPTY_NAME, None)
    site_empty.empty_display_type = 'CUBE'
    site_empty.empty_display_size = 4.0
    site_empty.parent = project_empty
    project_collection.objects.link(site_empty)
    link_func(site_empty, site)

    # Road Empty (child of Site)
    road_empty = bpy.data.objects.new(ROAD_EMPTY_NAME, None)
    road_empty.empty_display_type = 'CUBE'
    road_empty.empty_display_size = 3.0
    road_empty.parent = site_empty
    project_collection.objects.link(road_empty)
    link_func(road_empty, road)

    # Alignments Empty (child of Site)
    alignments_empty = bpy.data.objects.new(ALIGNMENTS_EMPTY_NAME, None)
    alignments_empty.empty_display_type = 'SPHERE'
    alignments_empty.empty_display_size = 2.0
    alignments_empty.parent = site_empty
    project_collection.objects.link(alignments_empty)

    # Geomodels Empty (child of Site)
    geomodels_empty = bpy.data.objects.new(GEOMODELS_EMPTY_NAME, None)
    geomodels_empty.empty_display_type = 'SPHERE'
    geomodels_empty.empty_display_size = 2.0
    geomodels_empty.parent = site_empty
    project_collection.objects.link(geomodels_empty)

    logger.info("Blender hierarchy created in outliner")

    return project_collection, alignments_empty, geomodels_empty


def clear_blender_hierarchy() -> None:
    """Remove Saikei Civil hierarchy from scene."""
    # Remove project collection and all its contents
    if PROJECT_COLLECTION_NAME in bpy.data.collections:
        collection = bpy.data.collections[PROJECT_COLLECTION_NAME]
        for obj in list(collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.context.scene.collection.children.unlink(collection)
        bpy.data.collections.remove(collection)
        logger.debug(f"Removed '{PROJECT_COLLECTION_NAME}' collection")

    # Clean up orphaned hierarchy objects
    orphan_names = [
        PROJECT_EMPTY_NAME,
        SITE_EMPTY_NAME,
        ROAD_EMPTY_NAME,
        ALIGNMENTS_EMPTY_NAME,
        GEOMODELS_EMPTY_NAME
    ]
    for obj_name in orphan_names:
        if obj_name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[obj_name], do_unlink=True)
            logger.debug(f"Removed orphaned object '{obj_name}'")


def get_or_find_collection(
    collection_ref: Optional[bpy.types.Collection],
    name: str
) -> Optional[bpy.types.Collection]:
    """Get collection reference or find by name.

    Args:
        collection_ref: Existing collection reference (may be stale)
        name: Collection name to search for

    Returns:
        Valid collection or None
    """
    # Validate existing reference
    if collection_ref is not None:
        try:
            _ = collection_ref.name
            if collection_ref.name in bpy.data.collections:
                return collection_ref
        except (ReferenceError, AttributeError):
            pass

    # Try to find by name
    if name in bpy.data.collections:
        return bpy.data.collections[name]

    return None


def get_or_find_object(
    object_ref: Optional[bpy.types.Object],
    name: str
) -> Optional[bpy.types.Object]:
    """Get object reference or find by name.

    Args:
        object_ref: Existing object reference (may be stale)
        name: Object name to search for

    Returns:
        Valid object or None
    """
    # Validate existing reference
    if object_ref is not None:
        try:
            _ = object_ref.name
            if object_ref.name in bpy.data.objects:
                return object_ref
        except (ReferenceError, AttributeError):
            pass

    # Try to find by name
    if name in bpy.data.objects:
        return bpy.data.objects[name]

    return None


def add_alignment_to_hierarchy(alignment_obj: bpy.types.Object) -> None:
    """Add alignment object to hierarchy by parenting to Alignments empty.

    Args:
        alignment_obj: Blender object representing an alignment
    """
    parent_empty = get_or_find_object(None, ALIGNMENTS_EMPTY_NAME)
    if parent_empty and alignment_obj.parent != parent_empty:
        alignment_obj.parent = parent_empty
        logger.info(f"Added alignment '{alignment_obj.name}' to Alignments hierarchy")


def add_geomodel_to_hierarchy(geomodel_obj: bpy.types.Object) -> None:
    """Add geomodel object to hierarchy by parenting to Geomodels empty.

    Args:
        geomodel_obj: Blender object representing a geomodel
    """
    parent_empty = get_or_find_object(None, GEOMODELS_EMPTY_NAME)
    if parent_empty and geomodel_obj.parent != parent_empty:
        geomodel_obj.parent = parent_empty
        logger.info(f"Added geomodel '{geomodel_obj.name}' to Geomodels hierarchy")


__all__ = [
    "create_blender_hierarchy",
    "clear_blender_hierarchy",
    "get_or_find_collection",
    "get_or_find_object",
    "add_alignment_to_hierarchy",
    "add_geomodel_to_hierarchy",
    "PROJECT_COLLECTION_NAME",
    "PROJECT_EMPTY_NAME",
    "SITE_EMPTY_NAME",
    "ROAD_EMPTY_NAME",
    "ALIGNMENTS_EMPTY_NAME",
    "GEOMODELS_EMPTY_NAME",
]
