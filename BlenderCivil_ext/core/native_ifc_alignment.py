# ==============================================================================
# BlenderCivil - Civil Engineering Tools for Blender
# Copyright (c) 2024-2025 Michael Yoder / Desert Springs Civil Engineering PLLC
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
Native IFC Alignment (Updated)
PI-driven horizontal alignment - PIs are pure intersection points (NO RADIUS!)
"""

import bpy
import math
import ifcopenshell
import ifcopenshell.guid
from mathutils import Vector


class SimpleVector:
    def __init__(self, x, y=0):
        if isinstance(x, (list, tuple)):
            self.x = float(x[0])
            self.y = float(x[1])
        else:
            self.x = float(x)
            self.y = float(y)
    
    def __sub__(self, other):
        return SimpleVector(self.x - other.x, self.y - other.y)
    
    def __add__(self, other):
        return SimpleVector(self.x + other.x, self.y + other.y)
    
    def __mul__(self, scalar):
        return SimpleVector(self.x * scalar, self.y * scalar)
    
    @property
    def length(self):
        return math.sqrt(self.x**2 + self.y**2)
    
    def normalized(self):
        l = self.length
        if l > 0:
            return SimpleVector(self.x / l, self.y / l)
        return SimpleVector(0, 0)
    
    def dot(self, other):
        return self.x * other.x + self.y * other.y

# ==================== NATIVE IFC ALIGNMENT ====================

class NativeIfcAlignment:
    """Native IFC alignment with PI-driven design - PIs are pure intersection points"""

    def __init__(self, ifc_file, name="New Alignment", alignment_entity=None):
        self.ifc = ifc_file
        self.alignment = None
        self.horizontal = None
        self.pis = []  # PIs have NO radius property!
        self.segments = []  # IfcAlignmentSegment entities (business logic)
        self.curve_segments = []  # IfcCurveSegment entities (geometric representation)
        self.referents = []  # Stationing referents (IfcReferent with Pset_Stationing)

        if alignment_entity:
            # Load from existing IFC alignment
            self.load_from_ifc(alignment_entity)
        else:
            # Create new alignment structure
            self.create_alignment_structure(name)
            # Set default starting station at 10+000 (10000.0 meters)
            self.set_starting_station(10000.0)

        # Register for updates
        self.auto_update = True
        from .complete_update_system import register_alignment
        register_alignment(self)

    @property
    def name(self):
        """Get alignment name from IFC entity."""
        if self.alignment:
            return self.alignment.Name
        return "Unnamed Alignment"

    def __del__(self):
        """Cleanup when alignment is deleted."""
        try:
            from .complete_update_system import unregister_alignment
            unregister_alignment(self)
        except:
            pass

    def create_alignment_structure(self, name):
        """Create IFC alignment hierarchy"""
        self.alignment = self.ifc.create_entity("IfcAlignment",
            GlobalId=ifcopenshell.guid.new(),
            Name=name,
            PredefinedType="USERDEFINED")

        self.horizontal = self.ifc.create_entity("IfcAlignmentHorizontal",
            GlobalId=ifcopenshell.guid.new())

        self.ifc.create_entity("IfcRelNests",
            GlobalId=ifcopenshell.guid.new(),
            Name="AlignmentToHorizontal",
            RelatingObject=self.alignment,
            RelatedObjects=[self.horizontal])

    def load_from_ifc(self, alignment_entity):
        """
        Load alignment from existing IFC entity.
        Reconstructs PIs and segments from saved IFC data.

        Args:
            alignment_entity: IfcAlignment entity from loaded IFC file
        """
        self.alignment = alignment_entity

        # Find horizontal alignment
        for rel in alignment_entity.IsNestedBy or []:
            for obj in rel.RelatedObjects:
                if obj.is_a("IfcAlignmentHorizontal"):
                    self.horizontal = obj
                    break

        if not self.horizontal:
            print(f"[Alignment] Warning: No horizontal alignment found for {alignment_entity.Name}")
            return

        # Load segments
        segments = []
        for rel in self.horizontal.IsNestedBy or []:
            for obj in rel.RelatedObjects:
                if obj.is_a("IfcAlignmentSegment"):
                    segments.append(obj)

        # Sort segments by order (if they have sequence numbers in names)
        # For now, trust the order from IFC file
        self.segments = segments

        # Reconstruct PIs from segments
        self._reconstruct_pis_from_segments()

        # Load stationing referents
        self._load_referents_from_ifc()

        print(f"[Alignment] Loaded '{alignment_entity.Name}': {len(self.pis)} PIs, {len(self.segments)} segments")

    def _reconstruct_pis_from_segments(self):
        """
        Reconstruct PI list from IFC segments.

        CRITICAL: PIs are at the THEORETICAL INTERSECTION of tangent lines,
        not at BC/EC points!

        Strategy:
        - Group segments into pattern: [LINE, (optional CURVE), LINE, ...]
        - Calculate PI as intersection of tangent bearings
        - Attach curve data to interior PIs
        """
        if not self.segments:
            return

        self.pis = []

        # Parse segments into tangent/curve groups
        i = 0
        while i < len(self.segments):
            segment = self.segments[i]
            design_params = segment.DesignParameters

            if not design_params:
                i += 1
                continue

            if design_params.PredefinedType == "LINE":
                # This is a tangent segment
                direction = design_params.StartDirection
                start_point = design_params.StartPoint
                start_pos = SimpleVector(start_point.Coordinates[0], start_point.Coordinates[1])
                length = design_params.SegmentLength

                # Calculate tangent end point
                end_x = start_pos.x + length * math.cos(direction)
                end_y = start_pos.y + length * math.sin(direction)
                end_pos = SimpleVector(end_x, end_y)

                # Add PI at start of first tangent
                if len(self.pis) == 0:
                    pi_data = {
                        'id': 0,
                        'position': start_pos,
                        'ifc_point': self.ifc.create_entity("IfcCartesianPoint",
                            Coordinates=[float(start_pos.x), float(start_pos.y)])
                    }
                    self.pis.append(pi_data)

                # Check if there's a curve after this tangent
                has_curve = False
                if i + 1 < len(self.segments):
                    next_seg = self.segments[i + 1]
                    if next_seg.DesignParameters and next_seg.DesignParameters.PredefinedType == "CIRCULARARC":
                        has_curve = True
                        curve_seg = next_seg
                        curve_params = curve_seg.DesignParameters

                if has_curve and i + 2 < len(self.segments):
                    # We have: tangent1 -> curve -> tangent2
                    # Calculate PI as intersection of tangent1 and tangent2 directions

                    # Get tangent2 direction
                    tangent2_seg = self.segments[i + 2]
                    if tangent2_seg.DesignParameters and tangent2_seg.DesignParameters.PredefinedType == "LINE":
                        t2_dir = tangent2_seg.DesignParameters.StartDirection

                        # Calculate PI from curve geometry
                        # BC = end of tangent1, EC = start of tangent2
                        bc = end_pos  # End of current tangent
                        ec_point = curve_params.StartPoint  # Start of curve
                        # Actually, need to calculate EC from curve
                        curve_length = curve_params.SegmentLength
                        radius = abs(curve_params.StartRadiusOfCurvature)
                        deflection = curve_length / radius

                        # Calculate tangent length: T = R * tan(Δ/2)
                        tangent_length = radius * math.tan(deflection / 2)

                        # PI = BC + T * tangent1_direction
                        t1_unit = SimpleVector(math.cos(direction), math.sin(direction))
                        pi_pos = bc + t1_unit * tangent_length

                        # Add PI with curve data
                        pi_data = {
                            'id': len(self.pis),
                            'position': pi_pos,
                            'ifc_point': self.ifc.create_entity("IfcCartesianPoint",
                                Coordinates=[float(pi_pos.x), float(pi_pos.y)]),
                            'curve': {
                                'radius': radius,
                                'arc_length': curve_length,
                                'deflection': deflection,
                                'bc': bc,
                                'ec': None,  # Calculate later
                                'start_direction': direction,
                                'turn_direction': 'LEFT' if curve_params.StartRadiusOfCurvature > 0 else 'RIGHT'
                            }
                        }
                        self.pis.append(pi_data)

                        # Skip the curve and move to tangent2
                        i += 2
                    else:
                        # No tangent2, just add end of tangent1 as PI
                        pi_data = {
                            'id': len(self.pis),
                            'position': end_pos,
                            'ifc_point': self.ifc.create_entity("IfcCartesianPoint",
                                Coordinates=[float(end_x), float(end_y)])
                        }
                        self.pis.append(pi_data)
                        i += 1
                else:
                    # No curve, just add end of tangent as PI
                    pi_data = {
                        'id': len(self.pis),
                        'position': end_pos,
                        'ifc_point': self.ifc.create_entity("IfcCartesianPoint",
                            Coordinates=[float(end_x), float(end_y)])
                    }
                    self.pis.append(pi_data)
                    i += 1

            elif design_params.PredefinedType == "CIRCULARARC":
                # Standalone curve without being detected by tangent logic
                # This shouldn't happen in our workflow
                print(f"[Alignment] Warning: Standalone curve segment found at index {i}")
                i += 1
            else:
                i += 1

        print(f"[Alignment] Reconstructed {len(self.pis)} PIs from {len(self.segments)} segments")

    def add_pi(self, x, y):
        """Add PI to alignment - Pure intersection point, NO RADIUS!"""
        pi_data = {
            'id': len(self.pis),
            'position': SimpleVector(x, y),
            # NO RADIUS PROPERTY!
            'ifc_point': self.ifc.create_entity("IfcCartesianPoint",
                Coordinates=[float(x), float(y)])
        }
        
        self.pis.append(pi_data)
        self.regenerate_segments()
        return pi_data
    
    def regenerate_segments(self):
        """Regenerate IFC tangent segments from PIs
        
        Creates straight line segments between consecutive PIs.
        Curves are added separately via insert_curve_at_pi().
        """
        self.segments = []
        
        if len(self.pis) < 2:
            return
        
        # Create tangent lines between consecutive PIs
        for i in range(len(self.pis) - 1):
            curr_pi = self.pis[i]
            next_pi = self.pis[i + 1]
            
            # Simple tangent from this PI to next PI
            tangent_seg = self._create_tangent_segment(
                curr_pi['position'],
                next_pi['position']
            )
            self.segments.append(tangent_seg)

        self._update_ifc_nesting()
        self._build_composite_curve_representation()

        print(f"[Alignment] Regenerated {len(self.segments)} tangent segments from {len(self.pis)} PIs")
    
    def _create_tangent_segment(self, start_pos, end_pos):
        """Create IFC tangent segment with both business logic and geometric representation"""
        from .ifc_geometry_builders import (
            create_line_parent_curve,
            create_curve_segment as create_ifc_curve_segment
        )

        direction = end_pos - start_pos
        length = direction.length
        angle = math.atan2(direction.y, direction.x)

        # Business logic layer (design parameters)
        design_params = self.ifc.create_entity(
            "IfcAlignmentHorizontalSegment",
            StartPoint=self.ifc.create_entity("IfcCartesianPoint",
                Coordinates=[float(start_pos.x), float(start_pos.y)]),
            StartDirection=float(angle),
            StartRadiusOfCurvature=0.0,
            EndRadiusOfCurvature=0.0,
            SegmentLength=float(length),
            PredefinedType="LINE"
        )

        # Geometric representation layer
        # Create parent line curve
        parent_curve = create_line_parent_curve(
            self.ifc,
            float(start_pos.x), float(start_pos.y),
            float(end_pos.x), float(end_pos.y)
        )

        # Create curve segment wrapper
        # Placement is at origin (0,0) since line defines its own endpoints
        placement = self.ifc.create_entity("IfcAxis2Placement2D",
            Location=self.ifc.create_entity("IfcCartesianPoint", Coordinates=[0.0, 0.0])
        )

        curve_geometry = create_ifc_curve_segment(
            self.ifc,
            parent_curve,
            placement,
            0.0,  # SegmentStart
            float(length)  # SegmentLength
        )

        # Store curve geometry separately (not in IfcAlignmentSegment)
        self.curve_segments.append(curve_geometry)

        # Create alignment segment with only business logic (no CurveGeometry attribute in IFC4X3_ADD2)
        segment = self.ifc.create_entity("IfcAlignmentSegment",
            GlobalId=ifcopenshell.guid.new(),
            Name=f"Tangent_{len(self.segments)}",
            DesignParameters=design_params
        )
        return segment
    
    def insert_curve_at_pi(self, pi_index, radius):
        """Insert curve at specified PI with given radius
        
        This is called by the curve tool to add curves between tangents.
        
        Args:
            pi_index: Index of PI where curve should be inserted
            radius: Curve radius in meters
        
        Returns:
            Curve data dictionary
        """
        if pi_index <= 0 or pi_index >= len(self.pis) - 1:
            print(f"[Alignment] Cannot insert curve at PI {pi_index} (must be interior PI)")
            return None
        
        # Get the three PIs involved
        prev_pi = self.pis[pi_index - 1]
        curr_pi = self.pis[pi_index]
        next_pi = self.pis[pi_index + 1]
        
        # Calculate curve geometry
        curve_data = self._calculate_curve(
            prev_pi['position'],
            curr_pi['position'],
            next_pi['position'],
            radius
        )
        
        if not curve_data:
            print(f"[Alignment] Could not calculate curve at PI {pi_index}")
            return None
        
        # Store curve data with PI
        curr_pi['curve'] = curve_data
        
        # Regenerate all segments (now with curve consideration)
        self.regenerate_segments_with_curves()
        
        return curve_data
    
    def regenerate_segments_with_curves(self):
        """Regenerate segments considering curves at PIs

        This creates: Tangent → Curve → Tangent → Curve → Tangent
        where curves exist at PIs that have curve data.

        CRITICAL: Recalculates curve geometry from current PI positions!
        """
        self.segments = []

        if len(self.pis) < 2:
            return

        # STEP 1: Recalculate all curve geometries from current PI positions
        for i in range(len(self.pis)):
            pi = self.pis[i]

            # If this PI has a curve, recalculate its geometry
            if 'curve' in pi:
                # Need prev and next PI
                if i > 0 and i < len(self.pis) - 1:
                    prev_pi = self.pis[i - 1]
                    next_pi = self.pis[i + 1]

                    # Recalculate curve geometry with current PI positions
                    radius = pi['curve']['radius']  # Keep the original radius
                    updated_curve = self._calculate_curve(
                        prev_pi['position'],
                        pi['position'],
                        next_pi['position'],
                        radius
                    )

                    if updated_curve:
                        pi['curve'] = updated_curve
                    else:
                        # Curve is no longer valid (e.g., PIs became collinear)
                        del pi['curve']
                        print(f"[Alignment] Removed invalid curve at PI {i}")

        # STEP 2: Generate segments using updated curve data
        for i in range(len(self.pis) - 1):
            curr_pi = self.pis[i]
            next_pi = self.pis[i + 1]

            # Determine tangent start
            # If curr_pi has a curve, the previous tangent ended at BC,
            # and the curve went from BC to EC, so this tangent starts at EC
            if 'curve' in curr_pi:
                start_pos = curr_pi['curve']['ec']
            else:
                start_pos = curr_pi['position']

            # Determine tangent end
            # If next_pi has a curve, this tangent should end at BC (before the PI)
            if 'curve' in next_pi:
                end_pos = next_pi['curve']['bc']
            else:
                end_pos = next_pi['position']

            # Create tangent segment
            tangent = self._create_tangent_segment(start_pos, end_pos)
            self.segments.append(tangent)

            # Add curve at next PI if it exists
            # The curve goes from BC to EC around next_pi
            if 'curve' in next_pi:
                curve = self._create_curve_segment(next_pi['curve'], next_pi['id'])
                self.segments.append(curve)

        self._update_ifc_nesting()
        self._build_composite_curve_representation()

        print(f"[Alignment] Regenerated {len(self.segments)} segments with curves")
    
    def _create_curve_segment(self, curve_data, pi_id=None):
        """Create IFC curve segment with SIGNED radius for turn direction and geometric representation"""
        from .ifc_geometry_builders import (
            create_circle_parent_curve,
            create_curve_segment as create_ifc_curve_segment,
            create_axis2placement_2d
        )

        name = f"Curve_{pi_id}" if pi_id is not None else f"Curve_{len(self.segments)}"

        # Use signed radius based on deflection angle
        signed_radius = curve_data['radius'] if curve_data['deflection'] > 0 else -curve_data['radius']

        # Business logic layer (design parameters)
        design_params = self.ifc.create_entity(
            "IfcAlignmentHorizontalSegment",
            StartPoint=self.ifc.create_entity("IfcCartesianPoint",
                Coordinates=[float(curve_data['bc'].x), float(curve_data['bc'].y)]),
            StartDirection=float(curve_data['start_direction']),
            StartRadiusOfCurvature=float(signed_radius),
            EndRadiusOfCurvature=float(signed_radius),
            SegmentLength=float(curve_data['arc_length']),
            PredefinedType="CIRCULARARC"
        )

        # Geometric representation layer
        # Calculate circle center from BC point and start direction
        radius = curve_data['radius']
        bc = curve_data['bc']
        start_dir = curve_data['start_direction']
        turn_dir = curve_data['turn_direction']

        # Center is perpendicular to start direction
        # LEFT turn: center is 90° CCW from start direction
        # RIGHT turn: center is 90° CW from start direction
        if turn_dir == 'LEFT':
            center_angle = start_dir + math.pi / 2
        else:
            center_angle = start_dir - math.pi / 2

        center_x = bc.x + radius * math.cos(center_angle)
        center_y = bc.y + radius * math.sin(center_angle)

        # Create parent circle curve
        parent_curve = create_circle_parent_curve(
            self.ifc,
            center_x,
            center_y,
            radius,
            start_dir  # Circle orientation
        )

        # Create placement at BC (start of curve)
        placement = create_axis2placement_2d(
            self.ifc,
            float(bc.x),
            float(bc.y),
            float(start_dir)
        )

        # Create curve segment
        # For a circle, SegmentStart is the starting angle relative to circle's X-axis
        # We'll use 0.0 and let the placement handle positioning
        curve_geometry = create_ifc_curve_segment(
            self.ifc,
            parent_curve,
            placement,
            0.0,  # SegmentStart (angle on circle)
            float(curve_data['arc_length']),  # SegmentLength
            "CONTSAMEGRADIENT"  # G1 continuity for smooth curves
        )

        # Store curve geometry separately (not in IfcAlignmentSegment)
        self.curve_segments.append(curve_geometry)

        # Create alignment segment with only business logic (no CurveGeometry attribute in IFC4X3_ADD2)
        segment = self.ifc.create_entity("IfcAlignmentSegment",
            GlobalId=ifcopenshell.guid.new(),
            Name=name,
            DesignParameters=design_params
        )
        return segment
    
    def _build_composite_curve_representation(self):
        """Build IfcCompositeCurve and shape representation from all segments

        This creates the geometric representation layer:
        - Collects CurveGeometry (IfcCurveSegment) from all segments
        - Wraps them in IfcCompositeCurve
        - Creates IfcAlignmentCurve wrapper
        - Creates IfcShapeRepresentation
        - Attaches to IfcAlignment via IfcProductDefinitionShape

        CRITICAL: Removes old representation first to avoid duplicates!
        """
        from .ifc_geometry_builders import (
            create_composite_curve,
            create_alignment_curve,
            create_shape_representation,
            create_product_definition_shape
        )
        from .native_ifc_manager import NativeIfcManager

        if not self.segments:
            print("[Alignment] No segments to build composite curve from")
            return None

        # STEP 1: Remove old representation to avoid duplicates
        if hasattr(self.alignment, 'Representation') and self.alignment.Representation:
            old_rep = self.alignment.Representation
            if old_rep.is_a("IfcProductDefinitionShape"):
                # Remove all shape representations
                for shape_rep in old_rep.Representations:
                    if shape_rep.is_a("IfcShapeRepresentation"):
                        # Remove the items (IfcAlignmentCurve, etc.)
                        for item in shape_rep.Items:
                            if item.is_a("IfcAlignmentCurve"):
                                # Remove the curve (IfcCompositeCurve)
                                if hasattr(item, 'Curve') and item.Curve:
                                    # Don't remove the segments - they're owned by IfcAlignmentSegment
                                    self.ifc.remove(item.Curve)
                                self.ifc.remove(item)
                        self.ifc.remove(shape_rep)
                self.ifc.remove(old_rep)
            # Clear the reference
            self.alignment.Representation = None

        # STEP 2: Use the stored curve segments (IfcCurveSegment entities)
        # These are stored separately because IfcAlignmentSegment doesn't have CurveGeometry in IFC4X3_ADD2
        if not self.curve_segments:
            print("[Alignment] No curve segments with geometry found")
            return None

        curve_segments = self.curve_segments

        # Create IfcCompositeCurve from all curve segments
        composite_curve = create_composite_curve(self.ifc, curve_segments, self_intersect=False)
        print(f"[Alignment] Created IfcCompositeCurve with {len(curve_segments)} segments")

        # Wrap in IfcAlignmentCurve
        alignment_curve = create_alignment_curve(self.ifc, composite_curve, "Axis")

        # Get geometric representation context
        # This is required for shape representation
        context = NativeIfcManager.get_geometric_context()
        if not context:
            print("[Alignment] Warning: No geometric representation context found")
            # Try to get from project
            project = self.ifc.by_type("IfcProject")
            if project:
                reps = project[0].RepresentationContexts
                if reps:
                    context = reps[0]

        if not context:
            print("[Alignment] Cannot create shape representation without context")
            return composite_curve

        # Create shape representation
        shape_rep = create_shape_representation(
            self.ifc,
            context,
            [alignment_curve],
            representation_type="Curve3D",
            representation_identifier="Axis"
        )

        # Create product definition shape
        product_shape = create_product_definition_shape(self.ifc, [shape_rep])

        # Attach to alignment
        # NOTE: IfcAlignment can have Representation according to IFC 4.3
        self.alignment.Representation = product_shape

        print(f"[Alignment] Attached geometric representation to {self.alignment.Name}")

        return composite_curve

    def _calculate_curve(self, prev_pi, curr_pi, next_pi, radius):
        """Calculate curve geometry from PIs with SIGNED deflection angle"""
        t1 = (curr_pi - prev_pi).normalized()
        t2 = (next_pi - curr_pi).normalized()
        
        # Calculate SIGNED deflection angle
        angle1 = math.atan2(t1.y, t1.x)
        angle2 = math.atan2(t2.y, t2.x)
        
        deflection = angle2 - angle1
        
        # Normalize to [-π, π]
        if deflection > math.pi:
            deflection -= 2 * math.pi
        elif deflection < -math.pi:
            deflection += 2 * math.pi
        
        # Check if deflection is too small
        if abs(deflection) < 0.001:
            return None
        
        # Calculate curve geometry
        tangent_length = radius * math.tan(abs(deflection) / 2)
        bc = curr_pi - t1 * tangent_length
        ec = curr_pi + t2 * tangent_length
        arc_length = radius * abs(deflection)
        
        return {
            'bc': bc,
            'ec': ec,
            'radius': radius,
            'arc_length': arc_length,
            'deflection': deflection,
            'start_direction': angle1,
            'turn_direction': 'LEFT' if deflection > 0 else 'RIGHT'
        }
    
    def _update_ifc_nesting(self):
        """Update IFC nesting relationships

        CRITICAL: This method removes old segments AND their geometry before nesting new ones.
        This prevents duplicate entities and maintains clean IFC structure.
        """
        # STEP 1: Clean up old curve geometry entities (stored separately)
        for curve_seg in self.curve_segments:
            try:
                # Remove ParentCurve (IfcLine or IfcCircle)
                if hasattr(curve_seg, 'ParentCurve') and curve_seg.ParentCurve:
                    parent = curve_seg.ParentCurve
                    # Remove position placement if it exists
                    if hasattr(parent, 'Position') and parent.Position:
                        pos = parent.Position
                        if hasattr(pos, 'Location') and pos.Location:
                            self.ifc.remove(pos.Location)
                        if hasattr(pos, 'RefDirection') and pos.RefDirection:
                            self.ifc.remove(pos.RefDirection)
                        self.ifc.remove(pos)
                    self.ifc.remove(parent)

                # Remove placement if it exists
                if hasattr(curve_seg, 'Placement') and curve_seg.Placement:
                    place = curve_seg.Placement
                    if hasattr(place, 'Location') and place.Location:
                        self.ifc.remove(place.Location)
                    if hasattr(place, 'RefDirection') and place.RefDirection:
                        self.ifc.remove(place.RefDirection)
                    self.ifc.remove(place)

                # Remove the curve segment itself
                # Note: IfcParameterValue (SegmentStart/Length) are simple types, not entities
                # They are automatically cleaned up when the parent is removed
                self.ifc.remove(curve_seg)
            except RuntimeError as e:
                # Entity might have already been removed - ignore
                print(f"[Alignment] Warning: Could not remove curve segment: {e}")

        # Clear the curve segments list
        if self.curve_segments:
            print(f"[Alignment] Removed {len(self.curve_segments)} old curve geometry entities")
        self.curve_segments = []

        # STEP 2: Remove old segment entities and nesting relationships
        old_segments = []
        for rel in self.horizontal.IsNestedBy or []:
            if rel.is_a("IfcRelNests"):
                # Collect old segments
                for obj in rel.RelatedObjects:
                    if obj.is_a("IfcAlignmentSegment"):
                        old_segments.append(obj)
                # Remove the nesting relationship
                self.ifc.remove(rel)

        # STEP 3: Remove old segment entities (business logic only)
        for segment in old_segments:
            try:
                # Remove DesignParameters
                if hasattr(segment, 'DesignParameters') and segment.DesignParameters:
                    params = segment.DesignParameters
                    if hasattr(params, 'StartPoint') and params.StartPoint:
                        self.ifc.remove(params.StartPoint)
                    self.ifc.remove(params)

                # Finally, remove the segment itself
                self.ifc.remove(segment)
            except RuntimeError as e:
                # Entity might have already been removed - ignore
                print(f"[Alignment] Warning: Could not remove segment: {e}")

        if old_segments:
            print(f"[Alignment] Removed {len(old_segments)} old segments")

        # STEP 4: Create new nesting with current segments
        if self.segments:
            self.ifc.create_entity("IfcRelNests",
                GlobalId=ifcopenshell.guid.new(),
                Name="HorizontalToSegments",
                RelatingObject=self.horizontal,
                RelatedObjects=self.segments
            )

    # ============================================================================
    # STATIONING METHODS (IFC Referents with Pset_Stationing)
    # ============================================================================

    def set_starting_station(self, station_value):
        """
        Set the starting station of the alignment.

        Creates an IfcReferent at distance_along = 0.0 with the specified station value.
        Per IFC 4.3 spec, the first referent in the ordered list defines the starting station.

        Args:
            station_value: Station value at the start of the alignment (e.g., 0.0 for 0+00)
        """
        # Remove existing starting station referent if it exists
        self.referents = [r for r in self.referents if r['distance_along'] != 0.0]

        # Add new starting station at distance 0
        referent_data = {
            'distance_along': 0.0,
            'station': float(station_value),
            'incoming_station': None,  # No incoming station for start
            'description': 'Starting Station',
            'ifc_referent': None  # Will be created when saving to IFC
        }

        self.referents.insert(0, referent_data)  # Insert at beginning (ordered list)
        self._sort_referents()
        self._update_referent_entities()

        print(f"[Alignment] Set starting station to {station_value:.2f}")

    def add_station_equation(self, distance_along, incoming_station, outgoing_station, description="Station Equation"):
        """
        Add a station equation (chainage break).

        Station equations are used when station values need to jump (e.g., for route continuity).

        Args:
            distance_along: Distance along alignment where equation occurs (meters)
            incoming_station: Station value approaching this point
            outgoing_station: Station value leaving this point
            description: Optional description of the equation

        Example:
            # At 500m along alignment, station jumps from 5+00 to 10+00
            alignment.add_station_equation(500.0, 500.0, 1000.0, "Route Continuation")
        """
        referent_data = {
            'distance_along': float(distance_along),
            'station': float(outgoing_station),
            'incoming_station': float(incoming_station),
            'description': description,
            'ifc_referent': None
        }

        # Remove any existing equation at this distance
        self.referents = [r for r in self.referents if r['distance_along'] != distance_along]

        self.referents.append(referent_data)
        self._sort_referents()
        self._update_referent_entities()

        print(f"[Alignment] Added station equation at {distance_along:.2f}m: {incoming_station:.2f} → {outgoing_station:.2f}")

    def remove_station_equation(self, distance_along):
        """
        Remove a station equation at the specified distance.

        Args:
            distance_along: Distance where the equation exists

        Returns:
            True if equation was removed, False if not found
        """
        initial_count = len(self.referents)

        # Don't remove starting station
        self.referents = [r for r in self.referents if
                         r['distance_along'] != distance_along or r['distance_along'] == 0.0]

        removed = len(self.referents) < initial_count

        if removed:
            self._update_referent_entities()
            print(f"[Alignment] Removed station equation at {distance_along:.2f}m")

        return removed

    def get_station_at_distance(self, distance_along):
        """
        Calculate station value at a given distance along the alignment.

        Accounts for station equations.

        Args:
            distance_along: Distance along alignment (meters)

        Returns:
            Station value at that distance
        """
        if not self.referents:
            # No stationing defined, return distance as station
            return distance_along

        # Find the applicable referent (last one before or at this distance)
        applicable_referent = None
        for ref in reversed(self.referents):
            if ref['distance_along'] <= distance_along:
                applicable_referent = ref
                break

        if not applicable_referent:
            # Before first referent, extrapolate backwards
            first_ref = self.referents[0]
            delta_distance = distance_along - first_ref['distance_along']
            return first_ref['station'] + delta_distance

        # Calculate station from applicable referent
        delta_distance = distance_along - applicable_referent['distance_along']
        station = applicable_referent['station'] + delta_distance

        return station

    def get_distance_at_station(self, station_value):
        """
        Calculate distance along alignment at a given station value.

        Accounts for station equations (inverse of get_station_at_distance).

        Args:
            station_value: Station value to find

        Returns:
            Distance along alignment (meters), or None if station not in range
        """
        if not self.referents:
            # No stationing defined, station equals distance
            return station_value

        # Find which segment this station falls in
        for i in range(len(self.referents)):
            current_ref = self.referents[i]

            # Check if this is the last referent
            if i == len(self.referents) - 1:
                # Beyond last referent, extrapolate
                if station_value >= current_ref['station']:
                    delta_station = station_value - current_ref['station']
                    return current_ref['distance_along'] + delta_station
            else:
                next_ref = self.referents[i + 1]
                next_station = next_ref.get('incoming_station', next_ref['station'])

                # Check if station is in this segment
                if current_ref['station'] <= station_value < next_station:
                    delta_station = station_value - current_ref['station']
                    return current_ref['distance_along'] + delta_station

        # Station before first referent
        first_ref = self.referents[0]
        if station_value < first_ref['station']:
            delta_station = station_value - first_ref['station']
            return first_ref['distance_along'] + delta_station

        return None

    def _sort_referents(self):
        """Sort referents by distance_along (required by IFC spec)"""
        self.referents.sort(key=lambda r: r['distance_along'])

    def _update_referent_entities(self):
        """
        Create/update IFC IfcReferent entities with Pset_Stationing.

        Per IFC 4.3 spec:
        - Referents are nested to IfcAlignment via IfcRelNests
        - Use separate IfcRelNests from alignment layout
        - PredefinedType = STATION
        - Station values stored in Pset_Stationing
        """
        if not self.alignment:
            return

        # Remove old referent entities and their relationships
        old_referents = []
        for rel in self.alignment.IsNestedBy or []:
            if rel.Name == "AlignmentToReferents":
                old_referents.extend(rel.RelatedObjects)
                self.ifc.remove(rel)

        for ref in old_referents:
            if ref.is_a("IfcReferent"):
                # Remove property sets
                for rel_def in ref.IsDefinedBy or []:
                    if rel_def.is_a("IfcRelDefinesByProperties"):
                        self.ifc.remove(rel_def.RelatingPropertyDefinition)
                        self.ifc.remove(rel_def)
                self.ifc.remove(ref)

        # Get the basis curve (IfcCompositeCurve) from alignment representation
        basis_curve = self._get_basis_curve()

        # Create new referent entities
        referent_entities = []
        for ref_data in self.referents:
            # Create IfcReferent
            referent = self.ifc.create_entity("IfcReferent",
                GlobalId=ifcopenshell.guid.new(),
                Name=ref_data['description'],
                PredefinedType="STATION"
            )

            # Create IfcLinearPlacement if we have a basis curve
            if basis_curve:
                # Create IfcPointByDistanceExpression
                point_by_distance = self.ifc.create_entity("IfcPointByDistanceExpression",
                    DistanceAlong=float(ref_data['distance_along']),
                    OffsetLateral=0.0,
                    OffsetVertical=0.0,
                    OffsetLongitudinal=0.0,
                    BasisCurve=basis_curve
                )

                # Create IfcAxis2PlacementLinear
                axis_placement_linear = self.ifc.create_entity("IfcAxis2PlacementLinear",
                    Location=point_by_distance,
                    Axis=None,  # Default perpendicular to curve
                    RefDirection=None  # Default tangent to curve
                )

                # Create IfcLinearPlacement
                linear_placement = self.ifc.create_entity("IfcLinearPlacement",
                    PlacementRelTo=None,  # Relative to alignment start
                    RelativePlacement=axis_placement_linear
                )

                # Assign placement to referent
                referent.ObjectPlacement = linear_placement

            # Create Pset_Stationing
            station_props = []

            # Station property (required)
            station_props.append(
                self.ifc.create_entity("IfcPropertySingleValue",
                    Name="Station",
                    NominalValue=self.ifc.create_entity("IfcLengthMeasure", ref_data['station'])
                )
            )

            # IncomingStation property (for station equations only)
            if ref_data['incoming_station'] is not None:
                station_props.append(
                    self.ifc.create_entity("IfcPropertySingleValue",
                        Name="IncomingStation",
                        NominalValue=self.ifc.create_entity("IfcLengthMeasure", ref_data['incoming_station'])
                    )
                )

            # DistanceAlong property (for reference)
            station_props.append(
                self.ifc.create_entity("IfcPropertySingleValue",
                    Name="DistanceAlong",
                    NominalValue=self.ifc.create_entity("IfcLengthMeasure", ref_data['distance_along'])
                )
            )

            # IncrementOrder property (True = increasing stations along alignment)
            station_props.append(
                self.ifc.create_entity("IfcPropertySingleValue",
                    Name="IncrementOrder",
                    NominalValue=self.ifc.create_entity("IfcBoolean", True)
                )
            )

            # Create property set
            pset = self.ifc.create_entity("IfcPropertySet",
                GlobalId=ifcopenshell.guid.new(),
                Name="Pset_Stationing",
                HasProperties=station_props
            )

            # Link property set to referent
            self.ifc.create_entity("IfcRelDefinesByProperties",
                GlobalId=ifcopenshell.guid.new(),
                RelatedObjects=[referent],
                RelatingPropertyDefinition=pset
            )

            referent_entities.append(referent)
            ref_data['ifc_referent'] = referent

        # Create IfcRelNests for referents (separate from layout nesting)
        if referent_entities:
            self.ifc.create_entity("IfcRelNests",
                GlobalId=ifcopenshell.guid.new(),
                Name="AlignmentToReferents",
                RelatingObject=self.alignment,
                RelatedObjects=referent_entities
            )

            print(f"[Alignment] Created {len(referent_entities)} IFC referents with stationing")

    def _get_basis_curve(self):
        """
        Get the basis curve (IfcCompositeCurve) from alignment representation.

        Returns:
            IfcCompositeCurve if found, None otherwise
        """
        if not self.alignment:
            return None

        # Check if alignment has a representation
        if not hasattr(self.alignment, 'Representation') or not self.alignment.Representation:
            return None

        # Navigate: IfcProductDefinitionShape → IfcShapeRepresentation → Items → IfcAlignmentCurve → Curve
        product_shape = self.alignment.Representation
        if not product_shape.is_a("IfcProductDefinitionShape"):
            return None

        for representation in product_shape.Representations:
            if representation.is_a("IfcShapeRepresentation"):
                for item in representation.Items:
                    if item.is_a("IfcAlignmentCurve"):
                        curve = item.Curve
                        # Could be IfcCompositeCurve or IfcGradientCurve
                        if curve.is_a("IfcCompositeCurve"):
                            return curve
                        elif curve.is_a("IfcGradientCurve"):
                            # For gradient curves, get the base curve (horizontal)
                            return curve.BaseCurve

        return None

    def _load_referents_from_ifc(self):
        """
        Load stationing referents from existing IFC alignment.

        Called during load_from_ifc() to reconstruct stationing from saved IFC.
        """
        if not self.alignment:
            return

        self.referents = []

        # Find referents nested to this alignment
        for rel in self.alignment.IsNestedBy or []:
            if rel.Name == "AlignmentToReferents":
                for obj in rel.RelatedObjects:
                    if obj.is_a("IfcReferent") and obj.PredefinedType == "STATION":
                        # Extract stationing data from Pset_Stationing
                        station_value = None
                        incoming_station = None
                        distance_along = 0.0

                        for rel_def in obj.IsDefinedBy or []:
                            if rel_def.is_a("IfcRelDefinesByProperties"):
                                pset = rel_def.RelatingPropertyDefinition
                                if pset.is_a("IfcPropertySet") and pset.Name == "Pset_Stationing":
                                    for prop in pset.HasProperties:
                                        if prop.Name == "Station":
                                            station_value = float(prop.NominalValue.wrappedValue)
                                        elif prop.Name == "IncomingStation":
                                            incoming_station = float(prop.NominalValue.wrappedValue)
                                        elif prop.Name == "DistanceAlong":
                                            distance_along = float(prop.NominalValue.wrappedValue)

                        if station_value is not None:
                            referent_data = {
                                'distance_along': distance_along,
                                'station': station_value,
                                'incoming_station': incoming_station,
                                'description': obj.Name or "Station Referent",
                                'ifc_referent': obj
                            }
                            self.referents.append(referent_data)

        self._sort_referents()

        if self.referents:
            print(f"[Alignment] Loaded {len(self.referents)} stationing referents from IFC")
        else:
            # No referents found, set default starting station
            print(f"[Alignment] No stationing referents found, setting default 10+000")
            self.set_starting_station(10000.0)
