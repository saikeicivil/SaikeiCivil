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
IFC Geometry Builders
=====================

Helper functions for creating IFC geometric entities that form the 
geometric representation layer of alignments.

This module supports the complete IFC 4.3 alignment specification by
creating the geometric ParentCurve entities (IfcLine, IfcCircle, etc.)
that are wrapped by IfcCurveSegment to form IfcCompositeCurve structures.

Architecture:
    Business Logic Layer (existing):
        IfcAlignmentHorizontalSegment with PredefinedType
    
    Geometric Representation Layer (this module):
        IfcLine, IfcCircle → IfcCurveSegment → IfcCompositeCurve

Usage:
    from saikei.core.ifc_geometry_builders import (
        create_line_parent_curve,
        create_circle_parent_curve,
        create_curve_segment,
        create_composite_curve
    )
    
    # Create geometric representation
    line = create_line_parent_curve(ifc, 0, 0, 100, 0)
    segment = create_curve_segment(ifc, line, placement, 0, 100)
    composite = create_composite_curve(ifc, [segment])

Author: Saikei Civil Team
Date: November 6, 2025
Sprint: Phase 1 - IFC Compliance
Status: Day 1 Implementation
"""

import ifcopenshell
import ifcopenshell.guid
import math
from typing import Tuple, Optional, List


# ============================================================================
# BASIC GEOMETRY HELPERS
# ============================================================================

def create_cartesian_point_2d(ifc_file, x: float, y: float):
    """Create 2D Cartesian point
    
    Args:
        ifc_file: IFC file object
        x: X coordinate in meters
        y: Y coordinate in meters
        
    Returns:
        IfcCartesianPoint entity
        
    Example:
        >>> point = create_cartesian_point_2d(ifc, 100.0, 50.0)
    """
    return ifc_file.create_entity("IfcCartesianPoint",
        Coordinates=[float(x), float(y)])


def create_cartesian_point_3d(ifc_file, x: float, y: float, z: float):
    """Create 3D Cartesian point
    
    Args:
        ifc_file: IFC file object
        x: X coordinate in meters
        y: Y coordinate in meters
        z: Z coordinate in meters
        
    Returns:
        IfcCartesianPoint entity
        
    Example:
        >>> point = create_cartesian_point_3d(ifc, 100.0, 50.0, 105.0)
    """
    return ifc_file.create_entity("IfcCartesianPoint",
        Coordinates=[float(x), float(y), float(z)])


def create_direction_2d(ifc_file, dx: float, dy: float):
    """Create 2D direction vector (automatically normalized)
    
    Args:
        ifc_file: IFC file object
        dx: X component of direction
        dy: Y component of direction
        
    Returns:
        IfcDirection entity (normalized to unit length)
        
    Note:
        If input is zero vector, returns direction (1, 0)
        
    Example:
        >>> # Create direction pointing northeast
        >>> direction = create_direction_2d(ifc, 1.0, 1.0)
        >>> # Result is normalized: (0.707, 0.707)
    """
    # Normalize to unit vector
    length = math.sqrt(dx*dx + dy*dy)
    if length < 1e-10:
        # Zero vector - default to X-axis
        dx, dy = 1.0, 0.0
    else:
        dx, dy = dx/length, dy/length
    
    return ifc_file.create_entity("IfcDirection",
        DirectionRatios=[float(dx), float(dy)])


def create_direction_3d(ifc_file, dx: float, dy: float, dz: float):
    """Create 3D direction vector (automatically normalized)
    
    Args:
        ifc_file: IFC file object
        dx: X component of direction
        dy: Y component of direction
        dz: Z component of direction
        
    Returns:
        IfcDirection entity (normalized to unit length)
        
    Example:
        >>> direction = create_direction_3d(ifc, 1.0, 0.0, 1.0)
        >>> # Result is normalized: (0.707, 0.0, 0.707)
    """
    # Normalize to unit vector
    length = math.sqrt(dx*dx + dy*dy + dz*dz)
    if length < 1e-10:
        # Zero vector - default to Z-axis
        dx, dy, dz = 0.0, 0.0, 1.0
    else:
        dx, dy, dz = dx/length, dy/length, dz/length
    
    return ifc_file.create_entity("IfcDirection",
        DirectionRatios=[float(dx), float(dy), float(dz)])


def create_vector_2d(ifc_file, dx: float, dy: float, magnitude: float = 1.0):
    """Create 2D vector with direction and magnitude
    
    Args:
        ifc_file: IFC file object
        dx: X component of direction
        dy: Y component of direction
        magnitude: Vector magnitude (default 1.0)
        
    Returns:
        IfcVector entity
        
    Example:
        >>> # Create vector of length 100 pointing east
        >>> vector = create_vector_2d(ifc, 1.0, 0.0, 100.0)
    """
    direction = create_direction_2d(ifc_file, dx, dy)
    return ifc_file.create_entity("IfcVector",
        Orientation=direction,
        Magnitude=float(magnitude))


def create_axis2placement_2d(ifc_file, x: float, y: float, 
                             angle: Optional[float] = None):
    """Create 2D axis placement (location + optional rotation)
    
    Args:
        ifc_file: IFC file object
        x: X coordinate of location
        y: Y coordinate of location
        angle: Optional rotation angle in radians (CCW from X-axis)
        
    Returns:
        IfcAxis2Placement2D entity
        
    Example:
        >>> # Placement at (100, 50) rotated 45° CCW
        >>> placement = create_axis2placement_2d(ifc, 100, 50, math.pi/4)
    """
    location = create_cartesian_point_2d(ifc_file, x, y)
    
    if angle is not None:
        # Create reference direction from angle
        dx = math.cos(angle)
        dy = math.sin(angle)
        ref_direction = create_direction_2d(ifc_file, dx, dy)
    else:
        # No rotation - default X-axis orientation
        ref_direction = None
    
    return ifc_file.create_entity("IfcAxis2Placement2D",
        Location=location,
        RefDirection=ref_direction)


def create_axis2placement_3d(ifc_file, x: float, y: float, z: float,
                             axis_direction: Optional[Tuple[float, float, float]] = None,
                             ref_direction: Optional[Tuple[float, float, float]] = None):
    """Create 3D axis placement (location + optional rotation)
    
    Args:
        ifc_file: IFC file object
        x, y, z: Location coordinates
        axis_direction: Optional Z-axis direction tuple (dx, dy, dz)
        ref_direction: Optional X-axis direction tuple (dx, dy, dz)
        
    Returns:
        IfcAxis2Placement3D entity
        
    Example:
        >>> # Simple placement at origin
        >>> placement = create_axis2placement_3d(ifc, 0, 0, 0)
    """
    location = create_cartesian_point_3d(ifc_file, x, y, z)
    
    axis = None
    if axis_direction is not None:
        axis = create_direction_3d(ifc_file, *axis_direction)
    
    ref = None
    if ref_direction is not None:
        ref = create_direction_3d(ifc_file, *ref_direction)
    
    return ifc_file.create_entity("IfcAxis2Placement3D",
        Location=location,
        Axis=axis,
        RefDirection=ref)


# ============================================================================
# PARENT CURVE CREATORS - THE GEOMETRIC ENTITIES
# ============================================================================

def create_line_parent_curve(ifc_file, start_x: float, start_y: float,
                              end_x: float, end_y: float):
    """Create IfcLine as ParentCurve for tangent segment

    This is the geometric representation of a straight line segment.
    IfcLine is defined by a point and a direction vector.

    IMPORTANT: The line is created at the ORIGIN (0,0), NOT at world coordinates!
    The IfcCurveSegment.Placement will position it in world space.
    Creating the line at world coords AND using Placement would cause double-positioning.

    Args:
        ifc_file: IFC file object
        start_x, start_y: Start point coordinates in meters (used for direction only)
        end_x, end_y: End point coordinates in meters

    Returns:
        IfcLine entity

    Example:
        >>> # Create line from (0,0) to (100,0)
        >>> line = create_line_parent_curve(ifc, 0, 0, 100, 0)

    Note:
        This creates the GEOMETRIC representation at origin.
        The IfcCurveSegment.Placement moves it to world position.
    """
    # Line is at ORIGIN - Placement will position it in world space
    # DO NOT use world coordinates here - it causes double-positioning!
    point = create_cartesian_point_2d(ifc_file, 0.0, 0.0)

    # Direction from start to end (this encodes the line orientation)
    dx = end_x - start_x
    dy = end_y - start_y
    direction = create_direction_2d(ifc_file, dx, dy)

    # Create direction vector (magnitude = 1.0 for unit vector)
    vector = ifc_file.create_entity("IfcVector",
        Orientation=direction,
        Magnitude=1.0)

    # Create line at origin with direction
    return ifc_file.create_entity("IfcLine",
        Pnt=point,
        Dir=vector)


def create_circle_parent_curve(ifc_file, center_x: float, center_y: float,
                                radius: float, start_angle: float = 0.0):
    """Create IfcCircle as ParentCurve for curve segment

    This is the geometric representation of a circular arc.
    IfcCircle is defined by a center placement and radius.

    IMPORTANT: The circle is created at the ORIGIN, NOT at world coordinates!
    The IfcCurveSegment.Placement will position it in world space.
    Creating the circle at world coords AND using Placement would cause double-positioning.

    Args:
        ifc_file: IFC file object
        center_x, center_y: Circle center coordinates (NOT USED - for API compatibility)
        radius: Circle radius in meters (must be positive)
        start_angle: Starting angle in radians (for RefDirection orientation)

    Returns:
        IfcCircle entity

    Example:
        >>> # Create circle with 100m radius
        >>> circle = create_circle_parent_curve(ifc, 50, 0, 100, 0)

    Note:
        The circle is at origin. IfcCurveSegment.Placement positions it.
        Radius must be positive. Turn direction is handled by signed angular extent.
    """
    # Ensure radius is positive (geometric representation)
    abs_radius = abs(radius)

    # Circle at ORIGIN with RefDirection encoding the start angle
    # DO NOT use world coordinates - Placement will position it!
    placement = create_axis2placement_2d(ifc_file, 0.0, 0.0, start_angle)

    # Create circle at origin
    return ifc_file.create_entity("IfcCircle",
        Position=placement,
        Radius=float(abs_radius))


# ============================================================================
# CURVE SEGMENT CREATORS - THE CRITICAL LINK
# ============================================================================

def create_curve_segment(ifc_file, parent_curve, placement,
                        segment_start: float, segment_length: float,
                        transition: str = "CONTINUOUS"):
    """Create IfcCurveSegment linking geometry to business logic
    
    This is THE CRITICAL LINK between:
    - ParentCurve (geometry): IfcLine, IfcCircle, IfcClothoid, etc.
    - Business logic: IfcAlignmentHorizontalSegment, IfcAlignmentVerticalSegment
    
    IfcCurveSegment defines a "segment" of the infinite ParentCurve by
    specifying where to start "cutting" and how much length to take.
    
    Args:
        ifc_file: IFC file object
        parent_curve: IfcLine, IfcCircle, or other IfcCurve entity
        placement: IfcAxis2Placement2D for segment start point and orientation
        segment_start: Distance along ParentCurve to start (usually 0.0)
        segment_length: Length to "cut" from ParentCurve in meters
        transition: Type of transition to next segment:
            - "CONTINUOUS" (default): G0 continuity (position only)
            - "CONTSAMEGRADIENT": G1 continuity (position + tangent)
            - "CONTSAMEGRADIENTSAMECURVATURE": G2 continuity (+ curvature)
            - "DISCONTINUOUS": No continuity guaranteed
            
    Returns:
        IfcCurveSegment entity
        
    Example:
        >>> # Create curve segment for a 100m line
        >>> line = create_line_parent_curve(ifc, 0, 0, 100, 0)
        >>> placement = create_axis2placement_2d(ifc, 0, 0, 0)
        >>> segment = create_curve_segment(ifc, line, placement, 0, 100)
        
    Note:
        This entity is what gets collected into IfcCompositeCurve.
        Without this, you only have business logic, not geometry!
    """
    # For IFC4X3, SegmentStart and SegmentLength are IfcCurveMeasureSelect
    # which requires IfcParameterValue entity instances (not raw floats).
    segment_start_param = ifc_file.create_entity("IfcParameterValue", float(segment_start))
    segment_length_param = ifc_file.create_entity("IfcParameterValue", float(segment_length))

    return ifc_file.create_entity("IfcCurveSegment",
        Transition=transition,
        Placement=placement,
        SegmentStart=segment_start_param,
        SegmentLength=segment_length_param,
        ParentCurve=parent_curve)


# ============================================================================
# COMPOSITE CURVE CREATORS - THE WRAPPER
# ============================================================================

def create_composite_curve(ifc_file, curve_segments: List, 
                           self_intersect: bool = False):
    """Create IfcCompositeCurve from list of IfcCurveSegment
    
    This wraps multiple IfcCurveSegment objects into a single curve entity.
    Used for horizontal alignment geometric representation.
    
    The IfcCompositeCurve represents the complete alignment as a single
    geometric entity, which is essential for:
    - Linking vertical to horizontal (BaseCurve reference)
    - Creating offset curves
    - Linear placement operations
    
    Args:
        ifc_file: IFC file object
        curve_segments: List of IfcCurveSegment entities
        self_intersect: Whether curve is allowed to self-intersect (usually False)
        
    Returns:
        IfcCompositeCurve entity
        
    Example:
        >>> # Create composite curve from 3 segments
        >>> segments = [segment1, segment2, segment3]
        >>> composite = create_composite_curve(ifc, segments)
        
    Note:
        This is used for horizontal alignments.
        For vertical, use IfcGradientCurve instead.
    """
    return ifc_file.create_entity("IfcCompositeCurve",
        Segments=curve_segments,
        SelfIntersect=self_intersect)


def create_gradient_curve(ifc_file, curve_segments: List,
                          base_curve,
                          self_intersect: bool = False):
    """Create IfcGradientCurve from vertical segments + horizontal base
    
    IfcGradientCurve is used for vertical alignments. It:
    - Wraps vertical curve segments (like IfcCompositeCurve)
    - Links to horizontal alignment via BaseCurve
    - Defines elevation in "distance along, elevation" 2D space
    
    Args:
        ifc_file: IFC file object
        curve_segments: List of IfcCurveSegment for vertical segments
        base_curve: IfcCompositeCurve from horizontal alignment
        self_intersect: Whether curve can self-intersect (usually False)
        
    Returns:
        IfcGradientCurve entity
        
    Example:
        >>> # Create gradient curve linked to horizontal
        >>> v_segments = [v_segment1, v_segment2]
        >>> h_composite = create_composite_curve(ifc, h_segments)
        >>> gradient = create_gradient_curve(ifc, v_segments, h_composite)
        
    Note:
        The BaseCurve linkage is THE KEY to connecting H+V layers!
    """
    return ifc_file.create_entity("IfcGradientCurve",
        Segments=curve_segments,
        BaseCurve=base_curve,
        SelfIntersect=self_intersect)


def create_alignment_curve(ifc_file, composite_or_gradient_curve,
                           tag: str = ""):
    """DEPRECATED: IfcAlignmentCurve does NOT exist in IFC 4.3!

    This function is kept for backwards compatibility but should NOT be used.
    Use IfcCompositeCurve or IfcGradientCurve directly in IfcShapeRepresentation.

    WARNING: External viewers like Solibri, FreeCAD, and BIMcollab will NOT
    recognize IfcAlignmentCurve entities because they don't exist in the schema!

    Correct approach:
        >>> composite = create_composite_curve(ifc, segments)
        >>> shape_rep = create_shape_representation(ifc, context, [composite], ...)

    DO NOT use this function for new code!
    """
    import warnings
    warnings.warn(
        "create_alignment_curve() is DEPRECATED. IfcAlignmentCurve does not exist in IFC 4.3! "
        "Use IfcCompositeCurve directly in IfcShapeRepresentation instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # Return the curve directly instead of wrapping in non-existent entity
    return composite_or_gradient_curve


# ============================================================================
# SHAPE REPRESENTATION CREATORS
# ============================================================================

def create_shape_representation(ifc_file, context, items: List, 
                                representation_type: str = "Curve3D",
                                representation_identifier: str = "Axis"):
    """Create IfcShapeRepresentation for geometric items
    
    IfcShapeRepresentation holds the geometric items (IfcAlignmentCurve)
    and links them to a geometric representation context.
    
    Args:
        ifc_file: IFC file object
        context: IfcGeometricRepresentationContext
        items: List of geometric items (typically [IfcAlignmentCurve])
        representation_type: Type of representation (usually "Curve3D")
        representation_identifier: Identifier (usually "Axis" for alignments)
        
    Returns:
        IfcShapeRepresentation entity
        
    Example:
        >>> context = get_geometric_representation_context(ifc)
        >>> shape_rep = create_shape_representation(
        ...     ifc, context, [alignment_curve], "Curve3D", "Axis"
        ... )
    """
    return ifc_file.create_entity("IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier=representation_identifier,
        RepresentationType=representation_type,
        Items=items)


def create_product_definition_shape(ifc_file, representations: List):
    """Create IfcProductDefinitionShape to hold shape representations
    
    IfcProductDefinitionShape is the container that holds one or more
    IfcShapeRepresentation entities. This is what gets assigned to the
    Representation attribute of IfcAlignmentHorizontal or IfcAlignmentVertical.
    
    Args:
        ifc_file: IFC file object
        representations: List of IfcShapeRepresentation entities
        
    Returns:
        IfcProductDefinitionShape entity
        
    Example:
        >>> shape_rep = create_shape_representation(ifc, context, items)
        >>> product_shape = create_product_definition_shape(ifc, [shape_rep])
        >>> alignment_horizontal.Representation = product_shape
    """
    return ifc_file.create_entity("IfcProductDefinitionShape",
        Representations=representations)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_curve_center(bc_x: float, bc_y: float, 
                           angle: float, radius: float,
                           turn_direction: str) -> Tuple[float, float]:
    """Calculate circle center from BC point, angle, and radius
    
    Given the Begin Curve point, tangent angle, radius, and turn direction,
    calculate where the circle center is located.
    
    Args:
        bc_x, bc_y: Begin Curve point coordinates
        angle: Tangent angle at BC in radians (CCW from X-axis)
        radius: Curve radius in meters (positive value)
        turn_direction: "LEFT" or "RIGHT"
        
    Returns:
        (center_x, center_y) tuple
        
    Example:
        >>> # BC at (100, 0), tangent pointing east, 50m radius, left turn
        >>> center = calculate_curve_center(100, 0, 0, 50, "LEFT")
        >>> # Result: (100, 50) - center is north of BC
    """
    # Perpendicular to tangent
    if turn_direction == "LEFT":
        # Center is 90° CCW from tangent
        perp_angle = angle + math.pi/2
    else:  # RIGHT
        # Center is 90° CW from tangent  
        perp_angle = angle - math.pi/2
    
    center_x = bc_x + radius * math.cos(perp_angle)
    center_y = bc_y + radius * math.sin(perp_angle)
    
    return center_x, center_y


def get_geometric_representation_context(ifc_file):
    """Get or create geometric representation context
    
    The geometric representation context defines the coordinate system
    and precision for geometric entities. All shape representations
    must reference a context.
    
    Args:
        ifc_file: IFC file object
        
    Returns:
        IfcGeometricRepresentationContext entity
        
    Note:
        This tries to find an existing 3D Model context first.
        If not found, creates a new one.
    """
    # Try to find existing context
    contexts = ifc_file.by_type("IfcGeometricRepresentationContext")
    
    for context in contexts:
        # Look for 3D model context
        if (hasattr(context, 'ContextType') and 
            context.ContextType == "Model" and 
            hasattr(context, 'CoordinateSpaceDimension') and
            context.CoordinateSpaceDimension == 3):
            return context
    
    # If not found, create one
    # (In practice, this should be created once per project)
    origin_3d = create_axis2placement_3d(ifc_file, 0.0, 0.0, 0.0)
    
    return ifc_file.create_entity("IfcGeometricRepresentationContext",
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=1e-5,
        WorldCoordinateSystem=origin_3d)


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_curve_segment(curve_segment) -> bool:
    """Validate that an IfcCurveSegment is properly formed
    
    Checks:
    - Has valid ParentCurve
    - Has valid Placement
    - SegmentLength is positive
    - Transition type is valid
    
    Args:
        curve_segment: IfcCurveSegment entity to validate
        
    Returns:
        True if valid, raises ValueError if invalid
        
    Raises:
        ValueError: If validation fails with descriptive message
    """
    if not curve_segment.is_a("IfcCurveSegment"):
        raise ValueError("Not an IfcCurveSegment entity")
    
    if curve_segment.ParentCurve is None:
        raise ValueError("IfcCurveSegment missing ParentCurve")
    
    if curve_segment.Placement is None:
        raise ValueError("IfcCurveSegment missing Placement")
    
    if curve_segment.SegmentLength <= 0:
        raise ValueError(f"IfcCurveSegment has non-positive length: {curve_segment.SegmentLength}")
    
    valid_transitions = ["CONTINUOUS", "CONTSAMEGRADIENT", 
                        "CONTSAMEGRADIENTSAMECURVATURE", "DISCONTINUOUS"]
    if curve_segment.Transition not in valid_transitions:
        raise ValueError(f"Invalid transition type: {curve_segment.Transition}")
    
    return True


def validate_composite_curve(composite_curve) -> bool:
    """Validate that an IfcCompositeCurve is properly formed
    
    Checks:
    - Has segments
    - All segments are IfcCurveSegment
    - Segments are properly ordered
    
    Args:
        composite_curve: IfcCompositeCurve or IfcGradientCurve entity
        
    Returns:
        True if valid, raises ValueError if invalid
    """
    if not (composite_curve.is_a("IfcCompositeCurve") or 
            composite_curve.is_a("IfcGradientCurve")):
        raise ValueError("Not an IfcCompositeCurve or IfcGradientCurve")
    
    if not composite_curve.Segments:
        raise ValueError("Composite curve has no segments")
    
    for i, segment in enumerate(composite_curve.Segments):
        try:
            validate_curve_segment(segment)
        except ValueError as e:
            raise ValueError(f"Segment {i} invalid: {e}")
    
    return True


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Basic geometry
    'create_cartesian_point_2d',
    'create_cartesian_point_3d',
    'create_direction_2d',
    'create_direction_3d',
    'create_vector_2d',
    'create_axis2placement_2d',
    'create_axis2placement_3d',
    
    # Parent curves (THE GEOMETRY)
    'create_line_parent_curve',
    'create_circle_parent_curve',
    
    # Curve segments (THE LINK)
    'create_curve_segment',
    
    # Composite curves (THE WRAPPER)
    'create_composite_curve',
    'create_gradient_curve',
    'create_alignment_curve',
    
    # Shape representations
    'create_shape_representation',
    'create_product_definition_shape',
    
    # Utilities
    'calculate_curve_center',
    'get_geometric_representation_context',
    
    # Validation
    'validate_curve_segment',
    'validate_composite_curve',
]
