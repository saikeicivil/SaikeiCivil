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
SaikeiIfcOperator Base Class
=============================

Provides a base class for all IFC-modifying operators with automatic
transaction handling.

All operators that modify IFC data should inherit from SaikeiIfcOperator
instead of bpy.types.Operator. This ensures:
1. Transactions are properly begun and ended
2. Undo/redo callbacks are registered
3. Nested operators share the parent's transaction
4. Errors are properly handled and transactions are rolled back

Usage:
    class BC_OT_my_operator(SaikeiIfcOperator):
        bl_idname = "bc.my_operator"
        bl_label = "My Operator"

        def _execute(self, context):
            # Your IFC-modifying code here
            # Transaction is already started
            ifc = NativeIfcManager.get_file()
            entity = ifc.create_entity("IfcSomething", ...)

            # Add custom undo/redo operations if needed
            self.add_operation(
                rollback=lambda data: delete_entity(data['id']),
                commit=lambda data: recreate_entity(data),
                data={'id': entity.id()}
            )

            return {'FINISHED'}

Architecture based on Bonsai/BlenderBIM patterns.
"""

from typing import Any, Callable, Dict, Optional, Set
import bpy
from bpy.types import Operator

from ..core.ifc_manager.transaction import TransactionManager
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class SaikeiIfcOperator(Operator):
    """
    Base class for IFC operators with automatic transaction handling.

    Inheriting from this class automatically wraps the execute() method
    in a transaction. Override _execute() instead of execute() to implement
    operator logic.

    Class Attributes:
        transaction_key: Optional key to share transaction with nested operators.
                        If set, nested operators will join this transaction.
        transaction_data: Optional dictionary to store operation-specific data
                         that can be accessed in _execute().

    Methods to Override:
        _execute(context): Implement your operator logic here. Return
                          {'FINISHED'} or {'CANCELLED'}.

    Helper Methods:
        add_operation(rollback, commit, data): Add custom undo/redo callbacks
        get_file(): Get the active IFC file
        report_and_log(type, message): Report to user and log
    """

    # Transaction configuration
    transaction_key: str = ""
    transaction_data: Optional[Dict[str, Any]] = None

    # Set of bl_idnames that should NOT be wrapped in transactions
    # (e.g., undo/redo operators themselves, file open/save)
    _non_transactional_operators: Set[str] = {
        "bc.undo_ifc",
        "bc.redo_ifc",
        "bc.open_ifc",
        "bc.save_ifc",
        "bc.new_ifc",
        "bc.clear_ifc",
        "bc.reload_ifc",
        "bc.show_ifc_info",
    }

    def execute(self, context) -> Set[str]:
        """
        Execute the operator with transaction wrapping.

        This method handles:
        1. Beginning a transaction (or joining an existing one)
        2. Calling _execute() with error handling
        3. Ending the transaction
        4. Rolling back on error

        Do not override this method. Override _execute() instead.

        Args:
            context: Blender context

        Returns:
            {'FINISHED'} or {'CANCELLED'}
        """
        # Check if this operator should be transactional
        if self.bl_idname in self._non_transactional_operators:
            return self._execute(context)

        # Get transaction key (use class name if not specified)
        key = self.transaction_key or self.__class__.__name__

        try:
            # Begin transaction
            TransactionManager.begin_transaction(key)

            # Execute the operator logic
            result = self._execute(context)

            # End transaction
            TransactionManager.end_transaction()

            return result

        except Exception as e:
            # Log the error
            logger.error(f"Operator {self.bl_idname} failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Try to end the transaction cleanly
            try:
                TransactionManager.end_transaction()
            except Exception:
                pass

            # Report error to user
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

    def _execute(self, context) -> Set[str]:
        """
        Override this method with your operator logic.

        The transaction is already started when this method is called.
        Return {'FINISHED'} or {'CANCELLED'}.

        Args:
            context: Blender context

        Returns:
            {'FINISHED'} or {'CANCELLED'}
        """
        raise NotImplementedError(
            f"Operator {self.__class__.__name__} must implement _execute()"
        )

    def add_operation(
        self,
        rollback: Callable[[Dict], None],
        commit: Callable[[Dict], None],
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add an operation to the current transaction.

        Use this to register custom undo/redo callbacks for operations
        that need special handling beyond basic IFC changes.

        Args:
            rollback: Function called when undoing this operation
            commit: Function called when redoing this operation
            data: Optional data dictionary passed to callbacks
        """
        TransactionManager.add_operation(rollback, commit, data)

    def get_file(self):
        """Get the active IFC file."""
        from ..core.ifc_manager.manager import NativeIfcManager
        return NativeIfcManager.get_file()

    def report_and_log(self, report_type: str, message: str) -> None:
        """
        Report to user and log the message.

        Args:
            report_type: Blender report type ('INFO', 'WARNING', 'ERROR')
            message: Message to report and log
        """
        self.report({report_type}, message)
        if report_type == 'ERROR':
            logger.error(message)
        elif report_type == 'WARNING':
            logger.warning(message)
        else:
            logger.info(message)


