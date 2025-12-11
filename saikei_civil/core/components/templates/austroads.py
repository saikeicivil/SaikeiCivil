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
Austroads Cross-Section Templates
==================================

Templates based on Austroads Guide to Road Design Part 3 for
Australian and New Zealand roadways.

Includes:
- Rural Single Carriageway (100 km/h)
- Motorway/Freeway (110 km/h)
- Urban Arterial (60 km/h)
"""

import logging
from typing import TYPE_CHECKING

from .metadata import TemplateMetadata

if TYPE_CHECKING:
    from ..native_ifc_cross_section import RoadAssembly

logger = logging.getLogger(__name__)


def create_rural_single(name: str = "Austroads Rural Single Carriageway") -> 'RoadAssembly':
    """Create Austroads Rural Single Carriageway (100 km/h design).

    Configuration:
    - 2 lanes @ 3.5m each
    - Sealed shoulders: 2.5m each side
    - Safety barriers where required
    - -2.5% cross slope (Australian standard)

    Standard: Austroads Guide to Road Design Part 3
    Design Speed: 100 km/h
    AADT: < 3,000 vpd

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
        category='Austroads',
        standard='Austroads Guide to Road Design Part 3',
        description='Rural single carriageway with sealed shoulders',
        typical_speed='100 km/h',
        design_vehicle='B-Double',
        terrain='Rural',
        functional_class='Rural Arterial'
    )

    # Right side
    right_lane = LaneComponent.create_standard_travel_lane("RIGHT")
    right_lane.width = 3.5
    right_lane.cross_slope = -0.025  # Australian standard

    right_shoulder = ShoulderComponent.create_paved_shoulder("RIGHT", 2.5)
    right_shoulder.cross_slope = -0.04

    right_ditch = DitchComponent.create_standard_ditch("RIGHT")
    right_ditch.foreslope = 4.0

    assembly.add_component(right_lane)
    assembly.add_component(right_shoulder, attach_to=right_lane)
    assembly.add_component(right_ditch, attach_to=right_shoulder)

    # Left side
    left_lane = LaneComponent.create_standard_travel_lane("LEFT")
    left_lane.width = 3.5
    left_lane.cross_slope = -0.025

    left_shoulder = ShoulderComponent.create_paved_shoulder("LEFT", 2.5)
    left_shoulder.cross_slope = -0.04

    left_ditch = DitchComponent.create_standard_ditch("LEFT")
    left_ditch.foreslope = 4.0

    assembly.add_component(left_lane)
    assembly.add_component(left_shoulder, attach_to=left_lane)
    assembly.add_component(left_ditch, attach_to=left_shoulder)

    logger.debug(f"Created Austroads rural single carriageway template: {name}")
    return assembly


def create_motorway(name: str = "Austroads Motorway/Freeway") -> 'RoadAssembly':
    """Create Austroads Motorway/Freeway (110 km/h design, one direction).

    Configuration:
    - Left shoulder: 1.0m paved (minimum)
    - 3 travel lanes @ 3.5m each
    - Right shoulder: 3.0m paved
    - Safety barriers on both sides
    - -2.5% cross slope

    Standard: Austroads Guide to Road Design Part 3
    Design Speed: 110 km/h
    AADT: > 15,000 vpd per direction

    Args:
        name: Assembly name

    Returns:
        Configured RoadAssembly
    """
    from ..components import LaneComponent, ShoulderComponent
    from ..native_ifc_cross_section import RoadAssembly

    assembly = RoadAssembly(name)
    assembly.metadata = TemplateMetadata(
        name=name,
        category='Austroads',
        standard='Austroads Guide to Road Design Part 3',
        description='Motorway/freeway with 3 lanes, one direction',
        typical_speed='110 km/h',
        design_vehicle='B-Double',
        terrain='Urban to Rural',
        functional_class='Motorway/Freeway'
    )

    # Inside (left) shoulder
    inside_shoulder = ShoulderComponent.create_paved_shoulder("LEFT", 1.0)
    inside_shoulder.cross_slope = -0.025

    # Lane 1 (inside)
    lane1 = LaneComponent.create_standard_travel_lane("RIGHT")
    lane1.width = 3.5
    lane1.cross_slope = -0.025

    # Lane 2 (middle)
    lane2 = LaneComponent.create_standard_travel_lane("RIGHT")
    lane2.width = 3.5
    lane2.cross_slope = -0.025

    # Lane 3 (outside)
    lane3 = LaneComponent.create_standard_travel_lane("RIGHT")
    lane3.width = 3.5
    lane3.cross_slope = -0.025

    # Outside shoulder
    outside_shoulder = ShoulderComponent.create_paved_shoulder("RIGHT", 3.0)
    outside_shoulder.cross_slope = -0.04

    # Build from inside out
    assembly.add_component(inside_shoulder)
    assembly.add_component(lane1, attach_to=inside_shoulder)
    assembly.add_component(lane2, attach_to=lane1)
    assembly.add_component(lane3, attach_to=lane2)
    assembly.add_component(outside_shoulder, attach_to=lane3)

    logger.debug(f"Created Austroads motorway template: {name}")
    return assembly


def create_urban_arterial(name: str = "Austroads Urban Arterial") -> 'RoadAssembly':
    """Create Austroads Urban Arterial (60 km/h design).

    Configuration:
    - Mountable curb (both sides)
    - 2 lanes @ 3.3m each
    - Parking lane: 2.5m both sides
    - -2.5% cross slope

    Standard: Austroads Guide to Road Design Part 3
    Design Speed: 60 km/h
    AADT: 3,000-10,000 vpd

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
        category='Austroads',
        standard='Austroads Guide to Road Design Part 3',
        description='Urban arterial with parking and mountable curbs',
        typical_speed='60 km/h',
        design_vehicle='Rigid Truck',
        terrain='Urban',
        functional_class='Urban Arterial'
    )

    # Right side
    right_travel = LaneComponent.create_standard_travel_lane("RIGHT")
    right_travel.width = 3.3
    right_travel.cross_slope = -0.025

    right_parking = LaneComponent.create_parking_lane("RIGHT")
    right_parking.width = 2.5
    right_parking.cross_slope = -0.025

    right_curb = CurbComponent.create_mountable_curb("RIGHT")

    assembly.add_component(right_travel)
    assembly.add_component(right_parking, attach_to=right_travel)
    assembly.add_component(right_curb, attach_to=right_parking)

    # Left side
    left_travel = LaneComponent.create_standard_travel_lane("LEFT")
    left_travel.width = 3.3
    left_travel.cross_slope = -0.025

    left_parking = LaneComponent.create_parking_lane("LEFT")
    left_parking.width = 2.5
    left_parking.cross_slope = -0.025

    left_curb = CurbComponent.create_mountable_curb("LEFT")

    assembly.add_component(left_travel)
    assembly.add_component(left_parking, attach_to=left_travel)
    assembly.add_component(left_curb, attach_to=left_parking)

    logger.debug(f"Created Austroads urban arterial template: {name}")
    return assembly


__all__ = [
    "create_rural_single",
    "create_motorway",
    "create_urban_arterial",
]
