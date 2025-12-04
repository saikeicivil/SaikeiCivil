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
Saikei Civil - Profile View Data Model (Core)
==============================================

Pure Python data structures for profile view visualization.
No Blender dependencies - just data and business logic.

This follows Saikei Civil's architecture pattern:
- core/ = Business logic, IFC operations, pure Python
- operators/ = Blender operators (user actions)
- ui/ = Blender UI panels and properties

Author: Saikei Civil Development Team
Date: November 2025
License: GPL v3
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ProfilePoint:
    """
    A point in the profile view (station, elevation).
    
    Attributes:
        station: Distance along alignment (m)
        elevation: Elevation (m)
        point_type: Type - "TERRAIN", "PVI", "CURVE_POINT", "GRADE_POINT"
        metadata: Additional data (grade, curve length, etc.)
    """
    station: float
    elevation: float
    point_type: str = "TERRAIN"
    metadata: Dict = field(default_factory=dict)
    
    def __repr__(self):
        return f"ProfilePoint({self.station:.2f}m, {self.elevation:.2f}m, {self.point_type})"


class ProfileViewData:
    """
    Data model for profile view visualization.
    
    This is the core business logic - manages terrain profile, 
    vertical alignment, and PVIs. Pure Python, no Blender dependencies.
    
    Responsibilities:
        - Store and manage profile data (terrain, alignment, PVIs)
        - Calculate view extents automatically
        - Provide coordinate queries
        - Handle selection state
    """
    
    def __init__(self):
        """Initialize empty profile view data"""
        # Point collections
        self.terrain_points: List[ProfilePoint] = []
        self.alignment_points: List[ProfilePoint] = []
        self.pvis: List[ProfilePoint] = []

        # Vertical alignments loaded from IFC
        # Each entry is a VerticalAlignment object
        self.vertical_alignments: List = []  # List of VerticalAlignment objects
        self.selected_vertical_index: Optional[int] = None  # Which vertical to display

        # View extents (in world coordinates)
        self.station_min = 0.0
        self.station_max = 1000.0
        self.elevation_min = 0.0
        self.elevation_max = 100.0

        # Grid settings
        self.station_grid_spacing = 50.0  # meters
        self.elevation_grid_spacing = 5.0  # meters

        # Visual toggles
        self.show_terrain = True
        self.show_alignment = True
        self.show_pvis = True
        self.show_grades = True
        self.show_grid = True

        # Selection state
        self.selected_pvi_index: Optional[int] = None
    
    def clear_all(self):
        """Clear all data"""
        self.terrain_points.clear()
        self.alignment_points.clear()
        self.pvis.clear()
        self.vertical_alignments.clear()
        self.selected_pvi_index = None
        self.selected_vertical_index = None

    def clear_terrain(self):
        """Clear terrain data only"""
        self.terrain_points.clear()

    def clear_alignment(self):
        """Clear alignment data only"""
        self.alignment_points.clear()
        self.pvis.clear()
        self.selected_pvi_index = None

    def clear_vertical_alignments(self):
        """Clear vertical alignment data only"""
        self.vertical_alignments.clear()
        self.selected_vertical_index = None
    
    def add_terrain_point(self, station: float, elevation: float):
        """Add a single terrain point"""
        self.terrain_points.append(ProfilePoint(station, elevation, "TERRAIN"))
    
    def add_alignment_point(self, station: float, elevation: float):
        """Add a single alignment point"""
        self.alignment_points.append(ProfilePoint(station, elevation, "CURVE_POINT"))
    
    def add_pvi(self, station: float, elevation: float, metadata: Dict = None) -> int:
        """
        Add a PVI (Point of Vertical Intersection).
        
        Args:
            station: Station coordinate (m)
            elevation: Elevation coordinate (m)
            metadata: Optional metadata (curve_length, grades, etc.)
            
        Returns:
            Index of added PVI
        """
        pvi = ProfilePoint(station, elevation, "PVI")
        if metadata:
            pvi.metadata = metadata
        self.pvis.append(pvi)
        return len(self.pvis) - 1
    
    def remove_pvi(self, index: int) -> bool:
        """
        Remove a PVI by index.
        
        Args:
            index: Index of PVI to remove
            
        Returns:
            True if removed, False if index invalid
        """
        if 0 <= index < len(self.pvis):
            del self.pvis[index]
            if self.selected_pvi_index == index:
                self.selected_pvi_index = None
            elif self.selected_pvi_index and self.selected_pvi_index > index:
                self.selected_pvi_index -= 1
            return True
        return False
    
    def update_pvi(self, index: int, station: float, elevation: float) -> bool:
        """
        Update PVI position.
        
        Args:
            index: Index of PVI to update
            station: New station coordinate (m)
            elevation: New elevation coordinate (m)
            
        Returns:
            True if updated, False if index invalid
        """
        if 0 <= index < len(self.pvis):
            self.pvis[index].station = station
            self.pvis[index].elevation = elevation
            return True
        return False
    
    def get_pvi(self, index: int) -> Optional[ProfilePoint]:
        """Get PVI by index"""
        if 0 <= index < len(self.pvis):
            return self.pvis[index]
        return None
    
    def select_pvi(self, index: int) -> bool:
        """
        Select a PVI by index.
        
        Args:
            index: Index of PVI to select
            
        Returns:
            True if selected, False if index invalid
        """
        if 0 <= index < len(self.pvis):
            self.selected_pvi_index = index
            return True
        return False
    
    def deselect_pvi(self):
        """Deselect current PVI"""
        self.selected_pvi_index = None
    
    def get_selected_pvi(self) -> Optional[ProfilePoint]:
        """Get currently selected PVI"""
        if self.selected_pvi_index is not None:
            return self.get_pvi(self.selected_pvi_index)
        return None

    # ========================================================================
    # VERTICAL ALIGNMENT MANAGEMENT
    # ========================================================================

    def add_vertical_alignment(self, vertical_alignment) -> int:
        """
        Add a vertical alignment to the profile view.

        Args:
            vertical_alignment: VerticalAlignment object

        Returns:
            Index of added vertical alignment
        """
        self.vertical_alignments.append(vertical_alignment)
        return len(self.vertical_alignments) - 1

    def remove_vertical_alignment(self, index: int) -> bool:
        """
        Remove a vertical alignment by index.

        Args:
            index: Index of vertical alignment to remove

        Returns:
            True if removed, False if index invalid
        """
        if 0 <= index < len(self.vertical_alignments):
            del self.vertical_alignments[index]
            if self.selected_vertical_index == index:
                self.selected_vertical_index = None
            elif self.selected_vertical_index and self.selected_vertical_index > index:
                self.selected_vertical_index -= 1
            return True
        return False

    def get_vertical_alignment(self, index: int):
        """
        Get vertical alignment by index.

        Args:
            index: Index of vertical alignment

        Returns:
            VerticalAlignment object or None if index invalid
        """
        if 0 <= index < len(self.vertical_alignments):
            return self.vertical_alignments[index]
        return None

    def select_vertical_alignment(self, index: int) -> bool:
        """
        Select a vertical alignment by index.

        Args:
            index: Index of vertical alignment to select

        Returns:
            True if selected, False if index invalid
        """
        if 0 <= index < len(self.vertical_alignments):
            self.selected_vertical_index = index
            return True
        return False

    def deselect_vertical_alignment(self):
        """Deselect current vertical alignment"""
        self.selected_vertical_index = None

    def get_selected_vertical_alignment(self):
        """
        Get currently selected vertical alignment.

        Returns:
            VerticalAlignment object or None if no selection
        """
        if self.selected_vertical_index is not None:
            return self.get_vertical_alignment(self.selected_vertical_index)
        return None

    # ========================================================================
    # VIEW EXTENTS
    # ========================================================================

    def update_view_extents(self, padding: float = 10.0):
        """
        Automatically calculate view extents from data.

        Args:
            padding: Extra space around data (m)
        """
        all_elevations = []
        all_stations = []

        # Collect all points from terrain, alignment, and PVIs
        for points in [self.terrain_points, self.alignment_points, self.pvis]:
            for pt in points:
                all_stations.append(pt.station)
                all_elevations.append(pt.elevation)

        # Collect points from vertical alignments
        for valign in self.vertical_alignments:
            # Add PVIs from vertical alignment
            for pvi in valign.pvis:
                all_stations.append(pvi.station)
                all_elevations.append(pvi.elevation)

        if not all_stations:
            # No data, use defaults
            return

        # Calculate extents with padding
        self.station_min = min(all_stations) - padding
        self.station_max = max(all_stations) + padding
        self.elevation_min = min(all_elevations) - padding
        self.elevation_max = max(all_elevations) + padding

        # Sync to UI properties if available
        try:
            import bpy
            if hasattr(bpy.context.scene, 'bc_profile_view_props'):
                props = bpy.context.scene.bc_profile_view_props
                props.station_min = self.station_min
                props.station_max = self.station_max
                props.elevation_min = self.elevation_min
                props.elevation_max = self.elevation_max
        except:
            pass  # Not in Blender context
    
    def get_statistics(self) -> Dict:
        """
        Calculate profile statistics.
        
        Returns:
            Dictionary with counts, ranges, grades, etc.
        """
        stats = {
            'num_terrain_points': len(self.terrain_points),
            'num_alignment_points': len(self.alignment_points),
            'num_pvis': len(self.pvis),
            'station_range': self.station_max - self.station_min,
            'elevation_range': self.elevation_max - self.elevation_min,
        }
        
        # Calculate grade statistics
        if len(self.pvis) >= 2:
            grades = []
            for i in range(len(self.pvis) - 1):
                pvi1 = self.pvis[i]
                pvi2 = self.pvis[i + 1]
                
                delta_elev = pvi2.elevation - pvi1.elevation
                delta_station = pvi2.station - pvi1.station
                
                if delta_station > 0:
                    grade = (delta_elev / delta_station) * 100.0  # percentage
                    grades.append(grade)
            
            if grades:
                stats['min_grade'] = min(grades)
                stats['max_grade'] = max(grades)
                stats['avg_grade'] = sum(grades) / len(grades)
        
        return stats
    
    def sort_pvis_by_station(self):
        """Sort PVIs by station (ascending order)"""
        self.pvis.sort(key=lambda p: p.station)
        self.selected_pvi_index = None  # Clear selection after sort
    
    def validate_pvis(self) -> List[str]:
        """
        Validate PVI configuration.
        
        Returns:
            List of warning/error messages (empty if valid)
        """
        warnings = []
        
        # Check minimum number
        if len(self.pvis) < 2:
            warnings.append("At least 2 PVIs required for vertical alignment")
        
        # Check station order
        stations = [pvi.station for pvi in self.pvis]
        if stations != sorted(stations):
            warnings.append("PVIs should be in ascending station order")
        
        # Check for duplicate stations
        if len(stations) != len(set(stations)):
            warnings.append("Duplicate station values found")
        
        # Check grade limits (example: ±10%)
        max_grade_limit = 10.0  # percent
        for i in range(len(self.pvis) - 1):
            pvi1 = self.pvis[i]
            pvi2 = self.pvis[i + 1]
            
            delta_elev = pvi2.elevation - pvi1.elevation
            delta_station = pvi2.station - pvi1.station
            
            if delta_station > 0:
                grade = abs((delta_elev / delta_station) * 100.0)
                if grade > max_grade_limit:
                    warnings.append(
                        f"Grade {grade:.2f}% between stations {pvi1.station:.1f}m "
                        f"and {pvi2.station:.1f}m exceeds limit ({max_grade_limit}%)"
                    )
        
        return warnings
    
    def export_to_dict(self) -> Dict:
        """
        Export profile data to dictionary (for serialization).
        
        Returns:
            Dictionary with all profile data
        """
        return {
            'terrain_points': [
                {'station': pt.station, 'elevation': pt.elevation}
                for pt in self.terrain_points
            ],
            'alignment_points': [
                {'station': pt.station, 'elevation': pt.elevation}
                for pt in self.alignment_points
            ],
            'pvis': [
                {
                    'station': pt.station,
                    'elevation': pt.elevation,
                    'metadata': pt.metadata
                }
                for pt in self.pvis
            ],
            'view_extents': {
                'station_min': self.station_min,
                'station_max': self.station_max,
                'elevation_min': self.elevation_min,
                'elevation_max': self.elevation_max,
            },
            'grid_settings': {
                'station_spacing': self.station_grid_spacing,
                'elevation_spacing': self.elevation_grid_spacing,
            }
        }
    
    def import_from_dict(self, data: Dict):
        """
        Import profile data from dictionary.
        
        Args:
            data: Dictionary with profile data (from export_to_dict)
        """
        self.clear_all()
        
        # Import terrain
        for pt_data in data.get('terrain_points', []):
            self.add_terrain_point(pt_data['station'], pt_data['elevation'])
        
        # Import alignment
        for pt_data in data.get('alignment_points', []):
            self.add_alignment_point(pt_data['station'], pt_data['elevation'])
        
        # Import PVIs
        for pvi_data in data.get('pvis', []):
            self.add_pvi(
                pvi_data['station'],
                pvi_data['elevation'],
                pvi_data.get('metadata', {})
            )
        
        # Import view extents
        if 'view_extents' in data:
            ext = data['view_extents']
            self.station_min = ext['station_min']
            self.station_max = ext['station_max']
            self.elevation_min = ext['elevation_min']
            self.elevation_max = ext['elevation_max']
        
        # Import grid settings
        if 'grid_settings' in data:
            grid = data['grid_settings']
            self.station_grid_spacing = grid['station_spacing']
            self.elevation_grid_spacing = grid['elevation_spacing']


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_grade(station1: float, elevation1: float, 
                    station2: float, elevation2: float) -> float:
    """
    Calculate grade between two points.
    
    Args:
        station1, elevation1: First point coordinates
        station2, elevation2: Second point coordinates
        
    Returns:
        Grade as percentage (positive = uphill, negative = downhill)
    """
    delta_station = station2 - station1
    if abs(delta_station) < 1e-6:
        return 0.0
    
    delta_elevation = elevation2 - elevation1
    return (delta_elevation / delta_station) * 100.0


