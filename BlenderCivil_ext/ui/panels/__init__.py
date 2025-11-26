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
BlenderCivil UI Panels
"""

from . import georeferencing_panel
from . import vertical_alignment_panel
from . import cross_section_panel
from . import visualization_panel

def register():
    georeferencing_panel.register()
    vertical_alignment_panel.register()
    cross_section_panel.register()
    visualization_panel.register()

def unregister():
    visualization_panel.unregister()
    cross_section_panel.unregister()
    vertical_alignment_panel.unregister()
    georeferencing_panel.unregister()
