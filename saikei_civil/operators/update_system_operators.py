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
2. Regenerates the alignment geometry
3. Updates the visualization

Operators:
    SAIKEI_OT_update_alignment: Manually update alignment from PI positions
    SAIKEI_OT_toggle_auto_update: Toggle automatic alignment updates

Also includes:
    - saikei_update_handler: Blender depsgraph handler for real-time updates
    - AlignmentVisualizer: Creates and updates Blender objects for alignments
"""

import bpy
from bpy.app.handlers import persistent
from mathutils import Vector
import time
import math

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
    """Get alignment from PI object."""
    if 'bc_alignment_id' not in pi_object:
        return None

    # Convert from string back to int (stored as string because Python int too large for C int)
    alignment_id = int(pi_object['bc_alignment_id'])
    return _alignment_registry.get(alignment_id)


# =============================================================================
# PART 2: UPDATE HANDLER
# =============================================================================

_last_update = {}
_throttle_ms = 50  # 20 FPS minimum
_updating = False  # Reentrancy guard


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
        
        # Get the alignment
        alignment = get_alignment_from_pi(obj)
        if alignment is None:
            continue
        
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
                # Update position
                pi['position'] = new_pos
                if pi.get('ifc_point'):
                    pi['ifc_point'].Coordinates = [float(new_pos.x), float(new_pos.y)]

                # REGENERATE ENTIRE ALIGNMENT
                # Check if any PI has curve data - if so, use regenerate_segments_with_curves()
                has_curves = any('curve' in pi for pi in alignment.pis)

                if has_curves:
                    alignment.regenerate_segments_with_curves()
                else:
                    alignment.regenerate_segments()

                # UPDATE VISUALIZATION
                if hasattr(alignment, 'visualizer') and alignment.visualizer:
                    try:
                        alignment.visualizer.update_all()
                    except (ReferenceError, AttributeError, RuntimeError) as e:
                        # Visualization update failed (possibly due to BlenderBIM override)
                        # Don't crash - just log and continue
                        logger.warning("Visualization update skipped: %s", e)
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
# PART 4: ENHANCED VISUALIZER
# =============================================================================

class AlignmentVisualizer:
    """
    Creates and updates Blender objects for alignment visualization.
    
    CRITICAL: This sets the properties that the update handler needs!
    """
    
    def __init__(self, alignment):
        self.alignment = alignment
        self.collection = None
        self.pi_objects = []
        self.segment_curves = []
        
        # Create collection
        self._create_collection()
    
    def _create_collection(self):
        """Create or get the collection for this alignment."""
        coll_name = f"Alignment_{self.alignment.name}"
        
        if coll_name in bpy.data.collections:
            self.collection = bpy.data.collections[coll_name]
        else:
            self.collection = bpy.data.collections.new(coll_name)
            bpy.context.scene.collection.children.link(self.collection)
    
    def create_pi_object(self, pi_data):
        """
        Create PI marker with CRITICAL properties.
        
        The update handler needs these properties:
        - bc_pi_id: Index of the PI
        - bc_alignment_id: ID of the alignment
        """
        pi_id = pi_data['id']
        obj = bpy.data.objects.new(f"PI_{pi_id:03d}", None)
        obj.empty_display_type = 'SPHERE'
        obj.empty_display_size = 3.0
        
        pos = pi_data['position']
        obj.location = Vector((pos.x, pos.y, 0))
        
        # CRITICAL: Set these custom properties!
        obj['bc_pi_id'] = pi_id
        obj['bc_alignment_id'] = id(self.alignment)
        
        # Color
        obj.color = (0.0, 1.0, 0.0, 1.0)
        
        # Link to collection
        self.collection.objects.link(obj)
        self.pi_objects.append(obj)
        
        # CRITICAL: Store reference in PI data!
        pi_data['blender_object'] = obj
        
        return obj
    
    def create_all_pi_objects(self):
        """Create markers for all PIs."""
        for pi in self.alignment.pis:
            if pi.get('blender_object') is None:
                self.create_pi_object(pi)
    
    def update_all(self):
        """Update entire visualization."""
        self.update_segment_curves()
        self.update_pi_markers()
    
    def update_segment_curves(self):
        """Recreate all segment curves."""
        # Remove old curves
        for curve_obj in self.segment_curves:
            if curve_obj.name in bpy.data.objects:
                bpy.data.objects.remove(curve_obj, do_unlink=True)
        self.segment_curves = []
        
        # Create new curves
        for segment in self.alignment.segments:
            curve_obj = self._create_segment_curve(segment)
            if curve_obj:
                self.segment_curves.append(curve_obj)
    
    def _create_segment_curve(self, segment):
        """Create Blender curve for a segment."""
        curve_data = bpy.data.curves.new(f"Seg_{segment['id']:03d}", 'CURVE')
        curve_data.dimensions = '3D'
        
        if segment['type'] == 'LINE':
            # Tangent line
            spline = curve_data.splines.new('POLY')
            spline.points.add(1)
            
            start = segment['start']
            end = segment['end']
            
            spline.points[0].co = (start.x, start.y, 0, 1)
            spline.points[1].co = (end.x, end.y, 0, 1)
            
            color = (0.0, 0.5, 1.0, 1.0)  # Blue
            
        elif segment['type'] == 'CIRCULARARC':
            # Circular curve
            center = segment['center']
            radius = segment['radius']
            bc = segment['start']
            ec = segment['end']
            
            # Calculate angles
            start_angle = math.atan2(bc.y - center.y, bc.x - center.x)
            end_angle = math.atan2(ec.y - center.y, ec.x - center.x)
            
            # Determine arc direction
            angle_diff = end_angle - start_angle
            if angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            elif angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            
            # Create points along arc
            num_points = max(8, int(abs(angle_diff) * radius / 5))  # Point every 5m
            
            spline = curve_data.splines.new('POLY')
            spline.points.add(num_points - 1)
            
            for i in range(num_points):
                t = i / (num_points - 1)
                angle = start_angle + t * angle_diff
                x = center.x + radius * math.cos(angle)
                y = center.y + radius * math.sin(angle)
                spline.points[i].co = (x, y, 0, 1)
            
            color = (1.0, 0.0, 0.0, 1.0)  # Red
        
        else:
            return None
        
        # Create object
        obj = bpy.data.objects.new(f"Seg_{segment['id']:03d}", curve_data)
        obj.color = color
        self.collection.objects.link(obj)
        
        return obj
    
    def update_pi_markers(self):
        """Update PI marker positions."""
        for pi_data in self.alignment.pis:
            if pi_data.get('blender_object'):
                obj = pi_data['blender_object']
                pos = pi_data['position']
                obj.location = (pos.x, pos.y, 0)


# =============================================================================
# PART 5: REGISTRATION
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
