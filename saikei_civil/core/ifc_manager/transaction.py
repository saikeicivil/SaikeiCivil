# ==============================================================================
# Saikei Civil - Civil Engineering Tools for Blender
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
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
Transaction System for IFC Operations
======================================

Provides a dual transaction system that synchronizes:
1. IfcOpenShell's native transactions - Changes to the IFC data model
2. Saikei's transaction history - Application-level operation tracking

This architecture ensures that every IFC modification is reversible and that
Blender's undo system stays synchronized with IFC file changes.

Architecture based on Bonsai/BlenderBIM patterns.

Usage:
    # Begin a transaction
    TransactionManager.begin_transaction("CreateAlignment")

    # Add operation callbacks for undo/redo
    TransactionManager.add_operation(
        rollback=lambda data: delete_entity(data['id']),
        commit=lambda data: recreate_entity(data),
        data={'id': entity.id(), 'name': entity.Name}
    )

    # End the transaction
    TransactionManager.end_transaction()

    # Undo/Redo
    TransactionManager.undo()
    TransactionManager.redo()
"""

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, TypedDict
import uuid

if TYPE_CHECKING:
    import ifcopenshell

from ..logging_config import get_logger

logger = get_logger(__name__)


class Operation(TypedDict):
    """A single operation within a transaction."""
    rollback: Callable[[Dict], None]  # Function to undo the operation
    commit: Callable[[Dict], None]    # Function to redo the operation
    data: Dict[str, Any]              # Operation-specific data


class TransactionStep(TypedDict):
    """A complete transaction containing multiple operations."""
    key: str                          # Unique identifier (UUID + operation name)
    operations: List[Operation]       # List of operations in this transaction


class TransactionManager:
    """
    Manages IFC transaction history for undo/redo functionality.

    This class implements a dual transaction system:
    - Uses IfcOpenShell's native transaction support for IFC file changes
    - Maintains an application-level history stack for complex operations

    The system supports:
    - Nested transactions (inner operators share outer operator's transaction)
    - Operation callbacks for custom undo/redo behavior
    - Synchronization with Blender's undo system

    Class Attributes:
        history: Stack of completed transactions (for undo)
        future: Stack of undone transactions (for redo)
        current_transaction: Key of the active transaction (empty if none)
        last_transaction: Key of the most recently completed transaction
        _transaction_depth: Nesting depth for nested operator support
        _ifc_file: Reference to the active IFC file
    """

    # Transaction stacks
    history: List[TransactionStep] = []
    future: List[TransactionStep] = []

    # Current transaction state
    current_transaction: str = ""
    last_transaction: str = ""
    _transaction_depth: int = 0

    # IFC file reference (set by NativeIfcManager)
    _ifc_file: Optional['ifcopenshell.file'] = None

    # Element linking maps for fast lookup
    id_map: Dict[int, Any] = {}      # IFC ID -> Blender object
    guid_map: Dict[str, Any] = {}    # GlobalId -> Blender object

    # Edit tracking
    edited_objs: set = set()         # Objects modified since last save
    is_dirty: bool = False           # File has unsaved changes

    @classmethod
    def set_file(cls, ifc_file: Optional['ifcopenshell.file']) -> None:
        """
        Set the active IFC file reference.

        Called by NativeIfcManager when a file is loaded or created.

        Args:
            ifc_file: The IfcOpenShell file object, or None to clear
        """
        cls._ifc_file = ifc_file
        if ifc_file is None:
            cls.clear_history()

    @classmethod
    def get_file(cls) -> Optional['ifcopenshell.file']:
        """Get the active IFC file."""
        return cls._ifc_file

    @classmethod
    def begin_transaction(cls, key: str = "") -> str:
        """
        Begin a new transaction or join an existing one.

        If already in a transaction, increments the nesting depth without
        creating a new transaction (nested operators share the transaction).

        Args:
            key: Transaction identifier (e.g., operator class name).
                 If empty, generates a UUID-based key.

        Returns:
            The transaction key
        """
        cls._transaction_depth += 1

        # If already in a transaction, just increment depth
        if cls._transaction_depth > 1:
            logger.debug(f"Joining existing transaction: {cls.current_transaction} (depth: {cls._transaction_depth})")
            return cls.current_transaction

        # Generate unique key
        transaction_key = f"{uuid.uuid4().hex[:8]}_{key}" if key else uuid.uuid4().hex
        cls.current_transaction = transaction_key

        # Create new transaction step
        cls.history.append({
            "key": transaction_key,
            "operations": []
        })

        # Clear future (can't redo after new operation)
        cls.future.clear()

        # Begin IFC file transaction if available
        if cls._ifc_file is not None:
            try:
                cls._ifc_file.begin_transaction()
                logger.debug(f"Started IFC transaction: {transaction_key}")
            except Exception as e:
                logger.warning(f"Could not start IFC transaction: {e}")

        logger.debug(f"Started transaction: {transaction_key}")
        return transaction_key

    @classmethod
    def add_operation(
        cls,
        rollback: Callable[[Dict], None],
        commit: Callable[[Dict], None],
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add an operation to the current transaction.

        Each operation consists of:
        - rollback: Function to undo the operation
        - commit: Function to redo the operation
        - data: Dictionary passed to rollback/commit functions

        Args:
            rollback: Function called when undoing this operation
            commit: Function called when redoing this operation
            data: Optional data dictionary passed to callbacks

        Raises:
            RuntimeError: If not in an active transaction
        """
        if not cls.current_transaction or not cls.history:
            logger.warning("add_operation called outside of transaction")
            return

        operation: Operation = {
            "rollback": rollback,
            "commit": commit,
            "data": data or {}
        }

        cls.history[-1]["operations"].append(operation)
        logger.debug(f"Added operation to transaction: {cls.current_transaction}")

    @classmethod
    def end_transaction(cls) -> None:
        """
        End the current transaction.

        If this is a nested transaction, decrements depth without committing.
        Only the outermost end_transaction() commits the full transaction.
        """
        if cls._transaction_depth <= 0:
            logger.warning("end_transaction called without matching begin_transaction")
            return

        cls._transaction_depth -= 1

        # If still nested, don't complete the transaction
        if cls._transaction_depth > 0:
            logger.debug(f"Exiting nested transaction (depth: {cls._transaction_depth})")
            return

        # End IFC file transaction
        if cls._ifc_file is not None:
            try:
                cls._ifc_file.end_transaction()
                logger.debug("Ended IFC transaction")
            except Exception as e:
                logger.warning(f"Could not end IFC transaction: {e}")

        # Add IFC undo/redo callbacks as final operations
        cls._add_ifc_undo_operations()

        # Update state
        cls.last_transaction = cls.current_transaction
        cls.current_transaction = ""
        cls.is_dirty = True

        logger.debug(f"Completed transaction: {cls.last_transaction} (history size: {len(cls.history)})")

    @classmethod
    def _add_ifc_undo_operations(cls) -> None:
        """Add IFC file undo/redo operations to the current transaction."""
        if cls._ifc_file is None or not cls.history:
            return

        def ifc_undo(data: Dict) -> None:
            """Undo IFC file changes."""
            try:
                if cls._ifc_file is not None:
                    cls._ifc_file.undo()
            except Exception as e:
                logger.error(f"IFC undo failed: {e}")

        def ifc_redo(data: Dict) -> None:
            """Redo IFC file changes."""
            try:
                if cls._ifc_file is not None:
                    cls._ifc_file.redo()
            except Exception as e:
                logger.error(f"IFC redo failed: {e}")

        cls.history[-1]["operations"].append({
            "rollback": ifc_undo,
            "commit": ifc_redo,
            "data": {}
        })

    @classmethod
    def undo(cls) -> bool:
        """
        Undo the last transaction.

        Executes rollback callbacks in reverse order for all operations
        in the last completed transaction.

        Returns:
            True if undo was successful, False if nothing to undo
        """
        if not cls.history:
            logger.debug("Nothing to undo")
            return False

        # Pop the last transaction
        transaction = cls.history.pop()

        logger.info(f"Undoing transaction: {transaction['key']}")

        # Execute rollback for each operation in reverse order
        for operation in reversed(transaction["operations"]):
            try:
                operation["rollback"](operation["data"])
            except Exception as e:
                logger.error(f"Rollback operation failed: {e}")

        # Move to future stack for potential redo
        cls.future.append(transaction)

        # Update state
        cls.last_transaction = transaction["key"]

        # Refresh visualizations after IFC state changes
        cls._refresh_all_visualizations()

        logger.debug(f"Undo complete (history: {len(cls.history)}, future: {len(cls.future)})")
        return True

    @classmethod
    def redo(cls) -> bool:
        """
        Redo the last undone transaction.

        Executes commit callbacks in order for all operations
        in the last undone transaction.

        Returns:
            True if redo was successful, False if nothing to redo
        """
        if not cls.future:
            logger.debug("Nothing to redo")
            return False

        # Pop the last undone transaction
        transaction = cls.future.pop()

        logger.info(f"Redoing transaction: {transaction['key']}")

        # Execute commit for each operation in order
        for operation in transaction["operations"]:
            try:
                operation["commit"](operation["data"])
            except Exception as e:
                logger.error(f"Commit operation failed: {e}")

        # Move back to history
        cls.history.append(transaction)

        # Update state
        cls.last_transaction = transaction["key"]

        # Refresh visualizations after IFC state changes
        cls._refresh_all_visualizations()

        logger.debug(f"Redo complete (history: {len(cls.history)}, future: {len(cls.future)})")
        return True

    @classmethod
    def _refresh_all_visualizations(cls) -> None:
        """
        Refresh all alignment visualizations after undo/redo.

        This is critical because IFC undo/redo changes the underlying data,
        but Blender objects may become stale or disconnected. This method
        rebuilds all visualizations from the current IFC state.
        """
        try:
            from ..alignment_registry import get_all_alignments, get_all_visualizers

            # Get all registered visualizers
            visualizers = get_all_visualizers()
            refresh_count = 0

            for visualizer in visualizers:
                try:
                    # Regenerate segments from current PIs (they're still in memory)
                    if hasattr(visualizer, 'alignment') and visualizer.alignment:
                        alignment = visualizer.alignment
                        # Regenerate IFC segments from current PI positions
                        if hasattr(alignment, 'regenerate_segments'):
                            alignment.regenerate_segments()

                    # Update visualization to match current IFC state
                    # Try update_visualizations first (creates full visualization)
                    if hasattr(visualizer, 'update_visualizations'):
                        visualizer.update_visualizations()
                        refresh_count += 1
                    elif hasattr(visualizer, 'update_all'):
                        visualizer.update_all()
                        refresh_count += 1

                    logger.debug(f"Refreshed visualizer for alignment")
                except Exception as e:
                    logger.warning(f"Failed to refresh visualizer: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())

            # Also check alignments that might not have visualizers in the list
            alignments = get_all_alignments()
            for alignment in alignments:
                try:
                    # Check if this alignment's visualizer was already handled
                    if hasattr(alignment, 'visualizer') and alignment.visualizer:
                        if alignment.visualizer in visualizers:
                            continue  # Already handled

                        # Regenerate segments
                        if hasattr(alignment, 'regenerate_segments'):
                            alignment.regenerate_segments()

                        # Update visualization
                        if hasattr(alignment.visualizer, 'update_visualizations'):
                            alignment.visualizer.update_visualizations()
                            refresh_count += 1
                        elif hasattr(alignment.visualizer, 'update_all'):
                            alignment.visualizer.update_all()
                            refresh_count += 1
                except Exception as e:
                    logger.warning(f"Failed to refresh alignment: {e}")

            if refresh_count > 0:
                logger.info(f"Refreshed {refresh_count} alignment visualizations after undo/redo")

        except ImportError:
            logger.debug("Alignment registry not available - skipping visualization refresh")
        except Exception as e:
            logger.warning(f"Error refreshing visualizations after undo/redo: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    @classmethod
    def clear_history(cls) -> None:
        """Clear all transaction history and reset state."""
        cls.history.clear()
        cls.future.clear()
        cls.current_transaction = ""
        cls.last_transaction = ""
        cls._transaction_depth = 0
        cls.id_map.clear()
        cls.guid_map.clear()
        cls.edited_objs.clear()
        cls.is_dirty = False
        logger.debug("Cleared transaction history")

    @classmethod
    def can_undo(cls) -> bool:
        """Check if undo is available."""
        return len(cls.history) > 0

    @classmethod
    def can_redo(cls) -> bool:
        """Check if redo is available."""
        return len(cls.future) > 0

    @classmethod
    def get_undo_description(cls) -> str:
        """Get description of the operation that would be undone."""
        if not cls.history:
            return ""
        key = cls.history[-1]["key"]
        # Extract the operation name from the key (after the UUID prefix)
        parts = key.split("_", 1)
        return parts[1] if len(parts) > 1 else key

    @classmethod
    def get_redo_description(cls) -> str:
        """Get description of the operation that would be redone."""
        if not cls.future:
            return ""
        key = cls.future[-1]["key"]
        # Extract the operation name from the key (after the UUID prefix)
        parts = key.split("_", 1)
        return parts[1] if len(parts) > 1 else key

    # =========================================================================
    # Element Linking with Transaction Support
    # =========================================================================

    @classmethod
    def link_element(
        cls,
        element: 'ifcopenshell.entity_instance',
        obj: Any
    ) -> None:
        """
        Link an IFC element to a Blender object with transaction support.

        If in a transaction, registers undo/redo operations for the link.

        Args:
            element: IFC entity to link
            obj: Blender object to link to
        """
        # Store in maps
        cls.id_map[element.id()] = obj
        if hasattr(element, "GlobalId") and element.GlobalId:
            cls.guid_map[element.GlobalId] = obj

        # Store reference on object
        obj["ifc_definition_id"] = element.id()
        obj["ifc_class"] = element.is_a()
        if hasattr(element, "GlobalId"):
            obj["GlobalId"] = element.GlobalId

        # Register transaction operation if in transaction
        if cls.current_transaction:
            element_id = element.id()
            element_guid = getattr(element, "GlobalId", None)
            obj_name = obj.name

            def rollback_link(data: Dict) -> None:
                """Remove the element link."""
                cls.id_map.pop(data["id"], None)
                if data.get("guid"):
                    cls.guid_map.pop(data["guid"], None)
                # Note: Can't reliably access obj after potential deletion

            def commit_link(data: Dict) -> None:
                """Re-establish the element link."""
                import bpy
                obj = bpy.data.objects.get(data["obj_name"])
                if obj and cls._ifc_file:
                    try:
                        element = cls._ifc_file.by_id(data["id"])
                        cls.id_map[data["id"]] = obj
                        if data.get("guid"):
                            cls.guid_map[data["guid"]] = obj
                    except RuntimeError:
                        pass  # Entity doesn't exist

            cls.add_operation(
                rollback=rollback_link,
                commit=commit_link,
                data={"id": element_id, "guid": element_guid, "obj_name": obj_name}
            )

    @classmethod
    def unlink_element(cls, element_id: int) -> None:
        """
        Remove link between IFC element and Blender object.

        Args:
            element_id: IFC entity step ID to unlink
        """
        obj = cls.id_map.pop(element_id, None)
        if obj and cls._ifc_file:
            try:
                element = cls._ifc_file.by_id(element_id)
                if hasattr(element, "GlobalId"):
                    cls.guid_map.pop(element.GlobalId, None)
            except RuntimeError:
                pass  # Element already deleted

    @classmethod
    def get_object(cls, element_id: int) -> Optional[Any]:
        """Get Blender object linked to IFC element ID."""
        return cls.id_map.get(element_id)

    @classmethod
    def get_object_by_guid(cls, guid: str) -> Optional[Any]:
        """Get Blender object linked to IFC GlobalId."""
        return cls.guid_map.get(guid)

    # =========================================================================
    # Edit Tracking
    # =========================================================================

    @classmethod
    def mark_edited(cls, obj: Any) -> None:
        """Mark an object as edited since last save."""
        cls.edited_objs.add(obj)
        cls.is_dirty = True

    @classmethod
    def clear_edited(cls) -> None:
        """Clear the edited objects set (called after save)."""
        cls.edited_objs.clear()
        cls.is_dirty = False

    @classmethod
    def get_history_info(cls) -> Dict[str, Any]:
        """Get information about current transaction state."""
        return {
            "history_size": len(cls.history),
            "future_size": len(cls.future),
            "can_undo": cls.can_undo(),
            "can_redo": cls.can_redo(),
            "in_transaction": bool(cls.current_transaction),
            "is_dirty": cls.is_dirty,
            "undo_description": cls.get_undo_description(),
            "redo_description": cls.get_redo_description(),
        }


__all__ = ["TransactionManager", "Operation", "TransactionStep"]