class BC_OT_undo_ifc(Operator):
    """Undo the last IFC operation."""
    bl_idname = "bc.undo_ifc"
    bl_label = "Undo IFC Operation"
    bl_description = "Undo the last IFC operation"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        """Check if undo is available."""
        return TransactionManager.can_undo()

    def execute(self, context):
        """Execute undo."""
        if TransactionManager.undo():
            description = TransactionManager.get_redo_description()
            self.report({'INFO'}, f"Undid: {description}")
            logger.info(f"Undid IFC operation: {description}")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Nothing to undo")
            return {'CANCELLED'}


class BC_OT_redo_ifc(Operator):
    """Redo the last undone IFC operation."""
    bl_idname = "bc.redo_ifc"
    bl_label = "Redo IFC Operation"
    bl_description = "Redo the last undone IFC operation"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        """Check if redo is available."""
        return TransactionManager.can_redo()

    def execute(self, context):
        """Execute redo."""
        if TransactionManager.redo():
            description = TransactionManager.get_undo_description()
            self.report({'INFO'}, f"Redid: {description}")
            logger.info(f"Redid IFC operation: {description}")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Nothing to redo")
            return {'CANCELLED'}


class BC_OT_show_transaction_info(Operator):
    """Show transaction history information."""
    bl_idname = "bc.show_transaction_info"
    bl_label = "Show Transaction Info"
    bl_description = "Display transaction history information"
    bl_options = {'REGISTER'}

    def execute(self, context):
        """Display transaction info."""
        info = TransactionManager.get_history_info()

        logger.info("=" * 60)
        logger.info("TRANSACTION HISTORY INFO")
        logger.info("=" * 60)
        logger.info(f"History size: {info['history_size']}")
        logger.info(f"Future size: {info['future_size']}")
        logger.info(f"Can undo: {info['can_undo']}")
        logger.info(f"Can redo: {info['can_redo']}")
        logger.info(f"In transaction: {info['in_transaction']}")
        logger.info(f"Is dirty: {info['is_dirty']}")
        if info['undo_description']:
            logger.info(f"Next undo: {info['undo_description']}")
        if info['redo_description']:
            logger.info(f"Next redo: {info['redo_description']}")
        logger.info("=" * 60)

        self.report(
            {'INFO'},
            f"History: {info['history_size']} | Future: {info['future_size']} | "
            f"Dirty: {info['is_dirty']}"
        )
        return {'FINISHED'}


# ============================================================================
# Registration
# ============================================================================

classes = (
    BC_OT_undo_ifc,
    BC_OT_redo_ifc,
    BC_OT_show_transaction_info,
)


def register():
    """Register operators."""
    for cls in classes:
        bpy.utils.register_class(cls)
    logger.info("Registered base operators")


def unregister():
    """Unregister operators."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    logger.info("Unregistered base operators")


__all__ = [
    "SaikeiIfcOperator",
    "BC_OT_undo_ifc",
    "BC_OT_redo_ifc",
    "BC_OT_show_transaction_info",
    "register",
    "unregister",
]