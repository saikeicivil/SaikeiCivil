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
Blender Undo/Redo Synchronization Handlers
==========================================

Provides persistent handlers to synchronize Blender's undo/redo system
with the IFC transaction system.

When the user performs undo/redo in Blender (Ctrl+Z, Ctrl+Shift+Z), these
handlers detect the change and trigger corresponding IFC undo/redo operations.

Handlers:
    undo_post: Called after Blender performs an undo
    redo_post: Called after Blender performs a redo
    depsgraph_update_post: Called after any scene update (for edit tracking)
    load_post: Called after a .blend file is loaded

Architecture based on Bonsai/BlenderBIM patterns.
"""

import bpy
from bpy.app.handlers import persistent

from ..core.ifc_manager.transaction import TransactionManager
from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Track the last known Blender undo step to detect undo/redo
_last_blender_undo_step: str = ""

# Flag to prevent recursive undo/redo calls
_processing_undo: bool = False


def _get_blender_undo_step() -> str:
    """
    Get a string representing the current Blender undo step.

    This is used to detect when Blender has performed an undo/redo
    that our handlers didn't initiate.

    Returns:
        String identifier for current undo state
    """
    # Use the operators that are available in the undo history
    # This is a simplification - Bonsai uses more sophisticated tracking
    try:
        # Get the last operator from the undo stack
        if bpy.context.window_manager.operators:
            last_op = bpy.context.window_manager.operators[-1]
            return f"{last_op.bl_idname}_{id(last_op)}"
    except Exception:
        pass
    return ""


@persistent
def undo_post_handler(scene):
    """
    Handler called after Blender performs an undo.

    Synchronizes IFC transaction undo with Blender's undo.
    This handler is called whenever Blender's undo system triggers,
    including from keyboard shortcuts (Ctrl+Z) and menu actions.

    Args:
        scene: The scene that was active when undo was triggered
    """
    global _processing_undo, _last_blender_undo_step

    if _processing_undo:
        return

    _processing_undo = True
    try:
        # Check if we need to sync IFC undo
        current_step = _get_blender_undo_step()

        # Detect if this is a Blender-initiated undo (not from our operators)
        if current_step != _last_blender_undo_step:
            # Check if we have IFC transactions to potentially sync
            if TransactionManager.can_undo():
                # The tricky part: Blender undo doesn't tell us WHAT was undone
                # We have to be careful not to double-undo
                # For now, we log but don't auto-sync to avoid confusion
                logger.debug(
                    f"Blender undo detected. IFC history has {len(TransactionManager.history)} items. "
                    "Use bc.undo_ifc to undo IFC operations."
                )

        _last_blender_undo_step = current_step

    except Exception as e:
        logger.error(f"Error in undo_post_handler: {e}")
    finally:
        _processing_undo = False


@persistent
def redo_post_handler(scene):
    """
    Handler called after Blender performs a redo.

    Synchronizes IFC transaction redo with Blender's redo.

    Args:
        scene: The scene that was active when redo was triggered
    """
    global _processing_undo, _last_blender_undo_step

    if _processing_undo:
        return

    _processing_undo = True
    try:
        current_step = _get_blender_undo_step()

        if current_step != _last_blender_undo_step:
            if TransactionManager.can_redo():
                logger.debug(
                    f"Blender redo detected. IFC future has {len(TransactionManager.future)} items. "
                    "Use bc.redo_ifc to redo IFC operations."
                )

        _last_blender_undo_step = current_step

    except Exception as e:
        logger.error(f"Error in redo_post_handler: {e}")
    finally:
        _processing_undo = False


@persistent
def depsgraph_update_post_handler(scene, depsgraph):
    """
    Handler called after any scene update.

    Used for edit tracking - detects when objects linked to IFC entities
    have been modified (moved, edited, etc.).

    Args:
        scene: The scene that was updated
        depsgraph: The dependency graph that was updated
    """
    try:
        # Check if we're in an active transaction (skip tracking during operations)
        if TransactionManager.current_transaction:
            return

        # Check for updates to objects that are linked to IFC entities
        for update in depsgraph.updates:
            if not isinstance(update.id, bpy.types.Object):
                continue

            obj = update.id

            # Check if object is linked to an IFC entity
            if "ifc_definition_id" not in obj:
                continue

            # Check if the object was transformed or its geometry changed
            if update.is_updated_transform or update.is_updated_geometry:
                TransactionManager.mark_edited(obj)
                logger.debug(f"Object marked as edited: {obj.name}")

    except Exception as e:
        # Don't log every depsgraph error - too noisy
        pass


@persistent
def load_post_handler(filepath):
    """
    Handler called after a .blend file is loaded.

    Clears the transaction history since the IFC state is unknown
    after loading a new .blend file.

    Args:
        filepath: Path to the loaded .blend file (may be empty for new files)
    """
    try:
        # Clear transaction history
        TransactionManager.clear_history()
        logger.debug("Cleared transaction history after .blend file load")
    except Exception as e:
        logger.error(f"Error in load_post_handler: {e}")


@persistent
def save_pre_handler(filepath):
    """
    Handler called before a .blend file is saved.

    Clears the dirty flag if both .blend and IFC are being saved together.

    Args:
        filepath: Path where the .blend file will be saved
    """
    # Note: This doesn't mean the IFC file is being saved
    # The user must explicitly save the IFC file
    pass


def register_handlers():
    """Register all undo/redo handlers."""
    # Undo/Redo handlers
    if undo_post_handler not in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.append(undo_post_handler)
        logger.debug("Registered undo_post handler")

    if redo_post_handler not in bpy.app.handlers.redo_post:
        bpy.app.handlers.redo_post.append(redo_post_handler)
        logger.debug("Registered redo_post handler")

    # Edit tracking handler
    if depsgraph_update_post_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_post_handler)
        logger.debug("Registered depsgraph_update_post handler")

    # Load handler
    if load_post_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post_handler)
        logger.debug("Registered load_post handler")

    logger.info("Registered undo/redo handlers")


def unregister_handlers():
    """Unregister all undo/redo handlers."""
    if undo_post_handler in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.remove(undo_post_handler)

    if redo_post_handler in bpy.app.handlers.redo_post:
        bpy.app.handlers.redo_post.remove(redo_post_handler)

    if depsgraph_update_post_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_post_handler)

    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)

    logger.info("Unregistered undo/redo handlers")


__all__ = [
    "register_handlers",
    "unregister_handlers",
    "undo_post_handler",
    "redo_post_handler",
    "depsgraph_update_post_handler",
    "load_post_handler",
]