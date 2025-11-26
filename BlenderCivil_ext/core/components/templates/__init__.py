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
Cross-Section Templates Package
================================

Comprehensive library of road cross-section templates based on international standards.

Supported Standards:
- AASHTO (American Association of State Highway and Transportation Officials)
- Austroads (Australian and New Zealand)
- UK DMRB (Design Manual for Roads and Bridges)

Example:
    >>> from blendercivil.core.components.templates import get_all_templates
    >>> templates = get_all_templates()
    >>> assembly = templates['AASHTO Two-Lane Rural']()
"""

# Metadata
from .metadata import TemplateMetadata

# Registry and lookup
from .registry import (
    get_all_templates,
    get_templates_by_category,
    list_templates,
    get_template_summary,
)

# AASHTO templates
from .aashto import (
    create_two_lane_rural as create_aashto_two_lane_rural,
    create_interstate as create_aashto_interstate,
    create_arterial_urban as create_aashto_arterial_urban,
    create_collector as create_aashto_collector,
    create_local_road as create_aashto_local_road,
)

# Austroads templates
from .austroads import (
    create_rural_single as create_austroads_rural_single,
    create_motorway as create_austroads_motorway,
    create_urban_arterial as create_austroads_urban_arterial,
)

# UK DMRB templates
from .uk_dmrb import (
    create_single_carriageway as create_uk_single_carriageway,
    create_dual_carriageway as create_uk_dual_carriageway,
    create_motorway as create_uk_motorway,
)

# Blender operators
from .operators import (
    BLENDERCIVIL_OT_load_template,
    BLENDERCIVIL_OT_template_browser,
    register,
    unregister,
)

__version__ = "1.0.0"
__author__ = "Michael Yoder"

__all__ = [
    # Metadata
    "TemplateMetadata",
    # Registry
    "get_all_templates",
    "get_templates_by_category",
    "list_templates",
    "get_template_summary",
    # AASHTO
    "create_aashto_two_lane_rural",
    "create_aashto_interstate",
    "create_aashto_arterial_urban",
    "create_aashto_collector",
    "create_aashto_local_road",
    # Austroads
    "create_austroads_rural_single",
    "create_austroads_motorway",
    "create_austroads_urban_arterial",
    # UK DMRB
    "create_uk_single_carriageway",
    "create_uk_dual_carriageway",
    "create_uk_motorway",
    # Operators
    "BLENDERCIVIL_OT_load_template",
    "BLENDERCIVIL_OT_template_browser",
    "register",
    "unregister",
]
