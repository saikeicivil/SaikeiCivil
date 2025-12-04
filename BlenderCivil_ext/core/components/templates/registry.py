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
Template Registry Module
=========================

Central registry for all cross-section templates with lookup and filtering.
"""

import logging
from typing import Callable, Dict, List, Tuple

from . import aashto
from . import austroads
from . import uk_dmrb

logger = logging.getLogger(__name__)


def get_all_templates() -> Dict[str, Callable]:
    """Get all available templates.

    Returns:
        Dictionary mapping template names to factory functions
    """
    return {
        # AASHTO Templates
        'AASHTO Two-Lane Rural': aashto.create_two_lane_rural,
        'AASHTO Interstate': aashto.create_interstate,
        'AASHTO Urban Arterial': aashto.create_arterial_urban,
        'AASHTO Rural Collector': aashto.create_collector,
        'AASHTO Local Road': aashto.create_local_road,

        # Austroads Templates
        'Austroads Rural Single': austroads.create_rural_single,
        'Austroads Motorway': austroads.create_motorway,
        'Austroads Urban Arterial': austroads.create_urban_arterial,

        # UK DMRB Templates
        'UK Single Carriageway': uk_dmrb.create_single_carriageway,
        'UK Dual Carriageway': uk_dmrb.create_dual_carriageway,
        'UK Motorway': uk_dmrb.create_motorway,
    }


def get_templates_by_category(category: str) -> Dict[str, Callable]:
    """Get templates filtered by category.

    Args:
        category: 'AASHTO', 'Austroads', 'UK DMRB', or 'All'

    Returns:
        Dictionary of templates in that category
    """
    all_templates = get_all_templates()

    if category == 'All':
        return all_templates

    return {
        name: func for name, func in all_templates.items()
        if category in name
    }


def list_templates() -> List[Tuple[str, str, str]]:
    """List all templates with metadata.

    Returns:
        List of tuples: (name, category, description)
    """
    return [
        ('AASHTO Two-Lane Rural', 'AASHTO',
         'Standard two-lane rural highway with paved shoulders'),
        ('AASHTO Interstate', 'AASHTO',
         'Interstate highway, one direction with full shoulders'),
        ('AASHTO Urban Arterial', 'AASHTO',
         'Urban arterial with curb, gutter, and parking'),
        ('AASHTO Rural Collector', 'AASHTO',
         'Rural collector with narrow lanes and gravel shoulders'),
        ('AASHTO Local Road', 'AASHTO',
         'Minimum local road with minimal shoulders'),
        ('Austroads Rural Single', 'Austroads',
         'Rural single carriageway with sealed shoulders'),
        ('Austroads Motorway', 'Austroads',
         'Motorway/freeway with 3 lanes, one direction'),
        ('Austroads Urban Arterial', 'Austroads',
         'Urban arterial with parking and mountable curbs'),
        ('UK Single Carriageway', 'UK DMRB',
         'Single carriageway with hard strips'),
        ('UK Dual Carriageway', 'UK DMRB',
         'Dual carriageway with wide hard shoulder, one direction'),
        ('UK Motorway', 'UK DMRB',
         'Motorway with 3 lanes and hard shoulder, one direction'),
    ]


def get_template_summary() -> str:
    """Get a summary of all available templates.

    Returns:
        Formatted string with template count and categories
    """
    templates = list_templates()

    categories: Dict[str, List[str]] = {}
    for name, category, _ in templates:
        if category not in categories:
            categories[category] = []
        categories[category].append(name)

    lines = [
        "Saikei Civil Cross-Section Template Library",
        "=" * 50,
        "",
        f"Total Templates: {len(templates)}",
        "",
    ]

    for category, names in sorted(categories.items()):
        lines.append(f"{category} ({len(names)} templates):")
        for name in names:
            lines.append(f"  - {name}")
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "get_all_templates",
    "get_templates_by_category",
    "list_templates",
    "get_template_summary",
]
