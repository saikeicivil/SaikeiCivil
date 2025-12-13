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
Saikei Civil - Native IFC Corridor Modeling System
Sprint 5 Day 2 - Core Architecture & Implementation

This module provides corridor modeling using IFC 4.3 IfcSectionedSolidHorizontal.
Sweeps cross-sections along 3D alignments to create complete road corridors.

Author: Saikei Civil Team
Date: November 4, 2025
Sprint: 5 of 16 - Corridor Modeling
Day: 2 of 5 - Architecture & Core

Key Features:
- Generate corridors from Alignment3D + CrossSectionAssembly
- Intelligent station management (curves, transitions, critical points)
- Native IFC 4.3 IfcSectionedSolidHorizontal creation
- Material associations via IfcMaterialProfileSet
- Parametric cross-section application
- Complete BIM-ready 3D solids

IFC Entities Created:
- IfcSectionedSolidHorizontal (main corridor solid)
- IfcAlignmentCurve (directrix)
- IfcCompositeProfileDef (cross-sections)
- IfcAxis2PlacementLinear (cross-section positions)
- IfcMaterialProfileSet (material associations)

Usage Example:
    >>> # Create corridor from alignment and cross-section
    >>> alignment_3d = Alignment3D(h_align, v_align)
    >>> assembly = RoadAssembly.create_two_lane_rural()
    >>> 
    >>> # Generate corridor
    >>> modeler = CorridorModeler(alignment_3d, assembly)
    >>> corridor_solid = modeler.create_corridor_solid(interval=10.0)
    >>> 
    >>> # Export to IFC
    >>> ifc_file = modeler.export_to_ifc()
    >>> ifc_file.write("corridor.ifc")
