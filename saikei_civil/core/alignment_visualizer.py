# ==============================================================================
# Saikei Civil - Civil Engineering Tools for Blender
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================

"""
Alignment Visualizer (Updated)
3D visualization of IFC alignments in Blender
PIs have NO radius - always green markers!
"""

import bpy
import math
import ifcopenshell
import ifcopenshell.guid
from mathutils import Vector
from .logging_config import get_logger

logger = get_logger(__name__)


class AlignmentVisualizer:
    """Create Blender visualization of IFC alignment"""

    def __init__(self, native_alignment):
        self.alignment = native_alignment
        self.collection = None  # Will use project collection
        self.alignment_empty = None  # Main alignment empty
        self.pi_objects = []
        self.segment_objects = []
        self.station_markers = []  # Station tick marks and labels (Blender-only visuals)

        self.setup_hierarchy()

    def setup_hierarchy(self):
        """Create alignment empty in IFC hierarchy (no separate collection)"""
        from .native_ifc_manager import NativeIfcManager

        name = self.alignment.alignment.Name or "Alignment"

        # Use the project collection for all objects (no separate collection)
        self.collection = NativeIfcManager.get_project_collection()
        if not self.collection:
            # Fallback to scene collection
            self.collection = bpy.context.scene.collection

        # Create alignment empty and parent to Alignments organizational empty
        alignments_parent = NativeIfcManager.get_alignments_collection()

        # Validate that alignments_parent still exists in Blender
        if alignments_parent:
            try:
                # Test if object is still valid
                _ = alignments_parent.name
            except ReferenceError:
                # Object was deleted, recreate the hierarchy
                logger.info("Alignments parent was deleted, recreating hierarchy")
                NativeIfcManager._create_blender_hierarchy()
                alignments_parent = NativeIfcManager.get_alignments_collection()

        if alignments_parent:
            # Check if alignment empty already exists and is valid
            alignment_empty_name = f"📐 {name}"
            if alignment_empty_name in bpy.data.objects:
                existing_empty = bpy.data.objects[alignment_empty_name]
                # Validate it's still valid
                try:
                    _ = existing_empty.name
                    self.alignment_empty = existing_empty
                except ReferenceError:
                    # Was deleted, will create new one below
                    self.alignment_empty = None
            else:
                self.alignment_empty = None

            if not self.alignment_empty:
                # Create new alignment empty
                self.alignment_empty = bpy.data.objects.new(alignment_empty_name, None)
                self.alignment_empty.empty_display_type = 'ARROWS'
                self.alignment_empty.empty_display_size = 2.0
                self.alignment_empty.parent = alignments_parent

                # Link to IFC
                self.alignment_empty["ifc_definition_id"] = self.alignment.alignment.id()
                self.alignment_empty["ifc_class"] = "IfcAlignment"

                # Add to project collection
                self.collection.objects.link(self.alignment_empty)
                logger.info("Created alignment empty: %s", alignment_empty_name)
        else:
            logger.warning("No Alignments parent found")

    def _ensure_valid_collection(self):
        """
        Ensure visualizer has a valid collection reference.
        If collection was deleted (e.g., by undo), fall back to scene collection.

        This fixes the "StructRNA of type Collection has been removed" error
        that occurs when the update system tries to create objects after the
        collection was deleted.

        Returns:
            bool: True if valid collection exists, False otherwise
        """
        # Check if current collection is still valid
        try:
            if self.collection and self.collection.name in bpy.data.collections:
                # Collection is still valid
                return True
        except (ReferenceError, AttributeError):
            # Collection reference is dead
            pass

        # Collection is invalid - use scene collection (always valid)
        # Don't try to recreate hierarchy during visualization - that can cause issues
        logger.warning("Collection was deleted (undo?), using scene collection")
        self.collection = bpy.context.scene.collection

        # Also clear alignment empty reference since hierarchy is gone
        self.alignment_empty = None

        return True

    def create_pi_object(self, pi_data):
        """Create Blender Empty for PI - Always GREEN (no radius!)"""

        # CRITICAL: Ensure valid collection before creating objects!
        if not self._ensure_valid_collection():
            logger.error("No valid collection available!")
            return None

        obj = bpy.data.objects.new(f"PI_{pi_data['id']:03d}", None)
        obj.empty_display_type = 'SPHERE'
        obj.empty_display_size = 3.0
        obj.location = Vector((pi_data['position'].x,
                              pi_data['position'].y, 0))

        # Link to IFC
        obj["ifc_pi_id"] = pi_data['id']
        obj["ifc_point_id"] = pi_data['ifc_point'].id()
        # NO RADIUS PROPERTY!

        # CRITICAL: Add these for update system!
        obj['bc_pi_id'] = pi_data['id']
        obj['bc_alignment_id'] = str(id(self.alignment))  # Store as string (Python int too large for C int)

        # CRITICAL: Store reference!
        pi_data['blender_object'] = obj

        # Always GREEN for PIs (they're just intersection points)
        obj.color = (0.0, 1.0, 0.0, 1.0)

        # Parent to alignment empty for hierarchy organization FIRST
        # (must be done before linking to collection for proper Outliner hierarchy)
        if self.alignment_empty:
            try:
                _ = self.alignment_empty.name
                obj.parent = self.alignment_empty
            except (ReferenceError, AttributeError):
                # Alignment empty was deleted, skip parenting
                pass

        # Link to collection AFTER parenting (already validated by _ensure_valid_collection)
        self.collection.objects.link(obj)

        self.pi_objects.append(obj)

        logger.debug("Created PI marker: PI_%03d", pi_data['id'])

        return obj
    
    def create_segment_curve(self, ifc_segment):
        """Create Blender curve for IFC segment"""
        from .native_ifc_manager import NativeIfcManager

        # CRITICAL: Ensure valid collection before creating objects!
        if not self._ensure_valid_collection():
            logger.error("No valid collection available!")
            return None

        params = ifc_segment.DesignParameters
        
        # Create curve data
        curve_data = bpy.data.curves.new(
            name=ifc_segment.Name or "Segment",
            type='CURVE'
        )
        curve_data.dimensions = '3D'
        curve_data.resolution_u = 24
        
        # Create spline based on type
        if params.PredefinedType == "LINE":
            spline = curve_data.splines.new('POLY')
            spline.points.add(1)
            
            start = params.StartPoint.Coordinates
            length = params.SegmentLength
            angle = params.StartDirection
            
            spline.points[0].co = (start[0], start[1], 0, 1)
            end_x = start[0] + length * math.cos(angle)
            end_y = start[1] + length * math.sin(angle)
            spline.points[1].co = (end_x, end_y, 0, 1)
            
        elif params.PredefinedType == "CIRCULARARC":
            # Generate smooth arc with PROPER turn direction handling
            spline = curve_data.splines.new('POLY')
            num_points = 32
            spline.points.add(num_points - 1)

            start = params.StartPoint.Coordinates
            start_dir = params.StartDirection
            radius = abs(params.StartRadiusOfCurvature)
            arc_length = params.SegmentLength
            angle_span = arc_length / radius

            # Determine turn direction from sign of radius
            is_right_turn = params.StartRadiusOfCurvature < 0

            # Debug output
            turn_type = "RIGHT" if is_right_turn else "LEFT"
            logger.debug("Curve %s: %s turn, R=%.2f, start=(%.2f,%.2f)",
                        ifc_segment.Name, turn_type, params.StartRadiusOfCurvature, start[0], start[1])

            if is_right_turn:
                # Right turn (clockwise)
                center_x = start[0] + radius * math.sin(start_dir)
                center_y = start[1] - radius * math.cos(start_dir)
                angle_span = -angle_span
            else:
                # Left turn (counterclockwise)
                center_x = start[0] - radius * math.sin(start_dir)
                center_y = start[1] + radius * math.cos(start_dir)

            # Generate arc points
            # CRITICAL: Tangent-to-radius conversion differs by turn direction!
            for i in range(num_points):
                t = i / (num_points - 1)
                angle = start_dir + angle_span * t

                # Convert tangent bearing to radial angle
                if is_right_turn:
                    # Right turn: radius is 90° CCW from tangent
                    radial_angle = angle + math.pi/2
                else:
                    # Left turn: radius is 90° CW from tangent
                    radial_angle = angle - math.pi/2

                x = center_x + radius * math.cos(radial_angle)
                y = center_y + radius * math.sin(radial_angle)
                spline.points[i].co = (x, y, 0, 1)
        
        # Create object
        obj = bpy.data.objects.new(ifc_segment.Name, curve_data)

        # Link to IFC
        NativeIfcManager.link_object(obj, ifc_segment)

        # Visual properties
        curve_data.bevel_depth = 0.5

        # Color code
        if params.PredefinedType == "LINE":
            obj.color = (0.2, 0.6, 1.0, 1.0)  # Blue for tangents
        else:
            obj.color = (1.0, 0.3, 0.3, 1.0)  # Red for curves

        # Parent to alignment empty for hierarchy organization FIRST
        # (must be done before linking to collection for proper Outliner hierarchy)
        if self.alignment_empty:
            try:
                _ = self.alignment_empty.name
                obj.parent = self.alignment_empty
            except (ReferenceError, AttributeError):
                # Alignment empty was deleted, skip parenting
                pass

        # Link to collection AFTER parenting (already validated by _ensure_valid_collection)
        self.collection.objects.link(obj)

        self.segment_objects.append(obj)

        logger.debug("Created segment: %s (%s)", ifc_segment.Name, params.PredefinedType)

        return obj
    
    def clear_visualizations(self):
        """Clear all existing visualizations"""
        # Remove all objects in tracked lists
        for obj in self.pi_objects + self.segment_objects:
            try:
                if obj and obj.name in bpy.data.objects:
                    bpy.data.objects.remove(obj, do_unlink=True)
            except (ReferenceError, AttributeError, RuntimeError):
                # Object already deleted or invalid - skip it
                pass

        self.pi_objects.clear()
        self.segment_objects.clear()

        # CRITICAL: Also remove any orphaned objects by name pattern
        # This handles the case where we're reloading and old objects exist
        # but aren't in our tracked lists
        if self.alignment_empty:
            try:
                # Remove all children of the alignment empty
                for child in list(self.alignment_empty.children):
                    try:
                        bpy.data.objects.remove(child, do_unlink=True)
                    except:
                        pass
            except (ReferenceError, AttributeError):
                pass

        logger.debug("Cleared visualizations")
    
    def update_visualizations(self):
        """Update all visualizations from current alignment state"""
        # Clear existing
        self.clear_visualizations()

        # Recreate all PIs
        for pi_data in self.alignment.pis:
            try:
                self.create_pi_object(pi_data)
            except Exception as e:
                logger.error("Error creating PI %s: %s", pi_data.get('id', '?'), e)

        # Recreate all segments
        for segment in self.alignment.segments:
            try:
                self.create_segment_curve(segment)
            except Exception as e:
                logger.error("Error creating segment: %s", e)

        logger.info("Updated: %d PIs, %d segments", len(self.pi_objects), len(self.segment_objects))

    def update_segments_in_place(self):
        """
        Update segment curves in-place without deleting/recreating objects.
        Safe to call during modal operations (like G for grab/move).
        Works alongside BlenderBIM without conflicts.
        """
        import math

        # Only update existing segments - don't delete/recreate
        for i, segment in enumerate(self.alignment.segments):
            if i >= len(self.segment_objects):
                # Need more segment objects - create them
                try:
                    self.create_segment_curve(segment)
                except Exception as e:
                    logger.error("Error creating new segment: %s", e)
                continue

            # Get existing segment object
            seg_obj = self.segment_objects[i]

            # Safety check - if object was deleted (e.g., by undo), recreate it
            needs_recreation = False
            try:
                if not seg_obj or seg_obj.name not in bpy.data.objects:
                    needs_recreation = True
            except (ReferenceError, AttributeError):
                needs_recreation = True

            if needs_recreation:
                # Object was deleted, recreate it
                try:
                    # create_segment_curve appends to segment_objects, so we need to handle that
                    old_len = len(self.segment_objects)
                    new_obj = self.create_segment_curve(segment)

                    if new_obj:
                        # Remove from end where it was appended
                        if len(self.segment_objects) > old_len:
                            self.segment_objects.pop()

                        # Put it in the correct position
                        if i < len(self.segment_objects):
                            self.segment_objects[i] = new_obj
                        else:
                            # If list isn't long enough, append is correct
                            self.segment_objects.append(new_obj)

                        logger.info("Recreated segment %d (was deleted)", i)
                except Exception as e:
                    logger.error("Error recreating segment %d: %s", i, e)
                continue

            # Update curve geometry data in-place
            try:
                params = segment.DesignParameters

                # CRITICAL: Update object name to match IFC segment name
                if seg_obj.name != segment.Name:
                    seg_obj.name = segment.Name

                # Also update color based on type
                if params.PredefinedType == "LINE":
                    seg_obj.color = (0.2, 0.6, 1.0, 1.0)  # Blue for tangents
                elif params.PredefinedType == "CIRCULARARC":
                    seg_obj.color = (1.0, 0.3, 0.3, 1.0)  # Red for curves

                curve_data = seg_obj.data

                # Clear existing splines
                curve_data.splines.clear()

                # Recreate geometry based on type
                if params.PredefinedType == "LINE":
                    # Tangent line
                    spline = curve_data.splines.new('POLY')
                    spline.points.add(1)  # Total 2 points

                    start = params.StartPoint.Coordinates
                    spline.points[0].co = (start[0], start[1], 0, 1)

                    length = params.SegmentLength
                    angle = params.StartDirection
                    end_x = start[0] + length * math.cos(angle)
                    end_y = start[1] + length * math.sin(angle)
                    spline.points[1].co = (end_x, end_y, 0, 1)

                elif params.PredefinedType == "CIRCULARARC":
                    # Circular arc
                    start = params.StartPoint.Coordinates
                    radius = abs(params.StartRadiusOfCurvature)  # FIXED: Use StartRadiusOfCurvature directly
                    angle_start = params.StartDirection
                    length = params.SegmentLength

                    # Calculate arc parameters
                    angle_subtended = length / radius
                    is_ccw = params.StartRadiusOfCurvature > 0  # FIXED: Use StartRadiusOfCurvature directly

                    if not is_ccw:
                        angle_subtended = -angle_subtended

                    # Center point
                    center_angle = angle_start + (math.pi / 2 if is_ccw else -math.pi / 2)
                    center_x = start[0] + radius * math.cos(center_angle)
                    center_y = start[1] + radius * math.sin(center_angle)

                    # Create arc points
                    num_points = max(8, int(abs(angle_subtended) * radius / 5))
                    spline = curve_data.splines.new('POLY')
                    spline.points.add(num_points - 1)

                    for j in range(num_points):
                        t = j / (num_points - 1)
                        angle = angle_start + t * angle_subtended - (math.pi / 2 if is_ccw else -math.pi / 2)
                        x = center_x + radius * math.cos(angle)
                        y = center_y + radius * math.sin(angle)
                        spline.points[j].co = (x, y, 0, 1)

            except Exception as e:
                logger.error("Error updating segment %d geometry: %s", i, e)

        # Remove extra segment objects if alignment has fewer segments now
        while len(self.segment_objects) > len(self.alignment.segments):
            extra_obj = self.segment_objects.pop()
            try:
                if extra_obj and extra_obj.name in bpy.data.objects:
                    bpy.data.objects.remove(extra_obj, do_unlink=True)
            except:
                pass

        logger.debug("Updated %d segments in-place", len(self.segment_objects))

    def update_all(self):
        """Update entire visualization - Required by complete_update_system"""
        # FIRST: Ensure we have a valid collection for all operations
        # This prevents some objects going to hierarchy and others to scene root
        self._ensure_valid_collection()

        # Validate and recreate PI objects if they were deleted (e.g., by undo)
        for pi_data in self.alignment.pis:
            blender_obj = pi_data.get('blender_object')
            needs_recreation = False

            if blender_obj is not None:
                # Check if object still exists
                try:
                    _ = blender_obj.name
                    if blender_obj.name not in bpy.data.objects:
                        needs_recreation = True
                except (ReferenceError, AttributeError):
                    needs_recreation = True
            else:
                needs_recreation = True

            if needs_recreation:
                # Recreate PI object
                try:
                    self.create_pi_object(pi_data)
                    logger.info("Recreated PI %d (was deleted)", pi_data['id'])
                except Exception as e:
                    logger.error("Error recreating PI %d: %s", pi_data['id'], e)

        # Use in-place updates to avoid conflicts with modal operators
        self.update_segments_in_place()

    def visualize_all(self):
        """Create complete visualization - Legacy method for compatibility"""
        logger.info("Creating %d PI markers...", len(self.alignment.pis))
        for pi_data in self.alignment.pis:
            self.create_pi_object(pi_data)
            logger.debug("  PI %d: (%.2f, %.2f)", pi_data['id'], pi_data['position'].x, pi_data['position'].y)

        logger.info("Creating %d segment curves...", len(self.alignment.segments))
        for segment in self.alignment.segments:
            self.create_segment_curve(segment)
            params = segment.DesignParameters
            logger.debug("  %s: %s %.2fm", segment.Name, params.PredefinedType, params.SegmentLength)

        logger.info("Visualization complete!")
        logger.info("   Collection: %s", self.collection.name)
        logger.info("   PIs: %d objects", len(self.pi_objects))
        logger.info("   Segments: %d curves", len(self.segment_objects))

    # ============================================================================
    # STATION MARKER VISUALIZATION (Blender-only, not saved to IFC)
    # ============================================================================

    def _get_station_markers_collection(self):
        """Get or create a separate collection for station markers.

        This keeps station markers (Blender-only visualization) separate from
        the IFC hierarchy to avoid confusion.

        Returns:
            Blender collection for station markers
        """
        collection_name = "Station Markers"

        # Check if collection already exists
        if collection_name in bpy.data.collections:
            return bpy.data.collections[collection_name]

        # Create new collection
        markers_collection = bpy.data.collections.new(collection_name)

        # Link to scene
        bpy.context.scene.collection.children.link(markers_collection)

        logger.info("Created '%s' collection for Blender-only visuals", collection_name)
        return markers_collection

    def clear_station_markers(self):
        """Remove all station marker objects from Blender."""
        markers_collection = self._get_station_markers_collection()

        for marker in self.station_markers:
            try:
                # Unlink from collection
                if markers_collection and marker.name in markers_collection.objects:
                    markers_collection.objects.unlink(marker)
                # Remove from Blender data
                bpy.data.objects.remove(marker, do_unlink=True)
            except (ReferenceError, AttributeError):
                # Object was already deleted
                pass

        self.station_markers = []
        logger.debug("Cleared station markers")

    def update_station_markers(self, major_interval=1000.0, minor_interval=100.0,
                               tick_size=5.0, label_size=2.0):
        """Create or update station markers along the alignment.

        Markers are placed at round station values (e.g., 10+500, 10+600, 11+000)
        rather than at fixed intervals from the start of the alignment.

        Args:
            major_interval: Interval for major stations (e.g., 1000m for full stations)
            minor_interval: Interval for minor stations (e.g., 100m for intermediate)
            tick_size: Size of tick marks perpendicular to alignment
            label_size: Size of text labels
        """
        from ..core.station_formatting import format_station_short
        import math

        # Clear existing markers
        self.clear_station_markers()

        # Need segments to visualize along
        if not self.alignment.segments:
            logger.warning("No segments to place station markers on")
            return

        # Get total length of alignment
        total_length = 0.0
        for segment in self.alignment.segments:
            if hasattr(segment.DesignParameters, 'SegmentLength'):
                total_length += segment.DesignParameters.SegmentLength

        if total_length <= 0:
            logger.warning("Alignment has zero length")
            return

        # Get station range
        starting_station = self.alignment.get_station_at_distance(0.0)
        ending_station = self.alignment.get_station_at_distance(total_length)

        # Find first round minor station value (round up to next interval)
        first_station = math.ceil(starting_station / minor_interval) * minor_interval

        logger.info("Creating station markers from %s to %s (interval: %sm)",
                   format_station_short(first_station), format_station_short(ending_station), minor_interval)

        # Iterate through round station values
        current_station = first_station
        while current_station <= ending_station:
            # Determine if this is a major or minor station
            is_major = abs(current_station % major_interval) < 0.01

            # Convert station value to distance along alignment
            distance = self._get_distance_at_station(current_station)

            if distance is not None and 0 <= distance <= total_length:
                # Get position and direction at this distance
                pos_data = self._get_position_at_distance(distance)
                if pos_data:
                    position = pos_data['position']
                    direction = pos_data['direction']

                    # Create tick mark perpendicular to alignment
                    tick_obj = self._create_tick_mark(position, direction, tick_size, is_major)
                    if tick_obj:
                        self.station_markers.append(tick_obj)

                    # Create label for major stations
                    if is_major:
                        label_obj = self._create_station_label(
                            position, direction, current_station, label_size
                        )
                        if label_obj:
                            self.station_markers.append(label_obj)

            current_station += minor_interval

        logger.info("Created %d station marker objects", len(self.station_markers))

    def _get_distance_at_station(self, station_value):
        """Convert station value to distance along alignment.

        This handles simple stationing. For alignments with station equations,
        this provides basic support but may need enhancement for complex cases.

        Args:
            station_value: Station value in meters

        Returns:
            Distance along alignment in meters, or None if station is out of range
        """
        if not self.alignment.referents:
            # No stationing defined, assume 1:1 relationship
            return station_value

        # Get starting station (at distance = 0)
        starting_station = None
        for ref in self.alignment.referents:
            if ref['distance_along'] == 0.0:
                starting_station = ref['station']
                break

        if starting_station is None:
            return None

        # Simple conversion: works correctly without station equations
        # With station equations, this is an approximation
        # TODO: Implement proper station equation handling
        distance = station_value - starting_station

        return distance if distance >= 0 else None

    def _get_position_at_distance(self, distance_along):
        """Get position and direction at a distance along the alignment.

        Args:
            distance_along: Distance in meters from start of alignment

        Returns:
            dict with 'position' (Vector) and 'direction' (Vector), or None if not found
        """
        # Walk through segments to find the position
        cumulative_distance = 0.0

        for segment in self.alignment.segments:
            params = segment.DesignParameters
            segment_length = params.SegmentLength

            if cumulative_distance + segment_length >= distance_along:
                # Position is in this segment
                local_distance = distance_along - cumulative_distance

                if params.PredefinedType == "LINE":
                    # Linear interpolation along line
                    start_point = params.StartPoint.Coordinates
                    direction_angle = params.StartDirection

                    position = Vector((
                        start_point[0] + local_distance * math.cos(direction_angle),
                        start_point[1] + local_distance * math.sin(direction_angle),
                        0.0
                    ))

                    direction = Vector((
                        math.cos(direction_angle),
                        math.sin(direction_angle),
                        0.0
                    ))

                    return {'position': position, 'direction': direction}

                elif params.PredefinedType == "CIRCULARARC":
                    # Calculate position on circular arc
                    start_point = params.StartPoint.Coordinates
                    radius = abs(params.StartRadiusOfCurvature)
                    start_direction = params.StartDirection
                    signed_radius = params.StartRadiusOfCurvature

                    # Calculate center of circle
                    if signed_radius > 0:  # LEFT turn (CCW)
                        center_angle = start_direction + math.pi / 2
                    else:  # RIGHT turn (CW)
                        center_angle = start_direction - math.pi / 2

                    center_x = start_point[0] + radius * math.cos(center_angle)
                    center_y = start_point[1] + radius * math.sin(center_angle)

                    # Calculate angle traveled along arc
                    arc_angle = local_distance / radius
                    if signed_radius < 0:  # CW turn
                        arc_angle = -arc_angle

                    # Current angle on circle
                    current_angle = start_direction + arc_angle
                    if signed_radius > 0:  # LEFT
                        current_angle -= math.pi / 2
                    else:  # RIGHT
                        current_angle += math.pi / 2

                    # Position on circle
                    position = Vector((
                        center_x + radius * math.cos(current_angle),
                        center_y + radius * math.sin(current_angle),
                        0.0
                    ))

                    # Tangent direction at this point
                    if signed_radius > 0:  # LEFT
                        tangent_angle = current_angle + math.pi / 2
                    else:  # RIGHT
                        tangent_angle = current_angle - math.pi / 2

                    direction = Vector((
                        math.cos(tangent_angle),
                        math.sin(tangent_angle),
                        0.0
                    ))

                    return {'position': position, 'direction': direction}

            cumulative_distance += segment_length

        return None

    def _create_tick_mark(self, position, direction, tick_size, is_major):
        """Create a tick mark perpendicular to the alignment.

        Args:
            position: Vector position along alignment
            direction: Vector direction of alignment at this point
            tick_size: Length of tick mark
            is_major: True for major stations, False for minor

        Returns:
            Blender curve object for the tick mark
        """
        # Perpendicular direction (90° CCW from alignment direction)
        perp_direction = Vector((-direction.y, direction.x, 0.0))
        perp_direction.normalize()

        # Tick mark extends on both sides of alignment
        if is_major:
            # Major tick: extends more
            start = position - perp_direction * tick_size * 0.75
            end = position + perp_direction * tick_size * 0.75
            line_width = 0.15
        else:
            # Minor tick: shorter
            start = position - perp_direction * tick_size * 0.4
            end = position + perp_direction * tick_size * 0.4
            line_width = 0.08

        # Create curve data
        curve_data = bpy.data.curves.new(name="Station_Tick", type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.bevel_depth = line_width
        curve_data.bevel_resolution = 2

        # Create spline
        spline = curve_data.splines.new('POLY')
        spline.points.add(1)  # Add one more point (starts with 1)
        spline.points[0].co = (start.x, start.y, start.z, 1.0)
        spline.points[1].co = (end.x, end.y, end.z, 1.0)

        # Create object
        tick_obj = bpy.data.objects.new("Station_Tick", curve_data)
        # Note: NOT parented to alignment - kept separate in Station Markers collection

        # Set color (cyan for visibility against aerial imagery)
        mat = bpy.data.materials.new(name="Station_Tick_Mat")
        mat.diffuse_color = (0.0, 0.9, 1.0, 1.0) if not is_major else (0.0, 1.0, 1.0, 1.0)
        curve_data.materials.append(mat)

        # Link to station markers collection (separate from IFC hierarchy)
        markers_collection = self._get_station_markers_collection()
        if markers_collection:
            markers_collection.objects.link(tick_obj)

        return tick_obj

    def _create_station_label(self, position, direction, station_value, label_size):
        """Create text label showing the station value.

        Args:
            position: Vector position along alignment
            direction: Vector direction of alignment
            station_value: Numeric station value in meters
            label_size: Size of text

        Returns:
            Blender text object
        """
        from ..core.station_formatting import format_station_short

        # Format station as text
        station_text = format_station_short(station_value)

        # Perpendicular direction for offset
        perp_direction = Vector((-direction.y, direction.x, 0.0))
        perp_direction.normalize()

        # Offset label to the side and lift above ground/imagery
        label_position = position + perp_direction * label_size * 3
        label_position.z = label_size * 2  # Lift above ground/background imagery

        # Create text data
        text_data = bpy.data.curves.new(name=f"Station_{station_text}", type='FONT')
        text_data.body = station_text
        text_data.size = label_size
        text_data.align_x = 'CENTER'
        text_data.align_y = 'CENTER'

        # Create object
        text_obj = bpy.data.objects.new(f"Station_{station_text}", text_data)
        text_obj.location = label_position
        # Note: NOT parented to alignment - kept separate in Station Markers collection

        # Set color (cyan for visibility against aerial imagery)
        mat = bpy.data.materials.new(name="Station_Label_Mat")
        mat.diffuse_color = (0.0, 1.0, 1.0, 1.0)  # Bright cyan
        text_data.materials.append(mat)

        # Link to station markers collection (separate from IFC hierarchy)
        markers_collection = self._get_station_markers_collection()
        if markers_collection:
            markers_collection.objects.link(text_obj)

        return text_obj
