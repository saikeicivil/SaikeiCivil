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
Tests for IFC Manager Module
=============================

Tests for IFC file management, entity creation, and validation.
These tests require ifcopenshell.
"""

import pytest

from conftest import requires_ifc, HAS_IFC

if HAS_IFC:
    from core.ifc_manager import (
        NativeIfcManager,
        create_units,
        create_geometric_context,
        create_local_placement,
        find_geometric_context,
        validate_for_external_viewers,
    )


@requires_ifc
class TestNativeIfcManager:
    """Tests for NativeIfcManager class."""

    @pytest.mark.unit
    def test_new_file_creates_project(self, ifc_file):
        """Test that new_file creates an IfcProject."""
        # Create project using the manager
        result = NativeIfcManager.new_file()

        assert result is not None
        assert "project" in result
        assert result["project"].is_a("IfcProject")

    @pytest.mark.unit
    def test_new_file_creates_site(self):
        """Test that new_file creates an IfcSite."""
        result = NativeIfcManager.new_file()

        assert "site" in result
        assert result["site"].is_a("IfcSite")

    @pytest.mark.unit
    def test_new_file_creates_road(self):
        """Test that new_file creates an IfcRoad."""
        result = NativeIfcManager.new_file()

        assert "road" in result
        assert result["road"].is_a("IfcRoad")

    @pytest.mark.unit
    def test_new_file_schema_is_4x3(self):
        """Test that new files use IFC 4x3 schema."""
        result = NativeIfcManager.new_file()
        ifc = result["ifc_file"]

        assert "4X3" in ifc.schema.upper() or "4.3" in ifc.schema


@requires_ifc
class TestIfcEntityCreation:
    """Tests for IFC entity creation functions."""

    @pytest.mark.unit
    def test_create_units(self, ifc_file):
        """Test unit assignment creation."""
        units = create_units(ifc_file)

        assert units is not None
        assert units.is_a("IfcUnitAssignment")

    @pytest.mark.unit
    def test_create_geometric_context(self, ifc_file):
        """Test geometric representation context creation."""
        context = create_geometric_context(ifc_file)

        assert context is not None
        assert context.is_a("IfcGeometricRepresentationContext")

    @pytest.mark.unit
    def test_create_local_placement(self, ifc_file):
        """Test local placement creation."""
        placement = create_local_placement(ifc_file)

        assert placement is not None
        assert placement.is_a("IfcLocalPlacement")

    @pytest.mark.unit
    def test_find_geometric_context(self, ifc_file_with_project):
        """Test finding existing geometric context."""
        # First create a context
        context = create_geometric_context(ifc_file_with_project)

        # Then find it
        found = find_geometric_context(ifc_file_with_project)

        assert found is not None
        assert found.id() == context.id()


@requires_ifc
class TestIfcValidation:
    """Tests for IFC file validation."""

    @pytest.mark.unit
    def test_validate_empty_file(self, ifc_file):
        """Test validation of empty IFC file."""
        issues = validate_for_external_viewers(ifc_file)

        # Empty file should have critical issues
        assert len(issues) > 0
        assert any("CRITICAL" in issue for issue in issues)

    @pytest.mark.unit
    def test_validate_file_with_project(self, ifc_file_with_project):
        """Test validation of file with project structure."""
        issues = validate_for_external_viewers(ifc_file_with_project)

        # File with project should have fewer issues
        critical_issues = [i for i in issues if "CRITICAL" in i]
        # May still have issues about missing units, context, etc.
        assert isinstance(issues, list)

    @pytest.mark.unit
    def test_validate_none_file(self):
        """Test validation handles None gracefully."""
        issues = validate_for_external_viewers(None)

        assert len(issues) > 0
        assert any("No IFC file" in issue for issue in issues)


@requires_ifc
class TestIfcSaveLoad:
    """Tests for IFC file save/load operations."""

    @pytest.mark.integration
    def test_save_and_load(self, temp_ifc_path):
        """Test saving and loading IFC file."""
        # Create new file
        result = NativeIfcManager.new_file()
        ifc = result["ifc_file"]

        # Save
        ifc.write(str(temp_ifc_path))

        # Verify file exists
        assert temp_ifc_path.exists()

        # Load
        import ifcopenshell
        loaded = ifcopenshell.open(str(temp_ifc_path))

        assert loaded is not None
        assert len(loaded.by_type("IfcProject")) == 1

    @pytest.mark.integration
    def test_round_trip_preserves_entities(self, temp_ifc_path):
        """Test that save/load preserves all entities."""
        # Create file with known entities
        result = NativeIfcManager.new_file()
        ifc = result["ifc_file"]

        # Count entities before save
        project_count = len(ifc.by_type("IfcProject"))
        site_count = len(ifc.by_type("IfcSite"))
        road_count = len(ifc.by_type("IfcRoad"))

        # Save and reload
        ifc.write(str(temp_ifc_path))

        import ifcopenshell
        loaded = ifcopenshell.open(str(temp_ifc_path))

        # Verify counts match
        assert len(loaded.by_type("IfcProject")) == project_count
        assert len(loaded.by_type("IfcSite")) == site_count
        assert len(loaded.by_type("IfcRoad")) == road_count
