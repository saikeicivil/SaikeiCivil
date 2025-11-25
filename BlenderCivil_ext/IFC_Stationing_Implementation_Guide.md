# IFC Stationing Implementation Guide
## BlenderCivil Native IFC Alignment Stationing System

**Document Version:** 1.0  
**Date:** 2024-11-19  
**Author:** BlenderCivil Development Team  
**Purpose:** Technical specification for implementing IFC 4.3 compliant stationing system

---

## Table of Contents

1. [Overview](#overview)
2. [IFC 4.3 Stationing Specification](#ifc-43-stationing-specification)
3. [Architecture & Design](#architecture--design)
4. [Implementation Details](#implementation-details)
5. [Integration with Existing Systems](#integration-with-existing-systems)
6. [Blender Visualization](#blender-visualization)
7. [Testing & Validation](#testing--validation)
8. [Code Examples](#code-examples)
9. [References](#references)

---

## Overview

### What is Stationing?

**Stationing** (also called **chainage** in international practice) is the linear measurement system used in civil engineering to locate points along an alignment. In the US, stations are typically expressed as:
- `0+00` = 0 feet from alignment start
- `1+00` = 100 feet from alignment start
- `10+50.25` = 1,050.25 feet from alignment start

In metric (SI) systems:
- `0+000` = 0 meters from alignment start
- `1+000` = 1,000 meters from alignment start
- `2+345.67` = 2,345.67 meters from alignment start

### Purpose in BlenderCivil

Stationing serves multiple critical functions:

1. **Reference System**: Primary method for locating features along alignments
2. **Communication**: Common language between designers, contractors, and stakeholders
3. **Object Placement**: Positions elements relative to alignment (IfcLinearPlacement)
4. **Documentation**: Ties plans, profiles, and cross-sections together
5. **Construction Layout**: Field staking and as-built verification

### Dual Nature of Stationing

Stationing has **two distinct aspects** that must both be implemented:

| Aspect | Storage | Purpose | Export to IFC |
|--------|---------|---------|---------------|
| **Semantic Data** | IFC File | Station values, equations, positioning data | ✅ YES |
| **Visual Markers** | Blender Scene | Tick marks, labels, annotations | ❌ NO |

---

## IFC 4.3 Stationing Specification

### Core Entities

#### 1. IfcReferent

**Definition:** Defines a position at a particular offset along an alignment curve.

**Key Characteristics:**
- Subtype of `IfcPositioningElement`
- Can represent various reference points along alignments
- Nested to `IfcAlignment` via `IfcRelNests` (ordered list)
- Uses `IfcLinearPlacement` for geometric positioning

**PredefinedType Enumeration:**
```
STATION          - Station/chainage markers
REFERENCEMARKER  - Reference markers
POSITION         - Generic position markers  
BLISTERMARKER    - Blister markers
MILEPOST         - Mile posts
NOTDEFINED       - Not defined
USERDEFINED      - User defined
```

For stationing purposes, use: **`STATION`**

**IFC Schema Definition:**
```express
ENTITY IfcReferent
  SUBTYPE OF (IfcPositioningElement);
  PredefinedType : OPTIONAL IfcReferentTypeEnum;
  RestartDistance : OPTIONAL IfcLengthMeasure;
END_ENTITY;
```

#### 2. IfcRelNests

**Critical Importance:** IfcRelNests maintains an **ORDERED LIST** of related objects.

**For Stationing:**
```
IfcAlignment
  └── IfcRelNests
      ├── RelatingObject: IfcAlignment
      └── RelatedObjects: [IfcReferent] (ORDERED LIST)
          ├── [0]: First station (starting station)
          ├── [1]: Second station
          ├── [2]: Third station
          └── ...
```

**Order Rules:**
1. First referent in list = starting station of alignment
2. Subsequent referents must be in ascending order of `DistanceAlong`
3. Station values can increase or decrease (controlled by `IncrementOrder`)

#### 3. Pset_Stationing

**Definition:** Property set that specifies stationing parameters for IfcReferent.

**Properties:**

| Property | Type | Data Type | Description |
|----------|------|-----------|-------------|
| `Station` | Required | `IfcLengthMeasure` | The station value at this location (e.g., 100.0 for station 1+00) |
| `IncomingStation` | Optional | `IfcLengthMeasure` | Station value of incoming segment (for station equations) |
| `IncrementOrder` | Optional | `IfcBoolean` | True = increasing stations (default), False = decreasing stations |

**Station Equations (Breaks in Chainage):**

Station equations occur when stationing needs to "jump" due to:
- Project phasing requirements
- Matching existing infrastructure
- Maintaining legacy station references

**Example:**
```
Regular flow:    ... 10+00 → 11+00 → 12+00 ...
Station equation: ... 10+00 → 15+00 → 16+00 ...
                        ↑ Station equation at this point
```

At the equation point, create an IfcReferent with:
- `IncomingStation`: 11+00 (what it "should" be)
- `Station`: 15+00 (what it "becomes")

#### 4. IfcLinearPlacement

**Purpose:** Positions the IfcReferent along the alignment's basis curve.

**Structure:**
```
IfcLinearPlacement
  ├── PlacementRelTo: IfcObjectPlacement (typically NULL = alignment start)
  └── RelativePlacement: IfcAxis2PlacementLinear
      ├── Location: IfcPointByDistanceExpression
      │   ├── DistanceAlong: IfcLengthMeasure (geometric position)
      │   ├── OffsetLateral: IfcLengthMeasure (optional, typically 0.0)
      │   ├── OffsetVertical: IfcLengthMeasure (optional, typically 0.0)
      │   └── OffsetLongitudinal: IfcLengthMeasure (optional, typically 0.0)
      ├── Axis: IfcDirection (optional)
      └── RefDirection: IfcDirection (optional, tangent to curve)
```

**Key Point:** `DistanceAlong` is the **geometric distance** from alignment start, while `Pset_Stationing.Station` is the **semantic station value**. These are usually equal but diverge at station equations.

---

## Architecture & Design

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     BlenderCivil Stationing System              │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
        ┌───────▼────────┐         ┌───────▼────────┐
        │   IFC Native   │         │    Blender     │
        │   Stationing   │         │  Visualization │
        │   (Core Data)  │         │   (UI/Display) │
        └───────┬────────┘         └───────┬────────┘
                │                           │
    ┌───────────┼───────────┐              │
    │           │           │              │
┌───▼───┐  ┌───▼───┐  ┌───▼───┐      ┌───▼────┐
│IfcRef │  │ Pset_ │  │ IfcLin│      │ Marker │
│erent  │  │Station│  │Placem │      │Objects │
│Creation│  │  ing  │  │  ent  │      │        │
└───────┘  └───────┘  └───────┘      └────────┘
```

### File Organization

Based on BlenderCivil's established patterns (Bonsai BIM structure):

```
blendercivil/
├── core/
│   ├── native_ifc_stationing.py          # NEW: Core stationing logic
│   ├── native_ifc_alignment.py           # Existing: Alignment base
│   ├── native_ifc_horizontal.py          # Existing: H alignment
│   └── native_ifc_vertical.py            # Existing: V alignment
│
├── operators/
│   ├── stationing_operators.py           # NEW: Blender operators
│   ├── add_station.py                    # NEW: Add individual station
│   ├── generate_stations.py              # NEW: Auto-generate stations
│   └── edit_station.py                   # NEW: Edit station properties
│
└── ui/
    ├── panels/
    │   └── stationing_panel.py           # NEW: UI panel
    └── visualization/
        └── station_markers.py            # NEW: Visual markers
```

### Class Structure

#### Core Classes

```python
# core/native_ifc_stationing.py

class NativeIfcStationing:
    """
    Manages IFC stationing system for alignments.
    
    Responsibilities:
    - Create IfcReferent entities with proper PredefinedType
    - Generate Pset_Stationing property sets
    - Create IfcLinearPlacement for positioning
    - Maintain ordered IfcRelNests relationships
    - Handle station equations
    """

class StationGenerator:
    """
    Generates station referents based on rules and intervals.
    
    Strategies:
    - Uniform interval (e.g., every 100m)
    - At segment boundaries (PIs, PCs, PTs)
    - At PVIs and curve quarter points
    - At user-specified critical points
    - Densification in curves
    """

class StationEquation:
    """
    Represents a station equation (break in chainage).
    
    Attributes:
    - distance_along: Geometric position
    - incoming_station: Station value before equation
    - outgoing_station: Station value after equation
    """
```

#### Blender Visualization Classes

```python
# ui/visualization/station_markers.py

class StationMarkerVisualizer:
    """
    Creates and manages Blender objects for station visualization.
    
    Features:
    - Tick marks perpendicular to alignment
    - Text labels with station values
    - Different styles for major/minor stations
    - Real-time updates on alignment changes
    """

class StationMarkerStyle:
    """
    Defines visual appearance of station markers.
    
    Attributes:
    - tick_length: Length of perpendicular tick
    - tick_width: Line width of tick
    - label_size: Font size of label
    - label_offset: Offset from alignment
    - color: Display color
    """
```

---

## Implementation Details

### Phase 1: Core IFC Stationing System

#### 1.1 Create IfcReferent with Pset_Stationing

```python
class NativeIfcStationing:
    """Core stationing functionality."""
    
    def __init__(self, ifc_file: ifcopenshell.file):
        self.ifc = ifc_file
        
    def add_station_referent(
        self,
        alignment: ifcopenshell.entity_instance,
        distance_along: float,
        station_value: float,
        name: str = None,
        incoming_station: float = None,
        increment_order: bool = True
    ) -> ifcopenshell.entity_instance:
        """
        Create an IfcReferent representing a station.
        
        Args:
            alignment: Parent IfcAlignment entity
            distance_along: Geometric distance from alignment start (meters)
            station_value: Station designation value (e.g., 100.0 for 1+00)
            name: Optional name for the referent
            incoming_station: Optional incoming station for equation
            increment_order: True if stations are increasing
            
        Returns:
            Created IfcReferent entity
            
        Example:
            >>> stationing = NativeIfcStationing(ifc_file)
            >>> alignment = ifc_file.by_type("IfcAlignment")[0]
            >>> 
            >>> # Regular station at 0+00
            >>> station_0 = stationing.add_station_referent(
            ...     alignment, 
            ...     distance_along=0.0,
            ...     station_value=0.0,
            ...     name="Station 0+00"
            ... )
            >>> 
            >>> # Regular station at 1+00
            >>> station_100 = stationing.add_station_referent(
            ...     alignment,
            ...     distance_along=100.0,
            ...     station_value=100.0,
            ...     name="Station 1+00"
            ... )
            >>>
            >>> # Station equation: jumps from 2+00 to 5+00
            >>> station_eq = stationing.add_station_referent(
            ...     alignment,
            ...     distance_along=200.0,
            ...     station_value=500.0,
            ...     name="Station 5+00 (Equation)",
            ...     incoming_station=200.0
            ... )
        """
        # Step 1: Create IfcReferent
        referent = self.ifc.create_entity(
            "IfcReferent",
            GlobalId=ifcopenshell.guid.new(),
            Name=name or f"Station {self._format_station(station_value)}",
            PredefinedType="STATION"
        )
        
        # Step 2: Create IfcLinearPlacement
        placement = self._create_linear_placement(
            alignment,
            distance_along
        )
        referent.ObjectPlacement = placement
        
        # Step 3: Create Pset_Stationing
        pset = self._create_pset_stationing(
            referent,
            station_value,
            incoming_station,
            increment_order
        )
        
        # Step 4: Nest to alignment (CRITICAL: maintain order!)
        self._nest_to_alignment(alignment, referent)
        
        return referent
    
    def _create_linear_placement(
        self,
        alignment: ifcopenshell.entity_instance,
        distance_along: float
    ) -> ifcopenshell.entity_instance:
        """
        Create IfcLinearPlacement for the referent.
        
        Args:
            alignment: Parent alignment
            distance_along: Distance along alignment basis curve
            
        Returns:
            IfcLinearPlacement entity
        """
        # Get alignment's basis curve (IfcCompositeCurve for H+V)
        basis_curve = self._get_basis_curve(alignment)
        
        # Create IfcPointByDistanceExpression
        point = self.ifc.create_entity(
            "IfcPointByDistanceExpression",
            DistanceAlong=distance_along,
            OffsetLateral=0.0,      # No lateral offset
            OffsetVertical=0.0,     # No vertical offset  
            OffsetLongitudinal=0.0, # No longitudinal offset
            BasisCurve=basis_curve
        )
        
        # Create IfcAxis2PlacementLinear
        axis_placement = self.ifc.create_entity(
            "IfcAxis2PlacementLinear",
            Location=point,
            Axis=None,       # Default: perpendicular to curve
            RefDirection=None # Default: tangent to curve
        )
        
        # Create IfcLinearPlacement
        placement = self.ifc.create_entity(
            "IfcLinearPlacement",
            PlacementRelTo=None,  # Relative to alignment start
            RelativePlacement=axis_placement
        )
        
        return placement
    
    def _create_pset_stationing(
        self,
        referent: ifcopenshell.entity_instance,
        station_value: float,
        incoming_station: float = None,
        increment_order: bool = True
    ) -> ifcopenshell.entity_instance:
        """
        Create Pset_Stationing property set.
        
        Args:
            referent: IfcReferent to attach property set to
            station_value: Station value at this location
            incoming_station: Optional incoming station for equation
            increment_order: True if stations increase along alignment
            
        Returns:
            IfcPropertySet entity
        """
        # Build property list
        properties = []
        
        # Required: Station property
        properties.append(
            self.ifc.create_entity(
                "IfcPropertySingleValue",
                Name="Station",
                NominalValue=self.ifc.create_entity(
                    "IfcLengthMeasure",
                    station_value
                )
            )
        )
        
        # Optional: IncomingStation (for station equations)
        if incoming_station is not None:
            properties.append(
                self.ifc.create_entity(
                    "IfcPropertySingleValue",
                    Name="IncomingStation",
                    NominalValue=self.ifc.create_entity(
                        "IfcLengthMeasure",
                        incoming_station
                    )
                )
            )
        
        # Optional: IncrementOrder
        properties.append(
            self.ifc.create_entity(
                "IfcPropertySingleValue",
                Name="IncrementOrder",
                NominalValue=self.ifc.create_entity(
                    "IfcBoolean",
                    increment_order
                )
            )
        )
        
        # Create property set
        pset = self.ifc.create_entity(
            "IfcPropertySet",
            GlobalId=ifcopenshell.guid.new(),
            Name="Pset_Stationing",
            HasProperties=properties
        )
        
        # Create relationship to attach pset to referent
        self.ifc.create_entity(
            "IfcRelDefinesByProperties",
            GlobalId=ifcopenshell.guid.new(),
            RelatedObjects=[referent],
            RelatingPropertyDefinition=pset
        )
        
        return pset
    
    def _nest_to_alignment(
        self,
        alignment: ifcopenshell.entity_instance,
        referent: ifcopenshell.entity_instance
    ):
        """
        Nest referent to alignment, maintaining ordered list.
        
        CRITICAL: IfcRelNests.RelatedObjects is an ORDERED list.
        Must maintain proper order based on DistanceAlong.
        
        Args:
            alignment: Parent IfcAlignment
            referent: IfcReferent to nest
        """
        # Find existing IfcRelNests for this alignment
        # Note: May have separate nests for layouts vs. referents
        nesting_rel = None
        
        for rel in self.ifc.by_type("IfcRelNests"):
            if rel.RelatingObject == alignment:
                # Check if this nest contains referents
                if rel.RelatedObjects and \
                   rel.RelatedObjects[0].is_a("IfcReferent"):
                    nesting_rel = rel
                    break
        
        if nesting_rel is None:
            # Create new IfcRelNests for referents
            nesting_rel = self.ifc.create_entity(
                "IfcRelNests",
                GlobalId=ifcopenshell.guid.new(),
                RelatingObject=alignment,
                RelatedObjects=[referent]
            )
        else:
            # Add to existing nest, maintaining order
            existing = list(nesting_rel.RelatedObjects)
            
            # Get distance_along for ordering
            new_distance = self._get_distance_along(referent)
            
            # Find insertion point
            insert_index = len(existing)
            for i, existing_ref in enumerate(existing):
                existing_distance = self._get_distance_along(existing_ref)
                if new_distance < existing_distance:
                    insert_index = i
                    break
            
            # Insert at correct position
            existing.insert(insert_index, referent)
            nesting_rel.RelatedObjects = existing
    
    def _get_distance_along(
        self,
        referent: ifcopenshell.entity_instance
    ) -> float:
        """
        Extract DistanceAlong from referent's placement.
        
        Args:
            referent: IfcReferent entity
            
        Returns:
            Distance along alignment in meters
        """
        placement = referent.ObjectPlacement
        if not placement or not placement.is_a("IfcLinearPlacement"):
            return 0.0
            
        relative = placement.RelativePlacement
        if not relative or not relative.is_a("IfcAxis2PlacementLinear"):
            return 0.0
            
        location = relative.Location
        if not location or not location.is_a("IfcPointByDistanceExpression"):
            return 0.0
            
        return location.DistanceAlong
    
    def _get_basis_curve(
        self,
        alignment: ifcopenshell.entity_instance
    ) -> ifcopenshell.entity_instance:
        """
        Get the basis curve (IfcCompositeCurve) from alignment.
        
        For 3D alignments (H+V), this is the horizontal projection.
        
        Args:
            alignment: IfcAlignment entity
            
        Returns:
            IfcCompositeCurve representing basis curve
        """
        # Navigate through representation to find curve
        # This depends on your alignment structure
        # Typically: Alignment → Representation → Curve
        
        for rep in alignment.Representation.Representations:
            for item in rep.Items:
                if item.is_a("IfcCompositeCurve"):
                    return item
                elif item.is_a("IfcGradientCurve"):
                    # For 3D curves, basis curve is the horizontal
                    return item.BaseCurve
                elif item.is_a("IfcSegmentedReferenceCurve"):
                    # For cant curves, get underlying gradient curve
                    gradient = item.BaseCurve
                    return gradient.BaseCurve
        
        raise ValueError(f"Could not find basis curve for alignment {alignment}")
    
    @staticmethod
    def _format_station(value: float, imperial: bool = False) -> str:
        """
        Format station value for display.
        
        Args:
            value: Station value in base units
            imperial: If True, use imperial format (1+00), else metric (1+000)
            
        Returns:
            Formatted station string
            
        Examples:
            >>> NativeIfcStationing._format_station(0.0)
            '0+000'
            >>> NativeIfcStationing._format_station(1234.56)
            '1+234.56'
            >>> NativeIfcStationing._format_station(100.0, imperial=True)
            '1+00'
        """
        if imperial:
            # US format: 1+00 = 100 feet
            major = int(value // 100)
            minor = value % 100
            return f"{major}+{minor:05.2f}"
        else:
            # Metric format: 1+000 = 1000 meters
            major = int(value // 1000)
            minor = value % 1000
            return f"{major}+{minor:06.2f}"
```

#### 1.2 Station Generator

```python
class StationGenerator:
    """
    Generates stations along alignment based on various rules.
    """
    
    def __init__(self, stationing: NativeIfcStationing):
        self.stationing = stationing
    
    def generate_uniform_stations(
        self,
        alignment: ifcopenshell.entity_instance,
        interval: float = 100.0,
        start_station: float = 0.0,
        include_start: bool = True,
        include_end: bool = True
    ) -> List[ifcopenshell.entity_instance]:
        """
        Generate stations at uniform intervals.
        
        Args:
            alignment: IfcAlignment to add stations to
            interval: Station interval in meters (default 100m)
            start_station: Starting station value
            include_start: Include station at alignment start
            include_end: Include station at alignment end
            
        Returns:
            List of created IfcReferent entities
            
        Example:
            >>> generator = StationGenerator(stationing)
            >>> stations = generator.generate_uniform_stations(
            ...     alignment,
            ...     interval=100.0,
            ...     start_station=0.0
            ... )
            >>> print(f"Created {len(stations)} stations")
            Created 11 stations  # For 1000m alignment: 0, 100, 200, ..., 1000
        """
        # Get alignment length
        length = self._get_alignment_length(alignment)
        
        # Calculate station positions
        stations = []
        current_distance = 0.0 if include_start else interval
        current_station = start_station + current_distance
        
        while current_distance <= length:
            # Don't exceed alignment length unless include_end is True
            if current_distance > length and not include_end:
                break
            
            # Clamp to alignment length
            distance = min(current_distance, length)
            
            # Create station
            referent = self.stationing.add_station_referent(
                alignment,
                distance_along=distance,
                station_value=current_station,
                name=f"Station {self.stationing._format_station(current_station)}"
            )
            stations.append(referent)
            
            # Stop if at end
            if distance >= length:
                break
            
            # Next station
            current_distance += interval
            current_station += interval
        
        return stations
    
    def generate_at_geometry_points(
        self,
        alignment: ifcopenshell.entity_instance,
        start_station: float = 0.0,
        include_pis: bool = True,
        include_pcs: bool = True,
        include_pts: bool = True,
        include_pvis: bool = True,
        curve_quarters: bool = True
    ) -> List[ifcopenshell.entity_instance]:
        """
        Generate stations at critical geometry points.
        
        Args:
            alignment: IfcAlignment entity
            start_station: Starting station value
            include_pis: Include stations at Point of Intersection
            include_pcs: Include stations at Point of Curvature
            include_pts: Include stations at Point of Tangency
            include_pvis: Include stations at Points of Vertical Intersection
            curve_quarters: Include quarter points on curves
            
        Returns:
            List of created IfcReferent entities
        """
        stations = []
        
        # Get horizontal and vertical layouts
        h_layout = self._get_horizontal_layout(alignment)
        v_layout = self._get_vertical_layout(alignment)
        
        # Process horizontal geometry
        if h_layout and include_pis:
            # Add stations at PIs, PCs, PTs based on segments
            current_distance = 0.0
            
            for segment in h_layout.segments:
                # Station at segment start
                if include_pcs:
                    station_value = start_station + current_distance
                    referent = self.stationing.add_station_referent(
                        alignment,
                        distance_along=current_distance,
                        station_value=station_value,
                        name=f"PC {self.stationing._format_station(station_value)}"
                    )
                    stations.append(referent)
                
                # If curve, add quarter points
                if curve_quarters and segment.is_curve():
                    length = segment.length()
                    for i in [0.25, 0.5, 0.75]:
                        dist = current_distance + (length * i)
                        station_value = start_station + dist
                        referent = self.stationing.add_station_referent(
                            alignment,
                            distance_along=dist,
                            station_value=station_value,
                            name=f"Curve {self.stationing._format_station(station_value)}"
                        )
                        stations.append(referent)
                
                # Station at segment end
                current_distance += segment.length()
                if include_pts:
                    station_value = start_station + current_distance
                    referent = self.stationing.add_station_referent(
                        alignment,
                        distance_along=current_distance,
                        station_value=station_value,
                        name=f"PT {self.stationing._format_station(station_value)}"
                    )
                    stations.append(referent)
        
        # Process vertical geometry
        if v_layout and include_pvis:
            for pvi in v_layout.pvis:
                station_value = start_station + pvi.station
                referent = self.stationing.add_station_referent(
                    alignment,
                    distance_along=pvi.station,
                    station_value=station_value,
                    name=f"PVI {self.stationing._format_station(station_value)}"
                )
                stations.append(referent)
                
                # Add curve quarter points if vertical curve exists
                if curve_quarters and pvi.curve_length > 0:
                    curve_length = pvi.curve_length
                    bvc = pvi.station - (curve_length / 2)  # Begin Vertical Curve
                    
                    for i in [0.25, 0.5, 0.75]:
                        dist = bvc + (curve_length * i)
                        station_value = start_station + dist
                        referent = self.stationing.add_station_referent(
                            alignment,
                            distance_along=dist,
                            station_value=station_value,
                            name=f"VC {self.stationing._format_station(station_value)}"
                        )
                        stations.append(referent)
        
        return stations
    
    def generate_adaptive(
        self,
        alignment: ifcopenshell.entity_instance,
        base_interval: float = 100.0,
        curve_densification: float = 2.0,
        start_station: float = 0.0
    ) -> List[ifcopenshell.entity_instance]:
        """
        Generate adaptive station spacing.
        
        Denser stations in curves, sparser on tangents.
        
        Args:
            alignment: IfcAlignment entity
            base_interval: Base interval on tangents (meters)
            curve_densification: Factor for curve density (2.0 = half interval)
            start_station: Starting station value
            
        Returns:
            List of created IfcReferent entities
            
        Example:
            >>> # Base interval = 100m on tangents
            >>> # Curve interval = 100m / 2.0 = 50m in curves
            >>> stations = generator.generate_adaptive(
            ...     alignment,
            ...     base_interval=100.0,
            ...     curve_densification=2.0
            ... )
        """
        stations = []
        h_layout = self._get_horizontal_layout(alignment)
        
        if not h_layout:
            # No horizontal layout, fall back to uniform
            return self.generate_uniform_stations(
                alignment,
                interval=base_interval,
                start_station=start_station
            )
        
        current_distance = 0.0
        current_station = start_station
        
        # Always add start station
        stations.append(
            self.stationing.add_station_referent(
                alignment,
                distance_along=0.0,
                station_value=start_station,
                name=f"Station {self.stationing._format_station(start_station)}"
            )
        )
        
        # Process each segment
        for segment in h_layout.segments:
            segment_length = segment.length()
            
            # Determine interval for this segment
            if segment.is_curve():
                interval = base_interval / curve_densification
            else:
                interval = base_interval
            
            # Add stations within segment
            segment_start = current_distance
            local_distance = interval
            
            while local_distance < segment_length:
                abs_distance = segment_start + local_distance
                station_value = start_station + abs_distance
                
                referent = self.stationing.add_station_referent(
                    alignment,
                    distance_along=abs_distance,
                    station_value=station_value,
                    name=f"Station {self.stationing._format_station(station_value)}"
                )
                stations.append(referent)
                
                local_distance += interval
            
            current_distance += segment_length
        
        # Add end station
        alignment_length = self._get_alignment_length(alignment)
        end_station_value = start_station + alignment_length
        stations.append(
            self.stationing.add_station_referent(
                alignment,
                distance_along=alignment_length,
                station_value=end_station_value,
                name=f"Station {self.stationing._format_station(end_station_value)}"
            )
        )
        
        return stations
    
    def _get_alignment_length(
        self,
        alignment: ifcopenshell.entity_instance
    ) -> float:
        """Get total length of alignment."""
        # Implementation depends on your alignment structure
        # Could sum segment lengths or query geometry
        pass
    
    def _get_horizontal_layout(self, alignment):
        """Get horizontal layout from alignment."""
        # Implementation depends on your structure
        pass
    
    def _get_vertical_layout(self, alignment):
        """Get vertical layout from alignment."""
        # Implementation depends on your structure
        pass
```

---

## Integration with Existing Systems

### Integration Points

#### 1. Alignment Creation

When creating a new alignment, optionally generate initial stations:

```python
# In core/native_ifc_horizontal.py or native_ifc_alignment.py

class NativeIfcAlignment:
    
    def create_alignment(
        self,
        name: str,
        start_station: float = 0.0,
        generate_stations: bool = True,
        station_interval: float = 100.0
    ) -> ifcopenshell.entity_instance:
        """
        Create new IFC alignment with optional stationing.
        
        Args:
            name: Alignment name
            start_station: Starting station value
            generate_stations: Auto-generate stations
            station_interval: Station interval if auto-generating
            
        Returns:
            Created IfcAlignment entity
        """
        # Create alignment (existing logic)
        alignment = self._create_alignment_entity(name)
        
        # Create horizontal/vertical layouts (existing logic)
        # ...
        
        # NEW: Optionally generate stations
        if generate_stations:
            stationing = NativeIfcStationing(self.ifc)
            generator = StationGenerator(stationing)
            
            stations = generator.generate_uniform_stations(
                alignment,
                interval=station_interval,
                start_station=start_station
            )
            
            print(f"Generated {len(stations)} stations for alignment '{name}'")
        
        return alignment
```

#### 2. Georeferencing Integration

Stations should be aware of georeferencing for coordinate output:

```python
# In core/native_ifc_stationing.py

class NativeIfcStationing:
    
    def get_station_coordinates(
        self,
        referent: ifcopenshell.entity_instance,
        coordinate_system: str = "local"
    ) -> Tuple[float, float, float]:
        """
        Get 3D coordinates of station in specified system.
        
        Args:
            referent: IfcReferent station entity
            coordinate_system: "local", "map", or "project"
            
        Returns:
            (x, y, z) coordinates in requested system
            
        Example:
            >>> # Get local coordinates
            >>> x, y, z = stationing.get_station_coordinates(
            ...     station_referent,
            ...     coordinate_system="local"
            ... )
            >>>
            >>> # Get real-world map coordinates  
            >>> easting, northing, elevation = stationing.get_station_coordinates(
            ...     station_referent,
            ...     coordinate_system="map"
            ... )
        """
        # Get distance along from placement
        distance_along = self._get_distance_along(referent)
        
        # Get alignment
        alignment = self._get_parent_alignment(referent)
        
        # Get 3D position from alignment at this distance
        position = self._evaluate_alignment_3d(alignment, distance_along)
        
        # Transform based on requested coordinate system
        if coordinate_system == "local":
            return position
        elif coordinate_system == "map":
            # Use georeferencing system (from Sprint 2)
            georef = self._get_georeferencing(alignment)
            return georef.local_to_map(position)
        elif coordinate_system == "project":
            # Use project coordinate system
            return self._transform_to_project(position)
        else:
            raise ValueError(f"Unknown coordinate system: {coordinate_system}")
```

#### 3. Profile View Integration

Stations should display in the profile view (from Sprint 3):

```python
# In ui/profile_view.py or similar

class ProfileView:
    
    def draw_stations(self, context, alignment_obj):
        """
        Draw station markers in profile view.
        
        Args:
            context: Blender context
            alignment_obj: Alignment Blender object
        """
        # Get IFC referents for this alignment
        ifc_file = get_ifc_file()
        alignment_entity = get_ifc_entity(alignment_obj)
        
        # Get all station referents
        stations = self._get_station_referents(alignment_entity)
        
        for referent in stations:
            # Get station value from Pset_Stationing
            station_value = self._get_station_value(referent)
            distance_along = self._get_distance_along(referent)
            
            # Get elevation at this station from vertical alignment
            elevation = self._get_elevation_at_station(
                alignment_entity,
                distance_along
            )
            
            # Draw vertical line at station
            self._draw_station_line(distance_along, elevation)
            
            # Draw station label
            self._draw_station_label(
                distance_along,
                elevation,
                station_value
            )
```

#### 4. Corridor Integration (Sprint 5)

Stations define cross-section placement in corridors:

```python
# In core/corridor_modeler.py or similar

class CorridorModeler:
    
    def create_corridor(
        self,
        alignment: ifcopenshell.entity_instance,
        cross_section_assembly: CrossSectionAssembly,
        use_station_referents: bool = True
    ) -> ifcopenshell.entity_instance:
        """
        Create corridor using stations for cross-section placement.
        
        Args:
            alignment: IfcAlignment entity
            cross_section_assembly: Cross-section template
            use_station_referents: Use existing station referents if True,
                                   otherwise generate from interval
                                   
        Returns:
            Created corridor entity (IfcSectionedSolidHorizontal)
        """
        if use_station_referents:
            # Get existing station referents from alignment
            stations = self._get_station_referents(alignment)
            
            # Convert to distances along
            station_distances = [
                self._get_distance_along(ref) for ref in stations
            ]
        else:
            # Generate from interval (existing logic)
            station_distances = self._generate_station_intervals(
                alignment,
                interval=10.0
            )
        
        # Create cross-sections at each station
        cross_sections = []
        for distance in station_distances:
            profile = cross_section_assembly.to_ifc(self.ifc)
            cross_sections.append(profile)
        
        # Create IfcSectionedSolidHorizontal
        corridor = self._create_sectioned_solid(
            alignment,
            cross_sections,
            station_distances
        )
        
        return corridor
```

---

## Blender Visualization

### Visualization Architecture

**Key Principle:** Station markers are **Blender-only** objects for visualization. They are NOT exported to IFC.

```
┌─────────────────────────────────────────────────────────┐
│              Blender Scene Hierarchy                    │
└─────────────────────────────────────────────────────────┘
    │
    └── Alignment_Object (has IFC entity)
        │
        └── Alignment_Stations (Collection)
            │
            ├── Station_Markers (Collection)
            │   ├── Station_0+00_Tick (Curve object)
            │   ├── Station_1+00_Tick (Curve object)
            │   └── Station_2+00_Tick (Curve object)
            │
            └── Station_Labels (Collection)
                ├── Station_0+00_Label (Text object)
                ├── Station_1+00_Label (Text object)
                └── Station_2+00_Label (Text object)
```

### Implementation

```python
# ui/visualization/station_markers.py

import bpy
import bmesh
from typing import List, Tuple

class StationMarkerVisualizer:
    """
    Creates Blender visualization objects for alignment stations.
    
    These objects are NOT exported to IFC - they're viewport helpers only.
    """
    
    def __init__(self):
        self.marker_style = StationMarkerStyle()
    
    def generate_markers(
        self,
        alignment_obj: bpy.types.Object,
        refresh: bool = False
    ):
        """
        Generate station marker objects for alignment.
        
        Args:
            alignment_obj: Blender object representing alignment
            refresh: If True, clear and regenerate all markers
        """
        # Get IFC data
        ifc_file = get_ifc_file()
        alignment_entity = get_ifc_entity(alignment_obj)
        
        if not alignment_entity:
            print(f"No IFC entity for alignment: {alignment_obj.name}")
            return
        
        # Get station referents from IFC
        stations = self._get_station_referents(alignment_entity)
        
        if not stations:
            print(f"No stations found for alignment: {alignment_obj.name}")
            return
        
        # Create or get marker collection
        marker_collection = self._get_or_create_marker_collection(alignment_obj)
        
        # Clear existing markers if refreshing
        if refresh:
            self._clear_markers(marker_collection)
        
        # Create markers for each station
        for referent in stations:
            self._create_station_marker(
                alignment_obj,
                alignment_entity,
                referent,
                marker_collection
            )
    
    def _create_station_marker(
        self,
        alignment_obj: bpy.types.Object,
        alignment_entity: ifcopenshell.entity_instance,
        referent: ifcopenshell.entity_instance,
        collection: bpy.types.Collection
    ):
        """
        Create tick mark and label for a single station.
        
        Args:
            alignment_obj: Blender alignment object
            alignment_entity: IFC alignment entity
            referent: IFC referent (station) entity
            collection: Collection to add objects to
        """
        # Get station data
        distance_along = self._get_distance_along(referent)
        station_value = self._get_station_value(referent)
        station_name = referent.Name or f"Station {station_value}"
        
        # Get 3D position from alignment
        position = self._evaluate_alignment_3d(
            alignment_entity,
            distance_along
        )
        
        # Get tangent direction at this point
        tangent = self._get_tangent_at_distance(
            alignment_entity,
            distance_along
        )
        
        # Calculate perpendicular direction for tick mark
        perpendicular = self._get_perpendicular(tangent)
        
        # Create tick mark
        tick_obj = self._create_tick_mark(
            position,
            perpendicular,
            station_name
        )
        collection.objects.link(tick_obj)
        
        # Create label
        label_obj = self._create_station_label(
            position,
            perpendicular,
            station_value,
            station_name
        )
        collection.objects.link(label_obj)
        
        # Store reference to IFC referent in custom properties
        tick_obj["ifc_referent_id"] = referent.GlobalId
        label_obj["ifc_referent_id"] = referent.GlobalId
        
        # Tag as non-exportable
        tick_obj["ifc_export_exclude"] = True
        label_obj["ifc_export_exclude"] = True
    
    def _create_tick_mark(
        self,
        position: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        name: str
    ) -> bpy.types.Object:
        """
        Create a tick mark curve object.
        
        Args:
            position: 3D position on alignment
            direction: Perpendicular direction
            name: Object name
            
        Returns:
            Created curve object
        """
        # Calculate tick endpoints
        tick_length = self.marker_style.tick_length
        start = (
            position[0] - direction[0] * tick_length / 2,
            position[1] - direction[1] * tick_length / 2,
            position[2]
        )
        end = (
            position[0] + direction[0] * tick_length / 2,
            position[1] + direction[1] * tick_length / 2,
            position[2]
        )
        
        # Create curve
        curve_data = bpy.data.curves.new(
            name=f"{name}_Tick",
            type='CURVE'
        )
        curve_data.dimensions = '3D'
        
        # Create spline
        spline = curve_data.splines.new('POLY')
        spline.points.add(1)  # Need 2 points total
        spline.points[0].co = (*start, 1.0)
        spline.points[1].co = (*end, 1.0)
        
        # Set line width
        curve_data.bevel_depth = self.marker_style.tick_width
        
        # Create object
        tick_obj = bpy.data.objects.new(f"{name}_Tick", curve_data)
        
        # Set color
        if not tick_obj.data.materials:
            mat = bpy.data.materials.new(name="Station_Tick_Material")
            mat.diffuse_color = (*self.marker_style.tick_color, 1.0)
            tick_obj.data.materials.append(mat)
        
        return tick_obj
    
    def _create_station_label(
        self,
        position: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        station_value: float,
        name: str
    ) -> bpy.types.Object:
        """
        Create a text object for station label.
        
        Args:
            position: 3D position on alignment
            direction: Perpendicular direction for offset
            station_value: Station value to display
            name: Object name
            
        Returns:
            Created text object
        """
        # Format station text
        station_text = self._format_station_text(station_value)
        
        # Calculate label position (offset from alignment)
        label_offset = self.marker_style.label_offset
        label_pos = (
            position[0] + direction[0] * label_offset,
            position[1] + direction[1] * label_offset,
            position[2] + self.marker_style.label_z_offset
        )
        
        # Create text
        text_data = bpy.data.curves.new(
            name=f"{name}_Label",
            type='FONT'
        )
        text_data.body = station_text
        text_data.size = self.marker_style.label_size
        text_data.align_x = 'CENTER'
        text_data.align_y = 'CENTER'
        
        # Create object
        label_obj = bpy.data.objects.new(f"{name}_Label", text_data)
        label_obj.location = label_pos
        
        # Set color
        if not label_obj.data.materials:
            mat = bpy.data.materials.new(name="Station_Label_Material")
            mat.diffuse_color = (*self.marker_style.label_color, 1.0)
            label_obj.data.materials.append(mat)
        
        return label_obj
    
    def _get_or_create_marker_collection(
        self,
        alignment_obj: bpy.types.Object
    ) -> bpy.types.Collection:
        """
        Get or create collection for station markers.
        
        Args:
            alignment_obj: Parent alignment object
            
        Returns:
            Blender collection for markers
        """
        collection_name = f"{alignment_obj.name}_Stations"
        
        # Check if collection exists
        if collection_name in bpy.data.collections:
            return bpy.data.collections[collection_name]
        
        # Create new collection
        marker_collection = bpy.data.collections.new(collection_name)
        
        # Link to scene
        bpy.context.scene.collection.children.link(marker_collection)
        
        # Set collection properties to indicate it's visualization only
        marker_collection["ifc_export_exclude"] = True
        marker_collection["station_markers"] = True
        
        return marker_collection
    
    def _clear_markers(self, collection: bpy.types.Collection):
        """Remove all objects from marker collection."""
        for obj in list(collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
    
    def update_markers(self, alignment_obj: bpy.types.Object):
        """
        Update markers when alignment changes.
        
        Args:
            alignment_obj: Alignment object that changed
        """
        # Regenerate markers
        self.generate_markers(alignment_obj, refresh=True)
    
    @staticmethod
    def _format_station_text(value: float) -> str:
        """
        Format station value for text display.
        
        Args:
            value: Station value
            
        Returns:
            Formatted string (e.g., "1+234.56")
        """
        major = int(value // 1000)
        minor = value % 1000
        return f"{major}+{minor:06.2f}"
    
    # Helper methods (implementations depend on your alignment system)
    def _get_station_referents(self, alignment):
        """Get all station referents from alignment."""
        pass
    
    def _get_distance_along(self, referent):
        """Extract distance along from referent."""
        pass
    
    def _get_station_value(self, referent):
        """Extract station value from Pset_Stationing."""
        pass
    
    def _evaluate_alignment_3d(self, alignment, distance):
        """Get 3D position from alignment at distance."""
        pass
    
    def _get_tangent_at_distance(self, alignment, distance):
        """Get tangent vector at distance along alignment."""
        pass
    
    @staticmethod
    def _get_perpendicular(vector):
        """Calculate perpendicular vector in XY plane."""
        # For 2D perpendicular: swap and negate one component
        return (-vector[1], vector[0], 0.0)


class StationMarkerStyle:
    """Visual appearance settings for station markers."""
    
    def __init__(self):
        # Tick mark settings
        self.tick_length = 5.0  # meters
        self.tick_width = 0.1    # meters
        self.tick_color = (1.0, 1.0, 0.0)  # Yellow
        
        # Label settings
        self.label_size = 2.0      # Text size
        self.label_offset = 3.0    # Offset from alignment (meters)
        self.label_z_offset = 1.0  # Z offset above alignment
        self.label_color = (1.0, 1.0, 1.0)  # White
        
        # Major station settings (e.g., every 500m)
        self.major_tick_length = 8.0
        self.major_tick_width = 0.2
        self.major_label_size = 3.0
```

---

## Testing & Validation

### Unit Tests

```python
# tests/test_stationing.py

import pytest
import ifcopenshell
from core.native_ifc_stationing import NativeIfcStationing, StationGenerator

class TestNativeIfcStationing:
    
    @pytest.fixture
    def ifc_file(self):
        """Create test IFC file."""
        return ifcopenshell.file(schema="IFC4X3")
    
    @pytest.fixture
    def alignment(self, ifc_file):
        """Create test alignment."""
        # Create minimal alignment for testing
        alignment = ifc_file.create_entity(
            "IfcAlignment",
            GlobalId=ifcopenshell.guid.new(),
            Name="Test Alignment"
        )
        return alignment
    
    def test_add_station_referent(self, ifc_file, alignment):
        """Test creating a single station referent."""
        stationing = NativeIfcStationing(ifc_file)
        
        referent = stationing.add_station_referent(
            alignment,
            distance_along=100.0,
            station_value=100.0,
            name="Station 1+00"
        )
        
        # Verify referent created
        assert referent is not None
        assert referent.is_a("IfcReferent")
        assert referent.PredefinedType == "STATION"
        assert referent.Name == "Station 1+00"
        
        # Verify placement
        assert referent.ObjectPlacement is not None
        assert referent.ObjectPlacement.is_a("IfcLinearPlacement")
        
        # Verify Pset_Stationing
        pset = self._get_pset(referent, "Pset_Stationing")
        assert pset is not None
        
        station_prop = self._get_property(pset, "Station")
        assert station_prop.NominalValue[0] == 100.0
    
    def test_station_equation(self, ifc_file, alignment):
        """Test station equation creation."""
        stationing = NativeIfcStationing(ifc_file)
        
        # Create station with equation
        referent = stationing.add_station_referent(
            alignment,
            distance_along=200.0,
            station_value=500.0,  # Jumps from 2+00 to 5+00
            name="Station 5+00 (Equation)",
            incoming_station=200.0
        )
        
        # Verify Pset_Stationing has both values
        pset = self._get_pset(referent, "Pset_Stationing")
        
        station_prop = self._get_property(pset, "Station")
        assert station_prop.NominalValue[0] == 500.0
        
        incoming_prop = self._get_property(pset, "IncomingStation")
        assert incoming_prop.NominalValue[0] == 200.0
    
    def test_nested_order(self, ifc_file, alignment):
        """Test that stations maintain proper order in IfcRelNests."""
        stationing = NativeIfcStationing(ifc_file)
        
        # Add stations out of order
        station_200 = stationing.add_station_referent(
            alignment, 200.0, 200.0
        )
        station_0 = stationing.add_station_referent(
            alignment, 0.0, 0.0
        )
        station_100 = stationing.add_station_referent(
            alignment, 100.0, 100.0
        )
        
        # Get nesting relationship
        nesting = self._get_nesting_rel(alignment)
        related = nesting.RelatedObjects
        
        # Verify order
        assert len(related) == 3
        assert related[0] == station_0
        assert related[1] == station_100
        assert related[2] == station_200
    
    def test_uniform_generation(self, ifc_file, alignment):
        """Test uniform station generation."""
        stationing = NativeIfcStationing(ifc_file)
        generator = StationGenerator(stationing)
        
        # Mock alignment length
        alignment._test_length = 1000.0
        
        stations = generator.generate_uniform_stations(
            alignment,
            interval=100.0,
            start_station=0.0
        )
        
        # Should create 11 stations (0, 100, 200, ..., 1000)
        assert len(stations) == 11
        
        # Verify first and last
        first_pset = self._get_pset(stations[0], "Pset_Stationing")
        first_station = self._get_property(first_pset, "Station")
        assert first_station.NominalValue[0] == 0.0
        
        last_pset = self._get_pset(stations[-1], "Pset_Stationing")
        last_station = self._get_property(last_pset, "Station")
        assert last_station.NominalValue[0] == 1000.0
    
    # Helper methods
    def _get_pset(self, entity, name):
        """Get property set by name."""
        for rel in entity.IsDefinedBy:
            if rel.is_a("IfcRelDefinesByProperties"):
                pset = rel.RelatingPropertyDefinition
                if pset.Name == name:
                    return pset
        return None
    
    def _get_property(self, pset, name):
        """Get property from property set."""
        for prop in pset.HasProperties:
            if prop.Name == name:
                return prop
        return None
    
    def _get_nesting_rel(self, alignment):
        """Get IfcRelNests for alignment."""
        for rel in alignment.IsDecomposedBy:
            if rel.is_a("IfcRelNests"):
                if rel.RelatedObjects and \
                   rel.RelatedObjects[0].is_a("IfcReferent"):
                    return rel
        return None
```

### Integration Tests

```python
# tests/test_stationing_integration.py

def test_stationing_with_georeferencing():
    """Test stationing works with georeferencing system."""
    # Create alignment with georeferencing
    # Add stations
    # Verify coordinates in multiple systems
    pass

def test_stationing_in_profile_view():
    """Test station markers appear in profile view."""
    # Create alignment with vertical
    # Add stations
    # Verify profile view rendering
    pass

def test_corridor_with_stations():
    """Test corridor uses station referents for placement."""
    # Create alignment with stations
    # Create corridor
    # Verify cross-sections at station locations
    pass
```

---

## Code Examples

### Complete Workflow Example

```python
# Example: Create alignment with adaptive stationing

import bpy
import ifcopenshell
from core.native_ifc_alignment import NativeIfcAlignment
from core.native_ifc_stationing import NativeIfcStationing, StationGenerator

# 1. Create IFC file
ifc_file = ifcopenshell.file(schema="IFC4X3")

# 2. Create alignment
alignment_system = NativeIfcAlignment(ifc_file)
alignment = alignment_system.create_alignment(
    name="Highway 101",
    start_station=100.0,  # Start at station 1+00
    generate_stations=False  # We'll do it manually
)

# 3. Add horizontal geometry (PIs, curves, etc.)
# ... (existing horizontal alignment code)

# 4. Add vertical geometry (PVIs, curves, etc.)
# ... (existing vertical alignment code)

# 5. Create stationing system
stationing = NativeIfcStationing(ifc_file)
generator = StationGenerator(stationing)

# 6. Generate adaptive stations
# - Base 100m interval on tangents
# - 50m interval in curves (2x densification)
stations = generator.generate_adaptive(
    alignment,
    base_interval=100.0,
    curve_densification=2.0,
    start_station=100.0
)

print(f"Created {len(stations)} stations")

# 7. Add specific station (e.g., bridge pier location)
bridge_station = stationing.add_station_referent(
    alignment,
    distance_along=567.89,
    station_value=667.89,  # 100.0 start + 567.89 distance
    name="Bridge Pier 1"
)

# 8. Create Blender visualization
alignment_obj = create_blender_object_from_ifc(alignment)

visualizer = StationMarkerVisualizer()
visualizer.generate_markers(alignment_obj)

# 9. Export IFC
ifc_file.write("highway_101.ifc")

print("✓ Alignment created with stationing")
print("✓ Station markers visualized in Blender")
print("✓ IFC file exported with native station referents")
```

### Query Stationing Example

```python
# Example: Query and use existing stations

import ifcopenshell
from core.native_ifc_stationing import NativeIfcStationing

# Load IFC file
ifc_file = ifcopenshell.open("highway_101.ifc")

# Get alignment
alignment = ifc_file.by_type("IfcAlignment")[0]

# Create stationing system
stationing = NativeIfcStationing(ifc_file)

# Get all stations
stations = stationing.get_all_stations(alignment)

print(f"Found {len(stations)} stations:")
for referent in stations:
    # Get station value
    station_value = stationing.get_station_value(referent)
    
    # Get distance along
    distance = stationing._get_distance_along(referent)
    
    # Get 3D coordinates (local)
    x, y, z = stationing.get_station_coordinates(
        referent,
        coordinate_system="local"
    )
    
    # Get map coordinates (real-world)
    e, n, elev = stationing.get_station_coordinates(
        referent,
        coordinate_system="map"
    )
    
    print(f"  {referent.Name}")
    print(f"    Station: {station_value}")
    print(f"    Distance: {distance:.2f}m")
    print(f"    Local: ({x:.2f}, {y:.2f}, {z:.2f})")
    print(f"    Map: ({e:.2f}m E, {n:.2f}m N, {elev:.2f}m)")
```

---

## References

### IFC 4.3 Specification

1. **IfcReferent**: https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcReferent.htm
2. **Pset_Stationing**: https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/Pset_Stationing.htm
3. **IfcLinearPlacement**: https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcLinearPlacement.htm
4. **IfcRelNests**: https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcRelNests.htm
5. **IfcAlignment**: https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcAlignment.htm

### BlenderCivil Project Documentation

1. **Section 8 - Referents and Stationing** (from project knowledge)
2. **Sprint 1 - Alignment Systems** (horizontal/vertical integration)
3. **Sprint 2 - Georeferencing** (coordinate transformation)
4. **Sprint 3 - Vertical Alignments** (profile view integration)
5. **Sprint 5 - Corridors** (cross-section placement)

### Industry Standards

1. **AASHTO Green Book** - Geometric design standards
2. **ISO 19148** - Geographic information – Linear referencing
3. **Civil 3D Documentation** - Industry reference for stationing workflows

---

## Implementation Checklist

### Phase 1: Core IFC System ✅
- [ ] Create `core/native_ifc_stationing.py`
- [ ] Implement `NativeIfcStationing` class
  - [ ] `add_station_referent()` method
  - [ ] `_create_linear_placement()` method
  - [ ] `_create_pset_stationing()` method
  - [ ] `_nest_to_alignment()` method with proper ordering
- [ ] Implement `StationGenerator` class
  - [ ] `generate_uniform_stations()` method
  - [ ] `generate_at_geometry_points()` method
  - [ ] `generate_adaptive()` method
- [ ] Add support for station equations
- [ ] Write unit tests

### Phase 2: Integration ✅
- [ ] Integrate with `NativeIfcAlignment`
- [ ] Integrate with georeferencing system
- [ ] Integrate with profile view
- [ ] Integrate with corridor modeler
- [ ] Write integration tests

### Phase 3: Blender Visualization ✅
- [ ] Create `ui/visualization/station_markers.py`
- [ ] Implement `StationMarkerVisualizer` class
  - [ ] `generate_markers()` method
  - [ ] `_create_tick_mark()` method
  - [ ] `_create_station_label()` method
  - [ ] `update_markers()` method
- [ ] Implement `StationMarkerStyle` class
- [ ] Ensure markers are NOT exported to IFC
- [ ] Test visualization updates on alignment changes

### Phase 4: UI/Operators ✅
- [ ] Create `operators/stationing_operators.py`
- [ ] Implement operators:
  - [ ] `ALIGNMENT_OT_add_station`
  - [ ] `ALIGNMENT_OT_generate_stations`
  - [ ] `ALIGNMENT_OT_edit_station`
  - [ ] `ALIGNMENT_OT_remove_station`
  - [ ] `ALIGNMENT_OT_show_station_markers`
- [ ] Create `ui/panels/stationing_panel.py`
- [ ] Add UI panel for stationing controls
- [ ] Add preferences for default intervals, styles

### Phase 5: Documentation ✅
- [ ] User documentation for stationing features
- [ ] Developer API documentation
- [ ] Tutorial videos/screenshots
- [ ] Update roadmap with stationing completion

---

## Notes for Claude Code

### Priority Implementation Order

1. **Start with Core**: Implement `NativeIfcStationing.add_station_referent()` first
2. **Test Early**: Write unit tests as you go
3. **Integration Points**: Focus on alignment creation and corridor modeling
4. **Visualization Last**: Get IFC data structure working before visualization

### Code Quality Standards

- Follow BlenderCivil's existing architectural patterns (Bonsai BIM style)
- Maintain separation: core/ for IFC, operators/ for Blender actions, ui/ for display
- Comprehensive docstrings with examples
- Type hints for all functions
- Error handling for edge cases
- Production-ready quality (not prototype code)

### Testing Strategy

- Unit tests for each core method
- Integration tests across systems
- Visual validation in Blender
- IFC validation with external viewers (Bonsai, Solibri)
- Test with real-world alignment data

### Key Architectural Decisions

1. **Stationing is dual-nature**: IFC entities (exported) + Blender objects (not exported)
2. **IfcRelNests order is critical**: Must maintain ascending distance order
3. **Pset_Stationing is required**: Always attach to IfcReferent
4. **Visualization is separate**: No mixing of IFC and display code
5. **Integration is key**: Stationing touches alignment, georef, profile, corridor systems

---

**End of Implementation Guide**

This document provides the complete technical specification for implementing IFC 4.3 compliant stationing in BlenderCivil. Use it as the authoritative reference for all stationing-related development work.
