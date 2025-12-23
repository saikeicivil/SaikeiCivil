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
Saikei Civil - Alignment Update System Operators

This module provides real-time update capabilities for alignments:
1. Detects when a PI moves
2. Updates the visualization immediately (fast Blender-only update)
3. Debounces IFC regeneration until movement stops

Operators:
    SAIKEI_OT_update_alignment: Manually update alignment from PI positions
    SAIKEI_OT_toggle_auto_update: Toggle automatic alignment updates

Also includes:
    - saikei_update_handler: Blender depsgraph handler for real-time updates
    - _debounced_ifc_regeneration: Timer for deferred IFC entity creation

Note: AlignmentVisualizer is in tool/alignment_visualizer.py (Layer 2).
The update handler accesses it via alignment.visualizer attribute.
"""

import bpy
from bpy.app.handlers import persistent
import time

from ..core.logging_config import get_logger

logger = get_logger(__name__)


# =============================================================================
# PART 1: ALIGNMENT REGISTRY
# =============================================================================

_alignment_registry = {}


def register_alignment(alignment):
    """Register an alignment for real-time updates."""
    alignment_id = id(alignment)  # Use Python object ID
    _alignment_registry[alignment_id] = alignment
    logger.info("Registered alignment: %s", alignment.alignment.Name)


def unregister_alignment(alignment):
    """Unregister an alignment."""
    alignment_id = id(alignment)
    if alignment_id in _alignment_registry:
        del _alignment_registry[alignment_id]
        logger.info("Unregistered alignment: %s", alignment.alignment.Name)


def get_alignment_from_pi(pi_object):
    """Get alignment from PI object.

    Uses IFC GlobalId (persistent across sessions) to look up the alignment.
    If needed, creates the alignment Python object and visualizer on-demand.
    """
    if 'bc_alignment_id' not in pi_object:
        return None

    alignment_id = pi_object['bc_alignment_id']

    # Handle both old format (Python object ID as string) and new format (IFC GlobalId)
    # IFC GlobalIds are 22 characters, Python object IDs are numeric
    if isinstance(alignment_id, str) and len(alignment_id) == 22:
        # New format: IFC GlobalId - look up by GlobalId and create if needed
        from ..core.alignment_registry import get_or_create_alignment, get_or_create_visualizer
        from ..core.native_ifc_manager import NativeIfcManager

        ifc = NativeIfcManager.get_file()
        if not ifc:
            return None

        # Find alignment entity by GlobalId
        try:
            alignment_entity = ifc.by_guid(alignment_id)
            if alignment_entity and alignment_entity.is_a('IfcAlignment'):
                # Get or create alignment Python object
                alignment_obj, _ = get_or_create_alignment(alignment_entity)

                # CRITICAL: Also ensure visualizer exists for real-time curve updates!
                # get_or_create_visualizer links the visualizer to alignment.visualizer
                get_or_create_visualizer(alignment_obj)

                return alignment_obj
        except (RuntimeError, KeyError):
            logger.debug("Could not find alignment with GlobalId: %s", alignment_id)
            return None
    else:
        # Old format: Python object ID (deprecated, for backward compatibility)
        try:
            alignment_id_int = int(alignment_id)
            return _alignment_registry.get(alignment_id_int)
        except (ValueError, TypeError):
            return None

    return None


# =============================================================================
# PART 2: UPDATE HANDLER
# =============================================================================

_last_update = {}
_throttle_ms = 50  # 20 FPS minimum
_updating = False  # Reentrancy guard

# DEBOUNCE: Track pending IFC regeneration
_pending_ifc_regeneration = {}  # alignment_id -> last_movement_time
_ifc_regeneration_delay = 0.3  # Wait 300ms after last movement before regenerating IFC
_last_regeneration_time = {}  # alignment_id -> time of last regeneration (cooldown)
_regeneration_cooldown = 0.5  # Don't regenerate again within 500ms of last regeneration


def _debounced_ifc_regeneration():
    """Timer callback to regenerate IFC after movement has stopped.

    This runs periodically and checks if enough time has passed since the last
    movement for each alignment. If so, it regenerates the IFC segments.
    """
    global _updating, _pending_ifc_regeneration

    if _updating:
        return 0.1  # Check again in 100ms

    current_time = time.time()
    regenerated = []

    # DEBUG: Show timer state
    logger.info("=== DEBOUNCE TIMER FIRED ===")
    logger.info("  Pending regenerations: %s", len(_pending_ifc_regeneration))
    logger.info("  Registry has %s alignments", len(_alignment_registry))
    logger.info("  Registry keys: %s", list(_alignment_registry.keys()))

    for alignment_id, last_move_time in list(_pending_ifc_regeneration.items()):
        time_since_move = current_time - last_move_time
        logger.info("  Checking alignment_id=%s, time_since_move=%.3fs", alignment_id, time_since_move)

        # Check if enough time has passed since last movement
        if time_since_move >= _ifc_regeneration_delay:
            # Check cooldown - don't regenerate if we just regenerated recently
            last_regen = _last_regeneration_time.get(alignment_id, 0)
            time_since_regen = current_time - last_regen
            if time_since_regen < _regeneration_cooldown:
                logger.info("  Skipping - cooldown active (%.3fs since last regen)", time_since_regen)
                regenerated.append(alignment_id)  # Remove from pending anyway
                continue

            # Find the alignment
            alignment = _alignment_registry.get(alignment_id)
            logger.info("  Looking up alignment_id=%s in registry: found=%s", alignment_id, alignment is not None)
            logger.info("  alignment type=%s, bool(alignment)=%s", type(alignment).__name__, bool(alignment) if alignment is not None else 'N/A')
            if alignment is not None:
                logger.info("  Alignment has %s PIs", len(alignment.pis) if hasattr(alignment, 'pis') else 'NO pis attr')
                _updating = True
                try:
                    # Now regenerate IFC segments (this is the expensive operation)
                    has_curves = any('curve' in pi for pi in alignment.pis)
                    logger.info("  has_curves=%s, calling regenerate_segments()", has_curves)
                    if has_curves:
                        alignment.regenerate_segments_with_curves()
                    else:
                        alignment.regenerate_segments()

                    # Record regeneration time for cooldown
                    _last_regeneration_time[alignment_id] = current_time

                    logger.info("  REGENERATION COMPLETE for %s", alignment.alignment.Name)
                except Exception as e:
                    logger.error("  ERROR in debounced regeneration: %s", e)
                    import traceback
                    traceback.print_exc()
                finally:
                    _updating = False

            regenerated.append(alignment_id)

    # Remove regenerated alignments from pending list
    for alignment_id in regenerated:
        del _pending_ifc_regeneration[alignment_id]

    # Keep timer running if there are pending regenerations, otherwise stop
    if _pending_ifc_regeneration:
        return 0.1  # Check again in 100ms
    else:
        return None  # Stop timer


@persistent
def saikei_update_handler(scene, depsgraph):
    """
    Detects PI movements/deletions and regenerates alignments.

    This is called by Blender whenever objects change.
    """
    global _updating

    # Prevent reentrancy - critical to avoid crashes when deleting/creating objects
    if _updating:
        return

    current_time = time.time()

    # DEBUG: Log handler activity
    pi_updates_found = 0

    # ========================================================================
    # PART 1: Check for deleted PI objects and sync to IFC
    # ========================================================================

    alignments_to_update = set()

    for alignment in list(_alignment_registry.values()):
        # Check if any PI objects have been deleted
        deleted_pis = []

        for pi_idx, pi in enumerate(alignment.pis):
            blender_obj = pi.get('blender_object')

            if blender_obj is not None:
                # Check if object still exists in Blender
                try:
                    # Try to access the object's name - will raise ReferenceError if deleted
                    _ = blender_obj.name

                    # Also check if it's in bpy.data.objects
                    if blender_obj.name not in bpy.data.objects:
                        deleted_pis.append(pi_idx)
                        logger.debug("PI %s deleted from outliner", pi_idx)
                except ReferenceError:
                    # Object was deleted
                    deleted_pis.append(pi_idx)
                    logger.debug("PI %s deleted (reference error)", pi_idx)

        # If any PIs were deleted, remove them from the alignment
        if deleted_pis:
            _updating = True
            try:
                # Remove PIs in reverse order to maintain indices
                for pi_idx in reversed(deleted_pis):
                    pi = alignment.pis[pi_idx]

                    # Remove IFC entity if it exists
                    if pi.get('ifc_point'):
                        try:
                            alignment.ifc.remove(pi['ifc_point'])
                            logger.debug("Removed IFC point for PI %s", pi_idx)
                        except Exception as e:
                            logger.error("Could not remove IFC point: %s", e)

                    # Remove from alignment.pis list
                    alignment.pis.pop(pi_idx)

                # Reindex remaining PIs
                for new_idx, pi in enumerate(alignment.pis):
                    pi['id'] = new_idx
                    # Update blender object property if it exists
                    if pi.get('blender_object'):
                        pi['blender_object']['bc_pi_id'] = new_idx

                # Mark this alignment for regeneration
                alignments_to_update.add(id(alignment))

                logger.info("Removed %s PI(s), %s remaining", len(deleted_pis), len(alignment.pis))

            except Exception as e:
                logger.error("Error during PI deletion: %s", e)
                import traceback
                traceback.print_exc()
            finally:
                _updating = False

    # Regenerate alignments that had deletions
    for alignment_id in alignments_to_update:
        for alignment in _alignment_registry.values():
            if id(alignment) == alignment_id:
                _updating = True
                try:
                    # Regenerate segments
                    has_curves = any('curve' in pi for pi in alignment.pis)
                    if has_curves:
                        alignment.regenerate_segments_with_curves()
                    else:
                        alignment.regenerate_segments()

                    # Update visualization
                    if hasattr(alignment, 'visualizer') and alignment.visualizer:
                        try:
                            alignment.visualizer.update_all()
                        except (ReferenceError, AttributeError, RuntimeError) as e:
                            logger.warning("Visualization update skipped: %s", e)

                    logger.info("Regenerated alignment after PI deletion")
                except Exception as e:
                    logger.error("Error regenerating after deletion: %s", e)
                    import traceback
                    traceback.print_exc()
                finally:
                    _updating = False
                break

    # ========================================================================
    # PART 2: Process transform updates (existing code)
    # ========================================================================

    for update in depsgraph.updates:
        # Only care about transforms
        if not update.is_updated_transform:
            continue

        obj = update.id

        # Must be an Object
        if not isinstance(obj, bpy.types.Object):
            continue

        # Safety check: ensure object is still valid (not being deleted by BlenderBIM)
        try:
            if obj.name not in bpy.data.objects:
                continue
        except (ReferenceError, AttributeError):
            # Object reference is dead - skip it
            continue

        # Must be a Saikei Civil PI
        if 'bc_pi_id' not in obj or 'bc_alignment_id' not in obj:
            continue

        # DEBUG: We found a PI being moved!
        logger.info("=== PI MOVEMENT DETECTED: %s ===", obj.name)
        logger.info("  bc_alignment_id: %s (type: %s, len: %s)",
                   obj['bc_alignment_id'],
                   type(obj['bc_alignment_id']).__name__,
                   len(str(obj['bc_alignment_id'])) if obj['bc_alignment_id'] else 0)

        # Get the alignment
        alignment = get_alignment_from_pi(obj)
        if alignment is None:
            logger.warning("  FAILED to get alignment from PI!")
            continue
        else:
            logger.info("  Got alignment: %s", alignment.alignment.Name)
        
        # Check auto-update enabled
        if not getattr(alignment, 'auto_update', True):
            continue
        
        # Throttle updates
        alignment_id = id(alignment)
        last_time = _last_update.get(alignment_id, 0)
        if (current_time - last_time) < (_throttle_ms / 1000.0):
            continue
        
        _last_update[alignment_id] = current_time

        # === UPDATE THE ALIGNMENT ===

        # Update PI position from object
        pi_id = obj['bc_pi_id']
        if pi_id < len(alignment.pis):
            pi = alignment.pis[pi_id]

            # Get new position
            from ..core.native_ifc_alignment import SimpleVector
            new_pos = SimpleVector(obj.location.x, obj.location.y)

            # Check if actually moved
            old_pos = pi['position']
            if abs(new_pos.x - old_pos.x) < 0.001 and abs(new_pos.y - old_pos.y) < 0.001:
                continue

            # Set reentrancy flag before updating
            _updating = True
            try:
                # Update position in memory (this is fast)
                pi['position'] = new_pos

                # ================================================================
                # VISUAL UPDATE ONLY - Update Blender curves without touching IFC
                # This gives real-time feedback during dragging
                # ================================================================
                if hasattr(alignment, 'visualizer') and alignment.visualizer:
                    try:
                        # Only update the visual curves (move existing points)
                        # Don't recreate them - just update their positions
                        alignment.visualizer.update_segment_curves_fast(alignment.pis)
                    except (ReferenceError, AttributeError, RuntimeError) as e:
                        logger.debug("Fast visual update skipped: %s", e)

                # ================================================================
                # DEBOUNCED IFC REGENERATION - Schedule for after movement stops
                # This prevents creating thousands of intermediate IFC entities
                # ================================================================
                _pending_ifc_regeneration[alignment_id] = current_time

                # Start the debounce timer if not already running
                if not bpy.app.timers.is_registered(_debounced_ifc_regeneration):
                    bpy.app.timers.register(_debounced_ifc_regeneration, first_interval=0.1)

            except Exception as e:
                # Catch any unexpected errors to prevent Blender crashes
                logger.error("Error updating alignment: %s", e)
                import traceback
                traceback.print_exc()
            finally:
                # Always reset flag, even if there's an error
                _updating = False


def register_handler():
    """Register the update handler with Blender."""
    if saikei_update_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(saikei_update_handler)
        logger.info("Saikei Civil update handler REGISTERED")
        return True
    return False


def unregister_handler():
    """Unregister the update handler."""
    if saikei_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(saikei_update_handler)
        logger.info("Saikei Civil update handler UNREGISTERED")
        return True
    return False


# =============================================================================
# PART 3: MANUAL UPDATE OPERATOR
# =============================================================================

class SAIKEI_OT_update_alignment(bpy.types.Operator):
    """Manually update alignment from PI positions"""
    bl_idname = "saikei.update_alignment"
    bl_label = "Update Alignment"
    bl_description = "Regenerate alignment from current PI positions"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        updated = 0

        for alignment in _alignment_registry.values():
            # Update all PI positions from Blender
            for pi in alignment.pis:
                if pi.get('blender_object'):
                    obj = pi['blender_object']
                    from ..core.native_ifc_alignment import SimpleVector
                    pi['position'] = SimpleVector(obj.location.x, obj.location.y)
                    if pi.get('ifc_point'):
                        pi['ifc_point'].Coordinates = [
                            float(pi['position'].x),
                            float(pi['position'].y)
                        ]

            # Regenerate (with curves if present)
            has_curves = any('curve' in pi for pi in alignment.pis)
            if has_curves:
                alignment.regenerate_segments_with_curves()
            else:
                alignment.regenerate_segments()

            # Visualize
            if hasattr(alignment, 'visualizer') and alignment.visualizer:
                alignment.visualizer.update_all()

            updated += 1

        self.report({'INFO'}, f"Updated {updated} alignment(s)")
        return {'FINISHED'}


class SAIKEI_OT_toggle_auto_update(bpy.types.Operator):
    """Toggle auto-update on/off"""
    bl_idname = "saikei.toggle_auto_update"
    bl_label = "Toggle Auto-Update"
    bl_description = "Toggle automatic alignment updates"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        if len(_alignment_registry) == 0:
            self.report({'WARNING'}, "No alignments found")
            return {'CANCELLED'}
        
        # Toggle first alignment (could be improved with selection)
        alignment = list(_alignment_registry.values())[0]
        alignment.auto_update = not getattr(alignment, 'auto_update', True)
        
        state = "enabled" if alignment.auto_update else "disabled"
        self.report({'INFO'}, f"Auto-update {state}")
        
        return {'FINISHED'}


# =============================================================================
# PART 4: REGISTRATION
# =============================================================================

classes = (
    SAIKEI_OT_update_alignment,
    SAIKEI_OT_toggle_auto_update,
)


def register():
    """Register operators and handler."""
    for cls in classes:
        bpy.utils.register_class(cls)

    register_handler()
    logger.info("Saikei Civil update system registered")


def unregister():
    """Unregister everything."""
    unregister_handler()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    logger.info("Saikei Civil update system unregistered")


# =============================================================================
# TESTING & DEBUGGING
# =============================================================================

def test_system():
    """Test the update system."""
    logger.info("\n=== Saikei Civil Update System Test ===")

    # Check handler
    logger.info("Handler registered: %s", saikei_update_handler in bpy.app.handlers.depsgraph_update_post)

    # Check alignments
    logger.info("Registered alignments: %s", len(_alignment_registry))
    for align_id, alignment in _alignment_registry.items():
        logger.info("  - %s: %s PIs, %s segments", alignment.name, len(alignment.pis), len(alignment.segments))

    # Check PIs
    if len(_alignment_registry) > 0:
        alignment = list(_alignment_registry.values())[0]
        logger.info("\nChecking PIs in '%s':", alignment.name)
        for pi in alignment.pis:
            obj = pi.get('blender_object')
            if obj:
                has_pi_id = 'bc_pi_id' in obj
                has_align_id = 'bc_alignment_id' in obj
                logger.info("  PI %s: Object=%s, bc_pi_id=%s, bc_alignment_id=%s", pi['id'], obj.name, has_pi_id, has_align_id)
            else:
                logger.info("  PI %s: No Blender object!", pi['id'])

    logger.info("=" * 40 + "\n")


if __name__ == "__main__":
    logger.info("Saikei Civil Update System")
    logger.info("Import this module in your addon")
