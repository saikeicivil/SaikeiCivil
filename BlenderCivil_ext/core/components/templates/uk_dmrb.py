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
UK DMRB Cross-Section Templates
================================

Templates based on UK Design Manual for Roads and Bridges (DMRB) standards.

Includes:
- Single Carriageway (100 km/h / 60 mph)
- Dual Carriageway (120 km/h / 70 mph)
- Motorway (120 km/h / 70 mph)
"""

import logging
from typing import TYPE_CHECKING

from .metadata import TemplateMetadata

if TYPE_CHECKING:
    from ..native_ifc_cross_section import RoadAssembly

logger = logging.getLogger(__name__)


def create_single_carriageway(name: str = "UK Single Carriageway (DMRB)") -> 'RoadAssembly':
    """Create UK Single Carriageway (100 km/h / 60 mph design).

    Configuration:
    - 2 lanes @ 3.65m each (UK standard)
    - Hard strips: 1.0m each side
    - Verges with drainage
    - -2.5% crossfall (UK term)

    Standard: UK DMRB CD 127 (Cross-sections and headrooms)
    Design Speed: 100 km/h (60 mph)
    AADT: < 13,000 vpd

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
        category='UK DMRB',
        standard='DMRB CD 127',
        description='Single carriageway with hard strips',
        typical_speed='100 km/h (60 mph)',
        design_vehicle='Articulated Lorry',
        terrain='Rural',
        functional_class='All-Purpose Single Carriageway'
    )

    # Right side
    right_lane = LaneComponent.create_standard_travel_lane("RIGHT")
    right_lane.width = 3.65  # UK standard
    right_lane.cross_slope = -0.025  # UK "crossfall"

    right_hardstrip = ShoulderComponent.create_paved_shoulder("RIGHT", 1.0)
    right_hardstrip.cross_slope = -0.025

    right_verge = DitchComponent.create_standard_ditch("RIGHT")
    right_verge.foreslope = 3.0  # UK verge slope

    assembly.add_component(right_lane)
    assembly.add_component(right_hardstrip, attach_to=right_lane)
    assembly.add_component(right_verge, attach_to=right_hardstrip)

    # Left side
    left_lane = LaneComponent.create_standard_travel_lane("LEFT")
    left_lane.width = 3.65
    left_lane.cross_slope = -0.025

    left_hardstrip = ShoulderComponent.create_paved_shoulder("LEFT", 1.0)
    left_hardstrip.cross_slope = -0.025

    left_verge = DitchComponent.create_standard_ditch("LEFT")
    left_verge.foreslope = 3.0

    assembly.add_component(left_lane)
    assembly.add_component(left_hardstrip, attach_to=left_lane)
    assembly.add_component(left_verge, attach_to=left_hardstrip)

    logger.debug(f"Created UK single carriageway template: {name}")
    return assembly


def create_dual_carriageway(name: str = "UK Dual Carriageway (DMRB)") -> 'RoadAssembly':
    """Create UK Dual Carriageway (120 km/h / 70 mph design, one direction).

    Configuration:
    - Central reserve hard strip: 1.0m
    - 2 lanes @ 3.65m each
    - Hard shoulder: 3.3m (UK wide hard shoulder)
    - Verge with safety fence
    - -2.5% crossfall

    Standard: UK DMRB CD 127
    Design Speed: 120 km/h (70 mph)
    AADT: > 13,000 vpd per direction

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
        category='UK DMRB',
        standard='DMRB CD 127',
        description='Dual carriageway with wide hard shoulder, one direction',
        typical_speed='120 km/h (70 mph)',
        design_vehicle='Articulated Lorry',
        terrain='Rural to Urban',
        functional_class='Dual Carriageway'
    )

    # Central reserve hard strip (left)
    central_hardstrip = ShoulderComponent.create_paved_shoulder("LEFT", 1.0)
    central_hardstrip.cross_slope = -0.025

    # Lane 1 (inside, near central reserve)
    lane1 = LaneComponent.create_standard_travel_lane("RIGHT")
    lane1.width = 3.65
    lane1.cross_slope = -0.025

    # Lane 2 (outside)
    lane2 = LaneComponent.create_standard_travel_lane("RIGHT")
    lane2.width = 3.65
    lane2.cross_slope = -0.025

    # Hard shoulder (right)
    hard_shoulder = ShoulderComponent.create_paved_shoulder("RIGHT", 3.3)
    hard_shoulder.cross_slope = -0.04

    # Verge
    verge = DitchComponent.create_standard_ditch("RIGHT")
    verge.foreslope = 3.0

    # Build from inside out
    assembly.add_component(central_hardstrip)
    assembly.add_component(lane1, attach_to=central_hardstrip)
    assembly.add_component(lane2, attach_to=lane1)
    assembly.add_component(hard_shoulder, attach_to=lane2)
    assembly.add_component(verge, attach_to=hard_shoulder)

    logger.debug(f"Created UK dual carriageway template: {name}")
    return assembly


def create_motorway(name: str = "UK Motorway (DMRB)") -> 'RoadAssembly':
    """Create UK Motorway (120 km/h / 70 mph design, one direction).

    Configuration:
    - Central reserve: 3.5m minimum
    - 3 lanes @ 3.65m each
    - Hard shoulder: 3.3m
    - Verge with drainage
    - -2.5% crossfall

    Standard: UK DMRB CD 127
    Design Speed: 120 km/h (70 mph)
    AADT: > 20,000 vpd per direction

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
        category='UK DMRB',
        standard='DMRB CD 127',
        description='Motorway with 3 lanes and hard shoulder, one direction',
        typical_speed='120 km/h (70 mph)',
        design_vehicle='Articulated Lorry',
        terrain='Any',
        functional_class='Motorway'
    )

    # Central reserve (simplified, left side)
    central_reserve = ShoulderComponent.create_paved_shoulder("LEFT", 1.75)  # Half of 3.5m
    central_reserve.cross_slope = -0.025

    # Lane 1 (inside, near central reserve)
    lane1 = LaneComponent.create_standard_travel_lane("RIGHT")
    lane1.width = 3.65
    lane1.cross_slope = -0.025

    # Lane 2 (middle)
    lane2 = LaneComponent.create_standard_travel_lane("RIGHT")
    lane2.width = 3.65
    lane2.cross_slope = -0.025

    # Lane 3 (outside)
    lane3 = LaneComponent.create_standard_travel_lane("RIGHT")
    lane3.width = 3.65
    lane3.cross_slope = -0.025

    # Hard shoulder
    hard_shoulder = ShoulderComponent.create_paved_shoulder("RIGHT", 3.3)
    hard_shoulder.cross_slope = -0.04

    # Verge
    verge = DitchComponent.create_standard_ditch("RIGHT")
    verge.foreslope = 3.0

    # Build from inside out
    assembly.add_component(central_reserve)
    assembly.add_component(lane1, attach_to=central_reserve)
    assembly.add_component(lane2, attach_to=lane1)
    assembly.add_component(lane3, attach_to=lane2)
    assembly.add_component(hard_shoulder, attach_to=lane3)
    assembly.add_component(verge, attach_to=hard_shoulder)

    logger.debug(f"Created UK motorway template: {name}")
    return assembly


__all__ = [
    "create_single_carriageway",
    "create_dual_carriageway",
    "create_motorway",
]
