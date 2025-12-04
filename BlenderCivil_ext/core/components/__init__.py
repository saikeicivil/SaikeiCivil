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
Cross-Section Components Package
Reusable components for road cross-section assemblies
"""

from .base_component import AssemblyComponent
from .lane_component import LaneComponent
from .shoulder_component import ShoulderComponent
from .curb_component import CurbComponent
from .ditch_component import DitchComponent
from .sidewalk_component import SidewalkComponent
from .median_component import MedianComponent

# Templates package
from .templates import (
    TemplateMetadata,
    get_all_templates,
    get_templates_by_category,
    list_templates,
    get_template_summary,
)

# Backwards compatibility
from .template_library_expanded import TemplateLibraryExpanded

__all__ = [
    # Core components
    'AssemblyComponent',
    'LaneComponent',
    'ShoulderComponent',
    'CurbComponent',
    'DitchComponent',
    'SidewalkComponent',
    'MedianComponent',
    # Templates
    'TemplateMetadata',
    'TemplateLibraryExpanded',
    'get_all_templates',
    'get_templates_by_category',
    'list_templates',
    'get_template_summary',
]