"""

import ifcopenshell
import ifcopenshell.guid
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
import math
from .logging_config import get_logger

logger = get_logger(__name__)


# =============================================================================
# Point Tags for IFC Corridor Interpolation
# =============================================================================

class PointTags:
    """
    Standard point tags for IFC corridor interpolation.

    Tags are CRITICAL for IfcSectionedSolidHorizontal - the IFC viewer/processor
    interpolates between consecutive profiles by matching points with the same tag.
    Points without matching tags in consecutive profiles create undefined geometry.
    """

    # Centerline
    CENTERLINE = "CL"
    CROWN = "CR"

    # Travel lanes
    EDGE_TRAVELED_WAY_LEFT = "ETW_L"
    EDGE_TRAVELED_WAY_RIGHT = "ETW_R"

    # Pavement edges
    EDGE_PAVEMENT_LEFT = "EPS_L"
    EDGE_PAVEMENT_RIGHT = "EPS_R"

    # Curb points
    FLOWLINE_LEFT = "FL_L"
    FLOWLINE_RIGHT = "FL_R"
    BACK_CURB_LEFT = "BC_L"
    BACK_CURB_RIGHT = "BC_R"
    TOP_CURB_LEFT = "TC_L"
    TOP_CURB_RIGHT = "TC_R"

    # Shoulder
    HINGE_LEFT = "HG_L"
    HINGE_RIGHT = "HG_R"
    SHOULDER_LEFT = "SH_L"
    SHOULDER_RIGHT = "SH_R"

    # Daylight/grading
    DAYLIGHT_LEFT = "DL_L"
    DAYLIGHT_RIGHT = "DL_R"

    # Subgrade
    DATUM_LEFT = "DAT_L"
    DATUM_RIGHT = "DAT_R"

    # Bottom points for closed profiles
    BOTTOM_LEFT = "BTM_L"
    BOTTOM_RIGHT = "BTM_R"


def create_tagged_cross_section_profile(
    ifc_file: Any,
    points: List[Tuple[float, float]],
    tags: List[str],
    station: float,
    profile_name: Optional[str] = None
) -> Any:
    """
    Create an IFC cross-section profile with tagged points for interpolation.

    This creates an IfcArbitraryClosedProfileDef with IfcIndexedPolyCurve
    containing tagged points. Tags are ESSENTIAL for proper interpolation
    between cross-sections in IfcSectionedSolidHorizontal.

    Args:
        ifc_file: IFC file object
        points: List of (offset, elevation) tuples defining the profile
        tags: List of point tags (same length as points)
        station: Station value for naming
        profile_name: Optional profile name override

    Returns:
        IfcArbitraryClosedProfileDef entity

    Raises:
        ValueError: If points and tags have different lengths
    """
    if len(points) != len(tags):
        raise ValueError(f"Points ({len(points)}) and tags ({len(tags)}) must have same length")

    if len(points) < 3:
        raise ValueError("Profile must have at least 3 points")

    # Create point list with tags
    # CoordList is a list of 2D coordinates (offset, elevation)
    point_list = ifc_file.create_entity(
        "IfcCartesianPointList2D",
        CoordList=points,
        TagList=tags
    )

    # Create indexed polycurve - line segments connecting all points
    # IFC indices are 1-based
    # Note: For IfcIndexedPolyCurve, Segments is optional
    # If omitted, points are connected in sequence
    curve = ifc_file.create_entity(
        "IfcIndexedPolyCurve",
        Points=point_list,
        Segments=None,  # Sequential connection
        SelfIntersect=False
    )

    # Create the profile definition
    name = profile_name or f"Road Section at Sta {station:.2f}"
    profile = ifc_file.create_entity(
        "IfcArbitraryClosedProfileDef",
        ProfileType="AREA",
        ProfileName=name,
        OuterCurve=curve
    )

    return profile


def create_profile_from_assembly(
    ifc_file: Any,
    assembly: Any,
    station: float,
    pavement_thickness: float = 0.3
) -> Any:
    """
    Create a closed, tagged cross-section profile from an assembly wrapper.

    This converts the assembly's component data into a closed polygon suitable
    for IfcSectionedSolidHorizontal. Points are tagged for proper interpolation.

    Args:
        ifc_file: IFC file object
        assembly: AssemblyWrapper instance with component data
        station: Station value for naming
        pavement_thickness: Total thickness of pavement layers (meters)

    Returns:
        IfcArbitraryClosedProfileDef entity with tagged points
    """
    from .corridor import AssemblyWrapper, ComponentData

    # Build the cross-section polygon from components
    # Start from left-most component, go to right-most, then bottom back
    top_points = []
    top_tags = []

    # Separate left and right components
    left_components = []
    right_components = []

    for comp in assembly.components:
        if comp.offset < 0:
            left_components.append(comp)
        else:
            right_components.append(comp)

    # Sort: left from most negative to least, right from least to most
    left_components.sort(key=lambda c: c.offset)
    right_components.sort(key=lambda c: c.offset)

    # Counter for unique tags per component type
    tag_counter = {}

    def get_tag(comp_type: str, side: str, position: str) -> str:
        """Generate unique tag for a point."""
        key = f"{side}_{comp_type}_{position}"
        if key not in tag_counter:
            tag_counter[key] = 0
        tag_counter[key] += 1
        count = tag_counter[key]
        if count == 1:
            return key
        return f"{key}_{count}"

    # Build left side points (from left edge toward center)
    for comp in left_components:
        # Outer edge of component
        outer_x = comp.offset
        outer_z = comp.elevation - comp.slope * comp.width
        top_points.append((outer_x, outer_z))
        top_tags.append(get_tag(comp.component_type, "L", "OUT"))

        # Inner edge (toward centerline)
        inner_x = comp.offset + comp.width
        inner_z = comp.elevation
        top_points.append((inner_x, inner_z))
        top_tags.append(get_tag(comp.component_type, "L", "IN"))

    # Add centerline point if no components reach it exactly
    if not left_components or left_components[-1].offset + left_components[-1].width < -0.001:
        top_points.append((0.0, 0.0))
        top_tags.append(PointTags.CENTERLINE)
    elif right_components and right_components[0].offset > 0.001:
        top_points.append((0.0, 0.0))
        top_tags.append(PointTags.CENTERLINE)

    # Build right side points (from center outward)
    for comp in right_components:
        # Inner edge (at offset)
        inner_x = comp.offset
        inner_z = comp.elevation
        top_points.append((inner_x, inner_z))
        top_tags.append(get_tag(comp.component_type, "R", "IN"))

        # Outer edge
        outer_x = comp.offset + comp.width
        outer_z = comp.elevation - comp.slope * comp.width
        top_points.append((outer_x, outer_z))
        top_tags.append(get_tag(comp.component_type, "R", "OUT"))

    # Remove duplicate points at centerline if needed
    cleaned_points = []
    cleaned_tags = []
    for i, (pt, tag) in enumerate(zip(top_points, top_tags)):
        if i == 0:
            cleaned_points.append(pt)
            cleaned_tags.append(tag)
        else:
            # Skip if same as previous point
            prev = cleaned_points[-1]
            if abs(pt[0] - prev[0]) > 0.001 or abs(pt[1] - prev[1]) > 0.001:
                cleaned_points.append(pt)
                cleaned_tags.append(tag)

    top_points = cleaned_points
    top_tags = cleaned_tags

    # Now create bottom points by going back right to left with elevation offset
    bottom_points = []
    bottom_tags = []

    for pt, tag in zip(reversed(top_points), reversed(top_tags)):
        bottom_points.append((pt[0], pt[1] - pavement_thickness))
        bottom_tags.append(f"{tag}_BTM")

    # Combine: top (L→R) + bottom (R→L) to form closed polygon
    all_points = top_points + bottom_points + [top_points[0]]  # Close loop
    all_tags = top_tags + bottom_tags + [top_tags[0]]

    # Convert tuples to list format for IFC
    coord_list = [list(pt) for pt in all_points]

    return create_tagged_cross_section_profile(
        ifc_file=ifc_file,
        points=coord_list,
        tags=all_tags,
        station=station,
        profile_name=f"Corridor Section at Sta {station:.2f}"
    )


@dataclass
class StationPoint:
    """
    A station location along an alignment where a cross-section will be placed.
    
    Attributes:
        station: Distance along alignment (m)
        x: Easting coordinate (m)
        y: Northing coordinate (m)
        z: Elevation (m)
        direction: Horizontal bearing (radians)
        grade: Vertical grade (decimal)
        reason: Why this station was selected (e.g., "interval", "curve_start", "pvi")
    """
    station: float
    x: float
    y: float
    z: float
    direction: float
    grade: float
    reason: str = "interval"
    
    def __repr__(self) -> str:
        return f"Station({self.station:.2f}m, reason='{self.reason}')"


class StationManager:
    """
    Intelligent station calculation for corridor generation.
    
    Calculates optimal station locations along an alignment, densifying at:
    - Horizontal curves (more stations needed)
    - Vertical curves (PVIs and parabolic curves)
    - Parametric constraints (where cross-section changes)
    - User-specified critical points
    
    Algorithm:
    1. Start with uniform interval stations (e.g., every 10m)
    2. Add stations at horizontal curve endpoints
    3. Add stations throughout curves (based on curvature)
    4. Add stations at vertical PVIs and curve midpoints
    5. Add stations where parametric constraints exist
    6. Remove duplicate/close stations
    7. Sort by station value
    """
    
    def __init__(self, alignment_3d: Any, interval: float = 10.0):
        """
        Initialize station manager.
        
        Args:
            alignment_3d: Alignment3D instance with H+V alignment
            interval: Base station interval in meters (default: 10m)
        """
        self.alignment = alignment_3d
        self.interval = interval
        self.stations: List[StationPoint] = []
        
        # Tolerance for merging close stations
        self.merge_tolerance = 0.5  # meters
    
    def calculate_stations(
        self,
        curve_densification_factor: float = 2.0,
        critical_stations: Optional[List[float]] = None
    ) -> List[StationPoint]:
        """
        Calculate all stations along the alignment.
        
        Args:
            curve_densification_factor: How much denser to make curves (2.0 = 2x more stations)
            critical_stations: Optional list of additional critical stations
            
        Returns:
            List of StationPoint objects, sorted by station
            
        Algorithm Steps:
        1. Generate base interval stations
        2. Add curve-specific stations
        3. Add vertical alignment stations
        4. Add critical stations
        5. Merge and sort
        """
        self.stations = []
        
        # Step 1: Base interval stations
        self._add_interval_stations()
        
        # Step 2: Horizontal curve stations
        self._add_horizontal_curve_stations(curve_densification_factor)
        
        # Step 3: Vertical alignment stations (PVIs, curve points)
        self._add_vertical_alignment_stations()
        
        # Step 4: User-specified critical stations
        if critical_stations:
            self._add_critical_stations(critical_stations)
        
        # Step 5: Merge close stations and sort
        self._merge_and_sort()
        
        return self.stations
    
    def _add_interval_stations(self):
        """Add uniform interval stations along the alignment."""
        start = self.alignment.get_start_station()
        end = self.alignment.get_end_station()
        
        station = start
        while station <= end:
            point = self._create_station_point(station, "interval")
            if point:
                self.stations.append(point)
            station += self.interval
        
        # Ensure end station is included
        if abs(self.stations[-1].station - end) > 0.01:
            point = self._create_station_point(end, "end")
            if point:
                self.stations.append(point)
    
    def _add_horizontal_curve_stations(self, densification_factor: float):
        """
        Add stations at horizontal curves.
        
        Curves need more stations for smooth corridor generation.
        """
        # Access horizontal alignment
        h_align = self.alignment.horizontal
        
        # Check if horizontal alignment has curve information
        if not hasattr(h_align, 'segments'):
            return
        
        for segment in h_align.segments:
            # Check if segment is a curve
            if hasattr(segment, 'type') and segment.type == 'CURVE':
                # Add station at curve start
                start_sta = segment.start_station
                point = self._create_station_point(start_sta, "curve_start")
                if point:
                    self.stations.append(point)
                
                # Add stations within curve (denser than interval)
                curve_interval = self.interval / densification_factor
                length = segment.length
                station = start_sta + curve_interval
                
                while station < start_sta + length - 0.01:
                    point = self._create_station_point(station, "curve_interior")
                    if point:
                        self.stations.append(point)
                    station += curve_interval
                
                # Add station at curve end
                end_sta = segment.end_station
                point = self._create_station_point(end_sta, "curve_end")
                if point:
                    self.stations.append(point)
    
    def _add_vertical_alignment_stations(self):
        """Add stations at vertical alignment critical points (PVIs, curve points)."""
        v_align = self.alignment.vertical
        
        # Check if vertical alignment has PVI information
        if not hasattr(v_align, 'pvis'):
            return
        
        for pvi in v_align.pvis:
            # Add station at PVI
            station = pvi.station
            point = self._create_station_point(station, "pvi")
            if point:
                self.stations.append(point)
            
            # If PVI has a curve, add stations throughout the curve
            if hasattr(pvi, 'curve_length') and pvi.curve_length > 0:
                curve_start = station - pvi.curve_length / 2
                curve_end = station + pvi.curve_length / 2
                
                # Add quarter points on vertical curves
                for fraction in [0.25, 0.75]:
                    curve_station = curve_start + pvi.curve_length * fraction
                    point = self._create_station_point(curve_station, "vertical_curve")
                    if point:
                        self.stations.append(point)
    
    def _add_critical_stations(self, critical_stations: List[float]):
        """Add user-specified critical stations."""
        for station in critical_stations:
            point = self._create_station_point(station, "critical")
            if point:
                self.stations.append(point)
    
    def _create_station_point(self, station: float, reason: str) -> Optional[StationPoint]:
        """
        Create a StationPoint at a given station.
        
        Args:
            station: Station value
            reason: Reason for this station
            
        Returns:
            StationPoint or None if station is out of range
        """
        try:
            # Get 3D position from Alignment3D
            x, y, z = self.alignment.get_3d_position(station)
            
            # Get direction (bearing)
            direction = self.alignment.get_direction(station)
            
            # Get grade
            grade = self.alignment.get_grade(station)
            
            return StationPoint(
                station=station,
                x=x,
                y=y,
                z=z,
                direction=direction,
                grade=grade,
                reason=reason
            )
        except (ValueError, AttributeError):
            # Station out of range or alignment doesn't have method
            return None
    
    def _merge_and_sort(self):
        """Merge stations that are too close together and sort by station."""
        if not self.stations:
            return
        
        # Sort by station
        self.stations.sort(key=lambda s: s.station)
        
        # Merge close stations
        merged = [self.stations[0]]
        
        for station in self.stations[1:]:
            last = merged[-1]
            
            # If this station is very close to the last one, skip it
            if abs(station.station - last.station) < self.merge_tolerance:
                # Keep the one with more important reason
                priority = {
                    "start": 5,
                    "end": 5,
                    "pvi": 4,
                    "curve_start": 4,
                    "curve_end": 4,
                    "critical": 3,
                    "vertical_curve": 2,
                    "curve_interior": 1,
                    "interval": 0
                }
                
                if priority.get(station.reason, 0) > priority.get(last.reason, 0):
                    # Replace last with this one
                    merged[-1] = station
            else:
                # Add this station
                merged.append(station)
        
        self.stations = merged
    
    def get_station_count(self) -> int:
        """Get the number of stations."""
        return len(self.stations)
    
    def get_stations(self) -> List[StationPoint]:
        """Get all stations."""
        return self.stations
    
    def get_station_values(self) -> List[float]:
        """Get station values as a simple list of floats."""
        return [s.station for s in self.stations]


class CorridorModeler:
    """
    Main corridor modeling class.
    
    Creates IFC 4.3 IfcSectionedSolidHorizontal by sweeping cross-sections
    along a 3D alignment.
    
    Process:
    1. Generate stations along alignment (StationManager)
    2. For each station, get cross-section profile (RoadAssembly)
    3. Create IfcAxis2PlacementLinear for each station
    4. Create IfcSectionedSolidHorizontal with:
       - Directrix (IfcAlignmentCurve from Alignment3D)
       - CrossSections (IfcCompositeProfileDef from RoadAssembly)
       - CrossSectionPositions (IfcAxis2PlacementLinear at each station)
    
    Attributes:
        alignment_3d: Complete 3D alignment (H+V)
        assembly: Cross-section assembly definition
        station_manager: Station calculation manager
        corridor_solid: Generated IFC corridor solid
        ifc_file: IFC file instance
    """
    
    def __init__(
        self,
        alignment_3d: Any,
        assembly: Any,
        name: str = "Road Corridor"
    ):
        """
        Initialize corridor modeler.
        
        Args:
            alignment_3d: Alignment3D instance (Sprint 3)
            assembly: RoadAssembly instance (Sprint 4)
            name: Corridor name
        """
        self.alignment = alignment_3d
        self.assembly = assembly
        self.name = name
        
        # Station management
        self.station_manager = None
        self.stations: List[StationPoint] = []
        
        # IFC entities
        self.corridor_solid = None
        self.ifc_file = None
        
        # Corridor metadata
        self.start_station = alignment_3d.get_start_station()
        self.end_station = alignment_3d.get_end_station()
        self.length = self.end_station - self.start_station
    
    def generate_stations(
        self,
        interval: float = 10.0,
        curve_densification: float = 2.0,
        critical_stations: Optional[List[float]] = None
    ) -> List[StationPoint]:
        """
        Generate stations along the alignment.
        
        Args:
            interval: Base station interval (m), default 10m
            curve_densification: Curve densification factor, default 2.0
            critical_stations: Additional critical stations
            
        Returns:
            List of StationPoint objects
        """
        self.station_manager = StationManager(self.alignment, interval)
        self.stations = self.station_manager.calculate_stations(
            curve_densification_factor=curve_densification,
            critical_stations=critical_stations
        )
        
        return self.stations
    
    def create_corridor_solid(
        self,
        interval: float = 10.0,
        ifc_file: Optional[Any] = None
    ) -> Any:
        """
        Create IFC IfcSectionedSolidHorizontal corridor solid.
        
        Args:
            interval: Station interval in meters (default: 10m)
            ifc_file: Existing IFC file or None to create new
            
        Returns:
            IfcSectionedSolidHorizontal entity
            
        Raises:
            ValueError: If alignment or assembly is invalid
        """
        # Create or use IFC file
        if ifc_file is None:
            self.ifc_file = ifcopenshell.file(schema="IFC4X3")
        else:
            self.ifc_file = ifc_file
        
        # Step 1: Generate stations
        if not self.stations:
            self.generate_stations(interval=interval)
        
        if len(self.stations) < 2:
            raise ValueError("Need at least 2 stations to create corridor")
        
        # Step 2: Get directrix (alignment curve) from Alignment3D
        directrix = self._create_directrix()
        
        # Step 3: Create cross-section profiles for each station
        cross_sections = self._create_cross_section_profiles()
        
        # Step 4: Create positions for each cross-section
        positions = self._create_cross_section_positions(directrix)
        
        # Step 5: Create IfcSectionedSolidHorizontal
        self.corridor_solid = self.ifc_file.create_entity(
            "IfcSectionedSolidHorizontal",
            Directrix=directrix,
            CrossSections=cross_sections,
            CrossSectionPositions=positions
        )
        
        return self.corridor_solid
    
    def _create_directrix(self) -> Any:
        """
        Create directrix (alignment curve) for the corridor.
        
        The directrix is the IfcAlignmentCurve that the cross-sections
        follow. It comes from the Alignment3D system.
        
        Returns:
            IfcAlignmentCurve entity (or IfcCompositeCurve fallback)
        """
        # Try to get IFC alignment curve from Alignment3D
        if hasattr(self.alignment, 'to_ifc'):
            # Alignment3D has IFC export
            alignment_entities = self.alignment.to_ifc(self.ifc_file)
            
            # Extract the alignment curve
            if hasattr(alignment_entities, 'Axis'):
                return alignment_entities.Axis
        
        # Fallback: Create simple polyline from stations
        # This is a simplified approach for when full alignment export isn't available
        points = []
        for station_point in self.stations:
            point = self.ifc_file.create_entity(
                "IfcCartesianPoint",
                Coordinates=(station_point.x, station_point.y, station_point.z)
            )
            points.append(point)
        
        # Create polyline
        polyline = self.ifc_file.create_entity(
            "IfcPolyline",
            Points=points
        )
        
        return polyline
    
    def _create_cross_section_profiles(self) -> List[Any]:
        """
        Create IFC cross-section profiles for each station.
        
        Uses RoadAssembly.to_ifc() to create IfcCompositeProfileDef
        for each station, applying parametric constraints.
        
        Returns:
            List of IfcProfileDef entities (one per station)
        """
        profiles = []
        
        for station_point in self.stations:
            # Get cross-section profile from assembly at this station
            # The assembly may have parametric constraints that vary the profile
            profile = self._export_assembly_to_ifc(station_point.station)
            profiles.append(profile)
        
        return profiles
    
    def _export_assembly_to_ifc(self, station: float) -> Any:
        """
        Export cross-section assembly to IFC profile at a specific station.

        Creates a closed, tagged profile for IfcSectionedSolidHorizontal.
        Uses proper tagging for interpolation between cross-sections.

        Args:
            station: Station where cross-section is placed

        Returns:
            IfcArbitraryClosedProfileDef entity with tagged points
        """
        # Check if assembly is an AssemblyWrapper (from corridor.py)
        from .corridor import AssemblyWrapper
        if isinstance(self.assembly, AssemblyWrapper):
            # Use the tagged profile creator for proper IFC corridor generation
            return create_profile_from_assembly(
                ifc_file=self.ifc_file,
                assembly=self.assembly,
                station=station,
                pavement_thickness=0.3  # Default 300mm pavement
            )

        # Check if assembly has native IFC export
        if hasattr(self.assembly, 'to_ifc'):
            # Assembly has IFC export with station support
            if hasattr(self.assembly.to_ifc, '__code__'):
                # Check if to_ifc accepts station parameter
                params = self.assembly.to_ifc.__code__.co_varnames
                if 'station' in params:
                    return self.assembly.to_ifc(self.ifc_file, station=station)

            # Default: call without station
            return self.assembly.to_ifc(self.ifc_file)

        # Fallback: Create simple rectangular profile with tags
        # This is for testing when RoadAssembly doesn't have IFC export
        points = [
            [-5.0, 0.0],    # Left edge top
            [5.0, 0.0],     # Right edge top
            [5.0, -0.3],    # Right edge bottom
            [-5.0, -0.3],   # Left edge bottom
            [-5.0, 0.0]     # Close loop
        ]
        tags = [
            PointTags.EDGE_PAVEMENT_LEFT,
            PointTags.EDGE_PAVEMENT_RIGHT,
            f"{PointTags.EDGE_PAVEMENT_RIGHT}_BTM",
            f"{PointTags.EDGE_PAVEMENT_LEFT}_BTM",
            PointTags.EDGE_PAVEMENT_LEFT  # Closing tag
        ]

        return create_tagged_cross_section_profile(
            ifc_file=self.ifc_file,
            points=points,
            tags=tags,
            station=station,
            profile_name=f"Default Section at Sta {station:.2f}"
        )
    
    def _create_cross_section_positions(self, directrix: Any) -> List[Any]:
        """
        Create IfcAxis2PlacementLinear positions for each cross-section.

        Each position defines where and how a cross-section is placed
        along the directrix.

        Per IFC 4.3 specification for IfcSectionedSolidHorizontal:
        - Location is IfcDistanceExpression (NOT IfcPointByDistanceExpression)
        - OffsetLongitudinal MUST NOT be used (would create non-manifold geometry)
        - Axis defaults to Z-up if not specified
        - RefDirection defaults to perpendicular to directrix tangent

        Args:
            directrix: The directrix curve

        Returns:
            List of IfcAxis2PlacementLinear entities
        """
        positions = []

        for station_point in self.stations:
            # Create distance expression (parametric location on directrix)
            # CRITICAL: OffsetLongitudinal must be None per IFC 4.3 spec
            distance_expr = self.ifc_file.create_entity(
                "IfcDistanceExpression",
                DistanceAlong=station_point.station,
                OffsetLateral=0.0,  # No lateral offset
                OffsetVertical=0.0,  # No vertical offset
                # OffsetLongitudinal intentionally omitted - MUST NOT be used
            )

            # Create axis placement at this distance along directrix
            # Per IFC 4.3: Location is directly the IfcDistanceExpression
            # Axis and RefDirection default to appropriate values based on directrix
            placement = self.ifc_file.create_entity(
                "IfcAxis2PlacementLinear",
                Location=distance_expr,
                Axis=None,  # Default: derived from directrix, typically Z-up
                RefDirection=None  # Default: perpendicular to directrix tangent
            )

            positions.append(placement)

        return positions
    
    def get_station_count(self) -> int:
        """Get the number of stations in the corridor."""
        return len(self.stations)
    
    def get_corridor_length(self) -> float:
        """Get the length of the corridor."""
        return self.length
    
    def export_to_ifc(self, filepath: str = "corridor.ifc") -> Any:
        """
        Export corridor to IFC file.
        
        Args:
            filepath: Output IFC file path
            
        Returns:
            IFC file instance
        """
        if self.ifc_file is None:
            raise ValueError("No IFC file created. Call create_corridor_solid() first.")
        
        if self.corridor_solid is None:
            raise ValueError("No corridor solid created. Call create_corridor_solid() first.")
        
        # Write to file
        self.ifc_file.write(filepath)
        
        return self.ifc_file
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get corridor generation summary.
        
        Returns:
            Dictionary with corridor statistics
        """
        return {
            "name": self.name,
            "start_station": self.start_station,
            "end_station": self.end_station,
            "length": self.length,
            "station_count": self.get_station_count(),
            "assembly_name": self.assembly.name if hasattr(self.assembly, 'name') else "Unknown",
            "has_corridor_solid": self.corridor_solid is not None,
            "ifc_created": self.ifc_file is not None
        }


