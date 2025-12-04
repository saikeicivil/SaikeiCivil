# IFC Roadway Templates & Assemblies: Complete Implementation Reference

**Document Purpose:** Comprehensive knowledge base for implementing roadway cross-section templates/assemblies in BlenderCivil, based on IFC 4.3 standards and industry best practices.

**Last Updated:** November 24, 2025  
**Sources:** buildingSMART IFC 4.3 documentation, IFC-ROAD WP3 examples, Civil 3D/OpenRoads analysis, BlenderCivil project decisions

---

## Table of Contents

1. [Terminology & Concepts](#terminology--concepts)
2. [IFC 4.3 Entity Structure](#ifc-43-entity-structure)
3. [Industry Software Analysis](#industry-software-analysis)
4. [BlenderCivil Design Decisions](#blendercivil-design-decisions)
5. [Implementation Architecture](#implementation-architecture)
6. [Component Types & Properties](#component-types--properties)
7. [Parametric Constraints System](#parametric-constraints-system)
8. [IFC Export Patterns](#ifc-export-patterns)
9. [Best Practices & Guidelines](#best-practices--guidelines)

---

## Terminology & Concepts

### Industry Terminology Differences

Different professional software packages use different terms for the same concept:

| Software | Primary Term | Description |
|----------|--------------|-------------|
| **Autodesk Civil 3D** | **Assembly** | Collection of subassemblies defining typical section |
| | **Subassembly** | Individual component (lane, shoulder, curb, etc.) |
| **Bentley OpenRoads** | **Template** | Complete cross-section definition |
| | **Component** | Individual section element |
| **IFC 4.3 Standard** | **IfcCompositeProfileDef** | Collection of profile definitions |
| | **IfcOpenCrossProfileDef** | Individual cross-section profile |
| **BlenderCivil** | **Assembly** | Matches Civil 3D terminology |
| | **Component** | Individual parametric section element |

**Key Insight:** These are all describing the same fundamental concept - a parametric, reusable definition of a roadway's typical cross-section that can be swept along an alignment to create a 3D corridor model.

### Core Concepts

**Assembly/Template**: A complete, parametric definition of a roadway cross-section containing:
- Multiple components arranged left-to-right from centerline
- Material layer definitions for pavement structure
- Parametric constraints that can vary by station
- Attachment logic defining how components connect

**Component**: A self-contained section element representing:
- Travel lanes (with specific widths, cross-slopes, materials)
- Shoulders (paved or gravel, with specified slopes)
- Curbs (vertical or sloped, with height specifications)
- Sidewalks (with width and slope requirements)
- Ditches (v-shaped or trapezoidal drainage elements)
- Side slopes (cut/fill with specified ratios)

**Parametric Constraints**: Station-range based overrides allowing:
- Width variations (lane widening in curves)
- Depth modifications (varying pavement thickness)
- Slope adjustments (superelevation transitions)
- Material changes (different pavement types by section)

---

## IFC 4.3 Entity Structure

### Spatial Hierarchy

```
IfcProject
└── IfcSite (project site)
    └── IfcRoad (the road facility)
        ├── IfcRoadPart (LONGITUDINAL) - longitudinal segments
        │   └── IfcRoadPart (LATERAL) - lateral divisions
        │       ├── IfcRoadPart (CARRIAGEWAY)
        │       ├── IfcRoadPart (SHOULDER)
        │       ├── IfcRoadPart (SIDEWALK)
        │       └── IfcRoadPart (ROADSIDE)
        └── IfcAlignment (horizontal & vertical geometry)
```

### IfcRoadPart Types (Predefined)

From buildingSMART IFC 4.3 specification, `IfcRoadPartTypeEnum` includes:

**Primary Types:**
- `CARRIAGEWAY` - Unitary lateral part of road built for traffic
- `TRAFFICLANE` - Lateral part designated for vehicular traffic
- `SHOULDER` - Lateral part adjacent to carriageway (emergency use)
- `SIDEWALK` - Footpath along side of road for pedestrians
- `ROADSIDE` - Area outside roadway plateau not intended for vehicles
- `CENTRALISLAND` / `TRAFFICISLAND` - Raised/marked areas directing traffic
- `CENTRALRESERVE` - Median separating carriageways

**Additional Types:**
- `BUS_STOP`, `LAYBY`, `PARKINGBAY`, `PASSINGBAY`
- `BICYCLECROSSING`, `PEDESTRIAN_CROSSING`, `RAILWAYCROSSING`
- `HARDSHOULDER`, `SOFTSHOULDER`
- `INTERSECTION`, `ROUNDABOUT`, `TOLLPLAZA`
- `ROADSEGMENT`, `ROADWAYPLATEAU`, `REFUGEISLAND`

**Usage Note:** In IFC 4.3, these `IfcRoadPart` entities represent **spatial divisions** of the road, not the geometric profiles themselves. The geometric representation is handled through `IfcSectionedSolidHorizontal` and profile definitions.

### Geometric Representation: IfcSectionedSolidHorizontal

**Purpose:** The primary IFC entity for creating 3D corridor geometry by sweeping cross-sections along an alignment.

**Entity Definition (EXPRESS):**
```
ENTITY IfcSectionedSolidHorizontal
  SUBTYPE OF (IfcSectionedSolid);
  Directrix : IfcCurve;                           -- 3D alignment curve
  CrossSections : LIST [2:?] OF IfcProfileDef;    -- Profile definitions
  CrossSectionPositions : LIST [2:?] OF IfcAxis2PlacementLinear;
  WHERE
    CorrespondingSectionPositions : 
      SIZEOF(CrossSections) = SIZEOF(CrossSectionPositions);
    NoLongitudinalOffsets : 
      SIZEOF(QUERY(temp <* CrossSectionPositions | 
        EXISTS(temp.Location.OffsetLongitudinal))) = 0;
END_ENTITY;
```

**Key Characteristics:**

1. **Directrix Requirements:**
   - MUST be 3D curve (Dim = 3) ✅ Matches BlenderCivil 3D alignments
   - Should be tangent continuous (or accept miters at discontinuities)
   - Typically an `IfcAlignmentCurve` from horizontal+vertical alignment

2. **Cross-Section Profiles:**
   - Minimum 2 profiles required
   - Profiles can vary along directrix (for widening, superelevation, etc.)
   - Linear interpolation between profiles with same tag values
   - Profile normal derived from `IfcAxis2PlacementLinear`, not tangent

3. **Profile Type Consistency (CRITICAL):**
   - All CrossSections MUST have same ProfileType (AREA or CURVE)
   - All profiles MUST be exact same subtype (e.g., all `IfcArbitraryClosedProfileDef`)
   - Cannot mix different profile definition types

4. **Tag System for Interpolation:**
   - Points with same tags are interpolated between consecutive sections
   - Enables smooth transitions for lane widening, shoulder adjustments
   - CRITICAL for proper corridor generation

5. **Coordinate System:**
   - Profile X axis = direction of RefDirection from `IfcAxis2PlacementLinear`
   - Profile Y axis = direction of Axis (typically vertical)
   - Enables proper orientation even with superelevation

**From buildingSMART Documentation:**
> "The solid is generated by sweeping the CrossSections between CrossSectionPositions with linear interpolation between profile points with the same tag along the directrix. The profile normal is derived from the associated IfcAxis2PlacementLinear, not necessarily the tangent of the Directrix."

### Profile Definitions for Cross-Sections

#### IfcOpenCrossProfileDef (NEW in IFC 4.3)

**Purpose:** Define open cross-section profiles using widths and slopes - the preferred method for roadway design.

**Entity Definition:**
```
ENTITY IfcOpenCrossProfileDef
  SUBTYPE OF (IfcProfileDef);
  HorizontalWidths : IfcBoolean;                -- True if widths measured horizontally
  Widths : LIST [1:?] OF IfcNonNegativeLengthMeasure;  -- Segment widths
  Slopes : LIST [1:?] OF IfcPlaneAngleMeasure;         -- Segment slopes
  Tags : OPTIONAL LIST [2:?] OF IfcLabel;              -- Point identifiers
  OffsetPoint : OPTIONAL IfcCartesianPoint;            -- Reference point offset
  WHERE
    CorrectProfileType : SELF\IfcProfileDef.ProfileType = IfcProfileTypeEnum.CURVE;
    CorrespondingSlopeWidths : SIZEOF(Slopes) = SIZEOF(Widths);
    CorrespondingTags : (NOT EXISTS(Tags)) OR 
                        (SIZEOF(Tags) = (SIZEOF(Slopes) + 1));
END_ENTITY;
```

**Usage Pattern:**
```python
# Example: Simple two-lane road cross-section
# Points: LT (left edge), LC (left center), CT (centerline), 
#         RC (right center), RT (right edge)

profile = ifcfile.create_entity('IfcOpenCrossProfileDef',
    ProfileType='CURVE',
    ProfileName='Two Lane Rural Road Section',
    HorizontalWidths=True,
    Widths=[3.6, 3.6],              # Two 3.6m lanes
    Slopes=[-0.02, 0.02],            # 2% cross-slopes
    Tags=['LT', 'LC', 'CT', 'RC', 'RT']  # 5 points = 4 segments + 1
)
```

**Tag System Details:**
- Tags allow consecutive cross-sections to have different numbers of breakpoints
- Points with same tag are connected via linear longitudinal breakline
- Enables branching longitudinal breaklines for complex geometries
- Number of tags = Number of widths + 1 (endpoints + breakpoints)

**Slope Sign Convention:**
- Positive slope = rising from left to right
- Negative slope = falling from left to right
- Based on mathematical slope definition

**From IFC-ROAD WP3 Examples:**
> "The behaviour of OpenCrossProfileDef in sweeping operation can be controlled by attribute Tags. Tags allow two consecutive cross sections to have different number of break points: points with the same tag value are connected either by assuming linear longitudinal breakline between them, or by a guide curve identified by the same Tag value."

#### IfcArbitraryClosedProfileDef

**Purpose:** Define closed cross-section profiles using explicit point coordinates.

**When to Use:**
- Complex, irregular geometries not easily defined by widths/slopes
- Precise control over profile shape
- Maintaining exact coordinates from design data

**Example Usage:**
```python
# Create point list for profile
points = ifcfile.create_entity('IfcCartesianPointList2D',
    CoordList=[
        (3.0, -0.1),   # LT (left edge)
        (0.0, 0.0),    # CT (centerline)
        (-3.0, -0.1),  # RT (right edge)
        (-3.0, -0.3),  # Bottom right
        (0.0, -0.2),   # Bottom center
        (3.0, -0.3),   # Bottom left
        (3.0, -0.1)    # Close to start
    ],
    TagList=['LT', 'CT', 'RT', 'rb', 'cb', 'lb', 'LT']
)

curve = ifcfile.create_entity('IfcIndexedPolyCurve',
    Points=points,
    Segments=None  # Use all points in sequence
)

profile = ifcfile.create_entity('IfcArbitraryClosedProfileDef',
    ProfileType='AREA',
    ProfileName='Lane with Pavement Structure',
    OuterCurve=curve
)
```

**Critical Rules:**
- For arbitrary profiles, consecutive sections should have same number of points
- Points with same tags get interpolated properly
- Profile must be closed (first point = last point)

#### IfcCompositeProfileDef

**Purpose:** Combine multiple profile definitions into a single assembly.

**When to Use:**
- Modeling multiple pavement courses/layers
- Complex assemblies with distinct material zones
- Representing different components with separate materials

**Entity Definition:**
```
ENTITY IfcCompositeProfileDef
  SUBTYPE OF (IfcProfileDef);
  Profiles : SET [2:?] OF IfcProfileDef;  -- Component profiles
  Label : OPTIONAL IfcLabel;               -- Optional description
  WHERE
    InvariantProfileType : 
      SIZEOF(QUERY(temp <* Profiles | 
        temp.ProfileType <> Profiles[1].ProfileType)) = 0;
    NoRecursion : 
      SIZEOF(QUERY(temp <* Profiles | 
        'IFCCOMPOSITEPROFILEDEF' IN TYPEOF(temp))) = 0;
END_ENTITY;
```

**Usage Pattern:**
```python
# Create individual component profiles
wearing_course = create_open_profile('Wearing Course', 
                                      widths=[3.6], slopes=[0.02])
base_course = create_open_profile('Base Course',
                                   widths=[3.6], slopes=[0.0])
subbase = create_open_profile('Subbase',
                               widths=[3.6], slopes=[0.0])

# Combine into composite
assembly = ifcfile.create_entity('IfcCompositeProfileDef',
    ProfileType='AREA',
    ProfileName='Full Depth Pavement Assembly',
    Profiles=[wearing_course, base_course, subbase],
    Label='Three-layer pavement structure'
)
```

**Constraints:**
- All profiles must have same ProfileType (all AREA or all CURVE)
- No recursive composition (no composites containing composites)
- Profiles are positioned in underlying coordinate system
- Minimum 2 profiles required

### Material Association

**IfcMaterialProfileSet Pattern:**

```python
# Create materials
asphalt = ifcfile.create_entity('IfcMaterial', Name='Asphalt HMA')
base = ifcfile.create_entity('IfcMaterial', Name='Aggregate Base')

# Create material profiles
material_profiles = [
    ifcfile.create_entity('IfcMaterialProfile',
        Name='Wearing Course',
        Material=asphalt,
        Profile=wearing_course_profile
    ),
    ifcfile.create_entity('IfcMaterialProfile',
        Name='Base Course',  
        Material=base,
        Profile=base_course_profile
    )
]

# Create material profile set
profile_set = ifcfile.create_entity('IfcMaterialProfileSet',
    Name='Pavement Structure',
    MaterialProfiles=material_profiles
)

# Associate with pavement element
ifcfile.create_entity('IfcRelAssociatesMaterial',
    RelatingMaterial=profile_set,
    RelatedObjects=[pavement_element]
)
```

### IfcAxis2PlacementLinear (Positioning)

**Purpose:** Position cross-sections along the alignment using distance expressions.

```python
# Create distance expression for station
distance_expr = ifcfile.create_entity('IfcDistanceExpression',
    DistanceAlong=100.0,        # Station 0+100
    OffsetLateral=0.0,          # No lateral offset
    OffsetVertical=0.0,         # No vertical offset
    OffsetLongitudinal=None     # MUST NOT use for cross-sections
)

# Create placement
placement = ifcfile.create_entity('IfcAxis2PlacementLinear',
    Location=distance_expr,
    Axis=None,                  # Use default vertical
    RefDirection=None           # Use default perpendicular
)
```

**Critical Constraints:**
- `OffsetLongitudinal` MUST NOT be used for cross-section positions
- Would create non-manifold geometry
- Can use `OffsetLateral` and `OffsetVertical` for profile positioning

---

## Industry Software Analysis

### AutoCAD Civil 3D Approach

**Terminology:**
- **Assembly** = Complete typical section definition
- **Subassembly** = Individual component (lane, shoulder, curb, etc.)
- **Corridor** = 3D model created by sweeping assembly along alignment

**Key Characteristics:**

1. **Subassembly Library:**
   - Ships with extensive library of standard subassemblies
   - Common types: `LaneSuperelevationAOR`, `ShoulderExtendAll`, `UrbanCurbGutterGeneral`
   - Each subassembly has parametric inputs (width, slope, depth, etc.)

2. **Attachment Logic:**
   - Subassemblies attach to baseline or other subassemblies
   - Sequential attachment from centerline outward
   - Attachment points define connection locations

3. **Parametric Behavior:**
   - Each subassembly has parameters that can be:
     - Set at assembly level (default values)
     - Overridden via targets (surface, alignment, feature line)
     - Modified using corridor transitions (new in 2023.2)
   - Parameters recalculate dynamically as corridor updates

4. **Corridor Transitions (2023.2+):**
   - Apply transitions to any dimension of any subassembly
   - No custom programming required
   - Define start/end stations and parameter values
   - System interpolates between values

5. **Target Mapping:**
   - Surface targets (for daylighting slopes)
   - Alignment targets (for lane widening)
   - Profile targets (for ditch invert elevation)
   - Feature line/polyline targets (for edge of pavement)

**Example Assembly Structure:**
```
Baseline (Centerline)
├─ Left Side
│  ├─ LaneSuperelevationAOR (3.6m width, 2% slope)
│  ├─ ShoulderExtendAll (2.4m width, 4% slope)
│  ├─ UrbanCurbGutterGeneral (6" height)
│  └─ BasicSideSlopeCutDitch (2:1 slope, targets surface)
└─ Right Side
   ├─ LaneSuperelevationAOR (3.6m width, 2% slope)
   ├─ ShoulderExtendAll (2.4m width, 4% slope)
   ├─ UrbanCurbGutterGeneral (6" height)
   └─ BasicSideSlopeCutDitch (2:1 slope, targets surface)
```

**Subassembly Properties (Example - Lane):**
```
LaneSuperelevationAOR Parameters:
- Width: 3.6m (can target alignment for widening)
- Side: Left/Right
- Slope: 2% (can vary via superelevation)
- Depth: Multiple layers supported
  - Surface: 50mm
  - Base: 150mm
  - Subbase: 300mm
- Material assignments per layer
```

**From Industry Documentation:**
> "Subassemblies are intelligent objects that dynamically react to changes in the design environment. Each subassembly has its own set of parameters that you can modify to change its appearance or behavior."

### Bentley OpenRoads Designer Approach

**Terminology:**
- **Template** = Complete cross-section definition
- **Component** = Individual template element
- **Corridor** = 3D model generated from template + alignments

**Key Characteristics:**

1. **Template Components:**
   - **Simple Component** - Closed parallelogram (4 points), slope/thickness defined
   - **Constrained Component** - Points restricted to first point movement
   - **Unconstrained Component** - Open/closed shape, no restrictions
   - **Null Point** - Reference point not part of component geometry
   - **End Condition** - Special open component targeting surfaces/features
   - **Overlay/Stripping** - Milling/stripping operations

2. **Point Constraints:**
   - Two-dimensional (offset + elevation)
   - One-way parent/child relationship
   - Multiple constraint types:
     - Offset constraint (horizontal distance)
     - Elevation constraint (vertical offset)
     - Slope constraint (angular relationship)
     - Elevation Difference (maintains vertical separation)
     - Project to Surface (finds intersection)

3. **Parametric Constraints (Most Powerful Feature):**
   - Can override ANY labeled constraint value
   - Applied station-by-station during corridor processing
   - Multiple constraints can overlap/combine
   - Station range based (start/end stations)
   - Linear interpolation between constraint ranges

4. **Point Controls:**
   - Override template point constraints dynamically
   - Control types:
     - Linear Geometry (alignment, feature)
     - Corridor Feature (target another corridor)
     - Superelevation (rotate about pivot)
     - Elevation Difference
     - Fixed Elevation
   - Take precedence over parametric constraints

5. **Processing Order (CRITICAL):**
   ```
   1. Template dropped, points placed per template constraints
   2. Parametric constraints applied (template + corridor)
   3. Horizontal feature constraints applied
   4. Point controls applied (highest priority)
   5. Component display rules solved
   ```

**Example Template Structure:**
```
Template: "Two Lane Rural Road"
Origin Point: (0, 0)

Points (Constrained):
├─ CLPG (Centerline Profile Grade) - origin
├─ LL_SHDR (Left Lane/Shoulder break)
│  └─ Offset: -3.6m from CLPG
│  └─ Elevation: 2% slope from CLPG
├─ L_SHDR (Left Shoulder edge)
│  └─ Offset: -2.4m from LL_SHDR
│  └─ Elevation: 4% slope from LL_SHDR
├─ RL_SHDR (Right Lane/Shoulder break)
│  └─ Offset: +3.6m from CLPG
│  └─ Elevation: -2% slope from CLPG
└─ R_SHDR (Right Shoulder edge)
   └─ Offset: +2.4m from RL_SHDR
   └─ Elevation: -4% slope from RL_SHDR

Components:
├─ Left Travel Lane (Simple, 4 points)
├─ Right Travel Lane (Simple, 4 points)
├─ Left Shoulder (Simple, 4 points)
├─ Right Shoulder (Simple, 4 points)
└─ Subbase (Simple, 8 points total)

Parametric Constraints:
├─ "Lane_Width" = 3.6m (default)
├─ "Shoulder_Width" = 2.4m (default)
├─ "Subbase_Depth" = -0.3m (default)
└─ "Cross_Slope" = 0.02 (default)
```

**Parametric Constraint Example:**
```
Constraint Name: "Lane_Width"
Applies To: Points [LL_SHDR, RL_SHDR]
Station Range: 0+500 to 1+000
Value: 4.0m (widened from 3.6m default)

→ In this range, lanes interpolate from 3.6m to 4.0m
→ All dependent points recalculate automatically
```

**From OpenRoads Documentation:**
> "Parametric constraints can be used to change one or more labeled constraint values of a template while the template is being processed in the corridor modeler. They enable powerful station-by-station control without requiring template modifications."

### Key Similarities Across Professional Software

Both Civil 3D and OpenRoads share these fundamental approaches:

1. **Component-Based Architecture:**
   - Cross-sections built from discrete, reusable components
   - Each component has well-defined parameters
   - Components attach sequentially with clear connection logic

2. **Parametric Control:**
   - Parameters can vary along the corridor
   - Station-range based overrides
   - Dynamic recalculation of dependent elements

3. **Material Assignments:**
   - Each component can have material properties
   - Supports multi-layer pavement structures
   - Materials used for visualization and quantity calculations

4. **Code-Based Backend:**
   - Geometry calculations performed by procedural code
   - NOT node-based visual programming
   - Python/C# APIs for advanced customization
   - GUI provides friendly interface to powerful backend

5. **Target/Constraint Systems:**
   - Components can reference surfaces, alignments, features
   - Enables automatic tie-ins and transitions
   - Priority-based resolution of conflicts

---

## BlenderCivil Design Decisions

### Decision: Python-Based Parametric System (NOT Geometry Nodes)

**Critical Architectural Decision from Sprint 0:**

BlenderCivil implements parametric assemblies using Python code with a Blender UI, explicitly **NOT** using Geometry Nodes for core functionality.

**Rationale:**

1. **Professional Software Precedent:**
   - Civil 3D uses C#/.NET backend with GUI
   - OpenRoads uses C++ with Python API
   - Both hide complexity behind friendly interfaces
   - Users never see code, but code powers everything

2. **Engineering Precision Requirements:**
   - Complex engineering calculations difficult to express in nodes
   - Debugging node networks is challenging
   - Standards validation easier in code
   - Sub-millimeter precision needed for survey-grade work

3. **Parametric ≠ Visual Programming:**
   - "Parametric" means values can vary and trigger regeneration
   - Does NOT mean node-based procedural modeling
   - Professional tools prove code-based parametric is industry standard

4. **Future Role for Geometry Nodes (Optional):**
   - Real-time preview while editing alignment
   - Low-poly approximation for quick feedback
   - Presentation/visualization mode only
   - Final generation ALWAYS uses Python for precision

**From BlenderCivil Sprint 0 Documentation:**
> "Don't assume 'parametric' means 'Geometry Nodes'. Professional software uses code backends universally. OpenRoads constraint system is more powerful than Civil 3D regions. GUI simplicity on top of code power is the winning pattern."

### User Experience Pattern

```
┌─────────────────────────────────────────┐
│   BLENDER UI PANELS                     │
│   (Friendly GUI - No Code Visible)     │
│   • Component library browser           │
│   • Add/remove/reorder components       │
│   • Property fields and dropdowns       │
│   • Material assignment UI              │
│   • Parametric constraint editor        │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│   PYTHON API LAYER                      │
│   (Blender PropertyGroups & Operators) │
│   • Data storage (assemblies, etc.)     │
│   • User action handlers                │
│   • Validation functions                │
│   • Constraint manager                  │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│   CORRIDOR GENERATION ENGINE            │
│   (Python + ifcopenshell + NumPy)      │
│   1. Sample alignment at stations       │
│   2. Get assembly for station           │
│   3. Apply parametric constraints       │
│   4. Calculate section geometry         │
│   5. Transform to 3D coordinates        │
│   6. Create IFC entities                │
│   7. Generate Blender mesh for preview  │
└─────────────────────────────────────────┘
```

### OpenRoads-Style Constraint System

BlenderCivil implements OpenRoads-style parametric constraints rather than Civil 3D-style regions.

**Why OpenRoads Style:**
- More powerful than Civil 3D's region-based approach
- Can override ANY parameter at ANY station range
- Multiple constraints can overlap/combine
- Simpler to implement than visual subassembly snapping
- Better for programmatic control and scripting

**Implementation:**
```python
class ParametricConstraint:
    """Station-range based parameter override"""
    parameter_name: str      # e.g., "lane_width"
    value: float             # e.g., 11.0 feet
    start_station: float     # e.g., 100.0
    end_station: float       # e.g., 500.0
    
    def applies_to_station(self, station: float) -> bool:
        return self.start_station <= station <= self.end_station

# At each station during corridor generation:
# 1. Get base assembly
# 2. Apply all active parametric constraints
# 3. Recalculate geometry with overridden values
# 4. Generate 3D section
```

**Example Usage:**
```python
# User defines in UI:
assembly.add_constraint(
    parameter="lane_width",
    value=11.0,  # feet
    start_station=100.0,
    end_station=500.0
)

# System applies during corridor generation:
for station in corridor_stations:
    section = assembly.calculate_section_at(station)
    # Constraint automatically applied if station in range
```

---

## Implementation Architecture

### Component-Based System

**Base Component Class:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import ifcopenshell

@dataclass
class ComponentParameters:
    """Base parameters for all components"""
    name: str
    width: float
    cross_slope: float  # As ratio (0.02 = 2%)
    side: str  # "left" or "right"

class BaseComponent(ABC):
    """Abstract base for all cross-section components"""
    
    def __init__(self, params: ComponentParameters):
        self.params = params
        self.attachment_point: Optional[Tuple[float, float]] = None
        
    @abstractmethod
    def calculate_points(self) -> List[Tuple[float, float]]:
        """Calculate 2D points for this component
        
        Returns list of (offset, elevation) tuples
        relative to attachment point
        """
        pass
    
    @abstractmethod
    def attach_to(self, point: Tuple[float, float], 
                   previous_component: Optional['BaseComponent']) -> None:
        """Attach this component to specified point
        
        Args:
            point: (offset, elevation) attachment location
            previous_component: Component this attaches to (if any)
        """
        pass
    
    @abstractmethod
    def to_ifc_profile(self, ifc_file: ifcopenshell.file) -> 'IfcProfileDef':
        """Export component as IFC profile definition
        
        Returns appropriate IfcProfileDef subtype
        """
        pass
    
    def get_total_width(self) -> float:
        """Calculate total width occupied by component"""
        return self.params.width
```

### Specific Component Types

**Lane Component:**
```python
@dataclass
class LaneParameters(ComponentParameters):
    """Parameters specific to travel lanes"""
    depth: float = 0.2  # Pavement depth in meters
    material_layers: List[Tuple[str, float]] = None  # (material, thickness)

class LaneComponent(BaseComponent):
    """Represents a travel lane with pavement structure"""
    
    def __init__(self, params: LaneParameters):
        super().__init__(params)
        if params.material_layers is None:
            # Default three-layer structure
            params.material_layers = [
                ("Asphalt HMA", 0.05),
                ("Aggregate Base", 0.10),
                ("Subbase", 0.05)
            ]
    
    def calculate_points(self) -> List[Tuple[float, float]]:
        """Calculate lane section points
        
        Returns 4 points forming closed profile:
        - Top left, top right, bottom right, bottom left
        """
        w = self.params.width
        slope = self.params.cross_slope
        depth = self.params.depth
        
        # Adjust for side (left lanes have positive slope)
        if self.params.side == "left":
            slope = abs(slope)
        else:
            slope = -abs(slope)
        
        # Top surface points
        x1, y1 = self.attachment_point
        x2 = x1 + w
        y2 = y1 + (w * slope)
        
        # Bottom points (same horizontal offset, depth below)
        x3, y3 = x2, y2 - depth
        x4, y4 = x1, y1 - depth
        
        return [(x1, y1), (x2, y2), (x3, y3), (x4, y4), (x1, y1)]
    
    def attach_to(self, point: Tuple[float, float],
                   previous_component: Optional[BaseComponent]) -> None:
        """Attach lane to specified point (typically centerline)"""
        self.attachment_point = point
    
    def to_ifc_profile(self, ifc_file: ifcopenshell.file) -> 'IfcProfileDef':
        """Export as IfcArbitraryClosedProfileDef with material layers"""
        points = self.calculate_points()
        
        # Create point list
        point_list = ifc_file.create_entity('IfcCartesianPointList2D',
            CoordList=points[:-1]  # Exclude duplicate closing point
        )
        
        # Create curve
        curve = ifc_file.create_entity('IfcIndexedPolyCurve',
            Points=point_list
        )
        
        # Create profile
        profile = ifc_file.create_entity('IfcArbitraryClosedProfileDef',
            ProfileType='AREA',
            ProfileName=self.params.name,
            OuterCurve=curve
        )
        
        return profile
```

**Shoulder Component:**
```python
@dataclass
class ShoulderParameters(ComponentParameters):
    """Parameters for shoulder sections"""
    material: str = "Gravel"  # or "Asphalt" for paved
    depth: float = 0.1

class ShoulderComponent(BaseComponent):
    """Paved or gravel shoulder"""
    
    def calculate_points(self) -> List[Tuple[float, float]]:
        """Calculate shoulder points"""
        w = self.params.width
        slope = self.params.cross_slope
        depth = self.depth
        
        # Shoulders always slope away from pavement
        if self.params.side == "left":
            slope = -abs(slope)  # Negative = down-left
        else:
            slope = abs(slope)   # Positive = down-right
        
        x1, y1 = self.attachment_point
        x2 = x1 + w
        y2 = y1 + (w * slope)
        
        # Bottom points
        x3, y3 = x2, y2 - depth
        x4, y4 = x1, y1 - depth
        
        return [(x1, y1), (x2, y2), (x3, y3), (x4, y4), (x1, y1)]
```

**Additional Components:**
- `CurbComponent` - Vertical or sloped curbs
- `SidewalkComponent` - Pedestrian walkways
- `DitchComponent` - V-ditches, trapezoidal ditches
- `SlopeComponent` - Cut/fill slopes to existing ground

### Assembly Class

```python
from typing import Dict, List
import ifcopenshell

class RoadAssembly:
    """Complete cross-section assembly"""
    
    def __init__(self, name: str, assembly_type: str = "Rural Two-Lane"):
        self.name = name
        self.assembly_type = assembly_type
        self.components: List[BaseComponent] = []
        self.default_parameters: Dict[str, float] = {}
        self.parametric_constraints: List[ParametricConstraint] = []
    
    def add_component(self, component: BaseComponent, 
                       position: str = "append") -> None:
        """Add component to assembly
        
        Args:
            component: Component to add
            position: "append", "prepend", or specific index
        """
        if position == "append":
            self.components.append(component)
        elif position == "prepend":
            self.components.insert(0, component)
        else:
            self.components.insert(int(position), component)
        
        # Recalculate attachment points
        self._update_attachments()
    
    def remove_component(self, index: int) -> None:
        """Remove component at specified index"""
        if 0 <= index < len(self.components):
            self.components.pop(index)
            self._update_attachments()
    
    def add_constraint(self, station: float, component_name: str,
                        parameter: str, value: float) -> None:
        """Add parametric constraint for component parameter
        
        Args:
            station: Station where constraint applies
            component_name: Name of component to constrain
            parameter: Parameter name (e.g., "width", "slope")
            value: Value to apply
        """
        constraint = ParametricConstraint(
            parameter_name=f"{component_name}.{parameter}",
            value=value,
            start_station=station,
            end_station=station  # Point constraint
        )
        self.parametric_constraints.append(constraint)
    
    def calculate_section_points(self, station: float) -> List[Tuple[float, float]]:
        """Calculate all component points at specified station
        
        Args:
            station: Station along alignment
            
        Returns:
            List of (offset, elevation) tuples for all components
        """
        # Apply constraints for this station
        active_constraints = [c for c in self.parametric_constraints 
                               if c.applies_to_station(station)]
        
        # Build section from centerline outward
        all_points = []
        attachment = (0.0, 0.0)  # Start at centerline
        
        for component in self.components:
            # Apply active constraints to component
            self._apply_constraints(component, active_constraints)
            
            # Attach and calculate
            component.attach_to(attachment, None)
            points = component.calculate_points()
            all_points.extend(points)
            
            # Next component attaches to this one's end
            attachment = points[-2]  # Second-to-last (before closing)
        
        return all_points
    
    def get_total_width(self) -> float:
        """Calculate total width of assembly"""
        return sum(c.get_total_width() for c in self.components)
    
    def to_ifc_composite_profile(self, ifc_file: ifcopenshell.file,
                                   station: float) -> 'IfcCompositeProfileDef':
        """Export assembly as IFC composite profile at station
        
        Args:
            ifc_file: IFC file handle
            station: Station for constraint application
            
        Returns:
            IfcCompositeProfileDef containing all component profiles
        """
        profiles = []
        for component in self.components:
            profile = component.to_ifc_profile(ifc_file)
            profiles.append(profile)
        
        composite = ifc_file.create_entity('IfcCompositeProfileDef',
            ProfileType='AREA',
            ProfileName=f"{self.name} @ Sta {station:.2f}",
            Profiles=profiles,
            Label=self.assembly_type
        )
        
        return composite
    
    def _update_attachments(self) -> None:
        """Recalculate attachment points for all components"""
        attachment = (0.0, 0.0)
        prev_component = None
        
        for component in self.components:
            component.attach_to(attachment, prev_component)
            points = component.calculate_points()
            attachment = points[-2]
            prev_component = component
    
    def _apply_constraints(self, component: BaseComponent,
                            constraints: List[ParametricConstraint]) -> None:
        """Apply active constraints to component parameters"""
        for constraint in constraints:
            if constraint.parameter_name.startswith(component.params.name):
                param = constraint.parameter_name.split('.')[-1]
                if hasattr(component.params, param):
                    setattr(component.params, param, constraint.value)
```

### Template Library (Factory Pattern)

```python
class TemplateLibrary:
    """Factory methods for standard assembly templates"""
    
    @staticmethod
    def create_two_lane_rural() -> RoadAssembly:
        """AASHTO standard two-lane rural highway"""
        assembly = RoadAssembly(
            name="Two Lane Rural Road",
            assembly_type="Rural Two-Lane"
        )
        
        # Left side
        assembly.add_component(LaneComponent(LaneParameters(
            name="Left Travel Lane",
            width=3.6,        # meters
            cross_slope=0.02,  # 2%
            side="left"
        )))
        assembly.add_component(ShoulderComponent(ShoulderParameters(
            name="Left Shoulder",
            width=2.4,
            cross_slope=0.04,  # 4%
            side="left",
            material="Gravel"
        )))
        
        # Right side  
        assembly.add_component(LaneComponent(LaneParameters(
            name="Right Travel Lane",
            width=3.6,
            cross_slope=0.02,
            side="right"
        )))
        assembly.add_component(ShoulderComponent(ShoulderParameters(
            name="Right Shoulder",
            width=2.4,
            cross_slope=0.04,
            side="right",
            material="Gravel"
        )))
        
        return assembly
    
    @staticmethod
    def create_four_lane_divided() -> RoadAssembly:
        """Interstate/freeway typical section"""
        # Implementation similar, with median components
        pass
    
    @staticmethod
    def create_urban_curb_gutter() -> RoadAssembly:
        """Urban street with curb and gutter"""
        # Implementation with curb, gutter, sidewalk components
        pass
```

---

## Component Types & Properties

### Standard Component Library

#### 1. Lane Component

**Purpose:** Represent travel lanes with full pavement structure

**Properties:**
- `width` (float): Lane width in meters (typical: 3.0-3.6m)
- `cross_slope` (float): Transverse slope as ratio (typical: 0.02 = 2%)
- `side` (str): "left" or "right" from centerline
- `depth` (float): Total pavement depth in meters
- `material_layers` (List[Tuple]): List of (material_name, thickness) tuples

**Geometry:**
- 4-point closed profile (rectangle)
- Top surface follows cross-slope
- Bottom parallel to top, offset by depth

**IFC Export:**
- `IfcArbitraryClosedProfileDef` for geometry
- `IfcMaterialProfileSet` for layered materials
- Can be decomposed into `IfcCourse` entities for each layer

**Usage:**
```python
lane = LaneComponent(LaneParameters(
    name="Right Travel Lane",
    width=3.6,
    cross_slope=0.02,
    side="right",
    depth=0.20,
    material_layers=[
        ("Asphalt Surface", 0.05),
        ("Aggregate Base", 0.10),
        ("Subbase", 0.05)
    ]
))
```

#### 2. Shoulder Component

**Purpose:** Paved or gravel shoulder adjacent to travel lanes

**Properties:**
- `width` (float): Shoulder width (typical: 1.8-3.0m)
- `cross_slope` (float): Slope away from pavement (typical: 0.04 = 4%)
- `material` (str): "Asphalt" or "Gravel"
- `depth` (float): Thickness (typically shallower than lanes)

**Geometry:**
- 4-point closed profile
- Always slopes away from adjacent lane
- Can be full-depth or cap only

**IFC Export:**
- `IfcOpenCrossProfileDef` for simple shoulders
- `IfcArbitraryClosedProfileDef` with materials for paved shoulders

#### 3. Curb Component

**Purpose:** Vertical or sloped barrier at pavement edge

**Properties:**
- `height` (float): Curb height (typical: 0.15-0.20m)
- `width` (float): Curb width at base (typical: 0.15-0.30m)
- `curb_type` (str): "Vertical", "Sloped", or "Mountable"
- `offset` (float): Distance from pavement edge

**Geometry:**
- Vertical: Simple rectangle
- Sloped: Trapezoid with specified face angle
- Mountable: Curved or beveled face

**IFC Export:**
- `IfcKerb` entity (new in IFC 4.3)
- Predefined types: CURB, GUTTER, or NOTDEFINED

#### 4. Sidewalk Component

**Purpose:** Pedestrian walkway

**Properties:**
- `width` (float): Sidewalk width (typical: 1.5-2.4m)
- `thickness` (float): Concrete thickness (typical: 0.10-0.15m)
- `cross_slope` (float): Slope for drainage (typical: 0.02 = 2%)
- `buffer_strip` (bool): Include planting strip

**Geometry:**
- Simple rectangular profile
- Typically elevated above adjacent grade

#### 5. Ditch Component

**Purpose:** Roadside drainage channel

**Properties:**
- `bottom_width` (float): Width at ditch bottom (typical: 0.6-1.5m)
- `side_slope_left` (float): Left side slope ratio (typical: 3:1)
- `side_slope_right` (float): Right side slope ratio
- `depth` (float): Ditch depth below reference

**Geometry:**
- Trapezoidal or V-shaped profile
- Can have flat bottom or pointed invert

**IFC Export:**
- `IfcDistributionChamberElement` (Type: DITCH)
- Or `IfcPipeSegment` for linear drainage elements

#### 6. Slope Component (Cut/Fill)

**Purpose:** Tie pavement to existing ground surface

**Properties:**
- `cut_slope` (float): Cut slope ratio (typical: 2:1 horizontal:vertical)
- `fill_slope` (float): Fill slope ratio (typical: 3:1)
- `max_offset` (float): Maximum daylight distance
- `target_surface` (str): Name of surface to intersect

**Geometry:**
- Open profile extending to surface intersection
- Slope varies based on cut vs. fill condition

**Special Behavior:**
- Queries existing ground surface at each station
- Calculates intersection point
- Adjusts slope based on cut/fill

### Component Parameter Ranges

**Lane Widths (AASHTO Guidelines):**
- Interstate/Freeway: 3.6m (12 feet)
- Arterials: 3.3-3.6m (11-12 feet)
- Local Streets: 3.0-3.3m (10-11 feet)
- Minimum: 2.7m (9 feet) for low-speed locals

**Cross-Slopes:**
- High-Type Pavement: 1.5-2.0% (0.015-0.020)
- Intermediate Pavement: 2.0-2.5%
- Low-Type Surface: 2.0-3.0%
- Shoulders: 4.0-6.0% (greater for drainage)

**Shoulder Widths:**
- Interstate: 3.0m (10 feet) outside, 1.2-3.0m inside
- Rural Arterial: 1.8-2.4m (6-8 feet)
- Urban Arterial: 1.2-1.8m (4-6 feet) if provided

**Pavement Depths:**
- Surface Course: 0.04-0.10m (1.5-4 inches)
- Base Course: 0.10-0.20m (4-8 inches)
- Subbase: 0.10-0.30m (4-12 inches)
- Total Depth: 0.25-0.50m typical

---

## Parametric Constraints System

### Constraint Types

**1. Point Constraints (Station-Specific):**
```python
class PointConstraint:
    """Single-station override"""
    station: float
    component: str
    parameter: str
    value: float
```

**2. Range Constraints (Linear Interpolation):**
```python
class RangeConstraint:
    """Constraint that interpolates between stations"""
    start_station: float
    end_station: float
    component: str
    parameter: str
    start_value: float
    end_value: float
```

### Common Constraint Scenarios

#### Lane Widening

**Scenario:** Widen right lane from 3.6m to 4.2m for right-turn lane

```python
# Add widening transition
assembly.add_constraint(
    start_station=200.0,  # Begin widening
    end_station=300.0,    # Complete widening
    component="Right Travel Lane",
    parameter="width",
    start_value=3.6,
    end_value=4.2
)

# Result: Linear interpolation over 100m
# Sta 200: 3.6m
# Sta 250: 3.9m (interpolated)
# Sta 300: 4.2m
```

#### Varying Pavement Depth

**Scenario:** Increase pavement depth for heavy truck route

```python
assembly.add_constraint(
    start_station=500.0,
    end_station=500.0,  # Point constraint
    component="Right Travel Lane",
    parameter="depth",
    start_value=0.25,   # 250mm
    end_value=0.25
)
```

#### Superelevation Transition

**Scenario:** Rotate cross-section for curve

```python
# This requires rotating entire assembly, not individual constraints
# Handled by superelevation system in Sprint 6
```

### Constraint Manager

```python
class ConstraintManager:
    """Manages parametric constraints for assembly"""
    
    def __init__(self, assembly: RoadAssembly):
        self.assembly = assembly
        self.constraints: List[Union[PointConstraint, RangeConstraint]] = []
    
    def add_point_constraint(self, station: float, component: str,
                              parameter: str, value: float) -> None:
        """Add single-station override"""
        constraint = PointConstraint(
            station=station,
            component=component,
            parameter=parameter,
            value=value
        )
        self.constraints.append(constraint)
    
    def add_range_constraint(self, start_station: float, end_station: float,
                              component: str, parameter: str,
                              start_value: float, end_value: float) -> None:
        """Add interpolating range constraint"""
        constraint = RangeConstraint(
            start_station=start_station,
            end_station=end_station,
            component=component,
            parameter=parameter,
            start_value=start_value,
            end_value=end_value
        )
        self.constraints.append(constraint)
    
    def get_value_at_station(self, component: str, parameter: str,
                              station: float) -> Optional[float]:
        """Get constrained value at specific station
        
        Returns:
            Constrained value if applicable, None otherwise
        """
        # Find applicable constraints
        applicable = [c for c in self.constraints
                       if c.component == component 
                       and c.parameter == parameter]
        
        if not applicable:
            return None
        
        # Check point constraints first (highest priority)
        point_constraints = [c for c in applicable 
                              if isinstance(c, PointConstraint)
                              and c.station == station]
        if point_constraints:
            return point_constraints[0].value
        
        # Check range constraints
        range_constraints = [c for c in applicable
                              if isinstance(c, RangeConstraint)
                              and c.start_station <= station <= c.end_station]
        
        if not range_constraints:
            return None
        
        # Linear interpolation for range
        constraint = range_constraints[0]  # Use first matching
        
        if constraint.start_station == constraint.end_station:
            return constraint.start_value
        
        # Calculate interpolation factor
        factor = ((station - constraint.start_station) /
                   (constraint.end_station - constraint.start_station))
        
        # Interpolate
        value = (constraint.start_value + 
                  factor * (constraint.end_value - constraint.start_value))
        
        return value
    
    def apply_constraints_at_station(self, station: float) -> None:
        """Apply all constraints for given station"""
        for component in self.assembly.components:
            for param_name in ['width', 'cross_slope', 'depth']:
                value = self.get_value_at_station(
                    component.params.name,
                    param_name,
                    station
                )
                if value is not None:
                    setattr(component.params, param_name, value)
```

---

## IFC Export Patterns

### Complete Corridor Export Workflow

```python
import ifcopenshell
import ifcopenshell.api
from typing import List, Tuple
import numpy as np

def export_corridor_to_ifc(
    alignment_3d: 'Alignment3D',
    assembly: RoadAssembly,
    stations: List[float],
    ifc_file: ifcopenshell.file,
    project: 'IfcProject',
    site: 'IfcSite'
) -> 'IfcRoad':
    """
    Complete workflow to export corridor as IFC
    
    Args:
        alignment_3d: 3D alignment (H+V integrated)
        assembly: Cross-section assembly
        stations: List of stations for profile drops
        ifc_file: IFC file handle
        project: IFC project root
        site: IFC site container
    
    Returns:
        IfcRoad entity containing corridor
    """
    
    # 1. Create IfcRoad spatial container
    road = ifc_file.create_entity('IfcRoad',
        GlobalId=ifcopenshell.guid.new(),
        Name=f"Road - {assembly.name}",
        Description=f"Corridor based on {assembly.assembly_type}",
        ObjectType="Highway"
    )
    
    # Link to spatial hierarchy
    ifcopenshell.api.run("spatial.assign_container",
        ifc_file,
        product=road,
        relating_structure=site
    )
    
    # 2. Create IfcAlignment for directrix
    alignment_curve = export_alignment_curve(alignment_3d, ifc_file)
    
    # 3. Generate cross-section profiles at each station
    profiles = []
    positions = []
    
    for station in stations:
        # Get 3D position at station
        position_3d = alignment_3d.get_position_at_station(station)
        
        # Create composite profile for this station
        composite = assembly.to_ifc_composite_profile(ifc_file, station)
        profiles.append(composite)
        
        # Create distance expression
        distance_expr = ifc_file.create_entity('IfcDistanceExpression',
            DistanceAlong=station,
            OffsetLateral=0.0,
            OffsetVertical=0.0
        )
        
        # Create placement
        placement = ifc_file.create_entity('IfcAxis2PlacementLinear',
            Location=distance_expr
        )
        positions.append(placement)
    
    # 4. Create IfcSectionedSolidHorizontal
    corridor_solid = ifc_file.create_entity('IfcSectionedSolidHorizontal',
        Directrix=alignment_curve,
        CrossSections=profiles,
        CrossSectionPositions=positions
    )
    
    # 5. Create shape representation
    shape_rep = ifc_file.create_entity('IfcShapeRepresentation',
        ContextOfItems=None,  # Get from project
        RepresentationIdentifier='Body',
        RepresentationType='SectionedSolidHorizontal',
        Items=[corridor_solid]
    )
    
    # 6. Create product definition shape
    product_shape = ifc_file.create_entity('IfcProductDefinitionShape',
        Representations=[shape_rep]
    )
    
    # 7. Assign to road
    road.Representation = product_shape
    
    # 8. Create material associations
    export_material_profile_set(assembly, ifc_file, road)
    
    return road


def export_alignment_curve(alignment_3d: 'Alignment3D',
                            ifc_file: ifcopenshell.file) -> 'IfcAlignmentCurve':
    """Export 3D alignment as IfcAlignmentCurve"""
    
    # Create horizontal alignment
    h_alignment = export_horizontal_alignment(
        alignment_3d.horizontal,
        ifc_file
    )
    
    # Create vertical alignment
    v_alignment = export_vertical_alignment(
        alignment_3d.vertical,
        ifc_file
    )
    
    # Create 3D alignment curve
    alignment_curve = ifc_file.create_entity('IfcAlignmentCurve',
        Horizontal=h_alignment,
        Vertical=v_alignment,
        Tag='CENTERLINE'
    )
    
    return alignment_curve


def export_material_profile_set(assembly: RoadAssembly,
                                  ifc_file: ifcopenshell.file,
                                  road: 'IfcRoad') -> None:
    """Create and associate material profile set"""
    
    material_profiles = []
    
    for component in assembly.components:
        # Get IFC profile
        profile = component.to_ifc_profile(ifc_file)
        
        # Create material
        material = ifc_file.create_entity('IfcMaterial',
            Name=component.params.name
        )
        
        # Create material profile
        mat_profile = ifc_file.create_entity('IfcMaterialProfile',
            Name=component.params.name,
            Material=material,
            Profile=profile
        )
        
        material_profiles.append(mat_profile)
    
    # Create material profile set
    profile_set = ifc_file.create_entity('IfcMaterialProfileSet',
        Name=assembly.name,
        MaterialProfiles=material_profiles
    )
    
    # Associate with road
    ifc_file.create_entity('IfcRelAssociatesMaterial',
        GlobalId=ifcopenshell.guid.new(),
        RelatingMaterial=profile_set,
        RelatedObjects=[road]
    )
```

### Material Layer Export (Detailed)

```python
def export_pavement_with_layers(lane: LaneComponent,
                                  ifc_file: ifcopenshell.file) -> 'IfcMaterialLayerSet':
    """Export lane with detailed material layers"""
    
    material_layers = []
    offset = 0.0
    
    # Create material layers from bottom to top
    for material_name, thickness in reversed(lane.params.material_layers):
        # Create material
        material = ifc_file.create_entity('IfcMaterial',
            Name=material_name
        )
        
        # Create material layer
        layer = ifc_file.create_entity('IfcMaterialLayer',
            Material=material,
            LayerThickness=thickness,
            Name=material_name
        )
        
        material_layers.append(layer)
        offset += thickness
    
    # Create material layer set
    layer_set = ifc_file.create_entity('IfcMaterialLayerSet',
        MaterialLayers=material_layers,
        LayerSetName=f"{lane.params.name} - Pavement Structure"
    )
    
    return layer_set
```

---

## Best Practices & Guidelines

### Design Principles

**1. Component Modularity:**
- Each component should be self-contained
- Components calculate their own geometry
- Components define their own attachment logic
- Avoid tight coupling between components

**2. Parameter Naming:**
- Use clear, descriptive names: `lane_width` not `lw`
- Include units in documentation
- Follow consistent naming conventions
- Use snake_case for Python, TitleCase for UI

**3. Constraint Application:**
- Apply constraints sparingly (performance impact)
- Use ranges for smooth transitions
- Validate constraint values before application
- Document constraint intent

**4. IFC Compliance:**
- Always use IFC 4.3 entities for new development
- Maintain profile type consistency
- Use proper tag systems for interpolation
- Follow buildingSMART naming conventions

### Performance Optimization

**Station Sampling:**
```python
def calculate_optimal_stations(alignment: 'Alignment3D',
                                 max_spacing: float = 25.0,
                                 min_spacing: float = 5.0) -> List[float]:
    """
    Calculate optimal station spacing for corridor
    
    Args:
        alignment: 3D alignment
        max_spacing: Maximum station spacing (straight sections)
        min_spacing: Minimum station spacing (curves)
    
    Returns:
        List of station values
    """
    stations = [0.0]  # Always include start
    current = 0.0
    
    while current < alignment.length:
        # Get curvature at current station
        curvature = alignment.get_curvature_at(current)
        
        # Adapt spacing based on curvature
        if curvature < 0.001:  # Straight
            spacing = max_spacing
        else:  # Curved
            # Tighter spacing for sharper curves
            spacing = max(min_spacing, min_spacing / curvature)
        
        current += spacing
        if current < alignment.length:
            stations.append(current)
    
    stations.append(alignment.length)  # Always include end
    return stations
```

### Validation

**Assembly Validation:**
```python
def validate_assembly(assembly: RoadAssembly) -> List[str]:
    """
    Validate assembly configuration
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check minimum components
    if len(assembly.components) < 2:
        errors.append("Assembly must have at least 2 components")
    
    # Check component widths
    for component in assembly.components:
        if component.params.width <= 0:
            errors.append(f"{component.params.name}: width must be positive")
        if component.params.width > 10.0:
            errors.append(f"{component.params.name}: width > 10m seems excessive")
    
    # Check slopes
    for component in assembly.components:
        slope = abs(component.params.cross_slope)
        if slope > 0.10:  # 10%
            errors.append(f"{component.params.name}: cross-slope > 10% unusual")
    
    # Check total width
    total_width = assembly.get_total_width()
    if total_width < 6.0:
        errors.append(f"Total width {total_width}m < 6m (very narrow)")
    if total_width > 50.0:
        errors.append(f"Total width {total_width}m > 50m (very wide)")
    
    return errors
```

### Testing Strategy

**Unit Tests for Components:**
```python
import pytest

def test_lane_component_geometry():
    """Test lane component calculates correct points"""
    lane = LaneComponent(LaneParameters(
        name="Test Lane",
        width=3.6,
        cross_slope=0.02,
        side="right",
        depth=0.20
    ))
    
    lane.attach_to((0.0, 0.0), None)
    points = lane.calculate_points()
    
    # Check 5 points (4 + closing)
    assert len(points) == 5
    
    # Check width
    assert points[1][0] == pytest.approx(3.6)
    
    # Check cross-slope (2% over 3.6m = -0.072m drop)
    assert points[1][1] == pytest.approx(-0.072, abs=0.001)
    
    # Check depth
    assert points[2][1] == pytest.approx(-0.272, abs=0.001)


def test_assembly_constraints():
    """Test parametric constraints apply correctly"""
    assembly = TemplateLibrary.create_two_lane_rural()
    
    # Add constraint
    assembly.add_constraint(
        start_station=100.0,
        end_station=200.0,
        component="Right Travel Lane",
        parameter="width",
        start_value=3.6,
        end_value=4.2
    )
    
    # Check interpolation at midpoint
    points = assembly.calculate_section_points(150.0)
    
    # Width should be 3.9m at midpoint
    # (Need to extract from points - test implementation)
    pass


def test_ifc_export():
    """Test IFC export creates valid entities"""
    assembly = TemplateLibrary.create_two_lane_rural()
    ifc_file = ifcopenshell.file(schema="IFC4X3")
    
    composite = assembly.to_ifc_composite_profile(ifc_file, 0.0)
    
    # Check entity creation
    assert composite.is_a("IfcCompositeProfileDef")
    assert len(composite.Profiles) == 4  # 2 lanes + 2 shoulders
    
    # Validate against schema
    # (Would need full IFC validation)
```

### Documentation Requirements

**Component Documentation:**
```python
class LaneComponent(BaseComponent):
    """
    Represents a travel lane with full pavement structure.
    
    The lane component creates a rectangular cross-section with:
    - Top surface following specified cross-slope
    - Multi-layer pavement structure (wearing, base, subbase)
    - Material assignments for each layer
    - Proper attachment to centerline or adjacent components
    
    Design Standards:
        - AASHTO: Minimum 3.0m width for local streets
        - AASHTO: 3.6m typical for arterials and highways
        - Typical cross-slope: 1.5-2.5% for high-type pavements
        - Typical depth: 200-400mm depending on traffic
    
    Example:
        >>> lane = LaneComponent(LaneParameters(
        ...     name="Right Travel Lane",
        ...     width=3.6,
        ...     cross_slope=0.02,
        ...     side="right"
        ... ))
        >>> lane.attach_to((0.0, 0.0), None)
        >>> points = lane.calculate_points()
    
    See Also:
        - ShoulderComponent: For adjacent shoulders
        - AASHTO Green Book: Design standards reference
        - IFC 4.3 IfcOpenCrossProfileDef specification
    """
```

---

## References & Resources

### buildingSMART Documentation

1. **IFC 4.3 Documentation:** https://ifc43-docs.standards.buildingsmart.org/
2. **IfcRoadPart:** https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcRoadPart.htm
3. **IfcSectionedSolidHorizontal:** https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcSectionedSolidHorizontal.htm
4. **IfcOpenCrossProfileDef:** http://www.bim-times.com/ifc/IFC4_3/buildingsmart/IfcOpenCrossProfileDef.htm
5. **IFC Road Conceptual Model Report:** Available from buildingSMART infrastructure room

### Industry Standards

6. **AASHTO Green Book:** "A Policy on Geometric Design of Highways and Streets"
7. **AASHTO M145:** Standard specification for pavement material classifications
8. **MUTCD:** Manual on Uniform Traffic Control Devices

### Software Documentation

9. **Civil 3D Subassemblies:** Autodesk Civil 3D Help
10. **OpenRoads Templates:** Bentley OpenRoads Designer CONNECT Edition documentation
11. **IfcOpenShell API:** http://docs.ifcopenshell.org/

### BlenderCivil Project Files

12. **Sprint 0 Architecture Decisions:** `/mnt/project/Template_architectureal_decision.md`
13. **Sprint 4 Cross-Section Research:** `/mnt/project/Sprint4_Day1_IFC_CrossSection_Research.md`
14. **Sprint 4 Implementation:** `/mnt/project/Sprint4_Day2_Summary_PART1.md`
15. **Sprint 4 Complete:** `/mnt/project/Sprint4_Complete_Summary.md`

---

## Appendix: Quick Reference

### Common Assembly Templates

```python
# Two-lane rural (AASHTO)
assembly = TemplateLibrary.create_two_lane_rural()
# Returns: 2x 3.6m lanes + 2x 2.4m shoulders

# Four-lane divided (Interstate)
assembly = TemplateLibrary.create_four_lane_divided()
# Returns: 4x 3.6m lanes + median + 2x 3.0m shoulders

# Urban with curb/gutter
assembly = TemplateLibrary.create_urban_curb_gutter()
# Returns: 2x 3.3m lanes + curbs + 1.5m sidewalks
```

### Common Constraints

```python
# Lane widening
assembly.add_constraint(100.0, 200.0, "Right Lane", "width", 3.6, 4.2)

# Pavement thickening
assembly.add_constraint(500.0, 500.0, "Left Lane", "depth", 0.25, 0.25)

# Shoulder widening
assembly.add_constraint(0.0, 1000.0, "Right Shoulder", "width", 2.4, 3.0)
```

### IFC Entity Hierarchy

```
IfcProject
  └─ IfcSite
      └─ IfcRoad
          ├─ IfcAlignment (directrix)
          ├─ IfcRoadPart (LONGITUDINAL segments)
          │   └─ IfcRoadPart (LATERAL divisions)
          └─ IfcShapeRepresentation
              └─ IfcSectionedSolidHorizontal
                  ├─ Directrix: IfcAlignmentCurve
                  ├─ CrossSections: [IfcCompositeProfileDef, ...]
                  └─ CrossSectionPositions: [IfcAxis2PlacementLinear, ...]
```

---

**Document Status:** ✅ Complete - Ready for Implementation  
**Next Steps:** Begin Sprint 5 corridor mesh generation using this framework  
**Maintenance:** Update as IFC 4.3 evolves and implementation reveals edge cases

