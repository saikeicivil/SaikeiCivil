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
BlenderCivil - Profile View Properties (UI)
============================================

Blender property groups for profile view settings.
These are stored in the Blender scene and persist with .blend files.

This follows BlenderCivil's architecture pattern:
- ui/ = Blender UI elements (properties, panels)

Author: BlenderCivil Development Team
Date: November 2025
License: GPL v3
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, IntProperty


def _update_view_extents(self, context):
    """
    Update callback for view extents properties.
    Synchronizes UI property values to ProfileViewData and triggers viewport refresh.
    """
    # Get the profile overlay and update view extents
    try:
        from ..core.profile_view_overlay import get_profile_overlay
        overlay = get_profile_overlay()

        # Sync property values to the data object
        overlay.data.station_min = self.station_min
        overlay.data.station_max = self.station_max
        overlay.data.elevation_min = self.elevation_min
        overlay.data.elevation_max = self.elevation_max

        # Refresh viewport if enabled
        if overlay.enabled:
            overlay.refresh(context)
    except:
        pass  # Overlay not available yet


def _update_display_toggle(self, context):
    """
    Update callback for display toggle properties.
    Triggers viewport refresh when visibility settings change.
    """
    # Get the profile overlay and refresh viewport
    try:
        from ..core.profile_view_overlay import get_profile_overlay
        overlay = get_profile_overlay()
        if overlay.enabled:
            overlay.refresh(context)
    except:
        pass  # Overlay not available yet


class BC_ProfileViewProperties(PropertyGroup):
    """
    Properties for profile view display settings.
    Stored in bpy.context.scene.bc_profile_view_props
    """
    
    # Display toggles
    show_terrain: BoolProperty(
        name="Show Terrain",
        description="Display terrain profile",
        default=True,
        update=_update_display_toggle
    )

    show_alignment: BoolProperty(
        name="Show Alignment",
        description="Display vertical alignment profile",
        default=True,
        update=_update_display_toggle
    )

    show_pvis: BoolProperty(
        name="Show PVIs",
        description="Display PVI control points",
        default=True,
        update=_update_display_toggle
    )

    show_grades: BoolProperty(
        name="Show Grades",
        description="Display grade lines between PVIs",
        default=True,
        update=_update_display_toggle
    )

    show_grid: BoolProperty(
        name="Show Grid",
        description="Display grid lines and labels",
        default=True,
        update=_update_display_toggle
    )
    
    # View extents
    station_min: FloatProperty(
        name="Station Min",
        description="Minimum station value (m)",
        default=0.0,
        unit='LENGTH',
        update=_update_view_extents
    )

    station_max: FloatProperty(
        name="Station Max",
        description="Maximum station value (m)",
        default=1000.0,
        unit='LENGTH',
        update=_update_view_extents
    )

    elevation_min: FloatProperty(
        name="Elevation Min",
        description="Minimum elevation value (m)",
        default=0.0,
        unit='LENGTH',
        update=_update_view_extents
    )

    elevation_max: FloatProperty(
        name="Elevation Max",
        description="Maximum elevation value (m)",
        default=100.0,
        unit='LENGTH',
        update=_update_view_extents
    )
    
    # Grid settings
    station_grid_spacing: FloatProperty(
        name="Station Grid Spacing",
        description="Spacing between vertical grid lines (m)",
        default=50.0,
        min=1.0,
        unit='LENGTH',
        update=_update_display_toggle
    )

    elevation_grid_spacing: FloatProperty(
        name="Elevation Grid Spacing",
        description="Spacing between horizontal grid lines (m)",
        default=5.0,
        min=0.1,
        unit='LENGTH',
        update=_update_display_toggle
    )
    
    # Overlay settings
    overlay_height: IntProperty(
        name="Overlay Height",
        description="Height of profile view overlay in pixels",
        default=200,
        min=100,
        max=500
    )


def register():
    bpy.utils.register_class(BC_ProfileViewProperties)
    bpy.types.Scene.bc_profile_view_props = bpy.props.PointerProperty(
        type=BC_ProfileViewProperties
    )


def unregister():
    del bpy.types.Scene.bc_profile_view_props
    bpy.utils.unregister_class(BC_ProfileViewProperties)


if __name__ == "__main__":
    register()