# Singleton manager for corridor system
_corridor_manager = None


def get_manager():
    """Get the global corridor manager instance."""
    global _corridor_manager
    if _corridor_manager is None:
        _corridor_manager = CorridorManager()
    return _corridor_manager


class CorridorManager:
    """
    Global manager for corridor modeling.
    
    Manages multiple corridors and provides high-level interface.
    """
    
    def __init__(self):
        """Initialize corridor manager."""
        self.corridors: Dict[str, CorridorModeler] = {}
        self.active_corridor = None
    
    def create_corridor(
        self,
        name: str,
        alignment_3d: Any,
        assembly: Any
    ) -> CorridorModeler:
        """
        Create a new corridor.
        
        Args:
            name: Corridor name
            alignment_3d: Alignment3D instance
            assembly: RoadAssembly instance
            
        Returns:
            CorridorModeler instance
        """
        modeler = CorridorModeler(alignment_3d, assembly, name)
        self.corridors[name] = modeler
        self.active_corridor = name
        return modeler
    
    def get_corridor(self, name: str) -> Optional[CorridorModeler]:
        """Get a corridor by name."""
        return self.corridors.get(name)
    
    def get_active_corridor(self) -> Optional[CorridorModeler]:
        """Get the active corridor."""
        if self.active_corridor:
            return self.corridors.get(self.active_corridor)
        return None
    
    def set_active_corridor(self, name: str):
        """Set the active corridor."""
        if name in self.corridors:
            self.active_corridor = name
        else:
            raise ValueError(f"Corridor '{name}' not found")
    
    def list_corridors(self) -> List[str]:
        """List all corridor names."""
        return list(self.corridors.keys())
    
    def remove_corridor(self, name: str):
        """Remove a corridor."""
        if name in self.corridors:
            del self.corridors[name]
            if self.active_corridor == name:
                self.active_corridor = None


if __name__ == "__main__":
    # Basic validation
    logger.info("Saikei Civil Native IFC Corridor System")
    logger.info("=" * 50)
    logger.info("✓ StationManager class defined")
    logger.info("✓ CorridorModeler class defined")
    logger.info("✓ CorridorManager class defined")
    logger.info("✓ Ready for integration testing")
    logger.info("Next: Create corridor_mesh_generator.py (Day 3)")
