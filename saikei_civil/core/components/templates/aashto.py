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
AASHTO Cross-Section Templates
===============================

Templates based on AASHTO Green Book 2018 standards for American roadways.

Includes:
- Two-Lane Rural Highway (60 mph)
- Interstate Highway (70 mph)
- Urban Arterial (45 mph)
- Rural Collector (50 mph)
- Local Road (30 mph)
"""

import logging
from typing import TYPE_CHECKING

from .metadata import TemplateMetadata

if TYPE_CHECKING:
    from ..native_ifc_cross_section import RoadAssembly

logger = logging.getLogger(__name__)


def create_two_lane_rural(name: str = "AASHTO Two-Lane Rural Highway") -> 'RoadAssembly':
    """Create AASHTO Two-Lane Rural Highway (60 mph design).

    Configuration:
    - 2 lanes @ 3.6m (12 ft) each
    - Paved shoulders: 2.4m (8 ft) each side
    - 4:1 foreslope ditches
    - -2% cross slope

    Standard: AASHTO Green Book 2018, Chapter 5
    Design Speed: 60 mph (95 km/h)
    ADT: < 2,000 vpd

    Args:
        name: Assembly name

    Returns:
        Configured RoadAssembly
    """
    from ..components import LaneComponent, ShoulderComponent, DitchComponent
    from ..native_ifc_cross_section import RoadAssembly

    assembly = RoadAssembly(name)
    assembly.metadata = TemplateMetadata(
        name=name,
        category='AASHTO',
        standard='AASHTO Green Book 2018',
        description='Standard two-lane rural highway with paved shoulders',
        typical_speed='60 mph (95 km/h)',
        design_vehicle='P (Passenger Car)',
        terrain='Rolling',
        functional_class='Rural'
    )

    # Right side (build outward from centerline)
    right_lane = LaneComponent.create_standard_travel_lane("RIGHT")
    right_lane.width = 3.6
    right_lane.cross_slope = -0.02

    right_shoulder = ShoulderComponent.create_paved_shoulder("RIGHT", 2.4)
    right_shoulder.cross_slope = -0.04

    right_ditch = DitchComponent.create_standard_ditch("RIGHT")

    assembly.add_component(right_lane)
    assembly.add_component(right_shoulder, attach_to=right_lane)
    assembly.add_component(right_ditch, attach_to=right_shoulder)

    # Left side
    left_lane = LaneComponent.create_standard_travel_lane("LEFT")
    left_lane.width = 3.6
    left_lane.cross_slope = -0.02

    left_shoulder = ShoulderComponent.create_paved_shoulder("LEFT", 2.4)
    left_shoulder.cross_slope = -0.04

    left_ditch = DitchComponent.create_standard_ditch("LEFT")

    assembly.add_component(left_lane)
    assembly.add_component(left_shoulder, attach_to=left_lane)
    assembly.add_component(left_ditch, attach_to=left_shoulder)

    logger.debug(f"Created AASHTO two-lane rural template: {name}")
    return assembly


def create_interstate(name: str = "AASHTO Interstate Highway") -> 'RoadAssembly':
    """Create AASHTO Interstate Highway (70 mph design, one direction).

    Configuration:
    - Inside shoulder: 3.0m (10 ft) paved
    - 2 travel lanes @ 3.6m (12 ft) each
    - Outside shoulder: 3.6m (12 ft) paved
    - 6:1 foreslope (clear zone requirement)
    - -2% cross slope

    Standard: AASHTO Green Book 2018, Chapter 7
    Design Speed: 70 mph (110 km/h)
    ADT: > 20,000 vpd per direction

    Args:
        name: Assembly name

    Returns:
        Configured RoadAssembly
    """
    from ..components import LaneComponent, ShoulderComponent, DitchComponent
    from ..native_ifc_cross_section import RoadAssembly

    assembly = RoadAssembly(name)
    assembly.metadata = TemplateMetadata(
        name=name,
        category='AASHTO',
        standard='AASHTO Green Book 2018',
        description='Interstate highway, one direction with full shoulders',
        typical_speed='70 mph (110 km/h)',
        design_vehicle='WB-67 (Interstate Semi)',
        terrain='Flat to Rolling',
        functional_class='Interstate'
    )

    # Inside (left) shoulder
    inside_shoulder = ShoulderComponent.create_interstate_shoulder("LEFT")
    inside_shoulder.width = 3.0
    inside_shoulder.cross_slope = -0.02

    # Lane 1 (inside lane)
    lane1 = LaneComponent.create_standard_travel_lane("RIGHT")
    lane1.width = 3.6
    lane1.cross_slope = -0.02

    # Lane 2 (outside lane)
    lane2 = LaneComponent.create_standard_travel_lane("RIGHT")
    lane2.width = 3.6
    lane2.cross_slope = -0.02

    # Outside shoulder
    outside_shoulder = ShoulderComponent.create_interstate_shoulder("RIGHT")
    outside_shoulder.width = 3.6
    outside_shoulder.cross_slope = -0.04

    # Ditch with gentle slope for clear zone
    outside_ditch = DitchComponent.create_standard_ditch("RIGHT")
    outside_ditch.foreslope = 6.0  # 6:1 for clear zone

    # Build from inside out
    assembly.add_component(inside_shoulder)
    assembly.add_component(lane1, attach_to=inside_shoulder)
    assembly.add_component(lane2, attach_to=lane1)
    assembly.add_component(outside_shoulder, attach_to=lane2)
    assembly.add_component(outside_ditch, attach_to=outside_shoulder)

    logger.debug(f"Created AASHTO interstate template: {name}")
    return assembly


def create_arterial_urban(name: str = "AASHTO Urban Arterial") -> 'RoadAssembly':
    """Create AASHTO Urban Arterial (45 mph design).

    Configuration:
    - Vertical curb and gutter (both sides)
    - 2 travel lanes @ 3.6m (12 ft) each
    - Parking lane: 2.4m (8 ft) both sides
    - -2% crown (center high point)

    Standard: AASHTO Green Book 2018, Chapter 6
    Design Speed: 45 mph (70 km/h)
    ADT: 5,000-15,000 vpd

    Args:
        name: Assembly name

    Returns:
        Configured RoadAssembly
    """
    from ..components import LaneComponent, CurbComponent
    from ..native_ifc_cross_section import RoadAssembly

    assembly = RoadAssembly(name)
    assembly.metadata = TemplateMetadata(
        name=name,
        category='AASHTO',
        standard='AASHTO Green Book 2018',
        description='Urban arterial with curb, gutter, and parking',
        typical_speed='45 mph (70 km/h)',
        design_vehicle='P (Passenger Car)',
        terrain='Urban',
        functional_class='Urban Principal Arterial'
    )

    # Right side
    right_travel = LaneComponent.create_standard_travel_lane("RIGHT")
    right_travel.width = 3.6
    right_travel.cross_slope = -0.02

    right_parking = LaneComponent.create_parking_lane("RIGHT")
    right_parking.width = 2.4
    right_parking.cross_slope = -0.02

    right_curb = CurbComponent.create_curb_and_gutter("RIGHT")

    assembly.add_component(right_travel)
    assembly.add_component(right_parking, attach_to=right_travel)
    assembly.add_component(right_curb, attach_to=right_parking)

    # Left side
    left_travel = LaneComponent.create_standard_travel_lane("LEFT")
    left_travel.width = 3.6
    left_travel.cross_slope = -0.02

    left_parking = LaneComponent.create_parking_lane("LEFT")
    left_parking.width = 2.4
    left_parking.cross_slope = -0.02

    left_curb = CurbComponent.create_curb_and_gutter("LEFT")

    assembly.add_component(left_travel)
    assembly.add_component(left_parking, attach_to=left_travel)
    assembly.add_component(left_curb, attach_to=left_parking)

    logger.debug(f"Created AASHTO urban arterial template: {name}")
    return assembly


def create_collector(name: str = "AASHTO Rural Collector") -> 'RoadAssembly':
    """Create AASHTO Rural Collector (50 mph design).

    Configuration:
    - 2 lanes @ 3.3m (11 ft) each
    - Gravel shoulders: 1.2m (4 ft) each side
    - 4:1 foreslope ditches
    - -2% cross slope

    Standard: AASHTO Green Book 2018, Chapter 5
    Design Speed: 50 mph (80 km/h)
    ADT: 400-2,000 vpd

    Args:
        name: Assembly name

    Returns:
        Configured RoadAssembly
    """
    from ..components import LaneComponent, ShoulderComponent, DitchComponent
    from ..native_ifc_cross_section import RoadAssembly

    assembly = RoadAssembly(name)
    assembly.metadata = TemplateMetadata(
        name=name,
        category='AASHTO',
        standard='AASHTO Green Book 2018',
        description='Rural collector with narrow lanes and gravel shoulders',
        typical_speed='50 mph (80 km/h)',
        design_vehicle='SU (Single Unit Truck)',
        terrain='Rolling to Mountainous',
        functional_class='Rural Collector'
    )

    # Right side
    right_lane = LaneComponent.create_standard_travel_lane("RIGHT")
    right_lane.width = 3.3  # Narrower for collector
    right_lane.cross_slope = -0.02

    right_shoulder = ShoulderComponent.create_gravel_shoulder("RIGHT", 1.2)
    right_shoulder.cross_slope = -0.06  # Steeper for gravel

    right_ditch = DitchComponent.create_standard_ditch("RIGHT")

    assembly.add_component(right_lane)
    assembly.add_component(right_shoulder, attach_to=right_lane)
    assembly.add_component(right_ditch, attach_to=right_shoulder)

    # Left side
    left_lane = LaneComponent.create_standard_travel_lane("LEFT")
    left_lane.width = 3.3
    left_lane.cross_slope = -0.02

    left_shoulder = ShoulderComponent.create_gravel_shoulder("LEFT", 1.2)
    left_shoulder.cross_slope = -0.06

    left_ditch = DitchComponent.create_standard_ditch("LEFT")

    assembly.add_component(left_lane)
    assembly.add_component(left_shoulder, attach_to=left_lane)
    assembly.add_component(left_ditch, attach_to=left_shoulder)

    logger.debug(f"Created AASHTO collector template: {name}")
    return assembly


def create_local_road(name: str = "AASHTO Local Road") -> 'RoadAssembly':
    """Create AASHTO Local Road (30 mph design).

    Configuration:
    - 2 lanes @ 3.0m (10 ft) each
    - Gravel shoulders: 0.6m (2 ft) each side
    - Simple ditch sections
    - -2% cross slope

    Standard: AASHTO Green Book 2018, Chapter 5
    Design Speed: 30 mph (50 km/h)
    ADT: < 400 vpd

    Args:
        name: Assembly name

    Returns:
        Configured RoadAssembly
    """
    from ..components import LaneComponent, ShoulderComponent, DitchComponent
    from ..native_ifc_cross_section import RoadAssembly

    assembly = RoadAssembly(name)
    assembly.metadata = TemplateMetadata(
        name=name,
        category='AASHTO',
        standard='AASHTO Green Book 2018',
        description='Minimum local road with minimal shoulders',
        typical_speed='30 mph (50 km/h)',
        design_vehicle='P (Passenger Car)',
        terrain='Any',
        functional_class='Local Road'
    )

    # Right side
    right_lane = LaneComponent.create_standard_travel_lane("RIGHT")
    right_lane.width = 3.0  # Minimum width
    right_lane.cross_slope = -0.02

    right_shoulder = ShoulderComponent.create_gravel_shoulder("RIGHT", 0.6)
    right_shoulder.cross_slope = -0.06

    right_ditch = DitchComponent.create_standard_ditch("RIGHT")
    right_ditch.depth = 0.3  # Shallow ditch

    assembly.add_component(right_lane)
    assembly.add_component(right_shoulder, attach_to=right_lane)
    assembly.add_component(right_ditch, attach_to=right_shoulder)

    # Left side
    left_lane = LaneComponent.create_standard_travel_lane("LEFT")
    left_lane.width = 3.0
    left_lane.cross_slope = -0.02

    left_shoulder = ShoulderComponent.create_gravel_shoulder("LEFT", 0.6)
    left_shoulder.cross_slope = -0.06

    left_ditch = DitchComponent.create_standard_ditch("LEFT")
    left_ditch.depth = 0.3

    assembly.add_component(left_lane)
    assembly.add_component(left_shoulder, attach_to=left_lane)
    assembly.add_component(left_ditch, attach_to=left_shoulder)

    logger.debug(f"Created AASHTO local road template: {name}")
    return assembly


__all__ = [
    "create_two_lane_rural",
    "create_interstate",
    "create_arterial_urban",
    "create_collector",
    "create_local_road",
]
