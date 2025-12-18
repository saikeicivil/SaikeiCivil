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
Alignment Stationing Module
============================

Manages stationing (chainage) for horizontal alignments using IFC Referents.
Supports station equations (chainage breaks) per IFC 4.3 specification.

IFC Implementation:
- IfcReferent entities with PredefinedType="STATION"
- Pset_Stationing property set for station values
- IfcLinearPlacement for positioning along alignment
"""

import logging
from typing import List, Optional

import ifcopenshell
import ifcopenshell.guid

logger = logging.getLogger(__name__)


class StationingManager:
    """Manages stationing (chainage) for an alignment.

    Handles creation, modification, and querying of station values along
    an alignment, including station equations (chainage breaks).

    Attributes:
        referents: List of referent data dictionaries

    Example:
        >>> stationing = StationingManager(ifc_file, alignment)
        >>> stationing.set_starting_station(10000.0)  # 10+000
        >>> station = stationing.get_station_at_distance(150.0)
        >>> print(f"Station at 150m: {station:.2f}")  # 10150.0
    """

    def __init__(
        self,
        ifc_file: ifcopenshell.file,
        alignment: ifcopenshell.entity_instance
    ):
        """Initialize stationing manager.

        Args:
            ifc_file: Active IFC file
            alignment: IfcAlignment entity to manage stationing for
        """
        self.ifc = ifc_file
        self.alignment = alignment
        self.referents: List[dict] = []

    def set_starting_station(self, station_value: float) -> None:
        """Set the starting station of the alignment.

        Creates an IfcReferent at distance_along = 0.0 with the specified
        station value. Per IFC 4.3, the first referent defines starting station.

        Args:
            station_value: Station value at alignment start (e.g., 10000.0 for 10+000)
        """
        # Remove existing starting station referent
        self.referents = [r for r in self.referents if r['distance_along'] != 0.0]

        referent_data = {
            'distance_along': 0.0,
            'station': float(station_value),
            'incoming_station': None,
            'description': 'Starting Station',
            'ifc_referent': None
        }

        self.referents.insert(0, referent_data)
        self._sort_referents()
        self._update_referent_entities()

        logger.info(f"Set starting station to {station_value:.2f}")

    def add_station_equation(
        self,
        distance_along: float,
        incoming_station: float,
        outgoing_station: float,
        description: str = "Station Equation"
    ) -> None:
        """Add a station equation (chainage break).

        Station equations are used when station values need to jump,
        such as for route continuity or phase boundaries.

        Args:
            distance_along: Distance along alignment where equation occurs (m)
            incoming_station: Station value approaching this point
            outgoing_station: Station value leaving this point
            description: Optional description

        Example:
            >>> # At 500m, station jumps from 5+00 to 10+00
            >>> stationing.add_station_equation(500.0, 500.0, 1000.0)
        """
        referent_data = {
            'distance_along': float(distance_along),
            'station': float(outgoing_station),
            'incoming_station': float(incoming_station),
            'description': description,
            'ifc_referent': None
        }

        # Remove existing equation at this distance
        self.referents = [
            r for r in self.referents
            if r['distance_along'] != distance_along
        ]

        self.referents.append(referent_data)
        self._sort_referents()
        self._update_referent_entities()

        logger.info(
            f"Added station equation at {distance_along:.2f}m: "
            f"{incoming_station:.2f} -> {outgoing_station:.2f}"
        )

    def remove_station_equation(self, distance_along: float) -> bool:
        """Remove a station equation at the specified distance.

        Args:
            distance_along: Distance where the equation exists

        Returns:
            True if equation was removed, False if not found
        """
        initial_count = len(self.referents)

        # Don't remove starting station (distance 0)
        self.referents = [
            r for r in self.referents
            if r['distance_along'] != distance_along or r['distance_along'] == 0.0
        ]

        removed = len(self.referents) < initial_count

        if removed:
            self._update_referent_entities()
            logger.info(f"Removed station equation at {distance_along:.2f}m")

        return removed

    def get_station_at_distance(self, distance_along: float) -> float:
        """Calculate station value at a given distance along alignment.

        Accounts for station equations.

        Args:
            distance_along: Distance along alignment (meters)

        Returns:
            Station value at that distance
        """
        if not self.referents:
            return distance_along

        # Find applicable referent (last one at or before this distance)
        applicable_referent = None
        for ref in reversed(self.referents):
            if ref['distance_along'] <= distance_along:
                applicable_referent = ref
                break

        if not applicable_referent:
            # Before first referent, extrapolate backwards
            first_ref = self.referents[0]
            delta = distance_along - first_ref['distance_along']
            return first_ref['station'] + delta

        # Calculate station from applicable referent
        delta = distance_along - applicable_referent['distance_along']
        return applicable_referent['station'] + delta

    def get_distance_at_station(self, station_value: float) -> Optional[float]:
        """Calculate distance along alignment at a given station value.

        Inverse of get_station_at_distance. Accounts for station equations.

        Args:
            station_value: Station value to find

        Returns:
            Distance along alignment (meters), or None if not in range
        """
        if not self.referents:
            return station_value

        # Find which segment this station falls in
        for i, current_ref in enumerate(self.referents):
            if i == len(self.referents) - 1:
                # Last referent - extrapolate forward
                if station_value >= current_ref['station']:
                    delta = station_value - current_ref['station']
                    return current_ref['distance_along'] + delta
            else:
                next_ref = self.referents[i + 1]
                next_station = next_ref.get('incoming_station', next_ref['station'])

                if current_ref['station'] <= station_value < next_station:
                    delta = station_value - current_ref['station']
                    return current_ref['distance_along'] + delta

        # Station before first referent
        first_ref = self.referents[0]
        if station_value < first_ref['station']:
            delta = station_value - first_ref['station']
            return first_ref['distance_along'] + delta

        return None

    def load_from_ifc(self) -> None:
        """Load stationing referents from existing IFC alignment."""
        if not self.alignment:
            return

        self.referents = []

        for rel in self.alignment.IsNestedBy or []:
            if rel.Name == "AlignmentToReferents":
                for obj in rel.RelatedObjects:
                    if obj.is_a("IfcReferent") and obj.PredefinedType == "STATION":
                        self._parse_referent(obj)

        self._sort_referents()

        if self.referents:
            logger.info(
                f"Loaded {len(self.referents)} stationing referents from IFC"
            )
        else:
            logger.debug("No stationing referents found, setting default 10+000")
            self.set_starting_station(10000.0)

    def _parse_referent(self, referent: ifcopenshell.entity_instance) -> None:
        """Parse an IfcReferent entity into referent data."""
        station_value = None
        incoming_station = None
        distance_along = 0.0

        for rel_def in referent.IsDefinedBy or []:
            if rel_def.is_a("IfcRelDefinesByProperties"):
                pset = rel_def.RelatingPropertyDefinition
                if pset.is_a("IfcPropertySet") and pset.Name == "Pset_Stationing":
                    for prop in pset.HasProperties:
                        if prop.Name == "Station":
                            station_value = float(prop.NominalValue.wrappedValue)
                        elif prop.Name == "IncomingStation":
                            incoming_station = float(prop.NominalValue.wrappedValue)
                        elif prop.Name == "DistanceAlong":
                            distance_along = float(prop.NominalValue.wrappedValue)

        if station_value is not None:
            self.referents.append({
                'distance_along': distance_along,
                'station': station_value,
                'incoming_station': incoming_station,
                'description': referent.Name or "Station Referent",
                'ifc_referent': referent
            })

    def _sort_referents(self) -> None:
        """Sort referents by distance_along (required by IFC spec)."""
        self.referents.sort(key=lambda r: r['distance_along'])

    def _update_referent_entities(self) -> None:
        """Create/update IFC IfcReferent entities with Pset_Stationing."""
        if not self.alignment:
            return

        # Remove old referent entities
        self._remove_old_referents()

        # Get basis curve for linear placement
        basis_curve = self._get_basis_curve()

        # Create new referent entities
        referent_entities = []
        for ref_data in self.referents:
            referent = self._create_referent_entity(ref_data, basis_curve)
            referent_entities.append(referent)
            ref_data['ifc_referent'] = referent

        # Create nesting relationship
        if referent_entities:
            self.ifc.create_entity(
                "IfcRelNests",
                GlobalId=ifcopenshell.guid.new(),
                Name="AlignmentToReferents",
                RelatingObject=self.alignment,
                RelatedObjects=referent_entities
            )

            logger.debug(
                f"Created {len(referent_entities)} IFC referents with stationing"
            )

    def _remove_old_referents(self) -> None:
        """Remove old referent entities from IFC file."""
        old_referents = []
        for rel in self.alignment.IsNestedBy or []:
            if rel.Name == "AlignmentToReferents":
                old_referents.extend(rel.RelatedObjects)
                self.ifc.remove(rel)

        for ref in old_referents:
            if ref.is_a("IfcReferent"):
                for rel_def in ref.IsDefinedBy or []:
                    if rel_def.is_a("IfcRelDefinesByProperties"):
                        self.ifc.remove(rel_def.RelatingPropertyDefinition)
                        self.ifc.remove(rel_def)
                self.ifc.remove(ref)

    def _create_referent_entity(
        self,
        ref_data: dict,
        basis_curve: Optional[ifcopenshell.entity_instance]
    ) -> ifcopenshell.entity_instance:
        """Create a single IfcReferent entity with properties."""
        referent = self.ifc.create_entity(
            "IfcReferent",
            GlobalId=ifcopenshell.guid.new(),
            Name=ref_data['description'],
            PredefinedType="STATION"
        )

        # Create linear placement if basis curve exists
        if basis_curve:
            self._create_linear_placement(referent, ref_data, basis_curve)
        else:
            # IfcReferent requires ObjectPlacement (WHERE rule: HasPlacement)
            # Create a simple IfcLocalPlacement at origin as fallback
            self._create_local_placement(referent)

        # Create Pset_Stationing
        self._create_stationing_pset(referent, ref_data)

        return referent

    def _create_local_placement(
        self,
        referent: ifcopenshell.entity_instance
    ) -> None:
        """Create a fallback IfcLocalPlacement at origin for referent.

        IfcReferent inherits from IfcPositioningElement which has a WHERE rule:
        HasPlacement: EXISTS(SELF\\IfcProduct.ObjectPlacement)

        This creates a simple placement at origin when linear placement
        cannot be created (e.g., when basis curve is not available).
        """
        # Get alignment's placement if available
        placement_rel_to = None
        if self.alignment and hasattr(self.alignment, 'ObjectPlacement'):
            placement_rel_to = self.alignment.ObjectPlacement

        axis_placement = self.ifc.create_entity(
            "IfcAxis2Placement3D",
            Location=self.ifc.create_entity(
                "IfcCartesianPoint",
                Coordinates=(0.0, 0.0, 0.0)
            )
        )

        local_placement = self.ifc.create_entity(
            "IfcLocalPlacement",
            PlacementRelTo=placement_rel_to,
            RelativePlacement=axis_placement
        )

        referent.ObjectPlacement = local_placement

    def _create_linear_placement(
        self,
        referent: ifcopenshell.entity_instance,
        ref_data: dict,
        basis_curve: ifcopenshell.entity_instance
    ) -> None:
        """Create IfcLinearPlacement for referent."""
        point_by_distance = self.ifc.create_entity(
            "IfcPointByDistanceExpression",
            DistanceAlong=float(ref_data['distance_along']),
            OffsetLateral=0.0,
            OffsetVertical=0.0,
            OffsetLongitudinal=0.0,
            BasisCurve=basis_curve
        )

        axis_placement = self.ifc.create_entity(
            "IfcAxis2PlacementLinear",
            Location=point_by_distance,
            Axis=None,
            RefDirection=None
        )

        linear_placement = self.ifc.create_entity(
            "IfcLinearPlacement",
            PlacementRelTo=None,
            RelativePlacement=axis_placement
        )

        referent.ObjectPlacement = linear_placement

    def _create_stationing_pset(
        self,
        referent: ifcopenshell.entity_instance,
        ref_data: dict
    ) -> None:
        """Create Pset_Stationing property set for referent."""
        station_props = []

        # Station property (required)
        station_props.append(
            self.ifc.create_entity(
                "IfcPropertySingleValue",
                Name="Station",
                NominalValue=self.ifc.create_entity(
                    "IfcLengthMeasure", ref_data['station']
                )
            )
        )

        # IncomingStation (for station equations)
        if ref_data['incoming_station'] is not None:
            station_props.append(
                self.ifc.create_entity(
                    "IfcPropertySingleValue",
                    Name="IncomingStation",
                    NominalValue=self.ifc.create_entity(
                        "IfcLengthMeasure", ref_data['incoming_station']
                    )
                )
            )

        # HasIncreasingStation (standard Pset_Stationing property)
        station_props.append(
            self.ifc.create_entity(
                "IfcPropertySingleValue",
                Name="HasIncreasingStation",
                NominalValue=self.ifc.create_entity("IfcBoolean", True)
            )
        )

        pset = self.ifc.create_entity(
            "IfcPropertySet",
            GlobalId=ifcopenshell.guid.new(),
            Name="Pset_Stationing",
            HasProperties=station_props
        )

        self.ifc.create_entity(
            "IfcRelDefinesByProperties",
            GlobalId=ifcopenshell.guid.new(),
            RelatedObjects=[referent],
            RelatingPropertyDefinition=pset
        )

    def _get_basis_curve(self) -> Optional[ifcopenshell.entity_instance]:
        """Get the basis curve from alignment representation."""
        if not self.alignment:
            return None

        if not hasattr(self.alignment, 'Representation'):
            return None
        if not self.alignment.Representation:
            return None

        product_shape = self.alignment.Representation
        if not product_shape.is_a("IfcProductDefinitionShape"):
            return None

        for representation in product_shape.Representations:
            if representation.is_a("IfcShapeRepresentation"):
                for item in representation.Items:
                    if item.is_a("IfcCompositeCurve"):
                        return item
                    elif item.is_a("IfcGradientCurve"):
                        return item.BaseCurve

        return None


__all__ = ["StationingManager"]
