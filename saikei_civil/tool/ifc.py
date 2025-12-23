# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under the GNU General Public License v3
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
Ifc tool implementation - bridges core interfaces with NativeIfcManager.

This tool wraps the existing NativeIfcManager and provides the standard
interface for IFC operations. It also provides the Ifc.run() method for
executing ifcopenshell.api commands.

Usage:
    from saikei_civil.tool import Ifc

    # Get the current IFC file
    ifc_file = Ifc.get()

    # Run an API command
    alignment = Ifc.run("alignment.create", name="My Alignment")

    # Get entity from Blender object
    entity = Ifc.get_entity(bpy.context.active_object)

    # Link entity to object
    Ifc.link(entity, obj)
"""
from typing import TYPE_CHECKING, Optional, List, Any

import bpy

if TYPE_CHECKING:
    import ifcopenshell

# Import will fail if ifcopenshell not installed - that's expected
try:
    import ifcopenshell
    import ifcopenshell.api
    HAS_IFCOPENSHELL = True
except ImportError:
    HAS_IFCOPENSHELL = False

from ..core import tool as core_tool


class Ifc(core_tool.Ifc):
    """
    Blender-specific IFC operations.

    This class wraps NativeIfcManager and provides the standard interface
    for all IFC operations in Saikei Civil.
    """

    @classmethod
    def get(cls) -> Optional["ifcopenshell.file"]:
        """Get the current IFC file from NativeIfcManager."""
        if not HAS_IFCOPENSHELL:
            return None

        # TEMPORARILY DISABLED - Testing hierarchy issue without Bonsai integration
        # Bonsai may be creating duplicate empties for IFC entities
        # try:
        #     from bonsai.bim.ifc import IfcStore
        #     bonsai_file = IfcStore.get_file()
        #     if bonsai_file is not None:
        #         return bonsai_file
        # except ImportError:
        #     pass

        # Fall back to Saikei's own manager
        from ..core.ifc_manager import NativeIfcManager
        return NativeIfcManager.get_file()

    @classmethod
    def set(cls, ifc_file: "ifcopenshell.file") -> None:
        """Set the current IFC file."""
        if not HAS_IFCOPENSHELL:
            raise RuntimeError("ifcopenshell not installed")

        from ..core.ifc_manager import NativeIfcManager
        NativeIfcManager.file = ifc_file

    @classmethod
    def run(cls, command: str, **kwargs) -> Any:
        """
        Run an ifcopenshell.api command.

        Args:
            command: API command in format "module.function"
                     Examples: "alignment.create", "georeference.add_georeferencing"
            **kwargs: Arguments to pass to the API function

        Returns:
            The result of the API call

        Raises:
            RuntimeError: If no IFC file is loaded or ifcopenshell not available
            ValueError: If the command format is invalid or module/function not found
        """
        if not HAS_IFCOPENSHELL:
            raise RuntimeError("ifcopenshell not installed")

        ifc = cls.get()
        if ifc is None:
            raise RuntimeError("No IFC file loaded. Create or open a file first.")

        # Parse command: "module.function" -> ifcopenshell.api.module.function
        parts = command.split(".")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid command format: '{command}'. "
                f"Expected 'module.function' (e.g., 'alignment.create')"
            )

        module_name, func_name = parts

        # Get the module
        module = getattr(ifcopenshell.api, module_name, None)
        if module is None:
            raise ValueError(
                f"Unknown ifcopenshell.api module: '{module_name}'. "
                f"Check available modules at ifcopenshell.api"
            )

        # Get the function
        func = getattr(module, func_name, None)
        if func is None:
            raise ValueError(
                f"Unknown function: '{module_name}.{func_name}'. "
                f"Check available functions in ifcopenshell.api.{module_name}"
            )

        # Call the function with ifc file as first argument
        return func(ifc, **kwargs)

    @classmethod
    def get_entity(cls, obj: bpy.types.Object) -> Optional["ifcopenshell.entity_instance"]:
        """Get the IFC entity linked to a Blender object."""
        if not HAS_IFCOPENSHELL:
            return None

        if obj is None:
            return None

        entity_id = obj.get("ifc_definition_id")
        if entity_id is None:
            return None

        ifc = cls.get()
        if ifc is None:
            return None

        try:
            return ifc.by_id(entity_id)
        except (RuntimeError, KeyError):
            # Entity no longer exists in file
            return None

    @classmethod
    def get_object(cls, entity: "ifcopenshell.entity_instance") -> Optional[bpy.types.Object]:
        """Get the Blender object linked to an IFC entity."""
        if entity is None:
            return None

        entity_id = entity.id()

        # Search all objects for matching ID
        for obj in bpy.data.objects:
            if obj.get("ifc_definition_id") == entity_id:
                return obj

        return None

    @classmethod
    def link(cls, entity: "ifcopenshell.entity_instance", obj: bpy.types.Object) -> None:
        """Link an IFC entity to a Blender object."""
        if entity is None or obj is None:
            return

        obj["ifc_definition_id"] = entity.id()
        obj["ifc_class"] = entity.is_a()

        # Store GlobalId if available (most IFC entities have this)
        if hasattr(entity, "GlobalId") and entity.GlobalId:
            obj["ifc_global_id"] = entity.GlobalId

        # Store Name if available
        if hasattr(entity, "Name") and entity.Name:
            obj["ifc_name"] = entity.Name

    @classmethod
    def unlink(cls, obj: bpy.types.Object) -> None:
        """Remove IFC linking from a Blender object."""
        if obj is None:
            return

        # Remove IFC-related custom properties
        for key in ["ifc_definition_id", "ifc_class", "ifc_global_id", "ifc_name"]:
            if key in obj:
                del obj[key]

    @classmethod
    def get_schema(cls) -> str:
        """Get the IFC schema version."""
        ifc = cls.get()
        if ifc is None:
            return "IFC4X3"  # Default for new files
        return ifc.schema

    @classmethod
    def by_type(cls, ifc_class: str) -> List["ifcopenshell.entity_instance"]:
        """Get all entities of a given IFC class."""
        ifc = cls.get()
        if ifc is None:
            return []
        try:
            return list(ifc.by_type(ifc_class))
        except RuntimeError:
            return []

    @classmethod
    def by_id(cls, entity_id: int) -> Optional["ifcopenshell.entity_instance"]:
        """Get an entity by its ID."""
        ifc = cls.get()
        if ifc is None:
            return None
        try:
            return ifc.by_id(entity_id)
        except (RuntimeError, KeyError):
            return None

    # =========================================================================
    # Operator Mixin
    # =========================================================================

    class Operator:
        """
        Base mixin for operators that modify IFC data.

        Inherit from this class along with bpy.types.Operator to get
        consistent IFC operation handling. Implement _execute() instead
        of execute().

        Example:
            class SAIKEI_OT_my_operator(bpy.types.Operator, tool.Ifc.Operator):
                bl_idname = "saikei.my_operator"
                bl_label = "My Operator"

                def _execute(self, context):
                    # Your implementation here
                    tool.Ifc.run("alignment.create", name="Test")
                    return {'FINISHED'}
        """

        def execute(self, context):
            """
            Execute the operator.

            This wraps _execute() and could add transaction handling,
            undo support, logging, etc. in the future.
            """
            return self._execute(context)

        def _execute(self, context):
            """
            Implement this method in your operator subclass.

            Returns:
                Blender operator result: {'FINISHED'}, {'CANCELLED'}, etc.
            """
            raise NotImplementedError(
                "Implement _execute() in your operator subclass"
            )

    # =========================================================================
    # Utility Methods (not part of interface, but useful)
    # =========================================================================

    @classmethod
    def is_available(cls) -> bool:
        """Check if IFC support is available."""
        return HAS_IFCOPENSHELL

    @classmethod
    def has_file(cls) -> bool:
        """Check if an IFC file is currently loaded."""
        return cls.get() is not None

    @classmethod
    def create_guid(cls) -> str:
        """Create a new IFC GlobalId."""
        if not HAS_IFCOPENSHELL:
            import uuid
            return str(uuid.uuid4())
        return ifcopenshell.guid.new()

    @classmethod
    def get_filepath(cls) -> Optional[str]:
        """Get the filepath of the current IFC file."""
        from ..core.ifc_manager import NativeIfcManager
        return NativeIfcManager.filepath