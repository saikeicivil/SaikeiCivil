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
Saikei Civil - 3D Alignment System (H+V Integration)
Sprint 3 Day 4 - Complete 3D Alignment Integration

This module provides the integration layer between horizontal (Sprint 1) 
and vertical (Sprint 3) alignments, enabling complete 3D alignment modeling.

Author: Saikei Civil Team
Date: November 2, 2025
Sprint: 3 of 16 - Vertical Alignments
Day: 4 of 5 - H+V Integration

Key Features:
- Link horizontal and vertical alignments
- Calculate 3D positions (x, y, z) from station
- Query 3D alignment data (position, grade, direction)
- Support for georeferenced coordinates
- 3D visualization in Blender
- IFC 4.3 IfcAlignment with both horizontal and vertical components

Mathematics:
- 3D Position: (x, y, z) = (horiz_x, horiz_y, vert_z)
- Station parameter is the common reference
- Horizontal provides: x, y, direction
- Vertical provides: z (elevation)
- Combined: complete 3D position along alignment

Usage Example:
    >>> # Create complete H+V alignment
    >>> h_alignment = HorizontalAlignment(...)
    >>> v_alignment = VerticalAlignment(...)
    >>> alignment_3d = Alignment3D(h_alignment, v_alignment)
    >>> 
    >>> # Query 3D position at station
    >>> x, y, z = alignment_3d.get_3d_position(station=150.0)
    >>> 
    >>> # Get alignment data
    >>> data = alignment_3d.get_alignment_data(station=150.0)
    >>> # data contains: position, elevation, grade, direction, curvature
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import math

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class AlignmentPoint3D:
    """
    A point along a 3D alignment.
    
    Attributes:
        station: Distance along alignment (m)
        x: Easting coordinate (m)
        y: Northing coordinate (m)
        z: Elevation (m)
        direction: Horizontal bearing (radians, 0 = North, clockwise)
        grade: Vertical grade (decimal, e.g., 0.02 = 2%)
        horizontal_curvature: 1/radius for horizontal (1/m), 0 = tangent
        vertical_curvature: K-value for vertical (m/%), 0 = tangent
    """
    station: float
    x: float
    y: float
    z: float
    direction: float
    grade: float
    horizontal_curvature: float = 0.0
    vertical_curvature: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for easy access."""
        return {
            'station': self.station,
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'elevation': self.z,  # Alias
            'direction': self.direction,
            'bearing': math.degrees(self.direction),  # In degrees
            'grade': self.grade,
            'grade_percent': self.grade * 100,  # As percentage
            'horizontal_curvature': self.horizontal_curvature,
            'vertical_curvature': self.vertical_curvature
        }


class Alignment3D:
    """
    Complete 3D alignment combining horizontal and vertical components.
    
    This class integrates horizontal alignment (Sprint 1) with vertical 
    alignment (Sprint 3) to create a complete 3D alignment. It provides
    methods to query 3D positions, generate visualization data, and export
    to IFC format.
    
    Attributes:
        horizontal: HorizontalAlignment instance (Sprint 1)
        vertical: VerticalAlignment instance (Sprint 3)
        name: Alignment name
        description: Optional description
    
    Methods:
        get_3d_position(station): Get (x, y, z) at station
        get_alignment_data(station): Get complete data at station
        sample_alignment(interval): Generate points along alignment
        get_start_station(): Get starting station
        get_end_station(): Get ending station
        validate(): Check alignment consistency
    """
    
    def __init__(
        self,
        horizontal: Any,  # HorizontalAlignment from Sprint 1
        vertical: Any,    # VerticalAlignment from Sprint 3
        name: str = "Alignment",
        description: str = ""
    ):
        """
        Initialize 3D alignment.
        
        Args:
            horizontal: HorizontalAlignment instance (Sprint 1)
            vertical: VerticalAlignment instance (Sprint 3)
            name: Alignment name
            description: Optional description
            
        Raises:
            ValueError: If alignments are incompatible
        """
        self.horizontal = horizontal
        self.vertical = vertical
        self.name = name
        self.description = description
        
        # Validate compatibility
        self._validate_compatibility()
    
    def _validate_compatibility(self):
        """
        Validate that horizontal and vertical alignments are compatible.
        
        Checks:
        - Both alignments exist
        - Station ranges overlap
        - Horizontal has method: get_position_at_station
        - Vertical has method: get_elevation
        
        Raises:
            ValueError: If alignments are incompatible
        """
        if self.horizontal is None:
            raise ValueError("Horizontal alignment is required")
        
        if self.vertical is None:
            raise ValueError("Vertical alignment is required")
        
        # Check horizontal has required methods
        if not hasattr(self.horizontal, 'get_position_at_station'):
            raise ValueError(
                "Horizontal alignment must have 'get_position_at_station' method"
            )
        
        # Check vertical has required methods
        if not hasattr(self.vertical, 'get_elevation'):
            raise ValueError(
                "Vertical alignment must have 'get_elevation' method"
            )
        
        # Check station range compatibility
        h_start = self.get_horizontal_start_station()
        h_end = self.get_horizontal_end_station()
        v_start = self.get_vertical_start_station()
        v_end = self.get_vertical_end_station()
        
        # Alignments should overlap
        if h_end < v_start or v_end < h_start:
            raise ValueError(
                f"Horizontal ({h_start}-{h_end}m) and vertical "
                f"({v_start}-{v_end}m) alignments do not overlap"
            )
    
    def get_horizontal_start_station(self) -> float:
        """Get horizontal alignment start station."""
        if hasattr(self.horizontal, 'start_station'):
            return self.horizontal.start_station
        return 0.0
    
    def get_horizontal_end_station(self) -> float:
        """Get horizontal alignment end station."""
        if hasattr(self.horizontal, 'end_station'):
            return self.horizontal.end_station
        if hasattr(self.horizontal, 'length'):
            return self.horizontal.length
        return 0.0
    
    def get_vertical_start_station(self) -> float:
        """Get vertical alignment start station."""
        if hasattr(self.vertical, 'start_station'):
            return self.vertical.start_station
        if hasattr(self.vertical, 'pvis') and len(self.vertical.pvis) > 0:
            return self.vertical.pvis[0].station
        return 0.0
    
    def get_vertical_end_station(self) -> float:
        """Get vertical alignment end station."""
        if hasattr(self.vertical, 'end_station'):
            return self.vertical.end_station
        if hasattr(self.vertical, 'pvis') and len(self.vertical.pvis) > 0:
            return self.vertical.pvis[-1].station
        return 0.0
    
    def get_start_station(self) -> float:
        """
        Get the start station for the complete alignment.
        
        Returns the maximum of horizontal and vertical start stations
        (the later starting point).
        
        Returns:
            Start station (m)
        """
        h_start = self.get_horizontal_start_station()
        v_start = self.get_vertical_start_station()
        return max(h_start, v_start)
    
    def get_end_station(self) -> float:
        """
        Get the end station for the complete alignment.
        
        Returns the minimum of horizontal and vertical end stations
        (the earlier ending point).
        
        Returns:
            End station (m)
        """
        h_end = self.get_horizontal_end_station()
        v_end = self.get_vertical_end_station()
        return min(h_end, v_end)
    
    def get_length(self) -> float:
        """
        Get the length of the complete alignment.
        
        Returns:
            Length (m)
        """
        return self.get_end_station() - self.get_start_station()
    
    def get_3d_position(self, station: float) -> Tuple[float, float, float]:
        """
        Get 3D position (x, y, z) at a given station.
        
        This is the core integration method that combines horizontal
        and vertical alignment data.
        
        Args:
            station: Distance along alignment (m)
            
        Returns:
            Tuple of (x, y, z) in meters
            
        Raises:
            ValueError: If station is out of range
            
        Example:
            >>> alignment_3d = Alignment3D(h_align, v_align)
            >>> x, y, z = alignment_3d.get_3d_position(150.0)
            >>> print(f"Position: ({x:.2f}, {y:.2f}, {z:.2f})")
        """
        # Validate station
        start = self.get_start_station()
        end = self.get_end_station()
        
        if station < start or station > end:
            raise ValueError(
                f"Station {station}m out of range [{start}, {end}]"
            )
        
        # Get horizontal position (x, y)
        # Sprint 1 HorizontalAlignment returns: (x, y, direction)
        result = self.horizontal.get_position_at_station(station)
        
        if len(result) >= 2:
            x = result[0]
            y = result[1]
        else:
            raise ValueError("Horizontal alignment returned invalid position")
        
        # Get vertical elevation (z)
        # Sprint 3 VerticalAlignment method
        z = self.vertical.get_elevation(station)
        
        return (x, y, z)
    
    def get_direction(self, station: float) -> float:
        """
        Get horizontal direction (bearing) at station.
        
        Args:
            station: Distance along alignment (m)
            
        Returns:
            Direction in radians (0 = North, clockwise positive)
        """
        result = self.horizontal.get_position_at_station(station)
        
        if len(result) >= 3:
            return result[2]  # direction
        
        # Fallback: calculate from nearby points
        ds = 0.1  # Small offset
        x1, y1, _ = self.horizontal.get_position_at_station(station - ds)
        x2, y2, _ = self.horizontal.get_position_at_station(station + ds)
        
        return math.atan2(x2 - x1, y2 - y1)  # Note: atan2(x, y) for North = 0
    
    def get_grade(self, station: float) -> float:
        """
        Get vertical grade at station.
        
        Args:
            station: Distance along alignment (m)
            
        Returns:
            Grade as decimal (e.g., 0.02 = 2%)
        """
        if hasattr(self.vertical, 'get_grade'):
            return self.vertical.get_grade(station)
        
        # Fallback: numerical differentiation
        ds = 0.1  # Small offset
        z1 = self.vertical.get_elevation(station - ds)
        z2 = self.vertical.get_elevation(station + ds)
        
        return (z2 - z1) / (2 * ds)
    
    def get_horizontal_curvature(self, station: float) -> float:
        """
        Get horizontal curvature (1/radius) at station.
        
        Args:
            station: Distance along alignment (m)
            
        Returns:
            Curvature as 1/radius (1/m), 0 for tangent
        """
        if hasattr(self.horizontal, 'get_curvature'):
            return self.horizontal.get_curvature(station)
        
        return 0.0  # Default to tangent
    
    def get_vertical_curvature(self, station: float) -> float:
        """
        Get vertical curvature (K-value) at station.
        
        Args:
            station: Distance along alignment (m)
            
        Returns:
            K-value (m/%), 0 for tangent
        """
        if hasattr(self.vertical, 'get_k_value'):
            return self.vertical.get_k_value(station)
        
        return 0.0  # Default to tangent
    
    def get_alignment_data(self, station: float) -> AlignmentPoint3D:
        """
        Get complete alignment data at station.
        
        This method returns all available alignment information at
        the specified station, packaged in an AlignmentPoint3D object.
        
        Args:
            station: Distance along alignment (m)
            
        Returns:
            AlignmentPoint3D with complete data
            
        Example:
            >>> data = alignment_3d.get_alignment_data(150.0)
            >>> print(f"Station: {data.station}m")
            >>> print(f"Position: ({data.x}, {data.y}, {data.z})")
            >>> print(f"Grade: {data.grade_percent}%")
            >>> print(f"Direction: {data.bearing}°")
        """
        # Get 3D position
        x, y, z = self.get_3d_position(station)
        
        # Get direction and grades
        direction = self.get_direction(station)
        grade = self.get_grade(station)
        
        # Get curvatures
        h_curvature = self.get_horizontal_curvature(station)
        v_curvature = self.get_vertical_curvature(station)
        
        return AlignmentPoint3D(
            station=station,
            x=x,
            y=y,
            z=z,
            direction=direction,
            grade=grade,
            horizontal_curvature=h_curvature,
            vertical_curvature=v_curvature
        )
    
    def sample_alignment(
        self,
        interval: float = 5.0,
        include_key_stations: bool = True
    ) -> List[AlignmentPoint3D]:
        """
        Sample the alignment at regular intervals.
        
        This method generates a series of points along the alignment,
        useful for visualization, analysis, or export.
        
        Args:
            interval: Spacing between sample points (m)
            include_key_stations: Also include PIs, PVIs, and curve points
            
        Returns:
            List of AlignmentPoint3D objects
            
        Example:
            >>> # Sample every 10m
            >>> points = alignment_3d.sample_alignment(interval=10.0)
            >>> 
            >>> # Create Blender curve
            >>> coords = [(p.x, p.y, p.z) for p in points]
        """
        start = self.get_start_station()
        end = self.get_end_station()
        
        # Generate regular stations
        stations = []
        current = start
        while current <= end:
            stations.append(current)
            current += interval
        
        # Ensure end station is included
        if stations[-1] < end:
            stations.append(end)
        
        # Add key stations if requested
        if include_key_stations:
            key_stations = set()
            
            # Add horizontal key stations (PIs, curve points)
            if hasattr(self.horizontal, 'pis'):
                for pi in self.horizontal.pis:
                    if hasattr(pi, 'station'):
                        key_stations.add(pi.station)
            
            # Add vertical key stations (PVIs, curve points)
            if hasattr(self.vertical, 'pvis'):
                for pvi in self.vertical.pvis:
                    if hasattr(pvi, 'station'):
                        key_stations.add(pvi.station)
            
            # Merge with regular stations
            stations = sorted(set(stations) | key_stations)
        
        # Sample at all stations
        points = []
        for station in stations:
            try:
                point = self.get_alignment_data(station)
                points.append(point)
            except (ValueError, AttributeError):
                # Skip invalid stations
                continue
        
        return points
    
    def get_chord_line(
        self,
        start_station: float,
        end_station: float
    ) -> Tuple[float, float]:
        """
        Get 3D chord length and slope between two stations.
        
        Args:
            start_station: Beginning station (m)
            end_station: Ending station (m)
            
        Returns:
            Tuple of (chord_length, slope_percent)
            
        Example:
            >>> # Check steep sections
            >>> length, slope = alignment_3d.get_chord_line(0, 100)
            >>> if slope > 8:
            ...     print("Steep section!")
        """
        x1, y1, z1 = self.get_3d_position(start_station)
        x2, y2, z2 = self.get_3d_position(end_station)
        
        # 3D distance
        dx = x2 - x1
        dy = y2 - y1
        dz = z2 - z1
        
        chord_length = math.sqrt(dx**2 + dy**2 + dz**2)
        
        # Slope (rise/run)
        horizontal_dist = math.sqrt(dx**2 + dy**2)
        if horizontal_dist > 0:
            slope = (dz / horizontal_dist) * 100  # Percent
        else:
            slope = 0.0
        
        return (chord_length, slope)
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate the 3D alignment.
        
        Checks for common issues and design violations.
        
        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'info': Dict[str, Any]
            }
            
        Example:
            >>> result = alignment_3d.validate()
            >>> if not result['valid']:
            ...     for error in result['errors']:
            ...         print(f"ERROR: {error}")
        """
        errors = []
        warnings = []
        info = {}
        
        # Check station ranges
        start = self.get_start_station()
        end = self.get_end_station()
        length = end - start
        
        if length <= 0:
            errors.append(f"Invalid length: {length}m")
        
        info['start_station'] = start
        info['end_station'] = end
        info['length'] = length
        
        # Check for gaps or discontinuities
        try:
            sample_interval = 10.0  # Check every 10m
            stations = []
            current = start
            while current <= end:
                stations.append(current)
                current += sample_interval
            
            # Try to get positions
            for station in stations:
                try:
                    self.get_3d_position(station)
                except Exception as e:
                    errors.append(
                        f"Error at station {station}m: {str(e)}"
                    )
        
        except Exception as e:
            errors.append(f"Sampling error: {str(e)}")
        
        # Check grade extremes
        if hasattr(self.vertical, 'get_max_grade'):
            max_grade = self.vertical.get_max_grade()
            info['max_grade'] = max_grade * 100  # Percent
            
            if abs(max_grade) > 0.12:  # 12%
                warnings.append(
                    f"Very steep grade: {max_grade*100:.1f}%"
                )
        
        # Overall result
        valid = len(errors) == 0
        
        return {
            'valid': valid,
            'errors': errors,
            'warnings': warnings,
            'info': info
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert alignment to dictionary representation.
        
        Returns:
            Dictionary with alignment information
        """
        return {
            'name': self.name,
            'description': self.description,
            'type': '3D Alignment (H+V)',
            'start_station': self.get_start_station(),
            'end_station': self.get_end_station(),
            'length': self.get_length(),
            'horizontal': {
                'type': type(self.horizontal).__name__,
                'start': self.get_horizontal_start_station(),
                'end': self.get_horizontal_end_station()
            },
            'vertical': {
                'type': type(self.vertical).__name__,
                'start': self.get_vertical_start_station(),
                'end': self.get_vertical_end_station()
            }
        }
    
    def __repr__(self) -> str:
        """String representation."""
        start = self.get_start_station()
        end = self.get_end_station()
        length = self.get_length()
        return (
            f"Alignment3D('{self.name}', "
            f"sta {start:.1f}-{end:.1f}m, "
            f"length {length:.1f}m)"
        )


def create_highway_example():
    """
    Create a simple highway alignment example.
    
    This demonstrates how to create a complete 3D alignment
    combining horizontal and vertical components.
    
    Returns:
        Alignment3D instance
    """
    # Note: This is a placeholder - actual implementation would
    # import from Sprint 1 (horizontal) and Sprint 3 (vertical)

    logger.info("Highway Example:")
    logger.info("- 2 km length")
    logger.info("- Gentle curves")
    logger.info("- Moderate grades (± 3%%)")
    logger.info("- AASHTO design speed: 100 km/h")
    
    # Would create actual alignment here
    # h_alignment = HorizontalAlignment(...)
    # v_alignment = VerticalAlignment(...)
    # return Alignment3D(h_alignment, v_alignment, name="Highway Example")
    
    return None


def create_urban_example():
    """
    Create an urban street alignment example.
    
    Returns:
        Alignment3D instance
    """
    logger.info("Urban Example:")
    logger.info("- 500 m length")
    logger.info("- Grid pattern")
    logger.info("- Flat with drainage (0.5-2%%)")
    logger.info("- Low speeds (40-50 km/h)")
    
    return None


def create_mountain_example():
    """
    Create a mountain road alignment example.
    
    Returns:
        Alignment3D instance
    """
    logger.info("Mountain Example:")
    logger.info("- 1.5 km length")
    logger.info("- Sharp horizontal curves")
    logger.info("- Steep grades (6-8%%)")
    logger.info("- Long vertical curves")
    
    return None


if __name__ == "__main__":
    logger.info("Saikei Civil - 3D Alignment System")
    logger.info("Sprint 3 Day 4 - H+V Integration")
    logger.info("=" * 50)
    logger.info("")
    logger.info("This module integrates horizontal and vertical alignments")
    logger.info("to create complete 3D road/rail alignments.")
    logger.info("")
    logger.info("Key Features:")
    logger.info("  • H+V alignment linking")
    logger.info("  • 3D position queries (x, y, z)")
    logger.info("  • Complete alignment data")
    logger.info("  • Sampling for visualization")
    logger.info("  • Validation and checking")
    logger.info("")
    logger.info("See docstrings for usage examples!")
