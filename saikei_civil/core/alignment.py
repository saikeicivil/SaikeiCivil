# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under Apache License 2.0
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
Horizontal Alignment Core Logic
================================

Pure business logic for horizontal alignment operations.
NO Blender imports - uses TYPE_CHECKING only for type hints.

This module contains the core algorithms and data transformations for
horizontal alignments. Tool interfaces are passed as parameters to enable
testing without Blender and to support the three-layer architecture.

Architecture:
    - This module: Pure Python business logic
    - tool/alignment.py: Blender-specific implementation
    - bim/module/alignment/: UI, operators, properties

Usage:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        import saikei_civil.tool as tool

    import saikei_civil.core.alignment as alignment_core

    def my_function(ifc: type[tool.Ifc], alignment: type[tool.Alignment]):
        pis = [{"x": 0, "y": 0}, {"x": 100, "y": 0}]
        entity = alignment_core.create_alignment(ifc, alignment, "Main Road", pis)
"""
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Tuple
import math

# Re-export the pure geometry functions - these already have no Blender deps
from .horizontal_alignment.vector import SimpleVector
from .horizontal_alignment.curve_geometry import (
    calculate_curve_geometry,
    calculate_curve_center,
    calculate_point_on_curve,
    get_tangent_intersection,
)

if TYPE_CHECKING:
    import saikei_civil.tool as tool
    import ifcopenshell


# =============================================================================
# Data Structures
# =============================================================================

def create_pi_data(
    pi_id: int,
    x: float,
    y: float,
    curve_data: Optional[Dict] = None
) -> Dict:
    """
    Create a PI data dictionary.

    This is the standard format for PI data used throughout the alignment module.
    PIs are pure intersection points - curves are stored separately.

    Args:
        pi_id: Unique identifier for this PI
        x: X coordinate (Easting)
        y: Y coordinate (Northing)
        curve_data: Optional curve data if a curve exists at this PI

    Returns:
        PI data dictionary with keys:
        - id: int
        - position: SimpleVector
        - curve: Optional[Dict] (curve geometry if present)
    """
    data = {
        'id': pi_id,
        'position': SimpleVector(x, y),
    }
    if curve_data:
        data['curve'] = curve_data
    return data


def format_pi_for_ifc(pi: Dict) -> Dict:
    """
    Format PI data for ifcopenshell.api compatibility.

    Args:
        pi: PI data dictionary

    Returns:
        Dictionary with Coordinates and optional Radius
    """
    pos = pi['position']
    result = {
        'Coordinates': (pos.x, pos.y),
    }
    if 'curve' in pi:
        result['Radius'] = pi['curve'].get('radius', 0.0)
    return result


def pis_from_coordinates(coords: List[Tuple[float, float]]) -> List[Dict]:
    """
    Create PI list from coordinate pairs.

    Args:
        coords: List of (x, y) tuples

    Returns:
        List of PI data dictionaries
    """
    return [
        create_pi_data(i, x, y)
        for i, (x, y) in enumerate(coords)
    ]


# =============================================================================
# Geometry Calculations (Pure Python)
# =============================================================================

def calculate_tangent_direction(
    start: SimpleVector,
    end: SimpleVector
) -> float:
    """
    Calculate direction angle of tangent line.

    Args:
        start: Start point
        end: End point

    Returns:
        Direction in radians from positive X axis
    """
    dx = end.x - start.x
    dy = end.y - start.y
    return math.atan2(dy, dx)


def calculate_tangent_length(start: SimpleVector, end: SimpleVector) -> float:
    """
    Calculate length of tangent line.

    Args:
        start: Start point
        end: End point

    Returns:
        Length in model units
    """
    return start.distance_to(end)


def calculate_deflection_angle(
    prev_pos: SimpleVector,
    curr_pos: SimpleVector,
    next_pos: SimpleVector
) -> float:
    """
    Calculate deflection angle at a PI.

    Args:
        prev_pos: Previous PI position
        curr_pos: Current PI position
        next_pos: Next PI position

    Returns:
        Signed deflection angle in radians
        (positive = left turn, negative = right turn)
    """
    # Tangent vectors
    t1 = (curr_pos - prev_pos).normalized()
    t2 = (next_pos - curr_pos).normalized()

    # Calculate angles
    angle1 = math.atan2(t1.y, t1.x)
    angle2 = math.atan2(t2.y, t2.x)

    deflection = angle2 - angle1

    # Normalize to [-pi, pi]
    if deflection > math.pi:
        deflection -= 2 * math.pi
    elif deflection < -math.pi:
        deflection += 2 * math.pi

    return deflection


def get_total_alignment_length(segments: List[Dict]) -> float:
    """
    Calculate total length of alignment from segments.

    Args:
        segments: List of segment dictionaries with 'length' key

    Returns:
        Total length in model units
    """
    return sum(seg.get('length', 0.0) for seg in segments)


def interpolate_position_on_line(
    start: SimpleVector,
    direction: float,
    distance: float
) -> SimpleVector:
    """
    Interpolate position along a straight line.

    Args:
        start: Start point
        direction: Direction in radians
        distance: Distance along line

    Returns:
        Position at specified distance
    """
    return SimpleVector(
        start.x + distance * math.cos(direction),
        start.y + distance * math.sin(direction)
    )


def interpolate_position_on_arc(
    center: SimpleVector,
    radius: float,
    start_angle: float,
    arc_distance: float,
    is_ccw: bool
) -> Tuple[SimpleVector, float]:
    """
    Interpolate position and direction along a circular arc.

    Args:
        center: Arc center point
        radius: Arc radius
        start_angle: Angle at start of arc (from center to start point)
        arc_distance: Distance along arc
        is_ccw: True for counter-clockwise (left turn)

    Returns:
        Tuple of (position, tangent_direction)
    """
    arc_angle = arc_distance / radius
    if not is_ccw:
        arc_angle = -arc_angle

    current_angle = start_angle + arc_angle

    position = SimpleVector(
        center.x + radius * math.cos(current_angle),
        center.y + radius * math.sin(current_angle)
    )

    # Tangent direction is perpendicular to radius
    if is_ccw:
        tangent_dir = current_angle + math.pi / 2
    else:
        tangent_dir = current_angle - math.pi / 2

    return position, tangent_dir


def get_point_at_station(
    segments: List[Dict],
    station: float,
    start_station: float = 0.0
) -> Optional[Dict]:
    """
    Get position and direction at a station value.

    Args:
        segments: List of segment dictionaries
        station: Station value to query
        start_station: Starting station of alignment

    Returns:
        Dictionary with 'x', 'y', 'direction' keys, or None if out of range
    """
    distance = station - start_station
    if distance < 0:
        return None

    cumulative = 0.0

    for seg in segments:
        seg_length = seg.get('length', 0.0)

        if cumulative + seg_length >= distance:
            local_dist = distance - cumulative

            if seg.get('type') == 'LINE':
                pos = interpolate_position_on_line(
                    seg['start'],
                    seg['direction'],
                    local_dist
                )
                return {
                    'x': pos.x,
                    'y': pos.y,
                    'direction': seg['direction']
                }

            elif seg.get('type') == 'CIRCULARARC':
                center = seg['center']
                radius = seg['radius']
                start_angle = seg['start_angle']
                is_ccw = seg.get('is_ccw', True)

                pos, direction = interpolate_position_on_arc(
                    center, radius, start_angle, local_dist, is_ccw
                )
                return {
                    'x': pos.x,
                    'y': pos.y,
                    'direction': direction
                }

        cumulative += seg_length

    return None


def get_station_at_point(
    segments: List[Dict],
    point: Tuple[float, float],
    start_station: float = 0.0,
    tolerance: float = 10.0
) -> Optional[float]:
    """
    Get station value at a point (projected onto alignment).

    Args:
        segments: List of segment dictionaries
        point: (x, y) coordinates to query
        start_station: Starting station of alignment
        tolerance: Maximum perpendicular distance to consider

    Returns:
        Station value, or None if point is too far from alignment
    """
    target = SimpleVector(point[0], point[1])
    best_station = None
    best_distance = tolerance

    cumulative = 0.0

    for seg in segments:
        seg_length = seg.get('length', 0.0)

        if seg.get('type') == 'LINE':
            # Project point onto line segment
            start = seg['start']
            direction = seg['direction']

            # Vector from start to target
            to_target = target - start

            # Unit direction vector
            dir_vec = SimpleVector(
                math.cos(direction),
                math.sin(direction)
            )

            # Project onto line
            proj_dist = to_target.dot(dir_vec)
            proj_dist = max(0, min(proj_dist, seg_length))

            # Calculate projected point
            proj_point = start + dir_vec * proj_dist
            perp_dist = target.distance_to(proj_point)

            if perp_dist < best_distance:
                best_distance = perp_dist
                best_station = start_station + cumulative + proj_dist

        elif seg.get('type') == 'CIRCULARARC':
            # Project point onto arc
            center = seg['center']
            radius = seg['radius']

            # Vector from center to target
            to_target = target - center
            dist_to_center = to_target.length

            if dist_to_center > 0:
                # Perpendicular distance is difference from radius
                perp_dist = abs(dist_to_center - radius)

                if perp_dist < best_distance:
                    # Calculate arc angle to this point
                    angle = math.atan2(to_target.y, to_target.x)

                    # Check if within arc bounds (simplified)
                    arc_dist = radius * abs(angle - seg['start_angle'])
                    if arc_dist <= seg_length:
                        best_distance = perp_dist
                        best_station = start_station + cumulative + arc_dist

        cumulative += seg_length

    return best_station


# =============================================================================
# Segment Generation Logic
# =============================================================================

def compute_tangent_segments(pis: List[Dict]) -> List[Dict]:
    """
    Compute tangent segments from PI list (no curves).

    Args:
        pis: List of PI data dictionaries

    Returns:
        List of tangent segment dictionaries
    """
    if len(pis) < 2:
        return []

    segments = []

    for i in range(len(pis) - 1):
        curr_pi = pis[i]
        next_pi = pis[i + 1]

        start = curr_pi['position']
        end = next_pi['position']

        direction = calculate_tangent_direction(start, end)
        length = calculate_tangent_length(start, end)

        segments.append({
            'type': 'LINE',
            'index': i,
            'start': start,
            'end': end,
            'direction': direction,
            'length': length,
        })

    return segments


def compute_segments_with_curves(pis: List[Dict]) -> List[Dict]:
    """
    Compute segments considering curves at PIs.

    Recalculates curve geometries and generates interleaved
    tangent/curve segments.

    Args:
        pis: List of PI data dictionaries (may have 'curve' data)

    Returns:
        List of segment dictionaries (tangents and curves)
    """
    if len(pis) < 2:
        return []

    # First, recalculate all curves
    _recalculate_curve_geometries(pis)

    segments = []

    for i in range(len(pis) - 1):
        curr_pi = pis[i]
        next_pi = pis[i + 1]

        # Determine tangent start
        if 'curve' in curr_pi and curr_pi['curve'].get('ec'):
            start_pos = curr_pi['curve']['ec']
        else:
            start_pos = curr_pi['position']

        # Determine tangent end
        if 'curve' in next_pi and next_pi['curve'].get('bc'):
            end_pos = next_pi['curve']['bc']
        else:
            end_pos = next_pi['position']

        # Create tangent segment
        direction = calculate_tangent_direction(start_pos, end_pos)
        length = calculate_tangent_length(start_pos, end_pos)

        segments.append({
            'type': 'LINE',
            'index': len(segments),
            'start': start_pos,
            'end': end_pos,
            'direction': direction,
            'length': length,
        })

        # Add curve at next PI if exists
        if 'curve' in next_pi:
            curve = next_pi['curve']

            # Calculate center for arc representation
            center = calculate_curve_center(
                curve['bc'],
                curve['start_direction'],
                curve['radius'],
                curve['turn_direction']
            )

            # Start angle is from center to BC
            start_angle = math.atan2(
                curve['bc'].y - center.y,
                curve['bc'].x - center.x
            )

            segments.append({
                'type': 'CIRCULARARC',
                'index': len(segments),
                'start': curve['bc'],
                'end': curve['ec'],
                'center': center,
                'radius': curve['radius'],
                'length': curve['arc_length'],
                'start_angle': start_angle,
                'direction': curve['start_direction'],
                'is_ccw': curve['turn_direction'] == 'LEFT',
                'deflection': curve['deflection'],
            })

    return segments


def _recalculate_curve_geometries(pis: List[Dict]) -> None:
    """
    Recalculate all curve geometries in-place.

    Args:
        pis: List of PI data dictionaries (modified in place)
    """
    for i, pi in enumerate(pis):
        if 'curve' not in pi:
            continue

        # Can only have curves at interior PIs
        if i <= 0 or i >= len(pis) - 1:
            del pi['curve']
            continue

        prev_pi = pis[i - 1]
        next_pi = pis[i + 1]

        updated_curve = calculate_curve_geometry(
            prev_pi['position'],
            pi['position'],
            next_pi['position'],
            pi['curve']['radius']
        )

        if updated_curve:
            pi['curve'] = updated_curve
        else:
            # Curve became invalid (e.g., PIs became collinear)
            del pi['curve']


def insert_curve(
    pis: List[Dict],
    pi_index: int,
    radius: float
) -> Optional[Dict]:
    """
    Insert a curve at the specified PI.

    Args:
        pis: List of PI data dictionaries (modified in place)
        pi_index: Index of interior PI where curve should be inserted
        radius: Curve radius in meters

    Returns:
        Curve data dictionary, or None if curve cannot be created
    """
    # Validate index (must be interior PI)
    if pi_index <= 0 or pi_index >= len(pis) - 1:
        return None

    prev_pi = pis[pi_index - 1]
    curr_pi = pis[pi_index]
    next_pi = pis[pi_index + 1]

    curve_data = calculate_curve_geometry(
        prev_pi['position'],
        curr_pi['position'],
        next_pi['position'],
        radius
    )

    if not curve_data:
        return None

    curr_pi['curve'] = curve_data
    return curve_data


def remove_curve(pis: List[Dict], pi_index: int) -> bool:
    """
    Remove curve at specified PI.

    Args:
        pis: List of PI data dictionaries (modified in place)
        pi_index: Index of PI to remove curve from

    Returns:
        True if curve was removed, False if no curve existed
    """
    if pi_index < 0 or pi_index >= len(pis):
        return False

    if 'curve' in pis[pi_index]:
        del pis[pi_index]['curve']
        return True

    return False


# =============================================================================
# High-Level Operations (Use Tool Interfaces)
# =============================================================================

def create_alignment(
    ifc: "type[tool.Ifc]",
    alignment_tool: "type[tool.Alignment]",
    blender: "type[tool.Blender]",
    name: str,
    pis: List[Dict],
) -> "ifcopenshell.entity_instance":
    """
    Create a new horizontal alignment.

    This is the main entry point for creating alignments using the
    three-layer architecture.

    Args:
        ifc: IFC tool interface
        alignment_tool: Alignment tool interface
        blender: Blender tool interface
        name: Alignment name
        pis: List of PI dictionaries with keys:
            - x: X coordinate
            - y: Y coordinate
            - radius: (optional) Curve radius

    Returns:
        The created IfcAlignment entity

    Raises:
        ValueError: If fewer than 2 PIs provided
    """
    if len(pis) < 2:
        raise ValueError("Alignment requires at least 2 PIs")

    # Format PI data
    formatted_pis = []
    for i, pi in enumerate(pis):
        x = pi.get('x', 0.0)
        y = pi.get('y', 0.0)
        radius = pi.get('radius', 0.0)

        pi_data = create_pi_data(i, x, y)
        if radius > 0 and i > 0 and i < len(pis) - 1:
            # Will calculate curve after all PIs are added
            pi_data['_pending_radius'] = radius
        formatted_pis.append(pi_data)

    # Insert curves for pending radii
    for i, pi in enumerate(formatted_pis):
        if '_pending_radius' in pi:
            insert_curve(formatted_pis, i, pi['_pending_radius'])
            del pi['_pending_radius']

    # Create alignment via tool interface
    alignment_entity = alignment_tool.create(name, formatted_pis)

    return alignment_entity


def update_alignment_pis(
    ifc: "type[tool.Ifc]",
    alignment_tool: "type[tool.Alignment]",
    alignment_entity: "ifcopenshell.entity_instance",
    pis: List[Dict],
) -> None:
    """
    Update an existing alignment's PI geometry.

    Args:
        ifc: IFC tool interface
        alignment_tool: Alignment tool interface
        alignment_entity: The IfcAlignment entity to update
        pis: Updated PI data
    """
    alignment_tool.set_pis(alignment_entity, pis)
    alignment_tool.update_visualization(alignment_entity)


def get_alignment_info(
    alignment_tool: "type[tool.Alignment]",
    alignment_entity: "ifcopenshell.entity_instance",
) -> Dict:
    """
    Get comprehensive information about an alignment.

    Args:
        alignment_tool: Alignment tool interface
        alignment_entity: The IfcAlignment entity

    Returns:
        Dictionary with alignment information
    """
    pis = alignment_tool.get_pis(alignment_entity)
    segments = alignment_tool.get_horizontal_segments(alignment_entity)
    length = alignment_tool.get_length(alignment_entity)

    return {
        'name': alignment_entity.Name if hasattr(alignment_entity, 'Name') else 'Unnamed',
        'pi_count': len(pis),
        'segment_count': len(segments),
        'total_length': length,
        'pis': pis,
        'segments': segments,
    }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Data structures
    'SimpleVector',
    'create_pi_data',
    'format_pi_for_ifc',
    'pis_from_coordinates',

    # Geometry calculations
    'calculate_curve_geometry',
    'calculate_curve_center',
    'calculate_point_on_curve',
    'get_tangent_intersection',
    'calculate_tangent_direction',
    'calculate_tangent_length',
    'calculate_deflection_angle',
    'get_total_alignment_length',
    'interpolate_position_on_line',
    'interpolate_position_on_arc',
    'get_point_at_station',
    'get_station_at_point',

    # Segment generation
    'compute_tangent_segments',
    'compute_segments_with_curves',
    'insert_curve',
    'remove_curve',

    # High-level operations
    'create_alignment',
    'update_alignment_pis',
    'get_alignment_info',
]