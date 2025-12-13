# IFC 4.3 Roadway Cross-Sections: Complete Implementation Reference for Saikei Civil

**Document Purpose:** Comprehensive knowledge base for implementing IFC 4.3 roadway cross-section profiles in Saikei Civil, the open-source Blender extension for native IFC civil infrastructure design.

**Last Updated:** November 24, 2025  
**Sources:** buildingSMART IFC 4.3 documentation, IFC-ROAD WP3 examples, Saikei Civil project architecture decisions

---

## Table of Contents

1. [IFC 4.3 Terminology](#ifc-43-terminology)
2. [Spatial Hierarchy](#spatial-hierarchy)
3. [Geometric Representation Entities](#geometric-representation-entities)
4. [Profile Definitions](#profile-definitions)
5. [Material Association](#material-association)
6. [Saikei Civil Architecture](#saikei-civil-architecture)
7. [Implementation Patterns](#implementation-patterns)
8. [Component Types](#component-types)
9. [Parametric Constraints](#parametric-constraints)
10. [IFC Export Workflow](#ifc-export-workflow)
11. [Best Practices](#best-practices)

---

## IFC 4.3 Terminology

### Core Concepts

**Cross-Section Profile (`IfcProfileDef`)**: A 2D definition of a roadway's typical section. Profiles define the shape that gets swept along an alignment to create 3D corridor geometry.

**Composite Profile (`IfcCompositeProfileDef`)**: A collection of multiple profile definitions combined into a single cross-section. Used when the roadway section has multiple distinct components (lanes, shoulders, curbs, etc.).

**Open Cross Profile (`IfcOpenCrossProfileDef`)**: IFC 4.3's preferred method for defining roadway cross-sections using widths and slopes rather than explicit coordinates. Optimized for civil infrastructure.

**Sectioned Solid (`IfcSectionedSolidHorizontal`)**: The IFC entity that creates 3D geometry by sweeping cross-section profiles along an alignment curve. This is the primary geometric representation for corridors.

**Road Part (`IfcRoadPart`)**: Spatial decomposition of a road facility. Can represent longitudinal segments (stations) or lateral divisions (carriageway, shoulder, sidewalk).

**Directrix**: The 3D alignment curve along which profiles are swept. Typically an `IfcAlignmentCurve` combining horizontal and vertical geometry.

### IFC-Standard Terms Used in Saikei Civil

| IFC 4.3 Term | Description | Usage in Saikei Civil |
|--------------|-------------|----------------------|
| `IfcCompositeProfileDef` | Combined cross-section | Complete roadway section definition |
| `IfcOpenCrossProfileDef` | Width/slope-based profile | Individual section components |
| `IfcArbitraryClosedProfileDef` | Coordinate-based profile | Complex/irregular shapes |
| `IfcSectionedSolidHorizontal` | Swept solid geometry | 3D corridor model |
| `IfcRoadPart` | Spatial container | Carriageway, shoulder, sidewalk zones |
| `IfcDistanceExpression` | Station positioning | Profile drop locations |
| `IfcAxis2PlacementLinear` | Profile orientation | Cross-section placement along alignment |

---

## Spatial Hierarchy

### IFC 4.3 Project Structure

```
IfcProject
└── IfcSite (project site with georeferencing)
    └── IfcRoad (the road facility)
        ├── IfcRoadPart (UsageType=LONGITUDINAL) - station-based segments
        │   └── IfcRoadPart (UsageType=LATERAL) - lateral divisions
        │       ├── IfcRoadPart (PredefinedType=CARRIAGEWAY)
        │       ├── IfcRoadPart (PredefinedType=SHOULDER)
        │       ├── IfcRoadPart (PredefinedType=SIDEWALK)
        │       └── IfcRoadPart (PredefinedType=ROADSIDE)
        └── IfcAlignment (horizontal & vertical geometry)
```

### IfcRoadPartTypeEnum (Predefined Types)

From buildingSMART IFC 4.3 specification:

**Primary Carriageway Types:**
- `CARRIAGEWAY` - Unitary lateral part of road built for traffic
- `TRAFFICLANE` - Lateral part designated for vehicular traffic
- `HARDSHOULDER` / `SOFTSHOULDER` - Emergency stopping areas
- `SHOULDER` - Lateral part adjacent to carriageway

**Pedestrian/Bicycle:**
- `SIDEWALK` - Footpath for pedestrians
- `BICYCLECROSSING` - Designated bicycle crossing

**Medians and Islands:**
- `CENTRALRESERVE` - Median separating carriageways
- `CENTRALISLAND` / `TRAFFICISLAND` - Raised/marked traffic direction areas
- `REFUGEISLAND` - Pedestrian refuge

**Special Areas:**
- `INTERSECTION` - Road junction area
- `ROUNDABOUT` - Circular intersection
- `BUS_STOP`, `LAYBY`, `PARKINGBAY`, `PASSINGBAY`
- `TOLLPLAZA` - Toll collection area
- `ROADSIDE` - Area outside roadway plateau

**Segments:**
- `ROADSEGMENT` - Longitudinal linear segment
- `ROADWAYPLATEAU` - Combined carriageway + shoulders area

**Note:** These `IfcRoadPart` entities represent **spatial divisions**, not geometric profiles. Geometry is defined through `IfcSectionedSolidHorizontal` and profile definitions.

---

## Geometric Representation Entities

### IfcSectionedSolidHorizontal

**Purpose:** The primary IFC 4.3 entity for creating 3D corridor geometry by sweeping varying cross-sections along an alignment.

**EXPRESS Definition:**
```
ENTITY IfcSectionedSolidHorizontal
  SUBTYPE OF (IfcSectionedSolid);
  Directrix : IfcCurve;
  CrossSections : LIST [2:?] OF IfcProfileDef;
  CrossSectionPositions : LIST [2:?] OF IfcAxis2PlacementLinear;
  WHERE
    CorrespondingSectionPositions : 
      SIZEOF(CrossSections) = SIZEOF(CrossSectionPositions);
    NoLongitudinalOffsets : 
      SIZEOF(QUERY(temp <* CrossSectionPositions | 
        EXISTS(temp.Location.OffsetLongitudinal))) = 0;
END_ENTITY;
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `Directrix` | `IfcCurve` | 3D alignment curve (must be Dim=3) |
| `CrossSections` | `LIST OF IfcProfileDef` | Profile definitions at each station |
| `CrossSectionPositions` | `LIST OF IfcAxis2PlacementLinear` | Positioning for each profile |

**Critical Constraints:**

1. **3D Directrix Required:** The directrix MUST be a 3D curve (Dim = 3)

2. **Profile Count Matching:** Number of CrossSections MUST equal number of CrossSectionPositions

3. **No Longitudinal Offsets:** CrossSectionPositions CANNOT use `OffsetLongitudinal` (would create non-manifold geometry)

4. **Profile Type Consistency:** All profiles MUST have same `ProfileType` (all AREA or all CURVE)

5. **Profile Subtype Consistency:** All profiles MUST be exact same subtype for proper interpolation

6. **Tag-Based Interpolation:** Points with matching tags interpolate linearly between sections

**From buildingSMART Documentation:**
> "The solid is generated by sweeping the CrossSections between CrossSectionPositions with linear interpolation between profile points with the same tag along the directrix."

### IfcSectionedSurface

**Purpose:** Creates surface geometry (not solid) by sweeping open cross-sections. Used for top-of-pavement surfaces or terrain modeling.

**Key Difference from IfcSectionedSolidHorizontal:**
- Uses CURVE profile type (open profiles)
- Creates surface, not solid volume
- Suitable for surface representation only

**EXPRESS Definition:**
```
ENTITY IfcSectionedSurface
  SUBTYPE OF (IfcSurface);
  Directrix : IfcCurve;
  CrossSectionPositions : LIST [2:?] OF IfcAxis2PlacementLinear;
  CrossSections : LIST [2:?] OF IfcProfileDef;
  WHERE
    AreaProfileTypes : 
      SIZEOF(QUERY(temp <* CrossSections | 
        temp.ProfileType = IfcProfileTypeEnum.CURVE)) <> 0;
END_ENTITY;
```

### IfcAxis2PlacementLinear

**Purpose:** Position and orient cross-sections along the alignment.

**Components:**
```python
# Create distance expression for station positioning
distance_expr = ifc_file.create_entity('IfcDistanceExpression',
    DistanceAlong=100.0,        # Station 0+100
    OffsetLateral=0.0,          # Lateral offset (allowed)
    OffsetVertical=0.0,         # Vertical offset (allowed)
    OffsetLongitudinal=None     # MUST NOT use for cross-sections
)

# Create placement
placement = ifc_file.create_entity('IfcAxis2PlacementLinear',
    Location=distance_expr,
    Axis=None,                  # Default: vertical (Z-up)
    RefDirection=None           # Default: perpendicular to directrix
)
```

**Orientation:**
- Profile X axis = RefDirection (perpendicular to alignment, positive right)
- Profile Y axis = Axis (typically vertical, positive up)
- Profile normal derived from placement, not directrix tangent

---

## Profile Definitions

### IfcOpenCrossProfileDef (Recommended for Roadways)

**Purpose:** Define cross-sections using widths and slopes - the IFC 4.3 preferred method for civil infrastructure.

**EXPRESS Definition:**
```
ENTITY IfcOpenCrossProfileDef
  SUBTYPE OF (IfcProfileDef);
  HorizontalWidths : IfcBoolean;
  Widths : LIST [1:?] OF IfcNonNegativeLengthMeasure;
  Slopes : LIST [1:?] OF IfcPlaneAngleMeasure;
  Tags : OPTIONAL LIST [2:?] OF IfcLabel;
  OffsetPoint : OPTIONAL IfcCartesianPoint;
  WHERE
    CorrectProfileType : SELF\IfcProfileDef.ProfileType = IfcProfileTypeEnum.CURVE;
    CorrespondingSlopeWidths : SIZEOF(Slopes) = SIZEOF(Widths);
    CorrespondingTags : (NOT EXISTS(Tags)) OR (SIZEOF(Tags) = (SIZEOF(Slopes) + 1));
END_ENTITY;
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `HorizontalWidths` | `BOOLEAN` | TRUE = widths measured horizontally |
| `Widths` | `LIST OF REAL` | Segment widths in sequence |
| `Slopes` | `LIST OF REAL` | Segment slopes (ratio or angle) |
| `Tags` | `LIST OF STRING` | Point identifiers for interpolation |
| `OffsetPoint` | `IfcCartesianPoint` | Optional reference point offset |

**Tag System (CRITICAL for Interpolation):**
- Number of Tags = Number of Widths + 1 (breakpoints between segments)
- Points with matching tags in consecutive sections are connected
- Enables varying numbers of breakpoints between sections
- Essential for lane widening, merges, and transitions

**Slope Convention:**
- Positive slope = rising from left to right
- Negative slope = falling from left to right
- Expressed as ratio (0.02 = 2%) or radians

**Example - Two-Lane Road:**
```python
# Profile points: LT (left edge), CT (centerline), RT (right edge)
# Two segments: left lane (3.6m, +2%) and right lane (3.6m, -2%)

profile = ifc_file.create_entity('IfcOpenCrossProfileDef',
    ProfileType='CURVE',
    ProfileName='Two Lane Section @ Sta 0+000',
    HorizontalWidths=True,
    Widths=[3.6, 3.6],           # Two 3.6m segments
    Slopes=[0.02, -0.02],         # Crown: +2% left, -2% right
    Tags=['LT', 'CT', 'RT']       # 3 tags for 2 segments
)
```

**Example - With Shoulders:**
```python
# Profile: LS (left shoulder), LT, CT, RT, RS (right shoulder)
# Four segments: L-shoulder, L-lane, R-lane, R-shoulder

profile = ifc_file.create_entity('IfcOpenCrossProfileDef',
    ProfileType='CURVE',
    ProfileName='Two Lane with Shoulders',
    HorizontalWidths=True,
    Widths=[2.4, 3.6, 3.6, 2.4],
    Slopes=[0.04, 0.02, -0.02, -0.04],  # Steeper shoulders
    Tags=['LS', 'LT', 'CT', 'RT', 'RS']
)
```

### IfcArbitraryClosedProfileDef

**Purpose:** Define closed cross-sections using explicit point coordinates. Used for pavement structures with depth.

**When to Use:**
- Profiles with thickness/depth (pavement layers)
- Complex irregular geometries
- When precise coordinate control is needed

**Structure:**
```python
# Create point list for rectangular lane profile
# Points define closed shape: top-left → top-right → bottom-right → bottom-left → close

point_list = ifc_file.create_entity('IfcCartesianPointList2D',
    CoordList=[
        (0.0, 0.0),      # Top-left (attachment point)
        (3.6, -0.072),   # Top-right (3.6m @ -2% slope)
        (3.6, -0.272),   # Bottom-right (200mm depth)
        (0.0, -0.200),   # Bottom-left
    ],
    TagList=['TL', 'TR', 'BR', 'BL']  # Optional tags for interpolation
)

curve = ifc_file.create_entity('IfcIndexedPolyCurve',
    Points=point_list,
    Segments=None,      # Use all points in sequence
    SelfIntersect=False
)

profile = ifc_file.create_entity('IfcArbitraryClosedProfileDef',
    ProfileType='AREA',
    ProfileName='Travel Lane with Pavement Structure',
    OuterCurve=curve
)
```

**Critical Rules:**
- Profile MUST be closed (implicit closure from last to first point)
- For interpolation: consecutive sections should have same point count
- Points with matching tags interpolate properly

### IfcCompositeProfileDef

**Purpose:** Combine multiple profile definitions into a single cross-section definition.

**EXPRESS Definition:**
```
ENTITY IfcCompositeProfileDef
  SUBTYPE OF (IfcProfileDef);
  Profiles : SET [2:?] OF IfcProfileDef;
  Label : OPTIONAL IfcLabel;
  WHERE
    InvariantProfileType : 
      SIZEOF(QUERY(temp <* Profiles | 
        temp.ProfileType <> Profiles[1].ProfileType)) = 0;
    NoRecursion : 
      SIZEOF(QUERY(temp <* Profiles | 
        'IFCCOMPOSITEPROFILEDEF' IN TYPEOF(temp))) = 0;
END_ENTITY;
```

**Constraints:**
- All profiles MUST have same ProfileType (all AREA or all CURVE)
- No recursive composition (composites cannot contain composites)
- Minimum 2 profiles required

**Example - Complete Road Section:**
```python
# Create individual component profiles
left_shoulder = create_open_profile('Left Shoulder', [2.4], [0.04])
left_lane = create_open_profile('Left Lane', [3.6], [0.02])
right_lane = create_open_profile('Right Lane', [3.6], [-0.02])
right_shoulder = create_open_profile('Right Shoulder', [2.4], [-0.04])

# Combine into composite
road_section = ifc_file.create_entity('IfcCompositeProfileDef',
    ProfileType='CURVE',
    ProfileName='Complete Two-Lane Rural Section',
    Profiles=[left_shoulder, left_lane, right_lane, right_shoulder],
    Label='AASHTO Rural Two-Lane'
)
```

### Profile Type Summary

| Profile Type | ProfileType Enum | Use Case |
|--------------|------------------|----------|
| `IfcOpenCrossProfileDef` | CURVE | Surface profiles (top of pavement) |
| `IfcArbitraryClosedProfileDef` | AREA | Solid profiles (pavement with depth) |
| `IfcCompositeProfileDef` | CURVE or AREA | Combined multi-component sections |

---

## Material Association

### IfcMaterialProfileSet

**Purpose:** Associate materials with profile definitions for pavement structure modeling.

**Pattern:**
```python
# Create materials
asphalt = ifc_file.create_entity('IfcMaterial', Name='Asphalt HMA')
aggregate = ifc_file.create_entity('IfcMaterial', Name='Aggregate Base')

# Create material profiles
material_profiles = [
    ifc_file.create_entity('IfcMaterialProfile',
        Name='Wearing Course',
        Material=asphalt,
        Profile=wearing_course_profile
    ),
    ifc_file.create_entity('IfcMaterialProfile',
        Name='Base Course',
        Material=aggregate,
        Profile=base_course_profile
    )
]

# Create material profile set
profile_set = ifc_file.create_entity('IfcMaterialProfileSet',
    Name='Pavement Structure',
    MaterialProfiles=material_profiles
)

# Associate with road element
ifc_file.create_entity('IfcRelAssociatesMaterial',
    GlobalId=ifcopenshell.guid.new(),
    RelatingMaterial=profile_set,
    RelatedObjects=[road_element]
)
```

### IfcMaterialLayerSet (Alternative)

**Purpose:** Define layered material structure for pavement courses.

```python
# Create layers (bottom to top)
layers = [
    ifc_file.create_entity('IfcMaterialLayer',
        Material=subbase_material,
        LayerThickness=0.150,  # 150mm
        Name='Subbase'
    ),
    ifc_file.create_entity('IfcMaterialLayer',
        Material=base_material,
        LayerThickness=0.100,  # 100mm
        Name='Aggregate Base'
    ),
    ifc_file.create_entity('IfcMaterialLayer',
        Material=asphalt_material,
        LayerThickness=0.050,  # 50mm
        Name='Wearing Course'
    )
]

layer_set = ifc_file.create_entity('IfcMaterialLayerSet',
    MaterialLayers=layers,
    LayerSetName='Full Depth Pavement'
)
```

---

## Saikei Civil Architecture

### Design Philosophy: Python-Based Parametric System

Saikei Civil implements parametric cross-sections using Python code with a Blender UI interface. This architectural decision is based on:

1. **IFC Native Approach:** Cross-sections are defined as IFC profile entities, not converted from other formats

2. **Engineering Precision:** Python calculations provide survey-grade accuracy needed for civil engineering

3. **Standard Compliance:** Direct mapping to IFC 4.3 entities ensures proper schema compliance

4. **Extensibility:** Python-based components are easily extended for new profile types

**Architecture Pattern:**
```
┌─────────────────────────────────────────┐
│   BLENDER UI PANELS                     │
│   (User Interface)                      │
│   • Profile component browser           │
│   • Add/remove/reorder components       │
│   • Property fields and dropdowns       │
│   • Material assignment UI              │
│   • Station-range constraint editor     │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│   PYTHON CORE                           │
│   (Business Logic - No Blender Imports) │
│   • Profile calculations                │
│   • Constraint interpolation            │
│   • IFC entity generation               │
│   • Validation functions                │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│   IFC OUTPUT                            │
│   (Native IFC 4.3)                      │
│   • IfcCompositeProfileDef              │
│   • IfcSectionedSolidHorizontal         │
│   • IfcMaterialProfileSet               │
│   • Proper spatial hierarchy            │
└─────────────────────────────────────────┘
```

### Three-Layer Architecture

Following Bonsai BIM patterns:

**Core Layer** (`core/`):
- Pure Python, no Blender imports
- Profile geometry calculations
- IFC entity creation via ifcopenshell
- Constraint management

**Tool Layer** (`tool/`):
- Blender-specific implementations
- Mesh generation for visualization
- Coordinate transformations

**UI Layer** (`ui/`):
- Blender panels and operators
- PropertyGroups for data storage
- User interaction handling

---

## Implementation Patterns

### Profile Component Base Class

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Optional
import ifcopenshell

@dataclass
class ProfileComponentParams:
    """Base parameters for all profile components"""
    name: str
    width: float              # Component width in meters
    cross_slope: float        # Transverse slope as ratio (0.02 = 2%)
    side: str                 # "left" or "right" from centerline

class ProfileComponent(ABC):
    """Abstract base for all cross-section profile components"""
    
    def __init__(self, params: ProfileComponentParams):
        self.params = params
        self.attachment_point: Tuple[float, float] = (0.0, 0.0)
    
    @abstractmethod
    def calculate_points(self) -> List[Tuple[float, float]]:
        """Calculate 2D profile points (offset, elevation)"""
        pass
    
    @abstractmethod
    def to_ifc_profile(self, ifc_file: ifcopenshell.file) -> 'IfcProfileDef':
        """Export as IFC profile definition"""
        pass
    
    def get_end_point(self) -> Tuple[float, float]:
        """Get attachment point for next component"""
        points = self.calculate_points()
        return points[-1] if points else self.attachment_point
```

### Lane Component Implementation

```python
@dataclass
class LaneParams(ProfileComponentParams):
    """Parameters for travel lane profiles"""
    depth: float = 0.20  # Pavement structure depth

class LaneComponent(ProfileComponent):
    """Travel lane with pavement structure"""
    
    def calculate_points(self) -> List[Tuple[float, float]]:
        """Calculate closed profile for lane with depth"""
        x0, y0 = self.attachment_point
        w = self.params.width
        slope = self.params.cross_slope
        depth = self.params.depth
        
        # Adjust slope sign based on side
        if self.params.side == "left":
            slope = abs(slope)
            x1 = x0 - w  # Extend left
        else:
            slope = -abs(slope)
            x1 = x0 + w  # Extend right
        
        # Calculate elevation change
        y1 = y0 + (w * slope)
        
        # Return closed profile (clockwise for AREA type)
        return [
            (x0, y0),           # Top attachment
            (x1, y1),           # Top outer edge
            (x1, y1 - depth),   # Bottom outer
            (x0, y0 - depth),   # Bottom attachment
        ]
    
    def to_ifc_profile(self, ifc_file: ifcopenshell.file) -> 'IfcProfileDef':
        """Export as IfcArbitraryClosedProfileDef"""
        points = self.calculate_points()
        
        point_list = ifc_file.create_entity('IfcCartesianPointList2D',
            CoordList=points
        )
        
        curve = ifc_file.create_entity('IfcIndexedPolyCurve',
            Points=point_list
        )
        
        return ifc_file.create_entity('IfcArbitraryClosedProfileDef',
            ProfileType='AREA',
            ProfileName=self.params.name,
            OuterCurve=curve
        )
    
    def to_ifc_open_profile(self, ifc_file: ifcopenshell.file) -> 'IfcProfileDef':
        """Export as IfcOpenCrossProfileDef (surface only)"""
        return ifc_file.create_entity('IfcOpenCrossProfileDef',
            ProfileType='CURVE',
            ProfileName=self.params.name,
            HorizontalWidths=True,
            Widths=[self.params.width],
            Slopes=[self.params.cross_slope],
            Tags=[f'{self.params.name}_start', f'{self.params.name}_end']
        )
```

### Composite Profile Manager

```python
class CompositeProfileManager:
    """Manages composite cross-section profiles"""
    
    def __init__(self, name: str):
        self.name = name
        self.components: List[ProfileComponent] = []
    
    def add_component(self, component: ProfileComponent) -> None:
        """Add component to profile"""
        if self.components:
            # Attach to previous component's end point
            prev_end = self.components[-1].get_end_point()
            component.attachment_point = prev_end
        self.components.append(component)
    
    def calculate_all_points(self) -> List[Tuple[float, float]]:
        """Get all points from all components"""
        all_points = []
        for component in self.components:
            all_points.extend(component.calculate_points())
        return all_points
    
    def get_total_width(self) -> float:
        """Calculate total profile width"""
        return sum(c.params.width for c in self.components)
    
    def to_ifc_composite(self, ifc_file: ifcopenshell.file,
                          station: float = 0.0) -> 'IfcCompositeProfileDef':
        """Export as IFC composite profile"""
        profiles = [c.to_ifc_profile(ifc_file) for c in self.components]
        
        return ifc_file.create_entity('IfcCompositeProfileDef',
            ProfileType='AREA',
            ProfileName=f'{self.name} @ Sta {station:.3f}',
            Profiles=profiles,
            Label=self.name
        )
    
    def to_ifc_open_composite(self, ifc_file: ifcopenshell.file,
                               station: float = 0.0) -> 'IfcOpenCrossProfileDef':
        """Export as single IfcOpenCrossProfileDef (combined)"""
        widths = [c.params.width for c in self.components]
        slopes = [c.params.cross_slope for c in self.components]
        
        # Generate tags for all breakpoints
        tags = [self.components[0].params.name + '_start']
        for c in self.components:
            tags.append(c.params.name + '_end')
        
        return ifc_file.create_entity('IfcOpenCrossProfileDef',
            ProfileType='CURVE',
            ProfileName=f'{self.name} @ Sta {station:.3f}',
            HorizontalWidths=True,
            Widths=widths,
            Slopes=slopes,
            Tags=tags
        )
```

### Standard Profile Factory

```python
class StandardProfiles:
    """Factory methods for common roadway profiles"""
    
    @staticmethod
    def create_two_lane_rural() -> CompositeProfileManager:
        """Standard two-lane rural road (AASHTO)"""
        profile = CompositeProfileManager("Two Lane Rural")
        
        # Build from centerline outward (left side)
        profile.add_component(LaneComponent(LaneParams(
            name="Left Lane", width=3.6, cross_slope=0.02, 
            side="left", depth=0.20
        )))
        profile.add_component(ShoulderComponent(ShoulderParams(
            name="Left Shoulder", width=2.4, cross_slope=0.04,
            side="left", depth=0.10
        )))
        
        # Reset attachment for right side
        # (In practice, handle symmetric sections appropriately)
        
        return profile
    
    @staticmethod
    def create_urban_section() -> CompositeProfileManager:
        """Urban section with curb and sidewalk"""
        profile = CompositeProfileManager("Urban Section")
        
        profile.add_component(LaneComponent(LaneParams(
            name="Travel Lane", width=3.3, cross_slope=0.02,
            side="right", depth=0.20
        )))
        profile.add_component(CurbComponent(CurbParams(
            name="Curb", width=0.15, height=0.15,
            curb_type="vertical"
        )))
        profile.add_component(SidewalkComponent(SidewalkParams(
            name="Sidewalk", width=1.5, cross_slope=0.02,
            thickness=0.10
        )))
        
        return profile
```

---

## Component Types

### Standard Component Library

#### 1. Lane Component

**Purpose:** Travel lanes with full pavement structure

**Parameters:**
- `width`: Lane width (typical: 3.0-3.6m)
- `cross_slope`: Transverse slope ratio (typical: 0.015-0.025)
- `depth`: Total pavement depth (typical: 0.20-0.40m)
- `side`: "left" or "right" from centerline

**Geometry:** Closed 4-point profile (rectangular with slope)

**IFC Export:** `IfcArbitraryClosedProfileDef` with ProfileType=AREA

#### 2. Shoulder Component

**Purpose:** Paved or unpaved shoulder areas

**Parameters:**
- `width`: Shoulder width (typical: 1.8-3.0m)
- `cross_slope`: Slope away from pavement (typical: 0.04-0.06)
- `depth`: Surface thickness
- `material`: "paved" or "gravel"

**Geometry:** Closed profile similar to lane

#### 3. Curb Component

**Purpose:** Vertical barrier at pavement edge

**Parameters:**
- `height`: Curb height (typical: 0.15-0.20m)
- `width`: Curb width at base (typical: 0.15-0.30m)
- `curb_type`: "vertical", "sloped", or "mountable"

**IFC Export:** Maps to `IfcKerb` entity

#### 4. Sidewalk Component

**Purpose:** Pedestrian walkway

**Parameters:**
- `width`: Sidewalk width (typical: 1.5-2.4m)
- `thickness`: Concrete thickness (typical: 0.10-0.15m)
- `cross_slope`: Drainage slope (typical: 0.02)

#### 5. Ditch Component

**Purpose:** Roadside drainage channel

**Parameters:**
- `bottom_width`: Width at ditch bottom
- `depth`: Ditch depth
- `side_slopes`: Left and right side slope ratios

**Geometry:** Trapezoidal or V-shaped open profile

#### 6. Slope Component

**Purpose:** Cut/fill tie to existing ground

**Parameters:**
- `cut_slope`: Cut slope ratio (typical: 2:1)
- `fill_slope`: Fill slope ratio (typical: 3:1)
- `max_offset`: Maximum daylight distance

**Special Behavior:** Targets existing ground surface

### AASHTO Standard Values

**Lane Widths:**
- Interstate/Freeway: 3.6m (12 ft)
- Arterials: 3.3-3.6m (11-12 ft)
- Local Streets: 3.0-3.3m (10-11 ft)

**Cross-Slopes:**
- High-Type Pavement: 1.5-2.0%
- Shoulders: 4.0-6.0%

**Pavement Depths:**
- Surface Course: 40-100mm
- Base Course: 100-200mm
- Subbase: 100-300mm

---

## Parametric Constraints

### Constraint System Overview

Saikei Civil implements station-range based parametric constraints that modify profile parameters along the alignment.

**Constraint Types:**

1. **Point Constraint:** Single-station override
2. **Range Constraint:** Linear interpolation between stations

### Implementation

```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class PointConstraint:
    """Single-station parameter override"""
    station: float
    component_name: str
    parameter: str
    value: float

@dataclass
class RangeConstraint:
    """Interpolating parameter override"""
    start_station: float
    end_station: float
    component_name: str
    parameter: str
    start_value: float
    end_value: float

class ConstraintManager:
    """Manages parametric constraints for profile"""
    
    def __init__(self):
        self.constraints: List = []
    
    def add_point_constraint(self, station: float, component: str,
                              parameter: str, value: float) -> None:
        """Add single-station override"""
        self.constraints.append(PointConstraint(
            station, component, parameter, value
        ))
    
    def add_range_constraint(self, start_sta: float, end_sta: float,
                              component: str, parameter: str,
                              start_val: float, end_val: float) -> None:
        """Add interpolating range constraint"""
        self.constraints.append(RangeConstraint(
            start_sta, end_sta, component, parameter, start_val, end_val
        ))
    
    def get_value_at_station(self, component: str, parameter: str,
                              station: float, default: float) -> float:
        """Get constrained value at specific station"""
        # Check point constraints first (highest priority)
        for c in self.constraints:
            if isinstance(c, PointConstraint):
                if (c.component_name == component and 
                    c.parameter == parameter and
                    abs(c.station - station) < 0.001):
                    return c.value
        
        # Check range constraints
        for c in self.constraints:
            if isinstance(c, RangeConstraint):
                if (c.component_name == component and
                    c.parameter == parameter and
                    c.start_station <= station <= c.end_station):
                    # Linear interpolation
                    if c.start_station == c.end_station:
                        return c.start_value
                    factor = ((station - c.start_station) / 
                              (c.end_station - c.start_station))
                    return c.start_value + factor * (c.end_value - c.start_value)
        
        return default
```

### Common Constraint Scenarios

**Lane Widening:**
```python
# Widen lane from 3.6m to 4.2m for turn lane
constraint_mgr.add_range_constraint(
    start_sta=200.0, end_sta=300.0,
    component="Right Lane", parameter="width",
    start_val=3.6, end_val=4.2
)
```

**Pavement Depth Variation:**
```python
# Increase pavement depth for heavy truck route
constraint_mgr.add_point_constraint(
    station=500.0, component="Travel Lane",
    parameter="depth", value=0.30
)
```

---

## IFC Export Workflow

### Complete Corridor Export

```python
import ifcopenshell
import ifcopenshell.guid

def export_corridor(
    alignment: 'Alignment3D',
    profile_manager: CompositeProfileManager,
    constraint_manager: ConstraintManager,
    stations: List[float],
    ifc_file: ifcopenshell.file,
    site: 'IfcSite'
) -> 'IfcRoad':
    """
    Export complete corridor as native IFC
    
    Args:
        alignment: 3D alignment (horizontal + vertical)
        profile_manager: Cross-section profile definition
        constraint_manager: Station-based constraints
        stations: List of profile drop stations
        ifc_file: IFC file handle
        site: Parent spatial container
    
    Returns:
        IfcRoad entity with corridor geometry
    """
    
    # 1. Create IfcRoad spatial container
    road = ifc_file.create_entity('IfcRoad',
        GlobalId=ifcopenshell.guid.new(),
        Name=f"Road - {profile_manager.name}",
        ObjectType="Highway"
    )
    
    # 2. Get alignment curve as directrix
    directrix = alignment.to_ifc_alignment_curve(ifc_file)
    
    # 3. Generate profiles at each station
    profiles = []
    positions = []
    
    for station in stations:
        # Apply constraints for this station
        for component in profile_manager.components:
            for param in ['width', 'cross_slope', 'depth']:
                value = constraint_manager.get_value_at_station(
                    component.params.name, param, station,
                    getattr(component.params, param, 0.0)
                )
                if hasattr(component.params, param):
                    setattr(component.params, param, value)
        
        # Create profile at this station
        profile = profile_manager.to_ifc_composite(ifc_file, station)
        profiles.append(profile)
        
        # Create position
        distance = ifc_file.create_entity('IfcDistanceExpression',
            DistanceAlong=station,
            OffsetLateral=0.0,
            OffsetVertical=0.0
        )
        
        position = ifc_file.create_entity('IfcAxis2PlacementLinear',
            Location=distance
        )
        positions.append(position)
    
    # 4. Create sectioned solid
    corridor_solid = ifc_file.create_entity('IfcSectionedSolidHorizontal',
        Directrix=directrix,
        CrossSections=profiles,
        CrossSectionPositions=positions
    )
    
    # 5. Create shape representation
    context = get_geometric_context(ifc_file)  # Helper function
    
    shape_rep = ifc_file.create_entity('IfcShapeRepresentation',
        ContextOfItems=context,
        RepresentationIdentifier='Body',
        RepresentationType='SectionedSolidHorizontal',
        Items=[corridor_solid]
    )
    
    product_shape = ifc_file.create_entity('IfcProductDefinitionShape',
        Representations=[shape_rep]
    )
    
    road.Representation = product_shape
    
    # 6. Link to spatial hierarchy
    ifc_file.create_entity('IfcRelAggregates',
        GlobalId=ifcopenshell.guid.new(),
        RelatingObject=site,
        RelatedObjects=[road]
    )
    
    return road
```

### Station Sampling Strategy

```python
def calculate_profile_stations(
    alignment: 'Alignment3D',
    max_spacing: float = 25.0,
    min_spacing: float = 5.0,
    constraint_stations: List[float] = None
) -> List[float]:
    """
    Calculate optimal stations for profile drops
    
    Args:
        alignment: 3D alignment
        max_spacing: Maximum spacing on tangent sections
        min_spacing: Minimum spacing on curves
        constraint_stations: Stations where constraints change
    
    Returns:
        Sorted list of stations for profile export
    """
    stations = set([0.0, alignment.length])  # Always include ends
    
    # Add constraint change points
    if constraint_stations:
        stations.update(constraint_stations)
    
    # Add regular intervals based on curvature
    current = 0.0
    while current < alignment.length:
        curvature = alignment.get_curvature_at(current)
        
        if curvature < 0.001:  # Tangent
            spacing = max_spacing
        else:
            # Tighter spacing for sharper curves
            spacing = max(min_spacing, min_spacing / (curvature * 100))
        
        current += spacing
        if current < alignment.length:
            stations.add(current)
    
    return sorted(stations)
```

---

## Best Practices

### IFC Compliance

1. **Always use IFC 4.3 entities** for new development
2. **Maintain profile type consistency** - all AREA or all CURVE
3. **Use meaningful tags** for interpolation control
4. **Follow buildingSMART naming** conventions

### Profile Design

1. **Start from centerline** and build outward
2. **Use `IfcOpenCrossProfileDef`** for surface-only profiles
3. **Use `IfcArbitraryClosedProfileDef`** for profiles with depth
4. **Validate total width** is reasonable

### Constraint Application

1. **Use constraints sparingly** for best performance
2. **Prefer range constraints** for smooth transitions
3. **Validate constraint values** before application
4. **Document constraint intent** in code comments

### Testing

```python
def validate_profile(profile_manager: CompositeProfileManager) -> List[str]:
    """Validate profile configuration"""
    errors = []
    
    if len(profile_manager.components) < 1:
        errors.append("Profile must have at least 1 component")
    
    for c in profile_manager.components:
        if c.params.width <= 0:
            errors.append(f"{c.params.name}: width must be positive")
        if abs(c.params.cross_slope) > 0.12:
            errors.append(f"{c.params.name}: slope > 12% unusual")
    
    total_width = profile_manager.get_total_width()
    if total_width > 30.0:
        errors.append(f"Total width {total_width}m exceeds typical maximum")
    
    return errors
```

---

## References

### buildingSMART Documentation

- **IFC 4.3 Documentation:** https://ifc43-docs.standards.buildingsmart.org/
- **IfcRoadPart:** https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcRoadPart.htm
- **IfcSectionedSolidHorizontal:** https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcSectionedSolidHorizontal.htm
- **IfcOpenCrossProfileDef:** https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcOpenCrossProfileDef.htm
- **IfcProfileResource:** https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/ifcprofileresource/content.html

### AASHTO Standards

- "A Policy on Geometric Design of Highways and Streets" (Green Book)
- AASHTO M145 - Pavement material classifications

### Saikei Civil Project Files

- Sprint 4 Cross-Section Research: `/mnt/project/Sprint4_Day1_IFC_CrossSection_Research.md`
- Sprint 4 Implementation: `/mnt/project/Sprint4_Complete_Summary.md`
- Sprint 5 Corridor Research: `/mnt/project/Sprint5_Day1_IFC_Corridor_Research.md`

---

**Document Status:** ✅ Complete - IFC 4.3 Focused  
**Target Audience:** Claude Code development assistance  
**Terminology:** IFC 4.3 standard terms only

