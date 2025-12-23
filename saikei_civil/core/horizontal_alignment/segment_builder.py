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
IFC Segment Builder Module
===========================

Creates IFC alignment segments (both business logic and geometric representation).
Handles tangent (LINE) and curve (CIRCULARARC) segments.
"""

import logging
import math
from typing import List, Tuple

import ifcopenshell
import ifcopenshell.guid

from .vector import SimpleVector

logger = logging.getLogger(__name__)


def create_tangent_segment(
    ifc_file: ifcopenshell.file,
    start_pos: SimpleVector,
    end_pos: SimpleVector,
    segment_index: int = 0,
    exact_start: Tuple[float, float] = None
) -> Tuple[ifcopenshell.entity_instance, ifcopenshell.entity_instance, Tuple[float, float]]:
    """Create IFC tangent segment with business logic and geometry.

    Args:
        ifc_file: Active IFC file
        start_pos: Start point of tangent
        end_pos: End point of tangent
        segment_index: Index for segment naming
        exact_start: Optional (x, y) tuple for exact start position
                     (for ensuring C0 continuity with previous segment)

    Returns:
        Tuple of (IfcAlignmentSegment, IfcCurveSegment, end_point)
        where end_point is (x, y) tuple for chaining to next segment
    """
    from ..ifc_geometry_builders import (
        create_line_parent_curve,
        create_curve_segment as create_ifc_curve_segment
    )

    direction = end_pos - start_pos
    length = direction.length
    angle = math.atan2(direction.y, direction.x)

    # Use exact start position for C0 continuity if provided
    if exact_start is not None:
        start_x, start_y = exact_start
    else:
        start_x, start_y = float(start_pos.x), float(start_pos.y)

    # Business logic layer (design parameters)
    design_params = ifc_file.create_entity(
        "IfcAlignmentHorizontalSegment",
        StartPoint=ifc_file.create_entity(
            "IfcCartesianPoint",
            Coordinates=[start_x, start_y]
        ),
        StartDirection=float(angle),
        StartRadiusOfCurvature=0.0,
        EndRadiusOfCurvature=0.0,
        SegmentLength=float(length),
        PredefinedType="LINE"
    )

    # Geometric representation layer
    parent_curve = create_line_parent_curve(
        ifc_file,
        start_x, start_y,
        float(end_pos.x), float(end_pos.y)
    )

    # Placement at segment start with correct direction
    # ALS016 FIX: RefDirection MUST be specified to define segment orientation.
    # Without it, the placement defaults to (1,0) and the validator interprets
    # all segments as pointing east, causing massive positional discontinuities.
    direction_x = math.cos(angle)
    direction_y = math.sin(angle)
    placement = ifc_file.create_entity(
        "IfcAxis2Placement2D",
        Location=ifc_file.create_entity(
            "IfcCartesianPoint",
            Coordinates=[start_x, start_y]
        ),
        RefDirection=ifc_file.create_entity(
            "IfcDirection",
            DirectionRatios=[direction_x, direction_y]
        )
    )

    curve_geometry = create_ifc_curve_segment(
        ifc_file,
        parent_curve,
        placement,
        0.0,
        float(length)
    )

    # Create alignment segment (business logic only)
    # Per BSI OJT001: ObjectType must have a value
    segment = ifc_file.create_entity(
        "IfcAlignmentSegment",
        GlobalId=ifcopenshell.guid.new(),
        Name=f"Tangent_{segment_index}",
        ObjectType="LINE",  # BSI OJT001: Set ObjectType for segment type
        DesignParameters=design_params
    )

    # Calculate exact end point for chaining to next segment
    end_x = start_x + length * math.cos(angle)
    end_y = start_y + length * math.sin(angle)
    exact_end = (end_x, end_y)

    return segment, curve_geometry, exact_end


def create_curve_segment(
    ifc_file: ifcopenshell.file,
    curve_data: dict,
    segment_index: int = 0,
    exact_start: Tuple[float, float] = None
) -> Tuple[ifcopenshell.entity_instance, ifcopenshell.entity_instance, Tuple[float, float]]:
    """Create IFC curve segment with business logic and geometry.

    Args:
        ifc_file: Active IFC file
        curve_data: Curve geometry dictionary from calculate_curve_geometry()
        segment_index: Index for segment naming
        exact_start: Optional (x, y) tuple for exact start position (BC)
                     (for ensuring C0 continuity with previous segment)

    Returns:
        Tuple of (IfcAlignmentSegment, IfcCurveSegment, end_point)
        where end_point is (x, y) tuple for chaining to next segment (EC)
    """
    from ..ifc_geometry_builders import (
        create_circle_parent_curve,
        create_curve_segment as create_ifc_curve_segment
    )

    # Extract curve data
    bc = curve_data['bc']
    ec = curve_data['ec']
    radius = curve_data['radius']
    arc_length = curve_data['arc_length']
    start_direction = curve_data['start_direction']
    turn_direction = curve_data['turn_direction']
    deflection = curve_data['deflection']

    # Use exact start position for C0 continuity if provided
    if exact_start is not None:
        bc_x, bc_y = exact_start
    else:
        bc_x, bc_y = float(bc.x), float(bc.y)

    # Signed radius for IFC (positive = left, negative = right)
    signed_radius = radius if deflection > 0 else -radius

    # Business logic layer (design parameters)
    design_params = ifc_file.create_entity(
        "IfcAlignmentHorizontalSegment",
        StartPoint=ifc_file.create_entity(
            "IfcCartesianPoint",
            Coordinates=[bc_x, bc_y]
        ),
        StartDirection=float(start_direction),
        StartRadiusOfCurvature=float(signed_radius),
        EndRadiusOfCurvature=float(signed_radius),
        SegmentLength=float(arc_length),
        PredefinedType="CIRCULARARC"
    )

    # Geometric representation layer
    # Calculate circle center and orientation
    if turn_direction == 'LEFT':
        center_angle = start_direction + math.pi / 2
        circle_ref_dir = start_direction - math.pi / 2
    else:
        center_angle = start_direction - math.pi / 2
        circle_ref_dir = start_direction + math.pi / 2

    center_x = bc_x + radius * math.cos(center_angle)
    center_y = bc_y + radius * math.sin(center_angle)

    # Create parent circle at ACTUAL CENTER position
    # ALS016 FIX: Circle must be at real center, not origin, because
    # angular parameterization traces around the center.
    parent_curve = create_circle_parent_curve(
        ifc_file,
        center_x,
        center_y,
        radius,
        circle_ref_dir
    )

    # ALS016 FIX: Placement must be at BC point with correct tangent direction!
    # Per IFC spec: "IfcCurveSegment.Placement.Location corresponds to the first
    # parameter value of the parent curve."
    # For a circle at actual center with refdir pointing to BC, θ=0 gives BC point.
    # The placement confirms/declares where this point is in world coordinates.
    # RefDirection MUST be specified to define the tangent direction at BC.
    tangent_dir_x = math.cos(start_direction)
    tangent_dir_y = math.sin(start_direction)
    placement = ifc_file.create_entity(
        "IfcAxis2Placement2D",
        Location=ifc_file.create_entity(
            "IfcCartesianPoint",
            Coordinates=[bc_x, bc_y]  # Placement at BC - matches circle's θ=0 point
        ),
        RefDirection=ifc_file.create_entity(
            "IfcDirection",
            DirectionRatios=[tangent_dir_x, tangent_dir_y]
        )
    )

    # Angular extent (signed for direction)
    angular_extent = arc_length / radius
    if turn_direction == 'RIGHT':
        angular_extent = -angular_extent

    curve_geometry = create_ifc_curve_segment(
        ifc_file,
        parent_curve,
        placement,
        0.0,
        float(angular_extent),
        "CONTSAMEGRADIENT"
    )

    # Create alignment segment (business logic only)
    # Per BSI OJT001: ObjectType must have a value
    segment = ifc_file.create_entity(
        "IfcAlignmentSegment",
        GlobalId=ifcopenshell.guid.new(),
        Name=f"Curve_{segment_index}",
        ObjectType="CIRCULARARC",  # BSI OJT001: Set ObjectType for segment type
        DesignParameters=design_params
    )

    # Calculate exact end point (EC) for chaining to next segment
    # EC is at center + radius at angle (center_angle + pi + deflection) for LEFT
    # or (center_angle + pi - deflection) for RIGHT
    if turn_direction == 'LEFT':
        ec_angle = center_angle + math.pi + abs(deflection)
    else:
        ec_angle = center_angle + math.pi - abs(deflection)

    ec_x = center_x + radius * math.cos(ec_angle)
    ec_y = center_y + radius * math.sin(ec_angle)
    exact_end = (ec_x, ec_y)

    return segment, curve_geometry, exact_end


def build_composite_curve(
    ifc_file: ifcopenshell.file,
    curve_segments: List[ifcopenshell.entity_instance],
    alignment: ifcopenshell.entity_instance
) -> ifcopenshell.entity_instance:
    """Build IfcCompositeCurve and attach to alignment.

    Args:
        ifc_file: Active IFC file
        curve_segments: List of IfcCurveSegment entities
        alignment: IfcAlignment to attach representation to

    Returns:
        IfcCompositeCurve entity
    """
    from ..ifc_geometry_builders import (
        create_composite_curve,
        create_shape_representation,
        create_product_definition_shape
    )
    from ..native_ifc_manager import NativeIfcManager

    if not curve_segments:
        logger.warning("No curve segments to build composite curve from")
        return None

    # Remove old representation - CRITICAL: Must remove IfcCurveSegments too!
    # ALS016 FIX: Old orphaned IfcCurveSegments cause 161m+ gap errors in validation
    if hasattr(alignment, 'Representation') and alignment.Representation:
        old_rep = alignment.Representation
        if old_rep.is_a("IfcProductDefinitionShape"):
            for shape_rep in old_rep.Representations:
                if shape_rep.is_a("IfcShapeRepresentation"):
                    for item in shape_rep.Items:
                        if item.is_a("IfcCompositeCurve"):
                            # Remove all curve segments within composite curve
                            if hasattr(item, 'Segments') and item.Segments:
                                for seg in list(item.Segments):
                                    _remove_curve_segment_with_geometry(ifc_file, seg)
                            ifc_file.remove(item)
                    ifc_file.remove(shape_rep)
            ifc_file.remove(old_rep)
        alignment.Representation = None

    # Create composite curve
    composite_curve = create_composite_curve(
        ifc_file, curve_segments, self_intersect=False
    )
    logger.debug(f"Created IfcCompositeCurve with {len(curve_segments)} segments")

    # Get geometric context
    context = NativeIfcManager.get_axis_subcontext()
    if not context:
        context = NativeIfcManager.get_geometric_context()

    if not context:
        project = ifc_file.by_type("IfcProject")
        if project and project[0].RepresentationContexts:
            context = project[0].RepresentationContexts[0]

    if not context:
        logger.warning("Cannot create shape representation without context")
        return composite_curve

    # Create shape representation
    shape_rep = create_shape_representation(
        ifc_file,
        context,
        [composite_curve],
        representation_type="Curve2D",
        representation_identifier="Axis"
    )

    product_shape = create_product_definition_shape(ifc_file, [shape_rep])
    alignment.Representation = product_shape

    logger.debug(f"Attached geometric representation to {alignment.Name}")

    return composite_curve


def _remove_curve_segment_with_geometry(
    ifc_file: ifcopenshell.file,
    curve_segment: ifcopenshell.entity_instance
) -> None:
    """Remove an IfcCurveSegment and all its nested geometry entities.

    This is critical for ALS016 compliance - orphaned curve segments cause
    massive positional gaps in validation.

    CRITICAL: Also removes IfcLengthMeasure entities (SegmentStart/SegmentLength)
    which were previously orphaned, causing entity ID explosion.

    Args:
        ifc_file: Active IFC file
        curve_segment: IfcCurveSegment entity to remove
    """
    try:
        # ================================================================
        # CRITICAL FIX: Remove SegmentStart and SegmentLength (IfcLengthMeasure)
        # These were previously orphaned, causing entity explosion!
        # ================================================================
        if hasattr(curve_segment, 'SegmentStart') and curve_segment.SegmentStart:
            try:
                ifc_file.remove(curve_segment.SegmentStart)
            except RuntimeError:
                pass  # Already removed

        if hasattr(curve_segment, 'SegmentLength') and curve_segment.SegmentLength:
            try:
                ifc_file.remove(curve_segment.SegmentLength)
            except RuntimeError:
                pass  # Already removed

        # Remove ParentCurve (IfcLine, IfcCircle) and its nested entities
        if hasattr(curve_segment, 'ParentCurve') and curve_segment.ParentCurve:
            parent = curve_segment.ParentCurve
            try:
                # IfcLine has Pnt and Dir
                if parent.is_a("IfcLine"):
                    if hasattr(parent, 'Pnt') and parent.Pnt:
                        ifc_file.remove(parent.Pnt)
                    if hasattr(parent, 'Dir') and parent.Dir:
                        vector = parent.Dir
                        if hasattr(vector, 'Orientation') and vector.Orientation:
                            ifc_file.remove(vector.Orientation)
                        ifc_file.remove(vector)
                # IfcCircle has Position
                elif parent.is_a("IfcCircle"):
                    if hasattr(parent, 'Position') and parent.Position:
                        pos = parent.Position
                        if hasattr(pos, 'Location') and pos.Location:
                            ifc_file.remove(pos.Location)
                        if hasattr(pos, 'RefDirection') and pos.RefDirection:
                            ifc_file.remove(pos.RefDirection)
                        ifc_file.remove(pos)
                ifc_file.remove(parent)
            except RuntimeError:
                pass  # Entity may already be removed

        # Remove Placement
        if hasattr(curve_segment, 'Placement') and curve_segment.Placement:
            placement = curve_segment.Placement
            try:
                if hasattr(placement, 'Location') and placement.Location:
                    ifc_file.remove(placement.Location)
                if hasattr(placement, 'RefDirection') and placement.RefDirection:
                    ifc_file.remove(placement.RefDirection)
                ifc_file.remove(placement)
            except RuntimeError:
                pass

        # Remove the curve segment itself
        ifc_file.remove(curve_segment)
    except RuntimeError:
        pass  # Entity already removed
    except Exception as e:
        logger.debug(f"Error removing curve segment: {e}")


def cleanup_old_geometry(
    ifc_file: ifcopenshell.file,
    curve_segments: List[ifcopenshell.entity_instance]
) -> None:
    """Clean up old curve geometry entities from IFC file.

    Properly removes both IfcLine and IfcCircle parent curves with all
    their nested geometry entities to prevent orphaned entities.

    CRITICAL: Also removes IfcLengthMeasure entities (SegmentStart/SegmentLength)
    which were previously orphaned, causing entity ID explosion during PI movement.

    Args:
        ifc_file: Active IFC file
        curve_segments: List of old IfcCurveSegment entities to remove
    """
    if not curve_segments:
        return

    removed_count = 0

    for curve_seg in curve_segments:
        try:
            # ================================================================
            # CRITICAL FIX: Remove SegmentStart and SegmentLength (IfcLengthMeasure)
            # These were previously orphaned, causing entity explosion!
            # ================================================================
            if hasattr(curve_seg, 'SegmentStart') and curve_seg.SegmentStart:
                try:
                    ifc_file.remove(curve_seg.SegmentStart)
                except RuntimeError:
                    pass  # Already removed

            if hasattr(curve_seg, 'SegmentLength') and curve_seg.SegmentLength:
                try:
                    ifc_file.remove(curve_seg.SegmentLength)
                except RuntimeError:
                    pass  # Already removed

            # Remove ParentCurve (IfcLine or IfcCircle) and nested entities
            if hasattr(curve_seg, 'ParentCurve') and curve_seg.ParentCurve:
                parent = curve_seg.ParentCurve
                try:
                    # IfcLine has Pnt (CartesianPoint) and Dir (Vector)
                    if parent.is_a("IfcLine"):
                        if hasattr(parent, 'Pnt') and parent.Pnt:
                            ifc_file.remove(parent.Pnt)
                        if hasattr(parent, 'Dir') and parent.Dir:
                            vector = parent.Dir
                            if hasattr(vector, 'Orientation') and vector.Orientation:
                                ifc_file.remove(vector.Orientation)
                            ifc_file.remove(vector)
                    # IfcCircle has Position (Axis2Placement2D)
                    elif parent.is_a("IfcCircle"):
                        if hasattr(parent, 'Position') and parent.Position:
                            pos = parent.Position
                            if hasattr(pos, 'Location') and pos.Location:
                                ifc_file.remove(pos.Location)
                            if hasattr(pos, 'RefDirection') and pos.RefDirection:
                                ifc_file.remove(pos.RefDirection)
                            ifc_file.remove(pos)
                    ifc_file.remove(parent)
                except RuntimeError:
                    pass  # Entity may already be removed

            # Remove placement
            if hasattr(curve_seg, 'Placement') and curve_seg.Placement:
                place = curve_seg.Placement
                try:
                    if hasattr(place, 'Location') and place.Location:
                        ifc_file.remove(place.Location)
                    if hasattr(place, 'RefDirection') and place.RefDirection:
                        ifc_file.remove(place.RefDirection)
                    ifc_file.remove(place)
                except RuntimeError:
                    pass

            # Remove the curve segment itself
            ifc_file.remove(curve_seg)
            removed_count += 1
        except RuntimeError:
            pass  # Entity already removed
        except Exception as e:
            logger.warning(f"Error cleaning curve segment: {e}")

    logger.info(f"Cleaned up {removed_count} old curve geometry entities")


__all__ = [
    "create_tangent_segment",
    "create_curve_segment",
    "build_composite_curve",
    "cleanup_old_geometry",
]
