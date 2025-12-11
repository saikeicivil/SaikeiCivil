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
Saikei Civil UI Panels
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
