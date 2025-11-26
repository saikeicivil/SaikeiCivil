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
Template Library Module (Backwards Compatibility Shim)
=======================================================

This module has been refactored into the templates package.
This shim provides backwards compatibility for existing imports.

New code should import from:
    from blendercivil.core.components.templates import (
        TemplateMetadata,
        get_all_templates,
        list_templates,
    )

This shim re-exports all public API from the new package.
"""

# Re-export everything from the new package for backwards compatibility
from .templates import (
    # Metadata
    TemplateMetadata,
    # Registry
    get_all_templates,
    get_templates_by_category,
    list_templates,
    get_template_summary,
    # AASHTO
    create_aashto_two_lane_rural,
    create_aashto_interstate,
    create_aashto_arterial_urban,
    create_aashto_collector,
    create_aashto_local_road,
    # Austroads
    create_austroads_rural_single,
    create_austroads_motorway,
    create_austroads_urban_arterial,
    # UK DMRB
    create_uk_single_carriageway,
    create_uk_dual_carriageway,
    create_uk_motorway,
    # Operators
    BLENDERCIVIL_OT_load_template,
    BLENDERCIVIL_OT_template_browser,
)


class TemplateLibraryExpanded:
    """Backwards compatibility wrapper for template library.

    This class wraps the new modular template functions to maintain
    compatibility with existing code that uses TemplateLibraryExpanded.

    New code should use the standalone functions from the templates package.
    """

    # AASHTO templates
    create_aashto_two_lane_rural = staticmethod(create_aashto_two_lane_rural)
    create_aashto_interstate = staticmethod(create_aashto_interstate)
    create_aashto_arterial_urban = staticmethod(create_aashto_arterial_urban)
    create_aashto_collector = staticmethod(create_aashto_collector)
    create_aashto_local_road = staticmethod(create_aashto_local_road)

    # Austroads templates
    create_austroads_rural_single = staticmethod(create_austroads_rural_single)
    create_austroads_motorway = staticmethod(create_austroads_motorway)
    create_austroads_urban_arterial = staticmethod(create_austroads_urban_arterial)

    # UK DMRB templates
    create_uk_single_carriageway = staticmethod(create_uk_single_carriageway)
    create_uk_dual_carriageway = staticmethod(create_uk_dual_carriageway)
    create_uk_motorway = staticmethod(create_uk_motorway)

    # Registry methods
    get_all_templates = classmethod(lambda cls: get_all_templates())
    get_templates_by_category = classmethod(
        lambda cls, category: get_templates_by_category(category)
    )
    list_templates = classmethod(lambda cls: list_templates())


__version__ = "1.0.0"
__author__ = "Michael Yoder"

__all__ = [
    "TemplateMetadata",
    "TemplateLibraryExpanded",
    "get_all_templates",
    "get_templates_by_category",
    "list_templates",
    "get_template_summary",
    "BLENDERCIVIL_OT_load_template",
    "BLENDERCIVIL_OT_template_browser",
]
