# ==============================================================================
# BlenderCivil - Civil Engineering Tools for Blender
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
Native IFC Horizontal Alignment Manager
========================================

Main alignment class for PI-driven horizontal alignment design.
PIs are pure intersection points (no radius property).
"""

import logging
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

logger = logging.getLogger(__name__)


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

        # Find horizontal alignment
        for rel in alignment_entity.IsNestedBy or []:
            for obj in rel.RelatedObjects:
                if obj.is_a("IfcAlignmentHorizontal"):
                    self.horizontal = obj
                    break

        if not self.horizontal:
            logger.warning(
                f"No horizontal alignment found for {alignment_entity.Name}"
            )
            return

        # Load segments
        segments = []
        for rel in self.horizontal.IsNestedBy or []:
            for obj in rel.RelatedObjects:
                if obj.is_a("IfcAlignmentSegment"):
                    segments.append(obj)

        self.segments = segments
        self._reconstruct_pis_from_segments()

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

    def add_pi(self, x: float, y: float) -> dict:
        """Add PI to alignment.

        PIs are pure intersection points - NO RADIUS!

        Args:
            x: X coordinate (Easting)
            y: Y coordinate (Northing)

        Returns:
            PI data dictionary
        """
        pi_data = {
            'id': len(self.pis),
            'position': SimpleVector(x, y),
            'ifc_point': self.ifc.create_entity(
                "IfcCartesianPoint",
                Coordinates=[float(x), float(y)]
            )
        }

        self.pis.append(pi_data)
        self.regenerate_segments()
        return pi_data

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

        for i in range(len(self.pis) - 1):
            curr_pi = self.pis[i]
            next_pi = self.pis[i + 1]

            segment, curve_geom = create_tangent_segment(
                self.ifc,
                curr_pi['position'],
                next_pi['position'],
                i
            )
            self.segments.append(segment)
            self.curve_segments.append(curve_geom)

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

            # Create tangent segment
            segment, curve_geom = create_tangent_segment(
                self.ifc, start_pos, end_pos, len(self.segments)
            )
            self.segments.append(segment)
            self.curve_segments.append(curve_geom)

            # Add curve at next PI if exists
            if 'curve' in next_pi:
                curve_seg, curve_geom = create_curve_segment(
                    self.ifc,
                    next_pi['curve'],
                    next_pi['id']
                )
                self.segments.append(curve_seg)
                self.curve_segments.append(curve_geom)

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
