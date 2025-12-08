# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under Apache License 2.0
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
Blender tool implementation - utilities for Blender-specific operations.

This tool provides a clean interface for common Blender operations,
abstracting away the Blender API details and providing consistent
behavior across the codebase.

Usage:
    from saikei_civil.tool import Blender

    # Create objects
    obj = Blender.create_object("MyObject")
    curve = Blender.create_curve("MyCurve")
    empty = Blender.create_empty("MyEmpty", empty_type='SPHERE')

    # Work with selection
    active = Blender.get_active_object()
    selected = Blender.get_selected_objects()
    Blender.select_object(obj, add=True)

    # Collections
    collection = Blender.get_collection("Alignments", create=True)
    Blender.link_to_collection(obj, collection)
"""
from typing import TYPE_CHECKING, Optional, List, Any

import bpy

import saikei_civil.core.tool


class Blender(saikei_civil.core.tool.Blender):
    """
    Blender-specific utilities.

    Provides helper methods for common Blender operations, handling
    edge cases and providing consistent behavior.
    """

    @classmethod
    def create_object(cls, name: str, data: Any = None) -> bpy.types.Object:
        """
        Create a new Blender object and link it to the scene.

        Args:
            name: Object name
            data: Optional object data (mesh, curve, etc.)

        Returns:
            The created object, linked to the active scene collection
        """
        obj = bpy.data.objects.new(name, data)
        cls._link_to_scene(obj)
        return obj

    @classmethod
    def get_active_object(cls) -> Optional[bpy.types.Object]:
        """Get the active (selected) object."""
        return bpy.context.active_object

    @classmethod
    def set_active_object(cls, obj: bpy.types.Object) -> None:
        """Set the active object."""
        if obj is None:
            return

        # Ensure object is in view layer
        if obj.name not in bpy.context.view_layer.objects:
            return

        bpy.context.view_layer.objects.active = obj

    @classmethod
    def get_selected_objects(cls) -> List[bpy.types.Object]:
        """Get all selected objects."""
        return list(bpy.context.selected_objects)

    @classmethod
    def select_object(cls, obj: bpy.types.Object, add: bool = False) -> None:
        """
        Select an object.

        Args:
            obj: Object to select
            add: If True, add to selection; if False, replace selection
        """
        if obj is None:
            return

        if not add:
            cls.deselect_all()

        # Ensure object is in view layer
        if obj.name in bpy.context.view_layer.objects:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

    @classmethod
    def deselect_all(cls) -> None:
        """Deselect all objects."""
        for obj in bpy.context.selected_objects:
            obj.select_set(False)

    @classmethod
    def delete_object(cls, obj: bpy.types.Object) -> None:
        """
        Delete a Blender object and its data.

        Args:
            obj: Object to delete
        """
        if obj is None:
            return

        # Store reference to data before removing object
        data = obj.data

        # Remove from all collections
        for collection in obj.users_collection:
            collection.objects.unlink(obj)

        # Remove object
        bpy.data.objects.remove(obj, do_unlink=True)

        # Remove orphaned data if applicable
        if data is not None:
            if hasattr(data, 'users') and data.users == 0:
                # Get the appropriate data collection
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Curve):
                    bpy.data.curves.remove(data)

    @classmethod
    def update_viewport(cls) -> None:
        """Force a viewport update."""
        bpy.context.view_layer.update()

    @classmethod
    def get_collection(cls, name: str, create: bool = True) -> Optional[bpy.types.Collection]:
        """
        Get or create a collection.

        Args:
            name: Collection name
            create: If True, create collection if it doesn't exist

        Returns:
            The collection, or None if not found and create=False
        """
        # Check if collection exists
        if name in bpy.data.collections:
            return bpy.data.collections[name]

        if not create:
            return None

        # Create new collection
        collection = bpy.data.collections.new(name)

        # Link to scene collection
        bpy.context.scene.collection.children.link(collection)

        return collection

    @classmethod
    def link_to_collection(cls, obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
        """
        Link an object to a collection.

        If the object is already in other collections, it remains there
        (objects can be in multiple collections).

        Args:
            obj: Object to link
            collection: Target collection
        """
        if obj is None or collection is None:
            return

        # Check if already in collection
        if obj.name in collection.objects:
            return

        collection.objects.link(obj)

    @classmethod
    def unlink_from_collection(cls, obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
        """
        Unlink an object from a collection.

        Args:
            obj: Object to unlink
            collection: Collection to unlink from
        """
        if obj is None or collection is None:
            return

        if obj.name in collection.objects:
            collection.objects.unlink(obj)

    @classmethod
    def create_curve(cls, name: str) -> bpy.types.Object:
        """
        Create a new curve object.

        Args:
            name: Curve name

        Returns:
            The created curve object with 3D curve data
        """
        curve_data = bpy.data.curves.new(name, type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.resolution_u = 12

        obj = cls.create_object(name, curve_data)
        return obj

    @classmethod
    def create_empty(cls, name: str, empty_type: str = 'PLAIN_AXES') -> bpy.types.Object:
        """
        Create a new empty object.

        Args:
            name: Empty name
            empty_type: Type of empty display. Options:
                - 'PLAIN_AXES': Three perpendicular lines
                - 'ARROWS': Three arrows
                - 'SINGLE_ARROW': Single arrow
                - 'CIRCLE': Circle
                - 'CUBE': Cube wireframe
                - 'SPHERE': Sphere wireframe
                - 'CONE': Cone wireframe
                - 'IMAGE': Image (requires additional setup)

        Returns:
            The created empty object
        """
        obj = cls.create_object(name, None)  # None data = empty
        obj.empty_display_type = empty_type
        return obj

    @classmethod
    def create_mesh(cls, name: str) -> bpy.types.Object:
        """
        Create a new mesh object.

        Args:
            name: Mesh name

        Returns:
            The created mesh object with empty mesh data
        """
        mesh_data = bpy.data.meshes.new(name)
        obj = cls.create_object(name, mesh_data)
        return obj

    # =========================================================================
    # Helper Methods
    # =========================================================================

    @classmethod
    def _link_to_scene(cls, obj: bpy.types.Object) -> None:
        """Link an object to the active scene collection."""
        # Try to link to active collection first
        try:
            if bpy.context.collection:
                bpy.context.collection.objects.link(obj)
                return
        except RuntimeError:
            pass

        # Fall back to scene collection
        bpy.context.scene.collection.objects.link(obj)

    @classmethod
    def set_object_location(cls, obj: bpy.types.Object, location: tuple) -> None:
        """
        Set object location.

        Args:
            obj: Target object
            location: (x, y, z) tuple
        """
        if obj is None:
            return
        obj.location = location

    @classmethod
    def set_object_rotation(cls, obj: bpy.types.Object, rotation: tuple, mode: str = 'XYZ') -> None:
        """
        Set object rotation.

        Args:
            obj: Target object
            rotation: (x, y, z) euler angles in radians
            mode: Rotation mode ('XYZ', 'ZYX', etc.)
        """
        if obj is None:
            return
        obj.rotation_mode = mode
        obj.rotation_euler = rotation

    @classmethod
    def get_cursor_location(cls) -> tuple:
        """Get the 3D cursor location."""
        return tuple(bpy.context.scene.cursor.location)

    @classmethod
    def set_cursor_location(cls, location: tuple) -> None:
        """Set the 3D cursor location."""
        bpy.context.scene.cursor.location = location

    @classmethod
    def ensure_object_mode(cls) -> None:
        """Ensure we're in Object mode."""
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

    @classmethod
    def get_scene_unit_scale(cls) -> float:
        """Get the scene's unit scale factor."""
        return bpy.context.scene.unit_settings.scale_length

    @classmethod
    def get_scene_unit_system(cls) -> str:
        """Get the scene's unit system ('METRIC', 'IMPERIAL', 'NONE')."""
        return bpy.context.scene.unit_settings.system

    @classmethod
    def frame_selected(cls) -> None:
        """Frame selected objects in the viewport."""
        try:
            bpy.ops.view3d.view_selected()
        except RuntimeError:
            pass  # No 3D viewport available

    @classmethod
    def redraw_ui(cls) -> None:
        """Force a UI redraw."""
        for area in bpy.context.screen.areas:
            area.tag_redraw()