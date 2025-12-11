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
Vertical Alignment Manager Module
==================================

Provides the VerticalAlignment class for managing complete vertical alignments
with PVI-based design, segment generation, and IFC export.
"""

import logging
from typing import List, Optional, Tuple, Union

import ifcopenshell

from .constants import DESIGN_STANDARDS, MIN_K_CREST_80KPH, MIN_K_SAG_80KPH
from .pvi import PVI
from .segments import ParabolicSegment, TangentSegment, VerticalSegment

logger = logging.getLogger(__name__)


class VerticalAlignment:
    """Complete vertical alignment with PVI-based design.

    Manages PVIs (Points of Vertical Intersection) and automatically
    generates vertical segments (tangents and parabolic curves).

    Design workflow:
        1. Create alignment
        2. Add PVIs (control points)
        3. Set curve lengths at PVIs
        4. Generate segments automatically
        5. Query elevation at any station
        6. Export to IFC 4.3

    Attributes:
        name: Alignment name
        pvis: List of PVI control points (sorted by station)
        segments: Generated vertical segments (tangents + curves)
        design_speed: Design speed for K-value validation (km/h)
        description: Optional description

    Example:
        >>> valign = VerticalAlignment("Main Street Profile")
        >>> valign.add_pvi(0.0, 100.0)
        >>> valign.add_pvi(200.0, 105.0, curve_length=80.0)
        >>> valign.add_pvi(450.0, 103.0, curve_length=100.0)
        >>> valign.add_pvi(650.0, 110.0)
        >>> elev = valign.get_elevation(300.0)
    """

    def __init__(
        self,
        name: str = "Vertical Alignment",
        design_speed: float = 80.0,
        description: str = ""
    ):
        """Initialize vertical alignment.

        Args:
            name: Alignment name
            design_speed: Design speed for K-value validation (km/h)
            description: Optional description
        """
        self.name = name
        self.design_speed = design_speed
        self.description = description

        self.pvis: List[PVI] = []
        self.segments: List[VerticalSegment] = []

        # Design standards based on speed
        if design_speed in DESIGN_STANDARDS:
            standards = DESIGN_STANDARDS[design_speed]
            self.min_k_crest = standards["k_crest"]
            self.min_k_sag = standards["k_sag"]
        else:
            # Default to 80 km/h if speed not in standards
            self.min_k_crest = MIN_K_CREST_80KPH
            self.min_k_sag = MIN_K_SAG_80KPH

    @classmethod
    def from_ifc(
        cls,
        ifc_vertical: ifcopenshell.entity_instance,
        design_speed: float = 80.0
    ) -> "VerticalAlignment":
        """Create VerticalAlignment from IFC IfcAlignmentVertical entity.

        Parses the semantic layer (IfcAlignmentVerticalSegment entities) to
        reconstruct PVIs and create the vertical alignment.

        Args:
            ifc_vertical: IfcAlignmentVertical entity
            design_speed: Design speed for K-value validation (km/h)

        Returns:
            VerticalAlignment object

        Raises:
            ValueError: If IFC entity is invalid or has no segments
        """
        name = ifc_vertical.Name or "Vertical Alignment"
        valign = cls(name=name, design_speed=design_speed)

        # Find nested segments using IfcRelNests
        segments = []
        for rel in ifc_vertical.IsNestedBy or []:
            for obj in rel.RelatedObjects:
                if obj.is_a("IfcAlignmentSegment"):
                    if hasattr(obj, 'DesignParameters') and obj.DesignParameters:
                        vert_seg = obj.DesignParameters
                        if vert_seg.is_a("IfcAlignmentVerticalSegment"):
                            segments.append(vert_seg)

        if not segments:
            raise ValueError(f"No vertical segments found in {name}")

        # Sort segments by StartDistAlong
        segments.sort(key=lambda s: s.StartDistAlong)

        # Reconstruct PVIs from segments
        valign._reconstruct_pvis_from_segments(segments)

        return valign

    def _reconstruct_pvis_from_segments(
        self,
        ifc_segments: List[ifcopenshell.entity_instance]
    ) -> None:
        """Reconstruct PVIs from IFC vertical segments.

        Args:
            ifc_segments: List of IfcAlignmentVerticalSegment entities (sorted)
        """
        # Add first PVI at start of first segment
        first_seg = ifc_segments[0]
        self.add_pvi(
            station=first_seg.StartDistAlong,
            elevation=first_seg.StartHeight,
            curve_length=0.0
        )

        # Process each segment to create PVIs
        for i, seg in enumerate(ifc_segments):
            seg_type = seg.PredefinedType
            start_station = seg.StartDistAlong
            horizontal_length = seg.HorizontalLength
            end_station = start_station + horizontal_length

            if seg_type == "CONSTANTGRADIENT":
                end_elevation = seg.StartHeight + seg.StartGradient * horizontal_length

                if i < len(ifc_segments) - 1:
                    self.add_pvi(
                        station=end_station,
                        elevation=end_elevation,
                        curve_length=0.0
                    )

            elif seg_type == "PARABOLICARC":
                g1 = seg.StartGradient
                g2 = seg.EndGradient
                A = (g2 - g1) / (2.0 * horizontal_length)
                end_elevation = (
                    seg.StartHeight +
                    g1 * horizontal_length +
                    A * (horizontal_length ** 2)
                )

                pvi_station = (start_station + end_station) / 2.0
                pvi_elevation = (
                    seg.StartHeight +
                    g1 * (horizontal_length / 2.0) +
                    A * ((horizontal_length / 2.0) ** 2)
                )

                if i < len(ifc_segments) - 1:
                    self.add_pvi(
                        station=pvi_station,
                        elevation=pvi_elevation,
                        curve_length=horizontal_length
                    )

        # Add final PVI at end of last segment
        last_seg = ifc_segments[-1]
        last_start = last_seg.StartDistAlong
        last_length = last_seg.HorizontalLength
        last_end_station = last_start + last_length

        if last_seg.PredefinedType == "CONSTANTGRADIENT":
            last_end_elev = last_seg.StartHeight + last_seg.StartGradient * last_length
        elif last_seg.PredefinedType == "PARABOLICARC":
            g1 = last_seg.StartGradient
            g2 = last_seg.EndGradient
            A = (g2 - g1) / (2.0 * last_length)
            last_end_elev = (
                last_seg.StartHeight +
                g1 * last_length +
                A * (last_length ** 2)
            )
        else:
            last_end_elev = last_seg.StartHeight

        self.add_pvi(
            station=last_end_station,
            elevation=last_end_elev,
            curve_length=0.0
        )

        logger.info(
            f"Reconstructed {len(self.pvis)} PVIs from "
            f"{len(ifc_segments)} IFC segments"
        )

    # ========================================================================
    # PVI MANAGEMENT
    # ========================================================================

    def add_pvi(
        self,
        station: float,
        elevation: float,
        curve_length: float = 0.0,
        description: str = ""
    ) -> PVI:
        """Add a PVI to the alignment.

        PVIs are automatically sorted by station.
        Grades and segments are recalculated after adding.

        Args:
            station: Station location (m)
            elevation: Elevation at this station (m)
            curve_length: Vertical curve length (m), 0 = no curve
            description: Optional PVI description

        Returns:
            The created PVI object

        Raises:
            ValueError: If PVI conflicts with existing PVI
        """
        # Check for duplicate station
        for existing in self.pvis:
            if abs(existing.station - station) < 1e-6:
                raise ValueError(f"PVI already exists at station {station:.3f}m")

        pvi = PVI(
            station=station,
            elevation=elevation,
            curve_length=curve_length,
            description=description
        )

        # Insert in sorted order
        insert_idx = 0
        for i, existing in enumerate(self.pvis):
            if station > existing.station:
                insert_idx = i + 1

        self.pvis.insert(insert_idx, pvi)

        # Recalculate everything
        self._calculate_grades()
        self._generate_segments()

        return pvi

    def remove_pvi(self, index: int) -> None:
        """Remove PVI at given index.

        Args:
            index: Index in pvis list

        Raises:
            IndexError: If index out of range
        """
        if not (0 <= index < len(self.pvis)):
            raise IndexError(
                f"PVI index {index} out of range [0, {len(self.pvis)-1}]"
            )

        self.pvis.pop(index)
        self._calculate_grades()
        self._generate_segments()

    def update_pvi(
        self,
        index: int,
        station: Optional[float] = None,
        elevation: Optional[float] = None,
        curve_length: Optional[float] = None
    ) -> None:
        """Update PVI parameters.

        Args:
            index: Index of PVI to update
            station: New station (None = keep existing)
            elevation: New elevation (None = keep existing)
            curve_length: New curve length (None = keep existing)

        Raises:
            IndexError: If index out of range
        """
        if not (0 <= index < len(self.pvis)):
            raise IndexError(f"PVI index {index} out of range")

        pvi = self.pvis[index]

        if station is not None:
            pvi.station = station
            self.pvis.sort(key=lambda p: p.station)

        if elevation is not None:
            pvi.elevation = elevation

        if curve_length is not None:
            pvi.curve_length = curve_length

        self._calculate_grades()
        self._generate_segments()

    def get_pvi(self, index: int) -> PVI:
        """Get PVI by index.

        Args:
            index: PVI index

        Returns:
            PVI object

        Raises:
            IndexError: If index out of range
        """
        return self.pvis[index]

    def find_pvi_at_station(
        self, station: float, tolerance: float = 1e-3
    ) -> Optional[int]:
        """Find PVI index at given station.

        Args:
            station: Station to search
            tolerance: Search tolerance (m)

        Returns:
            PVI index or None if not found
        """
        for i, pvi in enumerate(self.pvis):
            if abs(pvi.station - station) < tolerance:
                return i
        return None

    # ========================================================================
    # GRADE CALCULATIONS
    # ========================================================================

    def _calculate_grades(self) -> None:
        """Calculate grades between all adjacent PVIs.

        This is called automatically after PVI changes.
        Sets grade_in and grade_out for each PVI.
        """
        if len(self.pvis) < 2:
            return

        # Calculate grade between each pair of PVIs
        for i in range(len(self.pvis) - 1):
            pvi1 = self.pvis[i]
            pvi2 = self.pvis[i + 1]

            rise = pvi2.elevation - pvi1.elevation
            run = pvi2.station - pvi1.station

            if run == 0:
                raise ValueError(
                    f"PVIs at same station: {pvi1.station:.3f}m "
                    f"(indices {i} and {i+1})"
                )

            grade = rise / run

            pvi1.grade_out = grade
            pvi2.grade_in = grade

        # First PVI has no incoming grade
        self.pvis[0].grade_in = self.pvis[0].grade_out

        # Last PVI has no outgoing grade
        self.pvis[-1].grade_out = self.pvis[-1].grade_in

        # Calculate K-values for PVIs with curves
        for pvi in self.pvis:
            if (pvi.curve_length > 0 and
                pvi.grade_in is not None and
                pvi.grade_out is not None):
                try:
                    pvi.k_value = pvi.calculate_k_value()
                except (ValueError, ZeroDivisionError):
                    pvi.k_value = None

    # ========================================================================
    # SEGMENT GENERATION
    # ========================================================================

    def _generate_segments(self) -> None:
        """Generate vertical segments from PVIs.

        Creates tangent and parabolic segments based on PVI configuration.
        """
        self.segments.clear()

        if len(self.pvis) < 2:
            return

        current_station = self.pvis[0].station
        current_elevation = self.pvis[0].elevation

        for i in range(len(self.pvis) - 1):
            pvi1 = self.pvis[i]
            pvi2 = self.pvis[i + 1]

            grade = pvi1.grade_out

            if pvi2.curve_length > 0:
                bvc_station = pvi2.bvc_station

                # Create tangent from current position to BVC
                if bvc_station > current_station:
                    tangent = TangentSegment(
                        start_station=current_station,
                        end_station=bvc_station,
                        start_elevation=current_elevation,
                        grade=grade
                    )
                    self.segments.append(tangent)

                    current_station = bvc_station
                    current_elevation = tangent.end_elevation

                # Create parabolic curve
                evc_station = pvi2.evc_station

                curve = ParabolicSegment(
                    start_station=current_station,
                    end_station=evc_station,
                    start_elevation=current_elevation,
                    g1=pvi2.grade_in,
                    g2=pvi2.grade_out,
                    pvi_station=pvi2.station
                )
                self.segments.append(curve)

                current_station = evc_station
                current_elevation = curve.end_elevation

            else:
                # No curve at PVI2 - create tangent segment
                tangent = TangentSegment(
                    start_station=current_station,
                    end_station=pvi2.station,
                    start_elevation=current_elevation,
                    grade=grade
                )
                self.segments.append(tangent)

                current_station = pvi2.station
                current_elevation = tangent.end_elevation

    # ========================================================================
    # ELEVATION & GRADE QUERIES
    # ========================================================================

    def get_elevation(self, station: float) -> float:
        """Get elevation at any station along alignment.

        Args:
            station: Station location (m)

        Returns:
            Elevation (m)

        Raises:
            ValueError: If station is outside alignment range
        """
        if len(self.segments) == 0:
            raise ValueError("No segments generated (need at least 2 PVIs)")

        for segment in self.segments:
            if segment.contains_station(station):
                return segment.get_elevation(station)

        raise ValueError(
            f"Station {station:.3f}m outside alignment range "
            f"[{self.start_station:.3f}, {self.end_station:.3f}]"
        )

    def get_grade(self, station: float) -> float:
        """Get grade at any station along alignment.

        Args:
            station: Station location (m)

        Returns:
            Grade as decimal (e.g., 0.02 = 2%)

        Raises:
            ValueError: If station is outside alignment range
        """
        if len(self.segments) == 0:
            raise ValueError("No segments generated (need at least 2 PVIs)")

        for segment in self.segments:
            if segment.contains_station(station):
                return segment.get_grade(station)

        raise ValueError(
            f"Station {station:.3f}m outside alignment range "
            f"[{self.start_station:.3f}, {self.end_station:.3f}]"
        )

    def get_profile_points(
        self,
        interval: float = 5.0,
        include_pvis: bool = True
    ) -> List[Tuple[float, float, float]]:
        """Get list of (station, elevation, grade) points along profile.

        Args:
            interval: Station interval for sampling (m)
            include_pvis: Whether to include exact PVI stations

        Returns:
            List of (station, elevation, grade) tuples
        """
        if len(self.segments) == 0:
            return []

        points = []

        # Sample at regular intervals
        station = self.start_station
        while station <= self.end_station:
            try:
                elev = self.get_elevation(station)
                grade = self.get_grade(station)
                points.append((station, elev, grade))
            except ValueError:
                pass

            station += interval

        # Add exact PVI locations if requested
        if include_pvis:
            pvi_points = []
            for pvi in self.pvis:
                try:
                    elev = self.get_elevation(pvi.station)
                    grade = self.get_grade(pvi.station)
                    pvi_points.append((pvi.station, elev, grade))
                except ValueError:
                    pass

            # Merge and sort
            all_points = points + pvi_points
            all_points.sort(key=lambda p: p[0])

            # Remove duplicates
            unique_points = []
            last_sta = -float('inf')
            for sta, elev, grade in all_points:
                if abs(sta - last_sta) > 1e-6:
                    unique_points.append((sta, elev, grade))
                    last_sta = sta

            return unique_points

        return points

    # ========================================================================
    # PROPERTIES
    # ========================================================================

    @property
    def start_station(self) -> float:
        """Starting station of alignment."""
        return self.pvis[0].station if self.pvis else 0.0

    @property
    def end_station(self) -> float:
        """Ending station of alignment."""
        return self.pvis[-1].station if self.pvis else 0.0

    @property
    def length(self) -> float:
        """Total alignment length."""
        return self.end_station - self.start_station

    @property
    def start_elevation(self) -> float:
        """Starting elevation."""
        return self.pvis[0].elevation if self.pvis else 0.0

    @property
    def end_elevation(self) -> float:
        """Ending elevation."""
        return self.pvis[-1].elevation if self.pvis else 0.0

    @property
    def elevation_change(self) -> float:
        """Total elevation change."""
        return self.end_elevation - self.start_elevation

    @property
    def average_grade(self) -> float:
        """Average grade over entire alignment."""
        if self.length == 0:
            return 0.0
        return self.elevation_change / self.length

    @property
    def num_pvis(self) -> int:
        """Number of PVIs."""
        return len(self.pvis)

    @property
    def num_segments(self) -> int:
        """Number of segments."""
        return len(self.segments)

    @property
    def num_curves(self) -> int:
        """Number of vertical curves."""
        return sum(1 for pvi in self.pvis if pvi.curve_length > 0)

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate alignment design.

        Checks:
        - Minimum number of PVIs
        - K-values meet design standards
        - Segments generated correctly
        - No overlapping segments

        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []

        if len(self.pvis) < 2:
            warnings.append("Need at least 2 PVIs to create alignment")
            return False, warnings

        # Check K-values
        for i, pvi in enumerate(self.pvis):
            if pvi.curve_length > 0:
                is_valid, msg = pvi.validate_k_value(self.design_speed)
                if not is_valid:
                    warnings.append(f"PVI {i} at {pvi.station:.1f}m: {msg}")

        if len(self.segments) == 0:
            warnings.append("No segments generated")
            return False, warnings

        # Check segment continuity
        for i in range(len(self.segments) - 1):
            seg1 = self.segments[i]
            seg2 = self.segments[i + 1]

            gap = abs(seg2.start_station - seg1.end_station)
            if gap > 1e-3:
                warnings.append(
                    f"Gap between segments {i} and {i+1}: {gap:.3f}m"
                )

        is_valid = len(warnings) == 0
        return is_valid, warnings

    # ========================================================================
    # IFC EXPORT
    # ========================================================================

    def to_ifc(
        self,
        ifc_file: ifcopenshell.file,
        horizontal_alignment: Optional[ifcopenshell.entity_instance] = None
    ) -> ifcopenshell.entity_instance:
        """Export to IFC 4.3 IfcAlignmentVertical with semantic and geometric layers.

        Creates:
        - Semantic layer: IfcAlignmentVertical + IfcAlignmentSegment entities
        - Geometric layer: IfcGradientCurve with IfcCurveSegment entities

        Args:
            ifc_file: IFC file instance
            horizontal_alignment: Optional parent horizontal alignment

        Returns:
            IfcAlignmentVertical entity
        """
        # Create IfcAlignmentVertical
        vertical = ifc_file.create_entity(
            "IfcAlignmentVertical",
            Name=self.name
        )

        # Link to horizontal if provided
        if horizontal_alignment:
            ifc_file.create_entity(
                "IfcRelNests",
                RelatingObject=horizontal_alignment,
                RelatedObjects=[vertical]
            )

        # Export semantic layer segments
        ifc_alignment_segments = []
        for i, segment in enumerate(self.segments):
            ifc_vert_seg = segment.to_ifc_segment(ifc_file)

            ifc_alignment_seg = ifc_file.create_entity(
                "IfcAlignmentSegment",
                Name=f"Segment {i+1}",
                DesignParameters=ifc_vert_seg
            )
            ifc_alignment_segments.append(ifc_alignment_seg)

        if ifc_alignment_segments:
            ifc_file.create_entity(
                "IfcRelNests",
                RelatingObject=vertical,
                RelatedObjects=ifc_alignment_segments
            )

        # Create geometric layer
        ifc_curve_segments = []
        for segment in self.segments:
            curve_seg = segment.to_ifc_curve_segment(ifc_file)
            ifc_curve_segments.append(curve_seg)

        if ifc_curve_segments:
            gradient_curve = ifc_file.create_entity(
                "IfcGradientCurve",
                Segments=ifc_curve_segments,
                SelfIntersect=False
            )

            # Link BaseCurve if horizontal alignment provided
            if horizontal_alignment:
                base_curve = self._find_horizontal_base_curve(
                    ifc_file, horizontal_alignment
                )
                if base_curve:
                    gradient_curve.BaseCurve = base_curve
                    logger.debug(
                        f"Linked IfcGradientCurve to horizontal base curve "
                        f"#{base_curve.id()}"
                    )

            # Create shape representation
            self._create_geometric_representation(
                ifc_file, vertical, gradient_curve, horizontal_alignment
            )

            logger.info(
                f"Created IfcGradientCurve with {len(ifc_curve_segments)} "
                f"curve segments"
            )

        return vertical

    def _find_horizontal_base_curve(
        self,
        ifc_file: ifcopenshell.file,
        horizontal_alignment: ifcopenshell.entity_instance
    ) -> Optional[ifcopenshell.entity_instance]:
        """Find the IfcCompositeCurve representing the horizontal alignment.

        Args:
            ifc_file: IFC file instance
            horizontal_alignment: Horizontal alignment entity

        Returns:
            IfcCompositeCurve or None if not found
        """
        alignment_entity = horizontal_alignment

        # If it's IfcAlignmentHorizontal, find the parent IfcAlignment
        if horizontal_alignment.is_a("IfcAlignmentHorizontal"):
            for rel in ifc_file.by_type("IfcRelNests"):
                if (rel.RelatedObjects and
                    horizontal_alignment in rel.RelatedObjects):
                    if (rel.RelatingObject and
                        rel.RelatingObject.is_a("IfcAlignment")):
                        alignment_entity = rel.RelatingObject
                        break

        # Get IfcCompositeCurve from alignment's representation
        if alignment_entity and alignment_entity.is_a("IfcAlignment"):
            if alignment_entity.Representation:
                rep = alignment_entity.Representation
                if rep.is_a("IfcProductDefinitionShape") and rep.Representations:
                    for shape_rep in rep.Representations:
                        if (shape_rep.is_a("IfcShapeRepresentation") and
                            shape_rep.Items):
                            for item in shape_rep.Items:
                                if item.is_a("IfcCompositeCurve"):
                                    return item

        return None

    def _create_geometric_representation(
        self,
        ifc_file: ifcopenshell.file,
        vertical: ifcopenshell.entity_instance,
        gradient_curve: ifcopenshell.entity_instance,
        horizontal_alignment: Optional[ifcopenshell.entity_instance]
    ) -> None:
        """Create geometric representation for the vertical alignment.

        Args:
            ifc_file: IFC file instance
            vertical: IfcAlignmentVertical entity
            gradient_curve: IfcGradientCurve entity
            horizontal_alignment: Optional horizontal alignment
        """
        # Get or create geometric representation context
        context = None
        for ctx in ifc_file.by_type("IfcGeometricRepresentationContext"):
            if ctx.ContextType == "Model":
                context = ctx
                break

        if context is None:
            context = ifc_file.create_entity(
                "IfcGeometricRepresentationContext",
                ContextType="Model",
                CoordinateSpaceDimension=3,
                Precision=1.0e-5,
                WorldCoordinateSystem=ifc_file.create_entity(
                    "IfcAxis2Placement3D",
                    Location=ifc_file.create_entity(
                        "IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)
                    )
                )
            )

        shape_rep = ifc_file.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=context,
            RepresentationIdentifier="Axis",
            RepresentationType="Curve3D",
            Items=[gradient_curve]
        )

        product_shape = ifc_file.create_entity(
            "IfcProductDefinitionShape",
            Representations=[shape_rep]
        )

        # Find parent IfcAlignment
        alignment_entity = None
        if horizontal_alignment:
            if horizontal_alignment.is_a("IfcAlignmentHorizontal"):
                for rel in ifc_file.by_type("IfcRelNests"):
                    if (rel.RelatedObjects and
                        horizontal_alignment in rel.RelatedObjects):
                        if (rel.RelatingObject and
                            rel.RelatingObject.is_a("IfcAlignment")):
                            alignment_entity = rel.RelatingObject
                            break
            elif horizontal_alignment.is_a("IfcAlignment"):
                alignment_entity = horizontal_alignment

        # Assign representation to parent IfcAlignment
        if alignment_entity and alignment_entity.is_a("IfcAlignment"):
            if alignment_entity.Representation:
                old_rep = alignment_entity.Representation
                if old_rep.is_a("IfcProductDefinitionShape"):
                    for shape_rep_old in old_rep.Representations or []:
                        ifc_file.remove(shape_rep_old)
                    ifc_file.remove(old_rep)
                alignment_entity.Representation = None

            alignment_entity.Representation = product_shape
            logger.debug("Assigned 3D representation to parent IfcAlignment")
        else:
            vertical.Representation = product_shape
            logger.warning(
                "No parent IfcAlignment found, assigned to IfcAlignmentVertical"
            )

    def create_blender_empty(
        self,
        ifc_entity: ifcopenshell.entity_instance,
        horizontal_alignment: Optional[ifcopenshell.entity_instance] = None
    ):
        """Create a Blender Empty object to represent the vertical alignment.

        .. deprecated::
            Use ``tool.VerticalAlignment.create_blender_empty()`` instead.
            This method is kept for backwards compatibility.

        Args:
            ifc_entity: The IFC IfcAlignmentVertical entity
            horizontal_alignment: Optional parent horizontal alignment IFC entity

        Returns:
            Blender Empty object
        """
        import warnings
        warnings.warn(
            "VerticalAlignment.create_blender_empty() is deprecated. "
            "Use tool.VerticalAlignment.create_blender_empty() instead.",
            DeprecationWarning,
            stacklevel=2
        )

        # Delegate to tool layer
        try:
            from ...tool import VerticalAlignment as VerticalAlignmentTool
            return VerticalAlignmentTool.create_blender_empty(
                ifc_entity, horizontal_alignment
            )
        except ImportError:
            # Fallback to legacy implementation if tool layer not available
            import bpy
            from ..native_ifc_manager import NativeIfcManager

            logger.debug(f"Creating Empty for vertical alignment: {self.name}")

            empty_name = f"V: {self.name}"
            empty = bpy.data.objects.new(empty_name, None)
            empty.empty_display_type = 'SINGLE_ARROW'
            empty.empty_display_size = 1.0

            NativeIfcManager.link_object(empty, ifc_entity)

            project_collection = NativeIfcManager.get_project_collection()
            if project_collection:
                project_collection.objects.link(empty)

            if horizontal_alignment:
                horizontal_ifc_id = horizontal_alignment.id()
                for obj in bpy.data.objects:
                    obj_ifc_id = obj.get("ifc_definition_id")
                    obj_ifc_class = obj.get("ifc_class")
                    if obj_ifc_id == horizontal_ifc_id and obj_ifc_class == "IfcAlignment":
                        empty.parent = obj
                        logger.debug(f"Parented to horizontal alignment: {obj.name}")
                        break

            return empty

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def summary(self) -> str:
        """Generate text summary of alignment.

        Returns:
            Multi-line summary string
        """
        lines = []
        lines.append(f"Vertical Alignment: {self.name}")
        lines.append(f"  Design Speed: {self.design_speed} km/h")
        lines.append(f"  Length: {self.length:.1f}m")
        lines.append(f"  Elevation Change: {self.elevation_change:+.3f}m")
        lines.append(f"  Average Grade: {self.average_grade*100:+.2f}%")
        lines.append(
            f"  PVIs: {self.num_pvis}, Curves: {self.num_curves}, "
            f"Segments: {self.num_segments}"
        )
        lines.append("")

        lines.append("PVIs:")
        for i, pvi in enumerate(self.pvis):
            curve_info = ""
            if pvi.curve_length > 0:
                curve_type = "CREST" if pvi.is_crest_curve else "SAG"
                curve_info = f" | {curve_type} L={pvi.curve_length:.1f}m K={pvi.k_value:.1f}"

            lines.append(
                f"  {i}: Sta {pvi.station:.1f}m, Elev {pvi.elevation:.3f}m"
                f"{curve_info}"
            )
            if pvi.grade_in is not None:
                lines.append(f"      Grade in: {pvi.grade_in_percent:+.2f}%")
            if pvi.grade_out is not None:
                lines.append(f"      Grade out: {pvi.grade_out_percent:+.2f}%")

        lines.append("")
        lines.append("Segments:")
        for i, seg in enumerate(self.segments):
            lines.append(f"  {i}: {seg}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"VerticalAlignment('{self.name}', "
            f"{self.num_pvis} PVIs, {self.num_segments} segments, "
            f"{self.length:.1f}m)"
        )


__all__ = ["VerticalAlignment"]