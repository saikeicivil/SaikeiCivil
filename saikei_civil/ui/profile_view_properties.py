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
Saikei Civil - Profile View Properties (UI)
============================================

Blender property groups for profile view settings.
These are stored in the Blender scene and persist with .blend files.

This follows Saikei Civil's architecture pattern:
- ui/ = Blender UI elements (properties, panels)

Author: Saikei Civil Development Team
Date: November 2025
License: GPL v3
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, IntProperty


def _update_station_min(self, context):
    """Update callback for station_min property."""
    try:
        from ..core.profile_view_overlay import get_profile_overlay
        overlay = get_profile_overlay()
        overlay.data.station_min = self.station_min
        if overlay.enabled:
            overlay.refresh(context)
    except:
        pass


def _update_station_max(self, context):
    """Update callback for station_max property."""
    try:
        from ..core.profile_view_overlay import get_profile_overlay
        overlay = get_profile_overlay()
        overlay.data.station_max = self.station_max
        if overlay.enabled:
            overlay.refresh(context)
    except:
        pass


def _update_elevation_min(self, context):
    """Update callback for elevation_min property."""
    try:
        from ..core.profile_view_overlay import get_profile_overlay
        overlay = get_profile_overlay()
        overlay.data.elevation_min = self.elevation_min
        if overlay.enabled:
            overlay.refresh(context)
    except:
        pass


def _update_elevation_max(self, context):
    """Update callback for elevation_max property."""
    try:
        from ..core.profile_view_overlay import get_profile_overlay
        overlay = get_profile_overlay()
        overlay.data.elevation_max = self.elevation_max
        if overlay.enabled:
            overlay.refresh(context)
    except:
        pass


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
        update=_update_station_min
    )

    station_max: FloatProperty(
        name="Station Max",
        description="Maximum station value (m)",
        default=1000.0,
        unit='LENGTH',
        update=_update_station_max
    )

    elevation_min: FloatProperty(
        name="Elevation Min",
        description="Minimum elevation value (m)",
        default=0.0,
        unit='LENGTH',
        update=_update_elevation_min
    )

    elevation_max: FloatProperty(
        name="Elevation Max",
        description="Maximum elevation value (m)",
        default=100.0,
        unit='LENGTH',
        update=_update_elevation_max
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