def interpolate_elevation(station: float, 
                         station1: float, elevation1: float,
                         station2: float, elevation2: float) -> float:
    """
    Linearly interpolate elevation at a station.
    
    Args:
        station: Station to interpolate at
        station1, elevation1: Start point
        station2, elevation2: End point
        
    Returns:
        Interpolated elevation
    """
    if abs(station2 - station1) < 1e-6:
        return elevation1
    
    t = (station - station1) / (station2 - station1)
    return elevation1 + t * (elevation2 - elevation1)


if __name__ == "__main__":
    # Simple test
    logger.info("ProfileViewData Test")
    logger.info("=" * 50)

    data = ProfileViewData()

    # Add some PVIs
    data.add_pvi(0.0, 100.0, {'curve_length': 100.0})
    data.add_pvi(250.0, 110.0, {'curve_length': 150.0})
    data.add_pvi(500.0, 105.0, {'curve_length': 100.0})

    logger.info("Added %s PVIs", len(data.pvis))

    # Add terrain points
    for station in np.linspace(0, 500, 50):
        elevation = 95.0 + 10.0 * np.sin(station / 100.0)
        data.add_terrain_point(station, elevation)

    logger.info("Added %s terrain points", len(data.terrain_points))

    # Update extents
    data.update_view_extents()
    logger.info("View extents: Station %.1fm to %.1fm", data.station_min, data.station_max)
    logger.info("              Elevation %.1fm to %.1fm", data.elevation_min, data.elevation_max)

    # Statistics
    stats = data.get_statistics()
    logger.info("\nStatistics:")
    for key, value in stats.items():
        if isinstance(value, float):
            logger.info("  %s: %.2f", key, value)
        else:
            logger.info("  %s: %s", key, value)

    # Validation
    warnings = data.validate_pvis()
    if warnings:
        logger.warning("\nWarnings:")
        for warning in warnings:
            logger.warning("  - %s", warning)
    else:
        logger.info("\nValidation: OK")

    logger.info("\nProfileViewData working correctly!")
