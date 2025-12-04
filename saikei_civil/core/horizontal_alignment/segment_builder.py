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
    segment_index: int = 0
) -> Tuple[ifcopenshell.entity_instance, ifcopenshell.entity_instance]:
    """Create IFC tangent segment with business logic and geometry.

    Args:
        ifc_file: Active IFC file
        start_pos: Start point of tangent
        end_pos: End point of tangent
        segment_index: Index for segment naming

    Returns:
        Tuple of (IfcAlignmentSegment, IfcCurveSegment)
    """
    from ..ifc_geometry_builders import (
        create_line_parent_curve,
        create_curve_segment as create_ifc_curve_segment
    )

    direction = end_pos - start_pos
    length = direction.length
    angle = math.atan2(direction.y, direction.x)

    # Business logic layer (design parameters)
    design_params = ifc_file.create_entity(
        "IfcAlignmentHorizontalSegment",
        StartPoint=ifc_file.create_entity(
            "IfcCartesianPoint",
            Coordinates=[float(start_pos.x), float(start_pos.y)]
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
        float(start_pos.x), float(start_pos.y),
        float(end_pos.x), float(end_pos.y)
    )

    # Placement at segment start
    placement = ifc_file.create_entity(
        "IfcAxis2Placement2D",
        Location=ifc_file.create_entity(
            "IfcCartesianPoint",
            Coordinates=[float(start_pos.x), float(start_pos.y)]
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
    segment = ifc_file.create_entity(
        "IfcAlignmentSegment",
        GlobalId=ifcopenshell.guid.new(),
        Name=f"Tangent_{segment_index}",
        DesignParameters=design_params
    )

    return segment, curve_geometry


def create_curve_segment(
    ifc_file: ifcopenshell.file,
    curve_data: dict,
    segment_index: int = 0
) -> Tuple[ifcopenshell.entity_instance, ifcopenshell.entity_instance]:
    """Create IFC curve segment with business logic and geometry.

    Args:
        ifc_file: Active IFC file
        curve_data: Curve geometry dictionary from calculate_curve_geometry()
        segment_index: Index for segment naming

    Returns:
        Tuple of (IfcAlignmentSegment, IfcCurveSegment)
    """
    from ..ifc_geometry_builders import (
        create_circle_parent_curve,
        create_curve_segment as create_ifc_curve_segment
    )

    # Extract curve data
    bc = curve_data['bc']
    radius = curve_data['radius']
    arc_length = curve_data['arc_length']
    start_direction = curve_data['start_direction']
    turn_direction = curve_data['turn_direction']
    deflection = curve_data['deflection']

    # Signed radius for IFC (positive = left, negative = right)
    signed_radius = radius if deflection > 0 else -radius

    # Business logic layer (design parameters)
    design_params = ifc_file.create_entity(
        "IfcAlignmentHorizontalSegment",
        StartPoint=ifc_file.create_entity(
            "IfcCartesianPoint",
            Coordinates=[float(bc.x), float(bc.y)]
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

    center_x = bc.x + radius * math.cos(center_angle)
    center_y = bc.y + radius * math.sin(center_angle)

    # Create parent circle at world coordinates
    parent_curve = create_circle_parent_curve(
        ifc_file,
        center_x,
        center_y,
        radius,
        circle_ref_dir
    )

    # Placement at BC
    placement = ifc_file.create_entity(
        "IfcAxis2Placement2D",
        Location=ifc_file.create_entity(
            "IfcCartesianPoint",
            Coordinates=[float(bc.x), float(bc.y)]
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
    segment = ifc_file.create_entity(
        "IfcAlignmentSegment",
        GlobalId=ifcopenshell.guid.new(),
        Name=f"Curve_{segment_index}",
        DesignParameters=design_params
    )

    return segment, curve_geometry


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

    # Remove old representation
    if hasattr(alignment, 'Representation') and alignment.Representation:
        old_rep = alignment.Representation
        if old_rep.is_a("IfcProductDefinitionShape"):
            for shape_rep in old_rep.Representations:
                if shape_rep.is_a("IfcShapeRepresentation"):
                    for item in shape_rep.Items:
                        if item.is_a("IfcCompositeCurve"):
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


def cleanup_old_geometry(
    ifc_file: ifcopenshell.file,
    curve_segments: List[ifcopenshell.entity_instance]
) -> None:
    """Clean up old curve geometry entities from IFC file.

    Args:
        ifc_file: Active IFC file
        curve_segments: List of old IfcCurveSegment entities to remove
    """
    if not curve_segments:
        return

    removed_count = 0
    for curve_seg in curve_segments:
        try:
            # Remove ParentCurve (IfcLine or IfcCircle)
            if hasattr(curve_seg, 'ParentCurve') and curve_seg.ParentCurve:
                parent = curve_seg.ParentCurve
                if hasattr(parent, 'Position') and parent.Position:
                    pos = parent.Position
                    if hasattr(pos, 'Location') and pos.Location:
                        ifc_file.remove(pos.Location)
                    if hasattr(pos, 'RefDirection') and pos.RefDirection:
                        ifc_file.remove(pos.RefDirection)
                    ifc_file.remove(pos)
                ifc_file.remove(parent)

            # Remove placement
            if hasattr(curve_seg, 'Placement') and curve_seg.Placement:
                place = curve_seg.Placement
                if hasattr(place, 'Location') and place.Location:
                    ifc_file.remove(place.Location)
                if hasattr(place, 'RefDirection') and place.RefDirection:
                    ifc_file.remove(place.RefDirection)
                ifc_file.remove(place)

            # Remove the curve segment itself
            ifc_file.remove(curve_seg)
            removed_count += 1
        except RuntimeError:
            pass  # Entity already removed

    if removed_count > 0:
        logger.debug(f"Cleaned up {removed_count} old curve geometry entities")


__all__ = [
    "create_tangent_segment",
    "create_curve_segment",
    "build_composite_curve",
    "cleanup_old_geometry",
]
