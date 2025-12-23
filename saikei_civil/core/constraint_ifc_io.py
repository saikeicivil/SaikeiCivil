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
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================

"""
Constraint IFC I/O Module
=========================

Handles IFC import/export of parametric constraints.

Constraints are stored in a custom property set attached to IfcRoad or IfcAlignment
entities. This ensures data persistence in the IFC file (source of truth) while
maintaining interoperability with other IFC tools.

This module is part of the CORE layer - uses ifcopenshell but NO Blender dependencies.

Property Set Structure:
    SaikeiCivil_ParametricConstraints
    +-- Version: "1.0"
    +-- CreatedBy: "Saikei Civil"
    +-- LastModified: ISO datetime
    +-- ConstraintCount: integer
    +-- ConstraintsJSON: JSON-encoded constraint array

IMPORTANT: Uses "SaikeiCivil_" prefix (NOT "Pset_") because this is a custom
property set, not a standard IFC property set.

Example Usage:
    >>> from saikei_civil.core.constraint_ifc_io import ConstraintIFCHandler
    >>> from saikei_civil.core.parametric_constraints import ConstraintManager
    >>>
    >>> # Export constraints to IFC
    >>> handler = ConstraintIFCHandler(ifc_file)
    >>> pset = handler.export_constraints(manager, road_entity)
    >>>
    >>> # Import constraints from IFC
    >>> manager = handler.import_constraints(road_entity)
"""

import json
from datetime import datetime
from typing import Optional, List, Any

import ifcopenshell
import ifcopenshell.guid

from .parametric_constraints import ParametricConstraint, ConstraintManager


