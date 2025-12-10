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
IFC Validation Module
======================

Validation functions for ensuring IFC files work with external viewers
(Solibri, FreeCAD, BIMcollab, etc.).
"""

import logging
from typing import List

import ifcopenshell

logger = logging.getLogger(__name__)


def validate_for_external_viewers(ifc_file: ifcopenshell.file) -> List[str]:
    """Validate IFC file will work in external viewers.

    Checks for common issues that prevent files from displaying correctly
    in Solibri, FreeCAD, BIMcollab, etc.

    Args:
        ifc_file: IFC file to validate

    Returns:
        List of issue strings (empty if valid)
    """
    if not ifc_file:
        return ["CRITICAL: No IFC file loaded"]

    issues = []

    # Check project
    issues.extend(_validate_project(ifc_file))

    # Check spatial containment
    issues.extend(_validate_spatial_containment(ifc_file))

    # Check alignments
    issues.extend(_validate_alignments(ifc_file))

    # Check Site and Road placements
    issues.extend(_validate_placements(ifc_file))

    return issues


def _validate_project(ifc_file: ifcopenshell.file) -> List[str]:
    """Validate IfcProject requirements."""
    issues = []

    projects = ifc_file.by_type("IfcProject")
    if not projects:
        issues.append("CRITICAL: No IfcProject found")
        return issues

    project = projects[0]

    if not project.UnitsInContext:
        issues.append(
            "CRITICAL: Project missing UnitsInContext (units not defined)"
        )

    if not project.RepresentationContexts:
        issues.append(
            "CRITICAL: Project missing RepresentationContexts "
            "(geometry won't display)"
        )

    return issues


def _validate_spatial_containment(ifc_file: ifcopenshell.file) -> List[str]:
    """Validate spatial containment relationships.

    Note: This function currently only collects data for _validate_alignments.
    The actual containment validation is done there.
    """
    # This function doesn't produce issues directly - the containment
    # check is handled by _validate_alignments which has its own logic
    return []


def _validate_alignments(ifc_file: ifcopenshell.file) -> List[str]:
    """Validate alignment entities."""
    issues = []

    # Get contained element IDs
    containments = ifc_file.by_type("IfcRelContainedInSpatialStructure")
    contained_ids = set()
    for rel in containments:
        if rel.RelatedElements:
            for elem in rel.RelatedElements:
                contained_ids.add(elem.id())

    # Check each alignment
    alignments = ifc_file.by_type("IfcAlignment")
    for alignment in alignments:
        name = alignment.Name or f"#{alignment.id()}"

        if alignment.id() not in contained_ids:
            issues.append(
                f"CRITICAL: {name} not in spatial structure "
                f"(missing IfcRelContainedInSpatialStructure)"
            )

        if not alignment.ObjectPlacement:
            issues.append(
                f"CRITICAL: {name} missing ObjectPlacement "
                f"(position undefined)"
            )

        if not alignment.Representation:
            issues.append(
                f"WARNING: {name} missing Representation "
                f"(geometry won't display)"
            )

    return issues


def _validate_placements(ifc_file: ifcopenshell.file) -> List[str]:
    """Validate Site and Road placements."""
    issues = []

    sites = ifc_file.by_type("IfcSite")
    if sites and not sites[0].ObjectPlacement:
        issues.append("WARNING: IfcSite missing ObjectPlacement")

    roads = ifc_file.by_type("IfcRoad")
    if roads and not roads[0].ObjectPlacement:
        issues.append("WARNING: IfcRoad missing ObjectPlacement")

    return issues


def validate_and_report(ifc_file: ifcopenshell.file) -> bool:
    """Validate IFC file and print formatted report.

    Args:
        ifc_file: IFC file to validate

    Returns:
        True if valid (no critical issues), False otherwise
    """
    issues = validate_for_external_viewers(ifc_file)

    if not issues:
        logger.info("IFC file validated - ready for external viewers")
        return True

    critical_count = sum(1 for i in issues if i.startswith("CRITICAL"))
    warning_count = sum(1 for i in issues if i.startswith("WARNING"))

    logger.warning(
        f"IFC Validation: {critical_count} critical, {warning_count} warnings"
    )
    for issue in issues:
        if issue.startswith("CRITICAL"):
            logger.error(f"  {issue}")
        else:
            logger.warning(f"  {issue}")

    return critical_count == 0


__all__ = [
    "validate_for_external_viewers",
    "validate_and_report",
]
