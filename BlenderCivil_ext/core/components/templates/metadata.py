# ==============================================================================
# BlenderCivil - Civil Engineering Tools for Blender
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
