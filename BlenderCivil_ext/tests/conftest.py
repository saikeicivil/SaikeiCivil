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
Pytest Configuration and Fixtures
==================================

Shared fixtures for BlenderCivil test suite.
"""

import sys
from pathlib import Path
from typing import Generator, Optional
from unittest.mock import MagicMock

import pytest

# Add parent directory to path for imports
EXTENSION_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(EXTENSION_ROOT))


# =============================================================================
# Skip Markers
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external deps)")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "blender: Requires Blender environment")
    config.addinivalue_line("markers", "ifc: Requires ifcopenshell")
    config.addinivalue_line("markers", "slow: Slow running tests")


# =============================================================================
# Conditional Imports
# =============================================================================

# Check if ifcopenshell is available
try:
    import ifcopenshell
    HAS_IFC = True
except ImportError:
    HAS_IFC = False
    ifcopenshell = None

# Check if bpy (Blender) is available
try:
    import bpy
    HAS_BLENDER = True
except ImportError:
    HAS_BLENDER = False
    bpy = None


# =============================================================================
# Skip Decorators
# =============================================================================

requires_ifc = pytest.mark.skipif(
    not HAS_IFC,
    reason="ifcopenshell not installed"
)

requires_blender = pytest.mark.skipif(
    not HAS_BLENDER,
    reason="Blender environment not available"
)


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_bpy() -> MagicMock:
    """Create a mock bpy module for testing without Blender.

    Returns:
        MagicMock configured with common bpy attributes
    """
    mock = MagicMock()

    # Mock common bpy.data collections
    mock.data.objects = {}
    mock.data.collections = {}
    mock.data.meshes = {}
    mock.data.curves = {}
    mock.data.materials = {}

    # Mock context
    mock.context.scene = MagicMock()
    mock.context.view_layer = MagicMock()
    mock.context.active_object = None

    # Mock ops
    mock.ops.object = MagicMock()
    mock.ops.mesh = MagicMock()

    return mock


@pytest.fixture
def mock_ifc_file() -> MagicMock:
    """Create a mock IFC file for testing without ifcopenshell.

    Returns:
        MagicMock configured as an IFC file
    """
    mock = MagicMock()
    mock.schema = "IFC4X3"
    mock.by_type.return_value = []
    mock.by_id.return_value = None
    return mock


# =============================================================================
# IFC Fixtures (require ifcopenshell)
# =============================================================================

@pytest.fixture
def ifc_file() -> Generator[Optional["ifcopenshell.file"], None, None]:
    """Create a fresh IFC 4x3 file for testing.

    Yields:
        New ifcopenshell.file instance or None if not available
    """
    if not HAS_IFC:
        yield None
        return

    file = ifcopenshell.file(schema="IFC4X3")
    yield file
    # Cleanup happens automatically when file goes out of scope


@pytest.fixture
def ifc_file_with_project(ifc_file) -> Generator[Optional["ifcopenshell.file"], None, None]:
    """Create an IFC file with basic project structure.

    Yields:
        IFC file with Project, Site, and Road entities
    """
    if ifc_file is None:
        yield None
        return

    # Create project
    project = ifc_file.create_entity(
        "IfcProject",
        GlobalId=ifcopenshell.guid.new(),
        Name="Test Project"
    )

    # Create site
    site = ifc_file.create_entity(
        "IfcSite",
        GlobalId=ifcopenshell.guid.new(),
        Name="Test Site"
    )

    # Create road
    road = ifc_file.create_entity(
        "IfcRoad",
        GlobalId=ifcopenshell.guid.new(),
        Name="Test Road"
    )

    # Create aggregation relationships
    ifc_file.create_entity(
        "IfcRelAggregates",
        GlobalId=ifcopenshell.guid.new(),
        RelatingObject=project,
        RelatedObjects=[site]
    )

    ifc_file.create_entity(
        "IfcRelAggregates",
        GlobalId=ifcopenshell.guid.new(),
        RelatingObject=site,
        RelatedObjects=[road]
    )

    yield ifc_file


# =============================================================================
# Geometry Fixtures
# =============================================================================

@pytest.fixture
def sample_pi_points() -> list:
    """Sample PI (Point of Intersection) coordinates for alignment testing.

    Returns:
        List of (x, y, z) tuples representing PI points
    """
    return [
        (0.0, 0.0, 100.0),
        (100.0, 0.0, 100.0),
        (200.0, 50.0, 102.0),
        (300.0, 100.0, 105.0),
        (400.0, 100.0, 103.0),
    ]


@pytest.fixture
def sample_pvi_data() -> list:
    """Sample PVI (Point of Vertical Intersection) data for vertical alignment.

    Returns:
        List of dicts with station, elevation, and curve length
    """
    return [
        {"station": 0.0, "elevation": 100.0, "curve_length": 0.0},
        {"station": 100.0, "elevation": 102.0, "curve_length": 50.0},
        {"station": 200.0, "elevation": 101.0, "curve_length": 60.0},
        {"station": 300.0, "elevation": 105.0, "curve_length": 80.0},
        {"station": 400.0, "elevation": 103.0, "curve_length": 0.0},
    ]


@pytest.fixture
def sample_cross_section() -> dict:
    """Sample cross-section definition.

    Returns:
        Dict with lanes, shoulders, and slopes
    """
    return {
        "lanes": [
            {"side": "LEFT", "width": 3.6, "cross_slope": -0.02},
            {"side": "RIGHT", "width": 3.6, "cross_slope": -0.02},
        ],
        "shoulders": [
            {"side": "LEFT", "width": 2.4, "cross_slope": -0.04},
            {"side": "RIGHT", "width": 2.4, "cross_slope": -0.04},
        ],
        "ditches": [
            {"side": "LEFT", "foreslope": 4.0, "depth": 0.5},
            {"side": "RIGHT", "foreslope": 4.0, "depth": 0.5},
        ],
    }


# =============================================================================
# Temporary File Fixtures
# =============================================================================

@pytest.fixture
def temp_ifc_path(tmp_path) -> Path:
    """Create a temporary path for IFC file output.

    Args:
        tmp_path: pytest's tmp_path fixture

    Returns:
        Path object for temporary IFC file
    """
    return tmp_path / "test_output.ifc"


# =============================================================================
# Export fixtures for use in test files
# =============================================================================

__all__ = [
    "requires_ifc",
    "requires_blender",
    "mock_bpy",
    "mock_ifc_file",
    "ifc_file",
    "ifc_file_with_project",
    "sample_pi_points",
    "sample_pvi_data",
    "sample_cross_section",
    "temp_ifc_path",
    "HAS_IFC",
    "HAS_BLENDER",
]