class ConstraintIFCHandler:
    """
    Handles IFC import/export of parametric constraints.

    Stores constraints in a custom property set attached to the
    IfcRoad or IfcAlignment entity.

    This is a CORE layer class - no Blender dependencies.

    Attributes:
        ifc_file: IfcOpenShell file object
        PSET_NAME: Name of the custom property set
    """

    PSET_NAME = "SaikeiCivil_ParametricConstraints"
    VERSION = "1.0"

    def __init__(self, ifc_file):
        """
        Initialize handler with IFC file.

        Args:
            ifc_file: IfcOpenShell file object
        """
        self.ifc_file = ifc_file

    def export_constraints(
        self,
        manager: ConstraintManager,
        target_entity,
        replace_existing: bool = True
    ) -> Optional[Any]:
        """
        Export constraints to IFC property set.

        Creates a property set containing all constraints serialized as JSON,
        then associates it with the target entity (IfcRoad or IfcAlignment).

        Args:
            manager: ConstraintManager with constraints to export
            target_entity: IfcRoad or IfcAlignment to attach constraints to
            replace_existing: If True, removes existing constraint pset first

        Returns:
            Created IfcPropertySet entity, or None on failure
        """
        if not self.ifc_file:
            return None

        if not target_entity:
            return None

        # Remove existing constraint property set if requested
        if replace_existing:
            self._remove_existing_pset(target_entity)

        # Create properties list
        properties = []

        # Version property
        properties.append(self._create_property(
            "Version",
            "IfcLabel",
            self.VERSION
        ))

        # Created by property
        properties.append(self._create_property(
            "CreatedBy",
            "IfcLabel",
            "Saikei Civil"
        ))

        # Last modified property
        properties.append(self._create_property(
            "LastModified",
            "IfcLabel",
            datetime.now().isoformat()
        ))

        # Constraint count property
        properties.append(self._create_property(
            "ConstraintCount",
            "IfcInteger",
            len(manager.constraints)
        ))

        # Serialize all constraints as JSON
        constraints_data = manager.to_list()
        constraints_json = json.dumps(constraints_data, indent=None)

        properties.append(self._create_property(
            "ConstraintsJSON",
            "IfcText",
            constraints_json
        ))

        # Create property set
        owner_history = self._get_owner_history()

        pset = self.ifc_file.create_entity(
            "IfcPropertySet",
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=owner_history,
            Name=self.PSET_NAME,
            Description="Parametric cross-section constraints for corridor generation",
            HasProperties=properties
        )

        # Associate property set with target entity
        self.ifc_file.create_entity(
            "IfcRelDefinesByProperties",
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=owner_history,
            RelatedObjects=[target_entity],
            RelatingPropertyDefinition=pset
        )

        return pset

    def import_constraints(self, target_entity) -> Optional[ConstraintManager]:
        """
        Import constraints from IFC property set.

        Reads the constraint property set from the target entity and
        deserializes the JSON data into a ConstraintManager.

        Args:
            target_entity: IfcRoad or IfcAlignment to read constraints from

        Returns:
            ConstraintManager with loaded constraints, or None if not found
        """
        if not self.ifc_file:
            return None

        if not target_entity:
            return None

        # Find the property set
        pset = self._find_constraint_pset(target_entity)
        if not pset:
            return None

        # Find the JSON property
        constraints_json = None
        for prop in pset.HasProperties:
            if prop.Name == "ConstraintsJSON":
                # Handle different IFC value wrapping styles
                nominal_value = prop.NominalValue
                if hasattr(nominal_value, 'wrappedValue'):
                    constraints_json = nominal_value.wrappedValue
                else:
                    constraints_json = str(nominal_value)
                break

        if not constraints_json:
            return None

        # Parse and create constraints
        try:
            constraints_data = json.loads(constraints_json)
            manager = ConstraintManager.from_list(constraints_data)
            return manager
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error parsing constraints from IFC: {e}")
            return None

    def has_constraints(self, target_entity) -> bool:
        """
        Check if an entity has a constraint property set.

        Args:
            target_entity: IfcRoad or IfcAlignment to check

        Returns:
            True if constraint property set exists
        """
        return self._find_constraint_pset(target_entity) is not None

    def get_constraint_count(self, target_entity) -> int:
        """
        Get the number of constraints on an entity without loading all data.

        Args:
            target_entity: IfcRoad or IfcAlignment to check

        Returns:
            Number of constraints, or 0 if none
        """
        pset = self._find_constraint_pset(target_entity)
        if not pset:
            return 0

        for prop in pset.HasProperties:
            if prop.Name == "ConstraintCount":
                nominal_value = prop.NominalValue
                if hasattr(nominal_value, 'wrappedValue'):
                    return int(nominal_value.wrappedValue)
                return int(nominal_value)

        return 0

    def remove_constraints(self, target_entity) -> bool:
        """
        Remove all constraints from an entity.

        Args:
            target_entity: IfcRoad or IfcAlignment to remove constraints from

        Returns:
            True if removed, False if none existed
        """
        return self._remove_existing_pset(target_entity)

    def _create_property(
        self,
        name: str,
        value_type: str,
        value: Any
    ) -> Any:
        """
        Create an IFC property single value.

        Args:
            name: Property name
            value_type: IFC value type (IfcLabel, IfcText, IfcInteger, etc.)
            value: Property value

        Returns:
            IfcPropertySingleValue entity
        """
        # Create the nominal value based on type
        if value_type == "IfcInteger":
            nominal_value = self.ifc_file.create_entity("IfcInteger", int(value))
        elif value_type == "IfcReal":
            nominal_value = self.ifc_file.create_entity("IfcReal", float(value))
        elif value_type == "IfcBoolean":
            nominal_value = self.ifc_file.create_entity("IfcBoolean", bool(value))
        elif value_type == "IfcText":
            nominal_value = self.ifc_file.create_entity("IfcText", str(value))
        else:
            # Default to IfcLabel for string values
            nominal_value = self.ifc_file.create_entity("IfcLabel", str(value))

        return self.ifc_file.create_entity(
            "IfcPropertySingleValue",
            Name=name,
            NominalValue=nominal_value
        )

    def _find_constraint_pset(self, entity) -> Optional[Any]:
        """
        Find the constraint property set on an entity.

        Args:
            entity: IFC entity to search

        Returns:
            IfcPropertySet or None if not found
        """
        # Search through IfcRelDefinesByProperties relationships
        for rel in self.ifc_file.by_type("IfcRelDefinesByProperties"):
            if entity in rel.RelatedObjects:
                pset = rel.RelatingPropertyDefinition
                # Check if it's a PropertySet (not PropertySetTemplate)
                if pset.is_a("IfcPropertySet"):
                    if hasattr(pset, 'Name') and pset.Name == self.PSET_NAME:
                        return pset
        return None

    def _remove_existing_pset(self, entity) -> bool:
        """
        Remove existing constraint property set from an entity.

        Args:
            entity: IFC entity to remove pset from

        Returns:
            True if removed, False if none existed
        """
        pset = self._find_constraint_pset(entity)
        if not pset:
            return False

        # Find and remove the relationship
        for rel in self.ifc_file.by_type("IfcRelDefinesByProperties"):
            if pset == rel.RelatingPropertyDefinition:
                # Remove the relationship
                self.ifc_file.remove(rel)
                break

        # Remove the property set and its properties
        if hasattr(pset, 'HasProperties'):
            for prop in pset.HasProperties:
                if hasattr(prop, 'NominalValue') and prop.NominalValue:
                    # Don't remove shared values
                    pass
                self.ifc_file.remove(prop)

        self.ifc_file.remove(pset)
        return True

    def _get_owner_history(self) -> Optional[Any]:
        """
        Get or create owner history for new entities.

        Returns:
            IfcOwnerHistory entity or None
        """
        histories = self.ifc_file.by_type("IfcOwnerHistory")
        if histories:
            return histories[0]
        return None


def export_constraints_to_ifc(
    ifc_file,
    manager: ConstraintManager,
    target_entity
) -> Optional[Any]:
    """
    Convenience function to export constraints to IFC.

    Args:
        ifc_file: IfcOpenShell file object
        manager: ConstraintManager with constraints to export
        target_entity: IfcRoad or IfcAlignment to attach to

    Returns:
        Created IfcPropertySet entity, or None on failure
    """
    handler = ConstraintIFCHandler(ifc_file)
    return handler.export_constraints(manager, target_entity)


def import_constraints_from_ifc(
    ifc_file,
    target_entity
) -> Optional[ConstraintManager]:
    """
    Convenience function to import constraints from IFC.

    Args:
        ifc_file: IfcOpenShell file object
        target_entity: IfcRoad or IfcAlignment to read from

    Returns:
        ConstraintManager with loaded constraints, or None if not found
    """
    handler = ConstraintIFCHandler(ifc_file)
    return handler.import_constraints(target_entity)
