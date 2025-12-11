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
IFC Vertical Alignment Loader Module
=====================================

Functions for loading vertical alignments from IFC files and integrating
them with Blender's scene and the profile view system.

Note: This module uses the tool layer for Blender-specific operations
(creating empties) while keeping pure IFC loading logic here.
"""

import logging
from typing import List, Optional

import ifcopenshell

from .manager import VerticalAlignment

logger = logging.getLogger(__name__)


def _create_blender_empty(
    vertical_entity: ifcopenshell.entity_instance,
    horizontal_alignment: Optional[ifcopenshell.entity_instance] = None
) -> None:
    """Create Blender empty using tool layer.

    This is a wrapper that imports the tool layer on demand to avoid
    circular imports and keep core logic pure.
    """
    try:
        from ...tool import VerticalAlignment as VerticalAlignmentTool
        VerticalAlignmentTool.create_blender_empty(vertical_entity, horizontal_alignment)
    except ImportError:
        logger.warning("Tool layer not available - skipping Blender empty creation")


def load_vertical_alignments_from_ifc(
    ifc_file: ifcopenshell.file,
    horizontal_alignment: Optional[ifcopenshell.entity_instance] = None
) -> List[VerticalAlignment]:
    """Load all vertical alignments from an IFC file.

    If horizontal_alignment is provided, only loads vertical alignments
    nested under that horizontal alignment. Otherwise, loads all vertical
    alignments in the file.

    Args:
        ifc_file: IFC file instance
        horizontal_alignment: Optional parent horizontal alignment to filter by

    Returns:
        List of VerticalAlignment objects

    Example:
        >>> ifc = ifcopenshell.open("project.ifc")
        >>> valigns = load_vertical_alignments_from_ifc(ifc)
        >>> print(f"Loaded {len(valigns)} vertical alignments")
    """
    logger.debug("load_vertical_alignments_from_ifc called")
    logger.debug(f"horizontal_alignment parameter: {horizontal_alignment}")

    vertical_alignments = []

    if horizontal_alignment:
        vertical_alignments = _load_nested_verticals(
            ifc_file, horizontal_alignment
        )
    else:
        vertical_alignments = _load_all_verticals(ifc_file)

    logger.info(f"Total vertical alignments loaded: {len(vertical_alignments)}")

    # Add loaded vertical alignments to profile view data
    _update_profile_view(vertical_alignments)

    return vertical_alignments


def _load_nested_verticals(
    ifc_file: ifcopenshell.file,
    horizontal_alignment: ifcopenshell.entity_instance
) -> List[VerticalAlignment]:
    """Load vertical alignments nested under a horizontal alignment.

    Args:
        ifc_file: IFC file instance
        horizontal_alignment: Parent horizontal alignment

    Returns:
        List of VerticalAlignment objects
    """
    vertical_alignments = []

    for rel in horizontal_alignment.IsNestedBy or []:
        for obj in rel.RelatedObjects:
            if obj.is_a("IfcAlignmentVertical"):
                try:
                    valign = VerticalAlignment.from_ifc(obj)
                    vertical_alignments.append(valign)
                    logger.info(f"Loaded vertical alignment: {valign.name}")

                    # Create Blender Empty for visualization (via tool layer)
                    _create_blender_empty(obj, horizontal_alignment)

                except Exception as e:
                    logger.warning(
                        f"Failed to load vertical alignment {obj.Name}: {e}"
                    )

    return vertical_alignments


def _load_all_verticals(ifc_file: ifcopenshell.file) -> List[VerticalAlignment]:
    """Load all vertical alignments from file.

    Args:
        ifc_file: IFC file instance

    Returns:
        List of VerticalAlignment objects
    """
    vertical_alignments = []

    logger.debug("Loading all vertical alignments from file...")
    all_verticals = ifc_file.by_type("IfcAlignmentVertical")
    logger.debug(f"Found {len(all_verticals)} IfcAlignmentVertical entities")

    for ifc_vertical in all_verticals:
        try:
            logger.debug(f"Processing vertical alignment: {ifc_vertical.Name}")
            valign = VerticalAlignment.from_ifc(ifc_vertical)
            vertical_alignments.append(valign)
            logger.info(f"Loaded vertical alignment: {valign.name}")

            # Find parent horizontal alignment
            parent_horizontal = _find_parent_alignment(ifc_vertical)

            # Create Blender Empty (via tool layer)
            _create_blender_empty(ifc_vertical, parent_horizontal)

        except Exception as e:
            logger.error(
                f"Failed to load vertical alignment {ifc_vertical.Name}: {e}"
            )

    return vertical_alignments


def _find_parent_alignment(
    ifc_vertical: ifcopenshell.entity_instance
) -> Optional[ifcopenshell.entity_instance]:
    """Find the parent horizontal alignment for a vertical alignment.

    Args:
        ifc_vertical: IfcAlignmentVertical entity

    Returns:
        Parent IfcAlignment or None if not found
    """
    logger.debug("Looking for parent horizontal alignment...")

    for rel in ifc_vertical.Nests or []:
        logger.debug(f"  Checking relationship: {rel}")
        if rel.is_a("IfcRelNests"):
            relating_obj = rel.RelatingObject
            logger.debug(f"  Relating object: {relating_obj}")
            if relating_obj and relating_obj.is_a("IfcAlignment"):
                logger.debug(f"  Found parent horizontal: {relating_obj.Name}")
                return relating_obj

    return None


def _update_profile_view(vertical_alignments: List[VerticalAlignment]) -> None:
    """Update the profile view with loaded vertical alignments.

    Args:
        vertical_alignments: List of loaded vertical alignments
    """
    try:
        from ..profile_view_overlay import get_profile_overlay
        overlay = get_profile_overlay()

        if overlay and vertical_alignments:
            logger.debug(
                f"Adding {len(vertical_alignments)} vertical alignments "
                f"to profile view..."
            )

            # Clear existing vertical alignments
            overlay.data.clear_vertical_alignments()

            # Add each loaded vertical alignment
            for valign in vertical_alignments:
                overlay.data.add_vertical_alignment(valign)
                logger.debug(f"  Added {valign.name} to profile view")

            # Auto-select first vertical alignment
            if len(vertical_alignments) > 0:
                overlay.data.select_vertical_alignment(0)
                logger.debug(
                    f"  Selected {vertical_alignments[0].name} as active"
                )

            # Update view extents
            overlay.data.update_view_extents()

            logger.info("Profile view updated with vertical alignments")

    except Exception as e:
        logger.debug(f"Could not add vertical alignments to profile view: {e}")


# Helper functions for external use

def calculate_required_curve_length(
    grade_change_percent: float,
    k_value: float
) -> float:
    """Calculate required curve length for given K-value.

    L = K * A

    Args:
        grade_change_percent: Grade change in percent (e.g., 3.0 for 3%)
        k_value: Desired K-value (m/%)

    Returns:
        Required curve length (m)
    """
    return k_value * grade_change_percent


def calculate_k_value(
    curve_length: float,
    grade_change_percent: float
) -> float:
    """Calculate K-value for given curve length and grade change.

    K = L / A

    Args:
        curve_length: Curve length (m)
        grade_change_percent: Grade change in percent

    Returns:
        K-value (m/%)

    Raises:
        ValueError: If grade change is zero
    """
    if grade_change_percent == 0:
        raise ValueError("Cannot calculate K-value: grade change is zero")

    return curve_length / grade_change_percent


def get_minimum_k_value(design_speed: float, is_crest: bool) -> float:
    """Get minimum K-value for design speed.

    Args:
        design_speed: Design speed (km/h)
        is_crest: True for crest curve, False for sag curve

    Returns:
        Minimum K-value (m/%)

    Raises:
        ValueError: If design speed not in standards
    """
    from .constants import DESIGN_STANDARDS

    if design_speed not in DESIGN_STANDARDS:
        raise ValueError(f"No standards for design speed {design_speed} km/h")

    standards = DESIGN_STANDARDS[design_speed]
    return standards["k_crest"] if is_crest else standards["k_sag"]


__all__ = [
    "load_vertical_alignments_from_ifc",
    "calculate_required_curve_length",
    "calculate_k_value",
    "get_minimum_k_value",
]