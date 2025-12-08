# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under Apache License 2.0
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
Tool layer - Blender-specific implementations of core interfaces.

This module provides the bridge between pure business logic (core) and
Blender-specific functionality. Tools implement the interfaces defined
in core.tool and handle all Blender API interactions.

Usage:
    import saikei_civil.tool as tool

    # Get the current IFC file
    ifc_file = tool.Ifc.get()

    # Run an ifcopenshell.api command
    alignment = tool.Ifc.run("alignment.create", name="Main Road")

    # Create a Blender object
    obj = tool.Blender.create_object("MyObject")

    # In core functions, tools are passed as parameters:
    def my_core_function(ifc: type[tool.Ifc], blender: type[tool.Blender]):
        file = ifc.get()
        obj = blender.create_object("Test")
"""

from .ifc import Ifc
from .blender import Blender
from .alignment import Alignment
from .vertical_alignment import VerticalAlignment
from .georeference import Georeference
from .cross_section import CrossSection
from .corridor import Corridor
from .spatial import Spatial
from .visualizer import Visualizer

__all__ = [
    "Ifc",
    "Blender",
    "Alignment",
    "VerticalAlignment",
    "Georeference",
    "CrossSection",
    "Corridor",
    "Spatial",
    "Visualizer",
]


def register():
    """Register tool layer (no-op for now)."""
    pass


def unregister():
    """Unregister tool layer (no-op for now)."""
    pass