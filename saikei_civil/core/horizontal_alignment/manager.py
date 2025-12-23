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
Native IFC Horizontal Alignment Manager
========================================

Main alignment class for PI-driven horizontal alignment design.
PIs are pure intersection points (no radius property).
"""

import math
from typing import List, Optional

import ifcopenshell
import ifcopenshell.guid

from .vector import SimpleVector
from .curve_geometry import calculate_curve_geometry
from .segment_builder import (
    create_tangent_segment,
    create_curve_segment,
    build_composite_curve,
    cleanup_old_geometry,
)
from .stationing import StationingManager
from ..logging_config import get_logger

logger = get_logger(__name__)


class NativeIfcAlignment:
    """Native IFC alignment with PI-driven design.

    PIs (Points of Intersection) are pure intersection points - they do NOT
    have radius properties. Curves are inserted separately at interior PIs.

    Attributes:
        ifc: IFC file instance
        alignment: IfcAlignment entity
        horizontal: IfcAlignmentHorizontal entity
        pis: List of PI data dictionaries
        segments: List of IfcAlignmentSegment entities
        curve_segments: List of IfcCurveSegment entities
        stationing: StationingManager instance
        auto_update: Whether to auto-regenerate on changes

    Example:
        >>> alignment = NativeIfcAlignment(ifc_file, "Main Road")
        >>> alignment.add_pi(0, 0)
        >>> alignment.add_pi(100, 0)
        >>> alignment.add_pi(100, 100)
        >>> alignment.insert_curve_at_pi(1, radius=50.0)
    """

    def __init__(
        self,
        ifc_file: ifcopenshell.file,
        name: str = "New Alignment",
        alignment_entity: Optional[ifcopenshell.entity_instance] = None
    ):
        """Initialize alignment.

        Args:
            ifc_file: Active IFC file
            name: Alignment name (for new alignments)
            alignment_entity: Existing IfcAlignment to load (optional)
        """
        self.ifc = ifc_file
        self.alignment = None
        self.horizontal = None
        self.pis: List[dict] = []
        self.segments: List[ifcopenshell.entity_instance] = []
        self.curve_segments: List[ifcopenshell.entity_instance] = []
        self.auto_update = True

        if alignment_entity:
            self._load_from_ifc(alignment_entity)
        else:
            self._create_alignment_structure(name)
            self.stationing = StationingManager(ifc_file, self.alignment)
            self.stationing.set_starting_station(10000.0)

        # Register for updates
        from ..complete_update_system import register_alignment
        register_alignment(self)

        # CRITICAL: Also register in alignment_instances registry!
        # This is needed for GlobalId-based lookup in get_alignment_from_pi()
        from ..alignment_registry import register_alignment as register_instance
        register_instance(self)

    @property
    def name(self) -> str:
        """Get alignment name from IFC entity."""
        if self.alignment:
            return self.alignment.Name
        return "Unnamed Alignment"

    def __del__(self):
        """Cleanup when alignment is deleted."""
        try:
            from ..complete_update_system import unregister_alignment
            unregister_alignment(self)
        except Exception:
            pass

    # ========================================================================
    # INITIALIZATION
    # ========================================================================

    def _create_alignment_structure(self, name: str) -> None:
        """Create IFC alignment hierarchy with proper placement."""
        from ..native_ifc_manager import NativeIfcManager

        alignment_placement = NativeIfcManager.create_alignment_placement()

        self.alignment = self.ifc.create_entity(
            "IfcAlignment",
            GlobalId=ifcopenshell.guid.new(),
            Name=name,
            ObjectPlacement=alignment_placement,
            PredefinedType="USERDEFINED"
        )

        NativeIfcManager.contain_alignment_in_road(self.alignment)

        self.horizontal = self.ifc.create_entity(
            "IfcAlignmentHorizontal",
            GlobalId=ifcopenshell.guid.new()
        )

        self.ifc.create_entity(
            "IfcRelNests",
            GlobalId=ifcopenshell.guid.new(),
            Name="AlignmentToHorizontal",
            RelatingObject=self.alignment,
            RelatedObjects=[self.horizontal]
        )

    def _load_from_ifc(self, alignment_entity: ifcopenshell.entity_instance) -> None:
        """Load alignment from existing IFC entity."""
        self.alignment = alignment_entity
        logger.info("=== _load_from_ifc() for alignment: %s (GlobalId: %s) ===",
                   alignment_entity.Name, alignment_entity.GlobalId)

        # Find horizontal alignment via IsNestedBy inverse relationship
        is_nested_by = alignment_entity.IsNestedBy or []
        logger.info("  alignment.IsNestedBy: %d relationships", len(is_nested_by))

        for rel_idx, rel in enumerate(is_nested_by):
            logger.debug("    Rel[%d]: %s, %d related objects",
                        rel_idx, rel.is_a(), len(rel.RelatedObjects) if rel.RelatedObjects else 0)
            for obj in rel.RelatedObjects or []:
                logger.debug("      - %s: %s", obj.is_a(), getattr(obj, 'Name', 'unnamed'))
                if obj.is_a("IfcAlignmentHorizontal"):
                    self.horizontal = obj
                    logger.info("  Found IfcAlignmentHorizontal: %s (id: %d)",
                               getattr(obj, 'Name', 'unnamed'), obj.id())
                    break
            if self.horizontal:
                break

        if not self.horizontal:
            logger.warning(
                f"No horizontal alignment found for {alignment_entity.Name}"
            )
            logger.warning("  This alignment has no visualizable horizontal geometry!")
            return

        # Load segments from horizontal alignment via IsNestedBy
        horizontal_nested_by = self.horizontal.IsNestedBy or []
        logger.info("  horizontal.IsNestedBy: %d relationships", len(horizontal_nested_by))

        segments = []
        for rel_idx, rel in enumerate(horizontal_nested_by):
            logger.debug("    Rel[%d]: %s, %d related objects",
                        rel_idx, rel.is_a(), len(rel.RelatedObjects) if rel.RelatedObjects else 0)
            for obj in rel.RelatedObjects or []:
                if obj.is_a("IfcAlignmentSegment"):
                    segments.append(obj)
                    params = obj.DesignParameters
                    if params:
                        logger.debug("      - Segment: %s, type=%s, length=%.2f",
                                    obj.Name, params.PredefinedType, params.SegmentLength)
                    else:
                        logger.debug("      - Segment: %s (no DesignParameters!)", obj.Name)

        self.segments = segments
        logger.info("  Loaded %d segments from IFC", len(self.segments))

        if not self.segments:
            logger.warning("  WARNING: No segments found! PI reconstruction will fail.")
            logger.warning("  Check if IfcRelNests relationships exist for horizontal alignment.")

        self._reconstruct_pis_from_segments()
        logger.info("  Reconstructed %d PIs from segments", len(self.pis))

        # Log PI positions for verification
        for i, pi in enumerate(self.pis):
            pos = pi['position']
            has_curve = 'curve' in pi
            logger.debug("    PI[%d]: (%.2f, %.2f) %s", i, pos.x, pos.y,
                        "[CURVE]" if has_curve else "")

        # Initialize stationing manager and load referents
        self.stationing = StationingManager(self.ifc, self.alignment)
        self.stationing.load_from_ifc()

        logger.info(
            f"Loaded '{alignment_entity.Name}': "
            f"{len(self.pis)} PIs, {len(self.segments)} segments"
        )

    def _reconstruct_pis_from_segments(self) -> None:
        """Reconstruct PI list from IFC segments."""
        if not self.segments:
            return

        self.pis = []
        i = 0

        while i < len(self.segments):
            segment = self.segments[i]
            design_params = segment.DesignParameters

            if not design_params:
                i += 1
                continue

            # Skip zero-length endpoint segments (BSI ALB015) - they don't define new PIs
            if design_params.SegmentLength == 0:
                logger.debug(f"Skipping zero-length segment at index {i}")
                i += 1
                continue

            if design_params.PredefinedType == "LINE":
                self._process_line_segment(i, design_params)
                i += 1

            elif design_params.PredefinedType == "CIRCULARARC":
                logger.warning(f"Standalone curve segment at index {i}")
                i += 1
            else:
                i += 1

        logger.debug(
            f"Reconstructed {len(self.pis)} PIs from {len(self.segments)} segments"
        )

    def _process_line_segment(self, index: int, design_params) -> None:
        """Process a LINE segment during PI reconstruction."""
        direction = design_params.StartDirection
        start_point = design_params.StartPoint
        start_pos = SimpleVector(
            start_point.Coordinates[0],
            start_point.Coordinates[1]
        )
        length = design_params.SegmentLength

        end_x = start_pos.x + length * math.cos(direction)
        end_y = start_pos.y + length * math.sin(direction)
        end_pos = SimpleVector(end_x, end_y)

        # Add PI at start of first tangent
        if len(self.pis) == 0:
            self._add_pi_data(start_pos)

        # Check for curve after this tangent
        has_curve = False
        if index + 1 < len(self.segments):
            next_seg = self.segments[index + 1]
            if (next_seg.DesignParameters and
                next_seg.DesignParameters.PredefinedType == "CIRCULARARC"):
                has_curve = True

        if has_curve and index + 2 < len(self.segments):
            self._process_curve_at_tangent_end(
                index, direction, end_pos
            )
        else:
            self._add_pi_data(end_pos)

    def _process_curve_at_tangent_end(
        self,
        tangent_index: int,
        tangent_direction: float,
        tangent_end: SimpleVector
    ) -> None:
        """Process curve found after tangent during reconstruction."""
        curve_seg = self.segments[tangent_index + 1]
        curve_params = curve_seg.DesignParameters

        curve_length = curve_params.SegmentLength
        radius = abs(curve_params.StartRadiusOfCurvature)
        deflection = curve_length / radius

        tangent_length = radius * math.tan(deflection / 2)
        t1_unit = SimpleVector(
            math.cos(tangent_direction),
            math.sin(tangent_direction)
        )
        pi_pos = tangent_end + t1_unit * tangent_length

        pi_data = self._add_pi_data(pi_pos)
        pi_data['curve'] = {
            'radius': radius,
            'arc_length': curve_length,
            'deflection': deflection,
            'bc': tangent_end,
            'ec': None,
            'start_direction': tangent_direction,
            'turn_direction': (
                'LEFT' if curve_params.StartRadiusOfCurvature > 0 else 'RIGHT'
            )
        }

    def _add_pi_data(self, position: SimpleVector) -> dict:
        """Add PI data dictionary to list."""
        pi_data = {
            'id': len(self.pis),
            'position': position,
            'ifc_point': self.ifc.create_entity(
                "IfcCartesianPoint",
                Coordinates=[float(position.x), float(position.y)]
            )
        }
        self.pis.append(pi_data)
        return pi_data

    # ========================================================================
    # PI MANAGEMENT
    # ========================================================================

    def add_pi(
        self,
        x: float,
        y: float,
        regenerate: bool = True,
        create_ifc_point: bool = True
    ) -> dict:
        """Add PI to alignment.

        PIs are pure intersection points - NO RADIUS!

        Args:
            x: X coordinate (Easting)
            y: Y coordinate (Northing)
            regenerate: Whether to regenerate segments (default True).
                        Set to False for batch operations to avoid
                        creating thousands of intermediate entities.
            create_ifc_point: Whether to create IFC entity immediately (default True).
                        Set to False during interactive placement to defer
                        IFC entity creation until the command completes.

        Returns:
            PI data dictionary
        """
        ifc_point = None
        if create_ifc_point:
            ifc_point = self.ifc.create_entity(
                "IfcCartesianPoint",
                Coordinates=[float(x), float(y)]
            )

        pi_data = {
            'id': len(self.pis),
            'position': SimpleVector(x, y),
            'ifc_point': ifc_point
        }

        self.pis.append(pi_data)
        if regenerate:
            self.regenerate_segments()
        return pi_data

    def finalize_pis(self) -> int:
        """Create IFC entities for any PIs that don't have them.

        Called after interactive placement to create all IFC entities at once.
        This prevents creating/deleting intermediate entities during placement.

        Returns:
            Number of IFC points created
        """
        created_count = 0
        for pi_data in self.pis:
            if pi_data.get('ifc_point') is None:
                pi_data['ifc_point'] = self.ifc.create_entity(
                    "IfcCartesianPoint",
                    Coordinates=[float(pi_data['position'].x), float(pi_data['position'].y)]
                )
                created_count += 1

        if created_count > 0:
            logger.debug(f"Created {created_count} deferred IFC points")

        return created_count

    def remove_pis_from_index(self, start_index: int) -> int:
        """Remove PIs from start_index to end of list.

        Used when cancelling interactive placement to clean up
        any PIs that were added during the session.

        Args:
            start_index: Index from which to remove PIs

        Returns:
            Number of PIs removed
        """
        if start_index >= len(self.pis):
            return 0

        removed_count = 0
        # Remove in reverse order to avoid index shifting issues
        while len(self.pis) > start_index:
            pi_data = self.pis.pop()
            # Clean up IFC point if it was created
            if pi_data.get('ifc_point'):
                try:
                    self.ifc.remove(pi_data['ifc_point'])
                except RuntimeError:
                    pass  # Already removed
            removed_count += 1

        logger.debug(f"Removed {removed_count} PIs from index {start_index}")
        return removed_count

    def insert_curve_at_pi(
        self,
        pi_index: int,
        radius: float
    ) -> Optional[dict]:
        """Insert curve at specified PI with given radius.

        Args:
            pi_index: Index of interior PI where curve should be inserted
            radius: Curve radius in meters

        Returns:
            Curve data dictionary, or None if curve cannot be created
        """
        if pi_index <= 0 or pi_index >= len(self.pis) - 1:
            logger.warning(
                f"Cannot insert curve at PI {pi_index} (must be interior PI)"
            )
            return None

        prev_pi = self.pis[pi_index - 1]
        curr_pi = self.pis[pi_index]
        next_pi = self.pis[pi_index + 1]

        curve_data = calculate_curve_geometry(
            prev_pi['position'],
            curr_pi['position'],
            next_pi['position'],
            radius
        )

        if not curve_data:
            logger.warning(f"Could not calculate curve at PI {pi_index}")
            return None

        curr_pi['curve'] = curve_data
        self.regenerate_segments_with_curves()

        return curve_data

    # ========================================================================
    # SEGMENT GENERATION
    # ========================================================================

    def regenerate_segments(self) -> None:
        """Regenerate IFC tangent segments from PIs.

        Creates straight line segments between consecutive PIs.
        Curves are added separately via insert_curve_at_pi().
        """
        cleanup_old_geometry(self.ifc, self.curve_segments)

        self.segments = []
        self.curve_segments = []

        if len(self.pis) < 2:
            return

        # Track exact position for C0 continuity chaining
        current_exact_pos = None

        for i in range(len(self.pis) - 1):
            curr_pi = self.pis[i]
            next_pi = self.pis[i + 1]

            segment, curve_geom, exact_end = create_tangent_segment(
                self.ifc,
                curr_pi['position'],
                next_pi['position'],
                i,
                exact_start=current_exact_pos
            )
            self.segments.append(segment)
            self.curve_segments.append(curve_geom)

            # Chain end position to next segment's start
            current_exact_pos = exact_end

        # Store final position for zero-length segment
        self._last_exact_pos = current_exact_pos

        # BSI ALB015: Add zero-length final segment (business logic requirement)
        # Per IFC 4.3: Each alignment layout must end with a zero-length segment
        if self.segments and len(self.pis) >= 2:
            self._add_zero_length_final_segment()

        self._update_ifc_nesting()
        build_composite_curve(self.ifc, self.curve_segments, self.alignment)

        logger.debug(
            f"Regenerated {len(self.segments)} tangent segments "
            f"from {len(self.pis)} PIs"
        )

    def regenerate_segments_with_curves(self) -> None:
        """Regenerate segments considering curves at PIs."""
        cleanup_old_geometry(self.ifc, self.curve_segments)

        self.segments = []
        self.curve_segments = []

        if len(self.pis) < 2:
            return

        # Recalculate all curve geometries
        self._recalculate_curves()

        # Track exact position for C0 continuity chaining
        current_exact_pos = None

        # Generate segments
        for i in range(len(self.pis) - 1):
            curr_pi = self.pis[i]
            next_pi = self.pis[i + 1]

            # Determine tangent start
            if 'curve' in curr_pi:
                start_pos = curr_pi['curve']['ec']
            else:
                start_pos = curr_pi['position']

            # Determine tangent end
            if 'curve' in next_pi:
                end_pos = next_pi['curve']['bc']
            else:
                end_pos = next_pi['position']

            # Create tangent segment (use chained position for C0 continuity)
            segment, curve_geom, exact_end = create_tangent_segment(
                self.ifc, start_pos, end_pos, len(self.segments),
                exact_start=current_exact_pos
            )
            self.segments.append(segment)
            self.curve_segments.append(curve_geom)

            # Chain end position to next segment's start
            current_exact_pos = exact_end

            # Add curve at next PI if exists
            if 'curve' in next_pi:
                curve_seg, curve_geom, curve_exact_end = create_curve_segment(
                    self.ifc,
                    next_pi['curve'],
                    next_pi['id'],
                    exact_start=current_exact_pos
                )
                self.segments.append(curve_seg)
                self.curve_segments.append(curve_geom)

                # Chain curve end to next segment's start
                current_exact_pos = curve_exact_end

        # Store final position for zero-length segment
        self._last_exact_pos = current_exact_pos

        # BSI ALB015: Add zero-length final segment (business logic requirement)
        # Per IFC 4.3: Each alignment layout must end with a zero-length segment
        if self.segments and len(self.pis) >= 2:
            self._add_zero_length_final_segment()

        self._update_ifc_nesting()
        build_composite_curve(self.ifc, self.curve_segments, self.alignment)

        logger.debug(f"Regenerated {len(self.segments)} segments with curves")

    def _recalculate_curves(self) -> None:
        """Recalculate all curve geometries from current PI positions."""
        for i, pi in enumerate(self.pis):
            if 'curve' not in pi:
                continue

            if i <= 0 or i >= len(self.pis) - 1:
                continue

            prev_pi = self.pis[i - 1]
            next_pi = self.pis[i + 1]

            updated_curve = calculate_curve_geometry(
                prev_pi['position'],
                pi['position'],
                next_pi['position'],
                pi['curve']['radius']
            )

            if updated_curve:
                pi['curve'] = updated_curve
            else:
                del pi['curve']
                logger.info(f"Removed invalid curve at PI {i}")

    def _add_zero_length_final_segment(self) -> None:
        """Add zero-length final segment per BSI ALB015.

        Per IFC 4.3 specification, each alignment layout must end with
        a zero-length segment to mark the endpoint.
        """
        if not self.segments:
            return

        # Get endpoint from last segment
        last_seg = self.segments[-1]
        last_params = last_seg.DesignParameters

        if not last_params:
            return

        # Use chained exact position if available (for C0 continuity)
        if hasattr(self, '_last_exact_pos') and self._last_exact_pos is not None:
            end_x, end_y = self._last_exact_pos
            end_direction = last_params.StartDirection
            # For curves, adjust direction
            if last_params.PredefinedType == "CIRCULARARC":
                radius = abs(last_params.StartRadiusOfCurvature)
                seg_length = last_params.SegmentLength
                deflection = seg_length / radius if radius > 0 else 0
                sign = 1 if last_params.StartRadiusOfCurvature > 0 else -1
                end_direction = last_params.StartDirection + sign * deflection
        else:
            # Fallback: Calculate endpoint based on last segment type
            start_point = last_params.StartPoint
            start_dir = last_params.StartDirection
            seg_length = last_params.SegmentLength

            if last_params.PredefinedType == "LINE":
                # Linear segment - endpoint is start + direction * length
                end_x = start_point.Coordinates[0] + seg_length * math.cos(start_dir)
                end_y = start_point.Coordinates[1] + seg_length * math.sin(start_dir)
                end_direction = start_dir
            elif last_params.PredefinedType == "CIRCULARARC":
                # Circular arc - compute endpoint
                radius = abs(last_params.StartRadiusOfCurvature)
                deflection = seg_length / radius if radius > 0 else 0
                sign = 1 if last_params.StartRadiusOfCurvature > 0 else -1
                end_direction = start_dir + sign * deflection

                # Arc endpoint calculation
                center_offset_angle = start_dir + (math.pi / 2 * sign)
                cx = start_point.Coordinates[0] + radius * math.cos(center_offset_angle)
                cy = start_point.Coordinates[1] + radius * math.sin(center_offset_angle)

                end_angle_from_center = center_offset_angle + math.pi + (sign * deflection)
                end_x = cx + radius * math.cos(end_angle_from_center)
                end_y = cy + radius * math.sin(end_angle_from_center)
            else:
                # Default: use last PI position
                end_pos = self.pis[-1]['position']
                end_x = end_pos.x
                end_y = end_pos.y
                end_direction = start_dir

        # Create zero-length horizontal segment at endpoint
        end_point = self.ifc.create_entity(
            "IfcCartesianPoint",
            Coordinates=[float(end_x), float(end_y)]
        )

        zero_length_params = self.ifc.create_entity(
            "IfcAlignmentHorizontalSegment",
            StartPoint=end_point,
            StartDirection=float(end_direction),
            StartRadiusOfCurvature=0.0,
            EndRadiusOfCurvature=0.0,
            SegmentLength=0.0,  # Zero length - marks endpoint
            PredefinedType="LINE"
        )

        final_segment = self.ifc.create_entity(
            "IfcAlignmentSegment",
            GlobalId=ifcopenshell.guid.new(),
            Name="Endpoint",
            ObjectType="ENDPOINT",
            DesignParameters=zero_length_params
        )

        self.segments.append(final_segment)

        # Also add zero-length curve segment for geometry layer (ALS015)
        # This will be picked up by build_composite_curve
        placement = self.ifc.create_entity(
            "IfcAxis2Placement2D",
            Location=end_point,
            RefDirection=self.ifc.create_entity(
                "IfcDirection",
                DirectionRatios=[math.cos(end_direction), math.sin(end_direction)]
            )
        )

        parent_line = self.ifc.create_entity(
            "IfcLine",
            Pnt=self.ifc.create_entity(
                "IfcCartesianPoint", Coordinates=[0.0, 0.0]
            ),
            Dir=self.ifc.create_entity(
                "IfcVector",
                Orientation=self.ifc.create_entity(
                    "IfcDirection", DirectionRatios=[1.0, 0.0]
                ),
                Magnitude=1.0
            )
        )

        # Create DISCONTINUOUS zero-length final curve segment (ALS015)
        final_curve_seg = self.ifc.create_entity(
            "IfcCurveSegment",
            Transition="DISCONTINUOUS",  # Must be DISCONTINUOUS per ALS015
            Placement=placement,
            SegmentStart=self.ifc.create_entity("IfcLengthMeasure", 0.0),
            SegmentLength=self.ifc.create_entity("IfcLengthMeasure", 0.0),
            ParentCurve=parent_line
        )

        self.curve_segments.append(final_curve_seg)

        logger.debug("Added zero-length final segment (ALB015/ALS015)")

    def _update_ifc_nesting(self) -> None:
        """Update IFC nesting relationships for segments."""
        # Remove old segments and nesting
        old_segments = []
        for rel in self.horizontal.IsNestedBy or []:
            if rel.is_a("IfcRelNests"):
                for obj in rel.RelatedObjects:
                    if obj.is_a("IfcAlignmentSegment"):
                        old_segments.append(obj)
                self.ifc.remove(rel)

        # Remove old segment entities
        for segment in old_segments:
            try:
                if hasattr(segment, 'DesignParameters') and segment.DesignParameters:
                    params = segment.DesignParameters
                    if hasattr(params, 'StartPoint') and params.StartPoint:
                        self.ifc.remove(params.StartPoint)
                    self.ifc.remove(params)
                self.ifc.remove(segment)
            except RuntimeError:
                pass

        if old_segments:
            logger.debug(f"Removed {len(old_segments)} old segments")

        # Create new nesting
        if self.segments:
            self.ifc.create_entity(
                "IfcRelNests",
                GlobalId=ifcopenshell.guid.new(),
                Name="HorizontalToSegments",
                RelatingObject=self.horizontal,
                RelatedObjects=self.segments
            )

    # ========================================================================
    # STATIONING (Delegated to StationingManager)
    # ========================================================================

    def set_starting_station(self, station_value: float) -> None:
        """Set starting station. See StationingManager.set_starting_station()."""
        self.stationing.set_starting_station(station_value)

    def add_station_equation(
        self,
        distance_along: float,
        incoming_station: float,
        outgoing_station: float,
        description: str = "Station Equation"
    ) -> None:
        """Add station equation. See StationingManager.add_station_equation()."""
        self.stationing.add_station_equation(
            distance_along, incoming_station, outgoing_station, description
        )

    def remove_station_equation(self, distance_along: float) -> bool:
        """Remove station equation. See StationingManager.remove_station_equation()."""
        return self.stationing.remove_station_equation(distance_along)

    def get_station_at_distance(self, distance_along: float) -> float:
        """Get station at distance. See StationingManager.get_station_at_distance()."""
        return self.stationing.get_station_at_distance(distance_along)

    def get_distance_at_station(self, station_value: float) -> Optional[float]:
        """Get distance at station. See StationingManager.get_distance_at_station()."""
        return self.stationing.get_distance_at_station(station_value)

    @property
    def referents(self) -> List[dict]:
        """Access stationing referents."""
        return self.stationing.referents


__all__ = ["NativeIfcAlignment"]
