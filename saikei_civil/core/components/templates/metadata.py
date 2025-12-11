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
Template Metadata Module
=========================

Defines the TemplateMetadata dataclass for storing cross-section template information.
"""

from dataclasses import dataclass


@dataclass
class TemplateMetadata:
    """Metadata for a cross-section template.

    Attributes:
        name: Template display name
        category: Standard category ('AASHTO', 'Austroads', 'UK DMRB', 'Custom')
        standard: Reference standard (e.g., 'AASHTO Green Book 2018')
        description: Human-readable description
        typical_speed: Design speed (e.g., '50 mph (80 km/h)')
        design_vehicle: Design vehicle type (e.g., 'SU (Single Unit Truck)')
        terrain: Terrain classification ('Flat', 'Rolling', 'Mountainous')
        functional_class: Road functional class ('Rural', 'Urban', 'Interstate')
    """
    name: str
    category: str
    standard: str
    description: str
    typical_speed: str
    design_vehicle: str
    terrain: str
    functional_class: str


__all__ = ["TemplateMetadata"]
