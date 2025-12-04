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
IFC Entity Creation Module
===========================

Functions for creating IFC core entities required for external viewer compatibility.
Includes units, geometric contexts, and placements.
"""

import logging
from typing import Optional

import ifcopenshell

logger = logging.getLogger(__name__)


def create_units(ifc_file: ifcopenshell.file) -> ifcopenshell.entity_instance:
    """Create SI units required for external viewer compatibility.

    Creates length, area, volume, and angle units in SI.
    This is REQUIRED for viewers like Solibri, FreeCAD, etc.

    Args:
        ifc_file: Active IFC file

    Returns:
        IfcUnitAssignment entity
    """
    length_unit = ifc_file.create_entity(
        "IfcSIUnit",
        Dimensions=None,
        UnitType="LENGTHUNIT",
        Prefix=None,
        Name="METRE"
    )

    area_unit = ifc_file.create_entity(
        "IfcSIUnit",
        Dimensions=None,
        UnitType="AREAUNIT",
        Prefix=None,
        Name="SQUARE_METRE"
    )

    volume_unit = ifc_file.create_entity(
        "IfcSIUnit",
        Dimensions=None,
        UnitType="VOLUMEUNIT",
        Prefix=None,
        Name="CUBIC_METRE"
    )

    plane_angle_unit = ifc_file.create_entity(
        "IfcSIUnit",
        Dimensions=None,
        UnitType="PLANEANGLEUNIT",
        Prefix=None,
        Name="RADIAN"
    )

    unit_assignment = ifc_file.create_entity(
        "IfcUnitAssignment",
        Units=[length_unit, area_unit, volume_unit, plane_angle_unit]
    )

    logger.debug("Created SI unit assignment")
    return unit_assignment


def create_geometric_context(
    ifc_file: ifcopenshell.file
) -> tuple:
    """Create geometric representation context for geometry display.

    Creates:
    1. Main 3D Model context (parent)
    2. Axis sub-context for alignment curves

    Both are REQUIRED for shape representations to display
    in external viewers like Solibri.

    Args:
        ifc_file: Active IFC file

    Returns:
        Tuple of (main_context, axis_subcontext)
    """
    # Create origin point
    origin = ifc_file.create_entity(
        "IfcCartesianPoint",
        Coordinates=(0.0, 0.0, 0.0)
    )

    # Create axis directions
    z_axis = ifc_file.create_entity(
        "IfcDirection",
        DirectionRatios=(0.0, 0.0, 1.0)
    )
    x_axis = ifc_file.create_entity(
        "IfcDirection",
        DirectionRatios=(1.0, 0.0, 0.0)
    )

    # Create world coordinate system
    world_placement = ifc_file.create_entity(
        "IfcAxis2Placement3D",
        Location=origin,
        Axis=z_axis,
        RefDirection=x_axis
    )

    # Create main 3D Model context (parent)
    context = ifc_file.create_entity(
        "IfcGeometricRepresentationContext",
        ContextIdentifier="Model",
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=1e-5,
        WorldCoordinateSystem=world_placement,
        TrueNorth=None
    )

    # Create Axis sub-context for alignment curves
    axis_subcontext = ifc_file.create_entity(
        "IfcGeometricRepresentationSubContext",
        ContextIdentifier="Axis",
        ContextType="Model",
        ParentContext=context,
        TargetScale=None,
        TargetView="MODEL_VIEW",
        UserDefinedTargetView=None
    )

    logger.debug("Created geometric representation context with Axis sub-context")
    return context, axis_subcontext


def create_local_placement(
    ifc_file: ifcopenshell.file,
    relative_to: Optional[ifcopenshell.entity_instance] = None,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0
) -> ifcopenshell.entity_instance:
    """Create an IfcLocalPlacement at specified coordinates.

    Args:
        ifc_file: Active IFC file
        relative_to: Optional parent placement (IfcLocalPlacement)
        x: X coordinate
        y: Y coordinate
        z: Z coordinate

    Returns:
        IfcLocalPlacement entity
    """
    origin = ifc_file.create_entity(
        "IfcCartesianPoint",
        Coordinates=(float(x), float(y), float(z))
    )

    axis_placement = ifc_file.create_entity(
        "IfcAxis2Placement3D",
        Location=origin,
        Axis=None,
        RefDirection=None
    )

    local_placement = ifc_file.create_entity(
        "IfcLocalPlacement",
        PlacementRelTo=relative_to,
        RelativePlacement=axis_placement
    )

    return local_placement


def find_geometric_context(
    ifc_file: ifcopenshell.file
) -> Optional[ifcopenshell.entity_instance]:
    """Find existing geometric representation context in file.

    Args:
        ifc_file: IFC file to search

    Returns:
        IfcGeometricRepresentationContext or None
    """
    contexts = ifc_file.by_type("IfcGeometricRepresentationContext")
    for ctx in contexts:
        # Skip sub-contexts
        if hasattr(ctx, 'ParentContext') and ctx.ParentContext:
            continue
        if ctx.ContextType == "Model" and ctx.CoordinateSpaceDimension == 3:
            return ctx
    return None


def find_axis_subcontext(
    ifc_file: ifcopenshell.file
) -> Optional[ifcopenshell.entity_instance]:
    """Find existing Axis sub-context in file.

    Args:
        ifc_file: IFC file to search

    Returns:
        IfcGeometricRepresentationSubContext or None
    """
    subcontexts = ifc_file.by_type("IfcGeometricRepresentationSubContext")
    for ctx in subcontexts:
        if ctx.ContextIdentifier == "Axis":
            return ctx
    return None


__all__ = [
    "create_units",
    "create_geometric_context",
    "create_local_placement",
    "find_geometric_context",
    "find_axis_subcontext",
]
