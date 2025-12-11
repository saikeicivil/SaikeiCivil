# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under the GNU General Public License v3
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
Alignment Tool Implementation
==============================

Blender-specific implementation of the Alignment interface.
Bridges core business logic with Blender visualization and IFC operations.

This module implements the Alignment interface defined in core/tool.py,
providing concrete implementations for:
- Creating alignments (IFC + Blender visualization)
- Managing PI data
- Updating visualization from IFC data

Usage:
    from saikei_civil.tool import Alignment, Ifc

    # Create a new alignment
    pis = [
        {'x': 0, 'y': 0},
        {'x': 100, 'y': 0},
        {'x': 100, 'y': 100},
    ]
    alignment = Alignment.create("Main Road", pis)

    # Get existing PI data
    pi_data = Alignment.get_pis(alignment)

    # Update visualization
    Alignment.update_visualization(alignment)
"""
from typing import TYPE_CHECKING, Optional, List, Dict, Tuple
import math
import logging

import bpy
from mathutils import Vector

from ..core import tool as core_tool
from . import Ifc, Blender

# Import core alignment logic
from ..core import alignment as core_alignment
from ..core.alignment import SimpleVector

if TYPE_CHECKING:
    import ifcopenshell

logger = logging.getLogger(__name__)


class Alignment(core_tool.Alignment):
    """
    Blender-specific alignment operations.

    Implements the Alignment interface, providing concrete methods for
    creating and managing horizontal alignments with Blender visualization.
    """

    # =========================================================================
    # Interface Implementation
    # =========================================================================

    @classmethod
    def create(cls, name: str, pis: List[Dict]) -> "ifcopenshell.entity_instance":
        """
        Create a new horizontal alignment.

        Creates the IFC entities (IfcAlignment, IfcAlignmentHorizontal,
        segments) and Blender visualization objects.

        Args:
            name: Alignment name
            pis: List of PI dictionaries with keys:
                - x: X coordinate (or 'position': SimpleVector)
                - y: Y coordinate
                - curve: (optional) Curve data dict with 'radius'

        Returns:
            The created IfcAlignment entity
        """
        from ..core.ifc_manager import NativeIfcManager
        from ..core import ifc_api

        ifc = NativeIfcManager.get_file()
        if not ifc:
            raise RuntimeError("No IFC file loaded. Create a new file first.")

        # Extract PI coordinates and radii
        pi_coords = []
        radii = []
        for pi in pis:
            if isinstance(pi.get('position'), SimpleVector):
                x, y = pi['position'].x, pi['position'].y
            else:
                x = pi.get('x', 0.0)
                y = pi.get('y', 0.0)
            pi_coords.append((x, y))

            # Get radius for this PI
            radius = 0.0
            if 'curve' in pi and pi['curve'].get('radius'):
                radius = pi['curve']['radius']
            elif pi.get('radius', 0) > 0:
                radius = pi['radius']
            radii.append(radius)

        # Get or create Road container
        road = ifc_api.get_or_create_road(ifc)

        # Create alignment using API wrapper (falls back to legacy if needed)
        alignment_entity = ifc_api.create_alignment_by_pi(
            ifc,
            name=name,
            pis=pi_coords,
            radii=radii,
            container=road
        )

        # Create visualization
        # Note: For API-created alignments, we need to load it back
        from ..core.horizontal_alignment import NativeIfcAlignment
        from ..core.alignment_visualizer import AlignmentVisualizer

        # Load the alignment for visualization
        native_alignment = NativeIfcAlignment(ifc, alignment_entity=alignment_entity)
        visualizer = AlignmentVisualizer(native_alignment)
        visualizer.visualize_all()

        # Store visualizer reference for updates
        native_alignment._visualizer = visualizer

        return alignment_entity

    @classmethod
    def get_pis(cls, alignment: "ifcopenshell.entity_instance") -> List[Dict]:
        """
        Get PI data from an alignment.

        Extracts PI information from the IFC alignment's horizontal segments.

        Args:
            alignment: The IfcAlignment entity

        Returns:
            List of PI dictionaries with position and curve data
        """
        if not alignment:
            return []

        # Get horizontal layout
        horizontal = cls._get_horizontal_layout(alignment)
        if not horizontal:
            return []

        # Get segments
        segments = cls._get_nested_segments(horizontal)
        if not segments:
            return []

        # Reconstruct PIs from segments
        return cls._reconstruct_pis(segments)

    @classmethod
    def set_pis(cls, alignment: "ifcopenshell.entity_instance", pis: List[Dict]) -> None:
        """
        Update alignment geometry from PI data.

        Regenerates the IFC segments and updates visualization.

        Args:
            alignment: The IfcAlignment entity
            pis: Updated PI data
        """
        # Find associated NativeIfcAlignment instance
        native_alignment = cls._get_native_alignment(alignment)
        if not native_alignment:
            logger.warning("No NativeIfcAlignment found for entity")
            return

        # Update PIs
        native_alignment.pis = []
        for i, pi in enumerate(pis):
            if isinstance(pi.get('position'), SimpleVector):
                pos = pi['position']
            else:
                pos = SimpleVector(pi.get('x', 0), pi.get('y', 0))

            pi_data = {
                'id': i,
                'position': pos,
                'ifc_point': native_alignment.ifc.create_entity(
                    "IfcCartesianPoint",
                    Coordinates=[float(pos.x), float(pos.y)]
                )
            }

            if 'curve' in pi:
                pi_data['curve'] = pi['curve']

            native_alignment.pis.append(pi_data)

        # Regenerate segments
        if any('curve' in pi for pi in native_alignment.pis):
            native_alignment.regenerate_segments_with_curves()
        else:
            native_alignment.regenerate_segments()

        # Update visualization
        cls.update_visualization(alignment)

    @classmethod
    def get_horizontal_segments(cls, alignment: "ifcopenshell.entity_instance") -> List[Dict]:
        """
        Get computed horizontal segments.

        Args:
            alignment: The IfcAlignment entity

        Returns:
            List of segment dictionaries with type, geometry, etc.
        """
        if not alignment:
            return []

        horizontal = cls._get_horizontal_layout(alignment)
        if not horizontal:
            return []

        ifc_segments = cls._get_nested_segments(horizontal)
        return [cls._segment_to_dict(seg) for seg in ifc_segments]

    @classmethod
    def get_length(cls, alignment: "ifcopenshell.entity_instance") -> float:
        """
        Get total alignment length.

        Args:
            alignment: The IfcAlignment entity

        Returns:
            Total length in model units
        """
        segments = cls.get_horizontal_segments(alignment)
        return sum(seg.get('length', 0.0) for seg in segments)

    @classmethod
    def get_point_at_station(
        cls,
        alignment: "ifcopenshell.entity_instance",
        station: float
    ) -> Optional[Dict]:
        """
        Get coordinates and direction at a station.

        Args:
            alignment: The IfcAlignment entity
            station: Station value

        Returns:
            Dictionary with x, y, z, direction (radians), or None if invalid
        """
        segments = cls.get_horizontal_segments(alignment)
        if not segments:
            return None

        # Get starting station
        start_station = cls._get_starting_station(alignment)

        # Convert to internal segment format
        internal_segments = []
        for seg in segments:
            internal_seg = {
                'type': seg['type'],
                'length': seg['length'],
                'direction': seg.get('start_direction', 0.0),
            }

            if seg['type'] == 'LINE':
                internal_seg['start'] = SimpleVector(
                    seg['start_x'], seg['start_y']
                )
            elif seg['type'] == 'CIRCULARARC':
                # Calculate center
                start = SimpleVector(seg['start_x'], seg['start_y'])
                radius = abs(seg.get('radius', 100.0))
                direction = seg.get('start_direction', 0.0)
                is_ccw = seg.get('radius', 0) > 0

                if is_ccw:
                    center_angle = direction + math.pi / 2
                else:
                    center_angle = direction - math.pi / 2

                center = SimpleVector(
                    start.x + radius * math.cos(center_angle),
                    start.y + radius * math.sin(center_angle)
                )

                start_angle = math.atan2(
                    start.y - center.y,
                    start.x - center.x
                )

                internal_seg['center'] = center
                internal_seg['radius'] = radius
                internal_seg['start_angle'] = start_angle
                internal_seg['is_ccw'] = is_ccw

            internal_segments.append(internal_seg)

        result = core_alignment.get_point_at_station(
            internal_segments, station, start_station
        )

        if result:
            result['z'] = 0.0  # 2D alignment

        return result

    @classmethod
    def get_station_at_point(
        cls,
        alignment: "ifcopenshell.entity_instance",
        point: Tuple[float, float]
    ) -> Optional[float]:
        """
        Get station value at the closest point on alignment.

        Args:
            alignment: The IfcAlignment entity
            point: (x, y) coordinates

        Returns:
            Station value, or None if point is too far from alignment
        """
        segments = cls.get_horizontal_segments(alignment)
        if not segments:
            return None

        start_station = cls._get_starting_station(alignment)

        # Simplified implementation - find closest segment
        # Full implementation would use core_alignment.get_station_at_point

        target = Vector((point[0], point[1]))
        best_station = None
        best_distance = float('inf')
        cumulative = 0.0

        for seg in segments:
            if seg['type'] == 'LINE':
                start = Vector((seg['start_x'], seg['start_y']))
                direction = seg.get('start_direction', 0.0)
                length = seg['length']

                # Project point onto line
                dir_vec = Vector((math.cos(direction), math.sin(direction)))
                to_target = target - start
                proj_dist = to_target.dot(dir_vec)
                proj_dist = max(0, min(proj_dist, length))

                proj_point = start + dir_vec * proj_dist
                dist = (target - proj_point).length

                if dist < best_distance:
                    best_distance = dist
                    best_station = start_station + cumulative + proj_dist

            cumulative += seg['length']

        return best_station if best_distance < 100.0 else None

    @classmethod
    def update_visualization(cls, alignment: "ifcopenshell.entity_instance") -> None:
        """
        Update Blender visualization from IFC alignment data.

        Regenerates curve geometry and PI markers from current IFC data.

        Args:
            alignment: The IfcAlignment entity
        """
        native_alignment = cls._get_native_alignment(alignment)
        if native_alignment and hasattr(native_alignment, '_visualizer'):
            native_alignment._visualizer.update_all()
            return

        # Fallback: update via Blender object
        obj = Ifc.get_object(alignment)
        if obj:
            cls._update_curve_from_segments(obj, alignment)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    @classmethod
    def _get_horizontal_layout(
        cls,
        alignment: "ifcopenshell.entity_instance"
    ) -> Optional["ifcopenshell.entity_instance"]:
        """Get IfcAlignmentHorizontal from alignment."""
        if not hasattr(alignment, 'IsNestedBy') or not alignment.IsNestedBy:
            return None

        for rel in alignment.IsNestedBy:
            for obj in rel.RelatedObjects:
                if obj.is_a("IfcAlignmentHorizontal"):
                    return obj

        return None

    @classmethod
    def _get_nested_segments(
        cls,
        layout: "ifcopenshell.entity_instance"
    ) -> List["ifcopenshell.entity_instance"]:
        """Get nested IfcAlignmentSegment entities."""
        segments = []

        if not hasattr(layout, 'IsNestedBy') or not layout.IsNestedBy:
            return segments

        for rel in layout.IsNestedBy:
            for obj in rel.RelatedObjects:
                if obj.is_a("IfcAlignmentSegment"):
                    segments.append(obj)

        return segments

    @classmethod
    def _segment_to_dict(cls, segment: "ifcopenshell.entity_instance") -> Dict:
        """Convert IFC segment to dictionary."""
        params = segment.DesignParameters
        if not params:
            return {}

        result = {
            'name': segment.Name or 'Unnamed',
            'type': params.PredefinedType,
            'length': params.SegmentLength,
            'start_direction': params.StartDirection,
        }

        if hasattr(params, 'StartPoint') and params.StartPoint:
            coords = params.StartPoint.Coordinates
            result['start_x'] = coords[0]
            result['start_y'] = coords[1]

        if params.PredefinedType == "CIRCULARARC":
            result['radius'] = params.StartRadiusOfCurvature

        return result

    @classmethod
    def _reconstruct_pis(
        cls,
        segments: List["ifcopenshell.entity_instance"]
    ) -> List[Dict]:
        """Reconstruct PI list from IFC segments."""
        pis = []

        for i, segment in enumerate(segments):
            params = segment.DesignParameters
            if not params:
                continue

            if params.PredefinedType == "LINE":
                # Start of tangent
                if i == 0 or len(pis) == 0:
                    coords = params.StartPoint.Coordinates
                    pis.append({
                        'id': len(pis),
                        'x': coords[0],
                        'y': coords[1],
                        'position': SimpleVector(coords[0], coords[1]),
                    })

                # End of tangent (potential PI)
                length = params.SegmentLength
                direction = params.StartDirection
                start_coords = params.StartPoint.Coordinates
                end_x = start_coords[0] + length * math.cos(direction)
                end_y = start_coords[1] + length * math.sin(direction)

                # Check if next segment is a curve
                has_curve = (
                    i + 1 < len(segments) and
                    segments[i + 1].DesignParameters and
                    segments[i + 1].DesignParameters.PredefinedType == "CIRCULARARC"
                )

                if has_curve:
                    # PI is at tangent intersection, not at end of this tangent
                    curve_params = segments[i + 1].DesignParameters
                    curve_length = curve_params.SegmentLength
                    radius = abs(curve_params.StartRadiusOfCurvature)
                    deflection = curve_length / radius
                    tangent_length = radius * math.tan(deflection / 2)

                    pi_x = end_x + tangent_length * math.cos(direction)
                    pi_y = end_y + tangent_length * math.sin(direction)

                    pis.append({
                        'id': len(pis),
                        'x': pi_x,
                        'y': pi_y,
                        'position': SimpleVector(pi_x, pi_y),
                        'curve': {
                            'radius': radius,
                            'arc_length': curve_length,
                        }
                    })
                else:
                    pis.append({
                        'id': len(pis),
                        'x': end_x,
                        'y': end_y,
                        'position': SimpleVector(end_x, end_y),
                    })

        return pis

    @classmethod
    def _get_starting_station(cls, alignment: "ifcopenshell.entity_instance") -> float:
        """Get starting station from alignment referents."""
        # Default starting station
        default_station = 10000.0

        if not hasattr(alignment, 'IsNestedBy'):
            return default_station

        # Look for IfcReferent with starting station
        for rel in alignment.IsNestedBy or []:
            for obj in rel.RelatedObjects:
                if obj.is_a("IfcReferent"):
                    # Check Nests relationship for position
                    if hasattr(obj, 'Nests') and obj.Nests:
                        # Found referent - would need to extract station
                        pass

        return default_station

    @classmethod
    def _get_native_alignment(
        cls,
        alignment_entity: "ifcopenshell.entity_instance"
    ) -> Optional[object]:
        """Get NativeIfcAlignment instance for an entity."""
        from ..core.complete_update_system import get_registered_alignments

        try:
            registered = get_registered_alignments()
            for native in registered:
                if native.alignment == alignment_entity:
                    return native
        except Exception:
            pass

        return None

    @classmethod
    def _update_curve_from_segments(
        cls,
        obj: bpy.types.Object,
        alignment: "ifcopenshell.entity_instance"
    ) -> None:
        """Update Blender curve object from IFC segments."""
        segments = cls.get_horizontal_segments(alignment)
        if not segments:
            return

        # Create or get curve data
        if obj.type != 'CURVE':
            curve_data = bpy.data.curves.new(obj.name, 'CURVE')
            curve_data.dimensions = '3D'
            obj.data = curve_data
        else:
            curve_data = obj.data

        curve_data.splines.clear()

        # Generate points from segments
        points = cls._generate_curve_points(segments)

        if points:
            spline = curve_data.splines.new('POLY')
            spline.points.add(len(points) - 1)
            for i, (x, y, z) in enumerate(points):
                spline.points[i].co = (x, y, z, 1.0)

    @classmethod
    def _generate_curve_points(
        cls,
        segments: List[Dict],
        resolution: int = 10
    ) -> List[Tuple[float, float, float]]:
        """Generate 3D points from segments."""
        points = []

        for seg in segments:
            seg_type = seg.get('type')
            start_x = seg.get('start_x', 0.0)
            start_y = seg.get('start_y', 0.0)
            direction = seg.get('start_direction', 0.0)
            length = seg.get('length', 0.0)

            if seg_type == "LINE":
                if not points:
                    points.append((start_x, start_y, 0.0))
                end_x = start_x + length * math.cos(direction)
                end_y = start_y + length * math.sin(direction)
                points.append((end_x, end_y, 0.0))

            elif seg_type == "CIRCULARARC":
                radius = abs(seg.get('radius', 100.0))
                is_ccw = seg.get('radius', 0) > 0

                # Calculate center
                if is_ccw:
                    center_angle = direction + math.pi / 2
                else:
                    center_angle = direction - math.pi / 2

                center_x = start_x + radius * math.cos(center_angle)
                center_y = start_y + radius * math.sin(center_angle)

                # Arc points
                angle_span = length / radius
                if not is_ccw:
                    angle_span = -angle_span

                num_points = max(4, int(abs(angle_span) * radius / 5))
                start_angle = math.atan2(
                    start_y - center_y,
                    start_x - center_x
                )

                for i in range(num_points + 1):
                    t = i / num_points
                    angle = start_angle + angle_span * t
                    x = center_x + radius * math.cos(angle)
                    y = center_y + radius * math.sin(angle)
                    points.append((x, y, 0.0))

        return points


__all__ = ["Alignment"]