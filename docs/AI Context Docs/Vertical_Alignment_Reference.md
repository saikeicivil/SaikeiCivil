# Saikei Civil Vertical Alignment Reference
## Complete Guide for IFC 4.3 Vertical Alignment Creation and Handling

**Document Purpose:** This is a comprehensive reference for understanding and maintaining Saikei Civil's vertical alignment system. Use this when making edits or debugging vertical alignment code.

**Last Updated:** November 19, 2025  
**Sprint:** Phase 1 Complete - Sprint 3 (Vertical Alignments)  
**Status:** Production-Ready Implementation

---

## Table of Contents

1. [Overview & Core Concepts](#1-overview--core-concepts)
2. [Mathematical Foundations](#2-mathematical-foundations)
3. [Data Structures & Classes](#3-data-structures--classes)
4. [IFC 4.3 Mapping](#4-ifc-43-mapping)
5. [Common Operations](#5-common-operations)
6. [Validation & Error Handling](#6-validation--error-handling)
7. [Integration with Horizontal Alignments](#7-integration-with-horizontal-alignments)
8. [Critical Gotchas & Known Issues](#8-critical-gotchas--known-issues)
9. [Code Patterns & Examples](#9-code-patterns--examples)
10. [Testing Strategy](#10-testing-strategy)

---

## 1. Overview & Core Concepts

### 1.1 What is a Vertical Alignment?

A **vertical alignment** defines the elevation profile of a road, railway, or other linear infrastructure along its length. It consists of:

- **PVIs (Points of Vertical Intersection):** Control points where grade lines meet
- **Tangent Segments:** Straight sections with constant grade between PVIs
- **Vertical Curves:** Parabolic transitions at PVIs that provide smooth grade changes

### 1.2 Design Philosophy: PVI-Based Approach

Saikei Civil uses a **PVI-based** design methodology, matching professional tools like Civil 3D and OpenRoads:

```
User places PVIs → System calculates grades → System generates segments
                ↓
         Tangents + Curves
```

**Key Principle:** PVIs are control points, not the actual geometry. The segments (tangents and curves) are automatically generated and maintained by the system.

### 1.3 Native IFC Implementation

Saikei Civil creates **native IFC 4.3** vertical alignments:

- **Not a converter:** We create IFC entities directly, not export to IFC
- **Single source of truth:** The IFC file IS the alignment, not a Blender object
- **Always valid:** Every operation maintains IFC compliance
- **Bidirectional:** Blender visualization ↔ IFC entities stay synchronized

### 1.4 Relationship to Horizontal Alignments

Vertical alignments work in "distance along" space:

```
Station Parameter (distance along horizontal alignment)
        ↓
Vertical Alignment: station → elevation
Horizontal Alignment: station → (x, y, direction)
        ↓
Combined: station → (x, y, z) - Complete 3D position
```

**Critical:** Station values must overlap between horizontal and vertical alignments for 3D integration.

---

## 2. Mathematical Foundations

### 2.1 Grade Calculations

**Grade** is the rate of elevation change per unit horizontal distance:

```python
# Formula
grade = (elevation₂ - elevation₁) / (station₂ - station₁)

# Decimal vs Percent
grade_decimal = 0.025  # 2.5%
grade_percent = 2.5    # Display only, always work in decimal internally!

# Sign Convention
+grade = uphill (rising)
-grade = downhill (falling)
 0     = flat (level)
```

**Example:**
```python
# Between two PVIs
PVI1: station = 0m, elevation = 100m
PVI2: station = 200m, elevation = 105m

grade = (105 - 100) / (200 - 0) = 5 / 200 = 0.025 (2.5%)
```

### 2.2 Parabolic Vertical Curves

Vertical curves use **second-degree parabolas** for smooth grade transitions:

#### 2.2.1 Elevation Equation

```python
# Core Formula
E(x) = E_BVC + g₁×x + ((g₂ - g₁)/(2L))×x²

Where:
  x = station - S_BVC  (distance from curve start)
  E_BVC = elevation at Beginning of Vertical Curve
  g₁ = incoming grade (decimal, e.g., 0.03)
  g₂ = outgoing grade (decimal, e.g., -0.02)
  L = curve length (meters)
```

#### 2.2.2 Grade Equation (First Derivative)

```python
# Grade at any point on curve
g(x) = g₁ + ((g₂ - g₁)/L)×x

# Verification
g(0) = g₁    ✓ (grade at BVC)
g(L) = g₂    ✓ (grade at EVC)
```

#### 2.2.3 Rate of Grade Change (Constant)

```python
# Second derivative is constant
r = (g₂ - g₁) / L  # grade change per meter
```

### 2.3 Curve Stations and Elevations

#### 2.3.1 Key Stations

```python
# Given: PVI at station S_PVI with curve length L
S_BVC = S_PVI - L/2    # Begin Vertical Curve
S_EVC = S_PVI + L/2    # End Vertical Curve
S_PVI = S_BVC + L/2    # PVI is at midpoint
```

#### 2.3.2 BVC Elevation

```python
# Work backwards from PVI
E_BVC = E_PVI - g₁ × (L/2)

# Where:
#   E_PVI = elevation at PVI
#   g₁ = incoming grade
#   L = curve length
```

#### 2.3.3 EVC Elevation

```python
# Method 1: Using parabolic equation
E_EVC = E_BVC + g₁×L + ((g₂-g₁)/(2L))×L²
      = E_BVC + g₁×L + (g₂-g₁)×L/2
      = E_BVC + (g₁ + g₂)/2 × L

# Method 2: Average grade method (equivalent)
E_EVC = E_BVC + average_grade × L
where average_grade = (g₁ + g₂) / 2
```

### 2.4 K-Value Design Method

**K-value** is the horizontal distance required for 1% grade change:

```python
# Definition
K = L / A

Where:
  K = design parameter (m/% or ft/%)
  L = curve length (m or ft)
  A = |g₂ - g₁| × 100  (absolute grade change in %)

# Design Application
# Given K_min and grade change A, calculate required length:
L_min = K_min × A
```

#### 2.4.1 Crest vs Sag Curves

```python
# Crest Curve: Grade is decreasing
is_crest = (g₁ > g₂)
# Examples:
#   +3% to -2% → Crest (grade decreasing)
#   +5% to +2% → Crest (both positive, but decreasing)

# Sag Curve: Grade is increasing  
is_sag = (g₁ < g₂)
# Examples:
#   -4% to +1% → Sag (grade increasing)
#   -3% to -1% → Sag (both negative, but increasing)
```

#### 2.4.2 AASHTO Minimum K-Values

```python
# Design speed (km/h) : (K_crest, K_sag)
AASHTO_K_VALUES = {
    40:  (3, 6),
    50:  (7, 9),
    60:  (11, 11),
    70:  (17, 14),
    80:  (29, 17),    # Common for highways
    90:  (32, 20),
    100: (43, 24),
    110: (56, 29),
    120: (73, 33),
    130: (91, 38)
}
```

**Design Principle:**
- **Crest curves:** Based on stopping sight distance (driver must see over crest)
- **Sag curves:** Based on headlight sight distance (shorter curves acceptable)
- **Higher speeds = larger K-values required**

### 2.5 Curve Offset at PVI

```python
# Maximum offset from tangent occurs at PVI (curve midpoint)
offset = (g₂ - g₁) × L / 8

# Sign convention:
#   Crest: offset < 0 (curve below PVI)
#   Sag:   offset > 0 (curve above PVI)
```

---

## 3. Data Structures & Classes

### 3.1 Core Classes Overview

```
VerticalAlignment (Manager)
├── PVI objects (control points)
├── VerticalSegment objects (geometry)
│   ├── TangentSegment (constant grade)
│   └── ParabolicSegment (vertical curve)
└── Validation & IFC export
```

### 3.2 PVI Class

**File:** `core/native_ifc_vertical_alignment.py`

```python
class PVI:
    """
    Point of Vertical Intersection - Control point for vertical design.
    
    PVIs define where grade lines intersect. The system automatically
    calculates grades between PVIs and generates curve/tangent segments.
    """
    
    def __init__(self, station: float, elevation: float, curve_length: float = 0.0):
        self.station = station          # Distance along alignment (m)
        self.elevation = elevation      # Height (m)
        self.curve_length = curve_length  # Vertical curve length (m)
        
        # Calculated by VerticalAlignment.calculate_grades()
        self.grade_in: Optional[float] = None   # Incoming grade (decimal)
        self.grade_out: Optional[float] = None  # Outgoing grade (decimal)
```

**Key Properties (Auto-calculated):**

```python
@property
def grade_change(self) -> float:
    """Algebraic grade change (A-value)"""
    if self.grade_in is None or self.grade_out is None:
        return 0.0
    return abs(self.grade_out - self.grade_in)

@property
def is_crest_curve(self) -> bool:
    """True if crest curve (grade decreasing)"""
    if self.grade_in is None or self.grade_out is None:
        return False
    return self.grade_in > self.grade_out

@property
def bvc_station(self) -> float:
    """Begin Vertical Curve station"""
    return self.station - self.curve_length / 2

@property
def evc_station(self) -> float:
    """End Vertical Curve station"""
    return self.station + self.curve_length / 2

def calculate_k_value(self) -> float:
    """Calculate K-value for this curve"""
    if self.curve_length == 0 or self.grade_change == 0:
        return 0.0
    return self.curve_length / (self.grade_change * 100)
```

### 3.3 VerticalSegment Base Class

**File:** `core/native_ifc_vertical_alignment.py`

```python
class VerticalSegment(ABC):
    """
    Abstract base for vertical alignment segments.
    
    Segments represent the actual geometry - tangents and curves.
    They are generated automatically from PVIs.
    """
    
    def __init__(self, start_station: float, end_station: float):
        self.start_station = start_station
        self.end_station = end_station
        self.segment_type: str = "BASE"  # TANGENT or PARABOLIC
    
    @property
    def length(self) -> float:
        """Horizontal length of segment"""
        return self.end_station - self.start_station
    
    @abstractmethod
    def get_elevation(self, station: float) -> float:
        """Get elevation at station"""
        pass
    
    @abstractmethod
    def get_grade(self, station: float) -> float:
        """Get grade at station"""
        pass
    
    def contains_station(self, station: float) -> bool:
        """Check if station is within this segment"""
        return self.start_station <= station <= self.end_station
```

### 3.4 TangentSegment Class

**File:** `core/native_ifc_vertical_alignment.py`

```python
class TangentSegment(VerticalSegment):
    """
    Constant grade segment (tangent line).
    
    Simple linear interpolation between start and end.
    """
    
    def __init__(self, start_station: float, end_station: float,
                 start_elevation: float, grade: float):
        super().__init__(start_station, end_station)
        self.start_elevation = start_elevation
        self.grade = grade  # Decimal (e.g., 0.025 for 2.5%)
        self.segment_type = "TANGENT"
    
    def get_elevation(self, station: float) -> float:
        """
        Linear elevation: E = E₀ + g×(s - s₀)
        """
        if not self.contains_station(station):
            raise ValueError(f"Station {station} not in segment")
        
        x = station - self.start_station
        return self.start_elevation + self.grade * x
    
    def get_grade(self, station: float) -> float:
        """
        Constant grade throughout tangent
        """
        if not self.contains_station(station):
            raise ValueError(f"Station {station} not in segment")
        
        return self.grade
    
    @property
    def end_elevation(self) -> float:
        """Elevation at end of tangent"""
        return self.start_elevation + self.grade * self.length
    
    def to_ifc_segment(self, ifc_file):
        """
        Export to IFC IfcAlignmentVerticalSegment (CONSTANTGRADIENT)
        """
        return ifc_file.create_entity(
            "IfcAlignmentSegment",
            DesignParameters=ifc_file.create_entity(
                "IfcAlignmentVerticalSegment",
                StartDistAlong=float(self.start_station),
                HorizontalLength=float(self.length),
                StartHeight=float(self.start_elevation),
                StartGradient=float(self.grade),
                PredefinedType="CONSTANTGRADIENT"
            )
        )
```

### 3.5 ParabolicSegment Class

**File:** `core/native_ifc_vertical_alignment.py`

```python
class ParabolicSegment(VerticalSegment):
    """
    Parabolic vertical curve segment.
    
    Uses second-degree parabola for smooth grade transition.
    """
    
    def __init__(self, start_station: float, end_station: float,
                 start_elevation: float, g1: float, g2: float):
        super().__init__(start_station, end_station)
        self.start_elevation = start_elevation  # E_BVC
        self.g1 = g1  # Incoming grade (decimal)
        self.g2 = g2  # Outgoing grade (decimal)
        self.segment_type = "PARABOLIC"
    
    @property
    def rate_of_change(self) -> float:
        """Constant rate of grade change (per meter)"""
        return (self.g2 - self.g1) / self.length
    
    def get_elevation(self, station: float) -> float:
        """
        Parabolic equation: E(x) = E₀ + g₁×x + ((g₂-g₁)/(2L))×x²
        """
        if not self.contains_station(station):
            raise ValueError(f"Station {station} not in segment")
        
        x = station - self.start_station
        return (self.start_elevation + 
                self.g1 * x + 
                (self.g2 - self.g1) / (2 * self.length) * x**2)
    
    def get_grade(self, station: float) -> float:
        """
        First derivative: g(x) = g₁ + ((g₂-g₁)/L)×x
        """
        if not self.contains_station(station):
            raise ValueError(f"Station {station} not in segment")
        
        x = station - self.start_station
        return self.g1 + (self.g2 - self.g1) / self.length * x
    
    @property
    def end_elevation(self) -> float:
        """Elevation at EVC"""
        return self.get_elevation(self.end_station)
    
    @property
    def is_crest_curve(self) -> bool:
        """True if crest (grade decreasing)"""
        return self.g1 > self.g2
    
    @property
    def a_value(self) -> float:
        """A-value: absolute grade change (%)"""
        return abs(self.g2 - self.g1) * 100
    
    @property
    def k_value(self) -> float:
        """K-value for this curve"""
        if self.a_value == 0:
            return 0.0
        return self.length / self.a_value
    
    def get_high_low_point(self) -> Optional[Tuple[float, float]]:
        """
        Find turning point (high point for crest, low point for sag).
        Returns (station, elevation) or None if no turning point in segment.
        """
        # Turning point where g(x) = 0
        # 0 = g₁ + ((g₂-g₁)/L)×x
        # x = -g₁×L / (g₂-g₁)
        
        if abs(self.g2 - self.g1) < 1e-10:
            return None  # No grade change
        
        x = -self.g1 * self.length / (self.g2 - self.g1)
        
        if 0 <= x <= self.length:
            station = self.start_station + x
            elevation = self.get_elevation(station)
            return (station, elevation)
        
        return None
    
    def to_ifc_segment(self, ifc_file):
        """
        Export to IFC IfcAlignmentVerticalSegment (PARABOLICARC)
        """
        return ifc_file.create_entity(
            "IfcAlignmentSegment",
            DesignParameters=ifc_file.create_entity(
                "IfcAlignmentVerticalSegment",
                StartDistAlong=float(self.start_station),
                HorizontalLength=float(self.length),
                StartHeight=float(self.start_elevation),
                StartGradient=float(self.g1),
                EndGradient=float(self.g2),
                PredefinedType="PARABOLICARC"
            )
        )
```

### 3.6 VerticalAlignment Manager Class

**File:** `core/native_ifc_vertical_alignment.py`

```python
class VerticalAlignment:
    """
    Manager for complete vertical alignment design.
    
    Handles PVI-based workflow:
    1. Add/remove/modify PVIs
    2. Calculate grades between PVIs
    3. Generate tangent and curve segments
    4. Query elevation/grade at any station
    5. Validate design
    6. Export to IFC
    """
    
    def __init__(self, name: str = "Vertical Alignment"):
        self.name = name
        self.pvis: List[PVI] = []
        self.segments: List[VerticalSegment] = []
        self.min_k_crest: float = 29.0  # AASHTO 80 km/h
        self.min_k_sag: float = 17.0    # AASHTO 80 km/h
    
    def add_pvi(self, station: float, elevation: float, 
                curve_length: float = 0.0) -> None:
        """Add PVI and automatically sort by station"""
        pvi = PVI(station, elevation, curve_length)
        self.pvis.append(pvi)
        self.pvis.sort(key=lambda p: p.station)
        self.calculate_grades()
    
    def calculate_grades(self) -> None:
        """
        Calculate grades between all PVIs.
        Must be called after adding/modifying PVIs.
        """
        for i in range(len(self.pvis)):
            # Incoming grade (from previous PVI)
            if i > 0:
                prev_pvi = self.pvis[i - 1]
                curr_pvi = self.pvis[i]
                grade_in = ((curr_pvi.elevation - prev_pvi.elevation) / 
                           (curr_pvi.station - prev_pvi.station))
                curr_pvi.grade_in = grade_in
                prev_pvi.grade_out = grade_in
            
            # First PVI has no incoming grade
            if i == 0:
                self.pvis[0].grade_in = None
            
            # Last PVI has no outgoing grade
            if i == len(self.pvis) - 1:
                self.pvis[-1].grade_out = None
    
    def generate_segments(self) -> None:
        """
        Generate tangent and curve segments from PVIs.
        Must be called after calculate_grades().
        """
        self.segments.clear()
        
        if len(self.pvis) < 2:
            return
        
        for i in range(len(self.pvis) - 1):
            pvi_curr = self.pvis[i]
            pvi_next = self.pvis[i + 1]
            
            # Determine segment boundaries
            if pvi_curr.curve_length > 0:
                # Current PVI has curve
                curve_start = pvi_curr.station - pvi_curr.curve_length / 2
                curve_end = pvi_curr.station + pvi_curr.curve_length / 2
                
                # Create curve segment
                curve_start_elev = (pvi_curr.elevation - 
                                   pvi_curr.grade_in * (pvi_curr.curve_length / 2))
                
                curve_seg = ParabolicSegment(
                    start_station=curve_start,
                    end_station=curve_end,
                    start_elevation=curve_start_elev,
                    g1=pvi_curr.grade_in,
                    g2=pvi_curr.grade_out
                )
                self.segments.append(curve_seg)
                
                # Tangent from EVC to next PVI (or next BVC)
                tangent_start = curve_end
            else:
                # No curve at current PVI
                tangent_start = pvi_curr.station
            
            # Tangent endpoint
            if pvi_next.curve_length > 0:
                tangent_end = pvi_next.station - pvi_next.curve_length / 2
            else:
                tangent_end = pvi_next.station
            
            # Create tangent segment if length > 0
            if tangent_end > tangent_start:
                tangent_start_elev = self.get_elevation_at(tangent_start)
                
                tangent_seg = TangentSegment(
                    start_station=tangent_start,
                    end_station=tangent_end,
                    start_elevation=tangent_start_elev,
                    grade=pvi_curr.grade_out
                )
                self.segments.append(tangent_seg)
        
        # Sort segments by station
        self.segments.sort(key=lambda s: s.start_station)
    
    def get_elevation_at(self, station: float) -> float:
        """Get elevation at any station"""
        segment = self.find_segment_at(station)
        if segment is None:
            raise ValueError(f"No segment at station {station}")
        return segment.get_elevation(station)
    
    def get_grade_at(self, station: float) -> float:
        """Get grade at any station"""
        segment = self.find_segment_at(station)
        if segment is None:
            raise ValueError(f"No segment at station {station}")
        return segment.get_grade(station)
    
    def find_segment_at(self, station: float) -> Optional[VerticalSegment]:
        """Find segment containing station"""
        for segment in self.segments:
            if segment.contains_station(station):
                return segment
        return None
    
    def validate(self) -> List[str]:
        """
        Validate design and return warnings.
        Checks:
        - Curve overlaps
        - K-values vs minimums
        - Grade continuity
        """
        warnings = []
        
        # Check for curve overlaps
        for i in range(1, len(self.pvis) - 1):
            pvi_prev = self.pvis[i - 1]
            pvi_curr = self.pvis[i]
            
            if pvi_prev.curve_length > 0 and pvi_curr.curve_length > 0:
                evc_prev = pvi_prev.station + pvi_prev.curve_length / 2
                bvc_curr = pvi_curr.station - pvi_curr.curve_length / 2
                
                if bvc_curr < evc_prev:
                    warnings.append(
                        f"Curves overlap between PVI {i-1} and {i}"
                    )
        
        # Check K-values
        for i, pvi in enumerate(self.pvis):
            if pvi.curve_length > 0 and pvi.grade_in is not None and pvi.grade_out is not None:
                k = pvi.calculate_k_value()
                
                if pvi.is_crest_curve:
                    if k < self.min_k_crest:
                        warnings.append(
                            f"PVI {i}: Crest K={k:.1f} < minimum {self.min_k_crest}"
                        )
                else:
                    if k < self.min_k_sag:
                        warnings.append(
                            f"PVI {i}: Sag K={k:.1f} < minimum {self.min_k_sag}"
                        )
        
        return warnings
```

---

## 4. IFC 4.3 Mapping

### 4.1 IFC Entity Hierarchy

```
IfcProject
└── IfcSite
    └── IfcAlignment
        ├── IfcAlignmentHorizontal (Sprint 1)
        └── IfcAlignmentVertical (Sprint 3) ← THIS
            └── IfcAlignmentSegment[] (array)
                └── DesignParameters
                    └── IfcAlignmentVerticalSegment
                        ├── PredefinedType: CONSTANTGRADIENT | PARABOLICARC
                        ├── StartDistAlong: float
                        ├── HorizontalLength: float
                        ├── StartHeight: float
                        ├── StartGradient: float
                        └── EndGradient: float (for curves only)
```

### 4.2 Segment Type Mapping

| Saikei Civil Class | IFC PredefinedType | Geometric Representation |
|-------------------|-------------------|-------------------------|
| TangentSegment | CONSTANTGRADIENT | IfcLine (2D in distance-elevation space) |
| ParabolicSegment | PARABOLICARC | IfcPolynomialCurve (degree 2) |

### 4.3 IFC Export Code Pattern

```python
def create_ifc_vertical_alignment(vertical_manager, ifc_file, alignment_entity):
    """
    Export complete vertical alignment to IFC.
    
    Args:
        vertical_manager: VerticalAlignment instance
        ifc_file: ifcopenshell file object
        alignment_entity: Parent IfcAlignment entity
    """
    # 1. Create IfcAlignmentVertical
    vertical = ifc_file.createIfcAlignmentVertical(
        GlobalId=ifcopenshell.guid.new(),
        Name=f"{vertical_manager.name} - Vertical"
    )
    
    # 2. Create segment entities
    ifc_segments = []
    for segment in vertical_manager.segments:
        ifc_seg = segment.to_ifc_segment(ifc_file)
        ifc_segments.append(ifc_seg)
    
    # 3. Link segments to vertical alignment (IfcRelNests)
    ifc_file.createIfcRelNests(
        GlobalId=ifcopenshell.guid.new(),
        RelatingObject=vertical,
        RelatedObjects=ifc_segments
    )
    
    # 4. Link vertical to parent alignment (IfcRelNests)
    ifc_file.createIfcRelNests(
        GlobalId=ifcopenshell.guid.new(),
        RelatingObject=alignment_entity,
        RelatedObjects=[vertical]
    )
    
    return vertical
```

### 4.4 Critical IFC Properties

**IfcAlignmentVerticalSegment Properties:**

```python
# CONSTANTGRADIENT (Tangent)
{
    'PredefinedType': 'CONSTANTGRADIENT',
    'StartDistAlong': 0.0,          # Station at segment start (m)
    'HorizontalLength': 200.0,       # Segment length (m)
    'StartHeight': 100.0,            # Elevation at start (m)
    'StartGradient': 0.025,          # Grade (decimal, 0.025 = 2.5%)
    'EndGradient': None              # Not used for tangents
}

# PARABOLICARC (Curve)
{
    'PredefinedType': 'PARABOLICARC',
    'StartDistAlong': 160.0,         # Station at BVC (m)
    'HorizontalLength': 80.0,        # Curve length (m)
    'StartHeight': 104.0,            # Elevation at BVC (m)
    'StartGradient': 0.025,          # g₁ (incoming grade)
    'EndGradient': -0.008            # g₂ (outgoing grade)
}
```

**CRITICAL:** All grades in IFC are **decimal** format, not percentages!

### 4.5 IFC Coordinate System

Vertical alignments use a **2.5D coordinate system**:

- **X-axis:** "Distance along" the horizontal alignment (not map X!)
- **Y-axis:** Elevation (height)
- **2D space:** Curves are defined in (distance, elevation) plane
- **3D integration:** Combined with horizontal to get (map_x, map_y, elevation_z)

```
Vertical Coordinate System:
  X = station (distance along)
  Y = elevation

NOT the same as:
  Map X, Y coordinates
```

---

## 5. Common Operations

### 5.1 Creating a Vertical Alignment

```python
# 1. Create manager
va = VerticalAlignment(name="Highway 101 Profile")

# 2. Set design standards
va.min_k_crest = 29.0  # AASHTO 80 km/h
va.min_k_sag = 17.0

# 3. Add PVIs
va.add_pvi(station=0.0, elevation=100.0, curve_length=0.0)
va.add_pvi(station=200.0, elevation=105.0, curve_length=80.0)
va.add_pvi(station=450.0, elevation=103.0, curve_length=100.0)
va.add_pvi(station=650.0, elevation=110.0, curve_length=0.0)

# 4. Generate segments (automatic after add_pvi)
va.generate_segments()

# 5. Query elevations
elev_150 = va.get_elevation_at(150.0)
grade_150 = va.get_grade_at(150.0)

# 6. Validate design
warnings = va.validate()
if warnings:
    for w in warnings:
        print(f"Warning: {w}")
```

### 5.2 Modifying PVIs

```python
# Change PVI elevation
va.pvis[1].elevation = 106.0
va.calculate_grades()
va.generate_segments()

# Change curve length
va.pvis[1].curve_length = 100.0
va.generate_segments()

# Remove PVI
va.pvis.pop(2)
va.calculate_grades()
va.generate_segments()
```

### 5.3 Querying Alignment Data

```python
# Get elevation at station
elev = va.get_elevation_at(station=175.0)

# Get grade at station
grade = va.get_grade_at(station=175.0)
grade_percent = grade * 100

# Find which segment contains station
segment = va.find_segment_at(station=175.0)
if isinstance(segment, ParabolicSegment):
    print(f"In vertical curve: K={segment.k_value:.1f}")

# Get turning point of curve
if isinstance(segment, ParabolicSegment):
    tp = segment.get_high_low_point()
    if tp:
        print(f"High/low point at station {tp[0]}, elevation {tp[1]}")
```

### 5.4 Generating Profile Data

```python
def generate_profile_data(vertical_alignment, interval=5.0):
    """
    Generate elevation data at regular intervals for visualization.
    
    Args:
        vertical_alignment: VerticalAlignment instance
        interval: Station interval (m)
    
    Returns:
        List of (station, elevation, grade) tuples
    """
    if not vertical_alignment.segments:
        return []
    
    start = vertical_alignment.segments[0].start_station
    end = vertical_alignment.segments[-1].end_station
    
    stations = np.arange(start, end + interval, interval)
    data = []
    
    for station in stations:
        try:
            elev = vertical_alignment.get_elevation_at(station)
            grade = vertical_alignment.get_grade_at(station)
            data.append((station, elev, grade))
        except ValueError:
            continue
    
    return data
```

---

## 6. Validation & Error Handling

### 6.1 Required Validation Checks

```python
def validate_vertical_alignment(va: VerticalAlignment) -> Dict[str, Any]:
    """
    Comprehensive validation of vertical alignment.
    
    Returns dictionary with validation results.
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # 1. Minimum PVI count
    if len(va.pvis) < 2:
        results['errors'].append("Minimum 2 PVIs required")
        results['valid'] = False
        return results
    
    # 2. Station ordering
    for i in range(len(va.pvis) - 1):
        if va.pvis[i].station >= va.pvis[i + 1].station:
            results['errors'].append(f"PVI {i} and {i+1} out of order")
            results['valid'] = False
    
    # 3. Grades calculated
    for i, pvi in enumerate(va.pvis):
        if i > 0 and pvi.grade_in is None:
            results['errors'].append(f"PVI {i} missing incoming grade")
            results['valid'] = False
        if i < len(va.pvis) - 1 and pvi.grade_out is None:
            results['errors'].append(f"PVI {i} missing outgoing grade")
            results['valid'] = False
    
    # 4. Curve overlaps
    for i in range(1, len(va.pvis) - 1):
        pvi_prev = va.pvis[i - 1]
        pvi_curr = va.pvis[i]
        
        if pvi_prev.curve_length > 0 and pvi_curr.curve_length > 0:
            evc_prev = pvi_prev.evc_station
            bvc_curr = pvi_curr.bvc_station
            
            if bvc_curr < evc_prev:
                results['warnings'].append(
                    f"Curves overlap between PVI {i-1} and {i}"
                )
    
    # 5. K-value checks
    for i, pvi in enumerate(va.pvis):
        if pvi.curve_length > 0:
            k = pvi.calculate_k_value()
            
            if pvi.is_crest_curve:
                if k < va.min_k_crest:
                    results['warnings'].append(
                        f"PVI {i}: Crest K={k:.1f} < minimum {va.min_k_crest}"
                    )
            else:
                if k < va.min_k_sag:
                    results['warnings'].append(
                        f"PVI {i}: Sag K={k:.1f} < minimum {va.min_k_sag}"
                    )
    
    # 6. Segment continuity
    for i in range(len(va.segments) - 1):
        seg1 = va.segments[i]
        seg2 = va.segments[i + 1]
        
        # Check elevation continuity
        elev_diff = abs(seg1.end_elevation - seg2.start_elevation)
        if elev_diff > 0.001:  # 1mm tolerance
            results['warnings'].append(
                f"Elevation discontinuity between segments {i} and {i+1}: {elev_diff:.3f}m"
            )
        
        # Check station continuity
        station_diff = abs(seg1.end_station - seg2.start_station)
        if station_diff > 0.001:  # 1mm tolerance
            results['warnings'].append(
                f"Station gap between segments {i} and {i+1}: {station_diff:.3f}m"
            )
    
    return results
```

### 6.2 Common Error Scenarios

#### 6.2.1 Curve Overlap

**Problem:** Two adjacent PVIs have curves that overlap:

```python
PVI 1: station=200, curve_length=100 → EVC at 250
PVI 2: station=280, curve_length=100 → BVC at 230
Overlap: 230 < 250 ❌
```

**Solution:**
```python
# Reduce curve lengths or increase PVI spacing
min_spacing = (L1 + L2) / 2
if (PVI2.station - PVI1.station) < min_spacing:
    # Adjust curve lengths or move PVIs
```

#### 6.2.2 Invalid K-Values

**Problem:** Curve K-value below minimum for design speed:

```python
L = 60m, A = 3.5%, K = 60/3.5 = 17.1
Design speed = 80 km/h requires K_crest ≥ 29
17.1 < 29 ❌
```

**Solution:**
```python
# Calculate required length
L_required = K_min × A
L_required = 29 × 3.5 = 101.5m

# Update curve length
pvi.curve_length = 101.5
```

#### 6.2.3 Station Out of Range

**Problem:** Query station outside alignment range:

```python
va.get_elevation_at(1000.0)  # Last PVI at station=650
→ ValueError: No segment at station 1000.0
```

**Solution:**
```python
# Check bounds before querying
start = va.segments[0].start_station
end = va.segments[-1].end_station

if start <= station <= end:
    elev = va.get_elevation_at(station)
else:
    print(f"Station {station} out of range [{start}, {end}]")
```

---

## 7. Integration with Horizontal Alignments

### 7.1 The 3D Alignment Concept

Horizontal and vertical alignments combine to create complete 3D geometry:

```python
# Station is the common reference parameter
station = 150.0  # meters along alignment

# From horizontal alignment (Sprint 1)
x, y, direction = horizontal.get_position_at_station(station)

# From vertical alignment (Sprint 3)
z = vertical.get_elevation_at(station)

# Result: Complete 3D position
position_3d = (x, y, z)
```

### 7.2 Alignment3D Class

**File:** `core/alignment_3d.py`

```python
class Alignment3D:
    """
    Complete 3D alignment combining horizontal and vertical.
    """
    
    def __init__(self, horizontal, vertical, name="3D Alignment"):
        self.horizontal = horizontal
        self.vertical = vertical
        self.name = name
        self._validate_compatibility()
    
    def _validate_compatibility(self):
        """Check H and V alignments overlap in station range"""
        h_start = self.horizontal.start_station
        h_end = self.horizontal.end_station
        v_start = self.vertical.pvis[0].station
        v_end = self.vertical.pvis[-1].station
        
        if h_end < v_start or v_end < h_start:
            raise ValueError("H and V station ranges don't overlap")
    
    def get_3d_position(self, station: float) -> Tuple[float, float, float]:
        """Get complete 3D coordinates at station"""
        x, y = self.horizontal.get_position_at_station(station)
        z = self.vertical.get_elevation_at(station)
        return (x, y, z)
    
    def get_alignment_data(self, station: float) -> AlignmentPoint3D:
        """Get complete alignment data at station"""
        x, y = self.horizontal.get_position_at_station(station)
        direction = self.horizontal.get_direction_at_station(station)
        z = self.vertical.get_elevation_at(station)
        grade = self.vertical.get_grade_at(station)
        
        return AlignmentPoint3D(
            station=station,
            x=x, y=y, z=z,
            direction=direction,
            grade=grade
        )
```

### 7.3 Station Compatibility

**CRITICAL:** Horizontal and vertical alignments must have **overlapping station ranges**:

```python
# Example: Valid overlap
Horizontal: station 0 → 1000m
Vertical:   station 50 → 950m
Overlap:    station 50 → 950m ✓

# Example: Invalid (no overlap)
Horizontal: station 0 → 500m
Vertical:   station 600 → 1000m
Overlap:    NONE ❌
```

**Best Practice:** Design vertical alignment to cover the full horizontal alignment range, or slightly less if the road doesn't have vertical design at the very ends.

---

## 8. Critical Gotchas & Known Issues

### 8.1 Decimal vs Percent Grades

**GOTCHA:** Grades must **always** be stored as **decimals**, not percentages!

```python
# ❌ WRONG
grade = 2.5  # This is 250%!

# ✓ CORRECT
grade = 0.025  # 2.5%
grade_percent = grade * 100  # Display only
```

**Why:** IFC specification requires decimal grades. Converting back and forth causes confusion and bugs.

**Rule:** Store decimal internally, convert to percent only for UI display.

### 8.2 Grade Sign Convention

**GOTCHA:** Grade sign determines uphill vs downhill:

```python
# Positive grade = uphill (rising)
grade = +0.03  # +3%, rising 3m per 100m

# Negative grade = downhill (falling)
grade = -0.02  # -2%, falling 2m per 100m

# Zero grade = flat (level)
grade = 0.0
```

**Common mistake:** Forgetting negative sign for downhill grades.

### 8.3 Crest vs Sag Detection

**GOTCHA:** Curve type depends on **grade change direction**, not grade signs:

```python
# Crest: Grade is DECREASING
+3% → -2% = Crest ✓ (decreasing)
+5% → +2% = Crest ✓ (both positive, but decreasing)
 0% → -3% = Crest ✓ (decreasing)

# Sag: Grade is INCREASING
-4% → +1% = Sag ✓ (increasing)
-3% → -1% = Sag ✓ (both negative, but increasing)
 0% → +3% = Sag ✓ (increasing)
```

**Rule:** `is_crest = (g1 > g2)`, regardless of sign.

### 8.4 Station vs Distance Along

**GOTCHA:** In IFC, "distance along" refers to the horizontal alignment, NOT the 3D alignment arc length:

```python
# CORRECT: Station measured horizontally
station = 100.0  # 100m along horizontal alignment

# NOT: Arc length along 3D curve
# (3D arc length would include grade effects)
```

**Why:** Vertical alignments are in "2.5D" space - horizontal distance + elevation.

### 8.5 Curve Offset Direction

**GOTCHA:** Parabolic offset from PVI has opposite signs for crest/sag:

```python
# Crest curve: Curve is BELOW PVI
offset = (g2 - g1) × L / 8
if is_crest: offset < 0  # Negative offset

# Sag curve: Curve is ABOVE PVI  
offset = (g2 - g1) × L / 8
if is_sag: offset > 0  # Positive offset
```

**Visual:**
```
Crest:  PVI •
           \  ╱  ← Curve below PVI
            ╲╱

Sag:        ╱╲  ← Curve above PVI
           ╱  ╲
        PVI •
```

### 8.6 BVC/EVC Calculations

**GOTCHA:** BVC elevation requires working **backwards** from PVI:

```python
# WRONG: Start from previous PVI
E_BVC = E_prev_PVI + grade × distance  ❌

# CORRECT: Work backwards from current PVI
E_BVC = E_PVI - g1 × (L/2) ✓
```

**Why:** PVI is the **control point**, not the BVC. We must calculate from the known PVI.

### 8.7 K-Value Units

**GOTCHA:** K-value units depend on whether grades are in percent or decimal:

```python
# If using percent grades (for display)
K = L / A
where A = |g2 - g1| (already in percent)

# If using decimal grades (internal)
K = L / (A × 100)
where A = |g2 - g1| (decimal), multiply by 100

# Example:
g1 = 0.025 (2.5%)
g2 = -0.018 (-1.8%)
A = |(-0.018) - (0.025)| × 100 = 4.3%
L = 80m
K = 80 / 4.3 = 18.6 m/%
```

### 8.8 Missing Geometric Layer (IFC Compliance)

**CURRENT ISSUE:** Saikei Civil creates the semantic layer (IfcAlignmentVerticalSegment) but NOT the geometric layer (IfcCurveSegment with ParentCurve).

**What's missing:**
```python
# We create this:
IfcAlignmentVerticalSegment(
    PredefinedType="PARABOLICARC",
    StartDistAlong=160.0,
    HorizontalLength=80.0,
    StartHeight=104.0,
    StartGradient=0.025,
    EndGradient=-0.008
)

# We should ALSO create:
IfcCurveSegment(
    ParentCurve=IfcPolynomialCurve(
        CoefficientsY=(C, B, A)  # Parabola coefficients
    )
)
```

**Impact:** May cause interoperability issues with some IFC viewers.

**Status:** Known issue, planned for Phase 2 refactoring.

### 8.9 No IfcGradientCurve Wrapper

**CURRENT ISSUE:** We create individual segments but don't wrap them in IfcGradientCurve (composite curve).

**Should implement:**
```python
gradient_curve = ifc.create_entity("IfcGradientCurve",
    Segments=[curve_segment1, curve_segment2, ...],
    BaseCurve=horizontal_composite_curve  # Link to horizontal!
)
```

**Impact:** Missing proper 2.5D → 3D linking in IFC.

**Status:** Planned for Phase 2.

---

## 9. Code Patterns & Examples

### 9.1 Complete Workflow Example

```python
"""
Complete example: Create vertical alignment, validate, export to IFC.
"""
import ifcopenshell
from saikei.core.native_ifc_vertical_alignment import (
    VerticalAlignment, PVI
)

# 1. Create vertical alignment
va = VerticalAlignment(name="Highway 101 Profile")
va.min_k_crest = 29.0  # 80 km/h design speed
va.min_k_sag = 17.0

# 2. Add PVIs (control points)
va.add_pvi(station=0.0, elevation=100.0, curve_length=0.0)
va.add_pvi(station=200.0, elevation=105.0, curve_length=80.0)
va.add_pvi(station=450.0, elevation=103.0, curve_length=100.0)
va.add_pvi(station=650.0, elevation=110.0, curve_length=0.0)

# 3. System automatically calculates grades
print(f"PVI 1 grade out: {va.pvis[0].grade_out * 100:.2f}%")
print(f"PVI 2 grade in: {va.pvis[1].grade_in * 100:.2f}%")
print(f"PVI 2 grade out: {va.pvis[1].grade_out * 100:.2f}%")
print(f"PVI 2 K-value: {va.pvis[1].calculate_k_value():.1f}")

# 4. Generate segments
va.generate_segments()
print(f"Generated {len(va.segments)} segments")

# 5. Query elevations
for station in [0, 100, 200, 300, 400, 500, 600]:
    try:
        elev = va.get_elevation_at(station)
        grade = va.get_grade_at(station)
        print(f"Station {station}m: Elevation {elev:.3f}m, Grade {grade*100:.2f}%")
    except ValueError as e:
        print(f"Station {station}m: {e}")

# 6. Validate design
warnings = va.validate()
if warnings:
    print("\nDesign Warnings:")
    for w in warnings:
        print(f"  - {w}")
else:
    print("\nDesign is valid!")

# 7. Export to IFC
ifc = ifcopenshell.file(schema="IFC4X3")

# Create project structure
project = ifc.createIfcProject(
    GlobalId=ifcopenshell.guid.new(),
    Name="Highway 101"
)

site = ifc.createIfcSite(
    GlobalId=ifcopenshell.guid.new(),
    Name="Site"
)

alignment = ifc.createIfcAlignment(
    GlobalId=ifcopenshell.guid.new(),
    Name="Highway 101 Alignment"
)

# Create vertical alignment in IFC
vertical = ifc.createIfcAlignmentVertical(
    GlobalId=ifcopenshell.guid.new(),
    Name="Highway 101 Profile"
)

# Export segments
ifc_segments = []
for segment in va.segments:
    ifc_seg = segment.to_ifc_segment(ifc)
    ifc_segments.append(ifc_seg)

# Link segments to vertical
ifc.createIfcRelNests(
    GlobalId=ifcopenshell.guid.new(),
    RelatingObject=vertical,
    RelatedObjects=ifc_segments
)

# Link vertical to alignment
ifc.createIfcRelNests(
    GlobalId=ifcopenshell.guid.new(),
    RelatingObject=alignment,
    RelatedObjects=[vertical]
)

# Write file
ifc.write("highway_101_profile.ifc")
print("\nExported to highway_101_profile.ifc")
```

### 9.2 K-Value Design Pattern

```python
"""
Design a vertical curve using K-value method.
"""
from saikei.core.native_ifc_vertical_alignment import calculate_required_curve_length

# Design parameters
design_speed_kmh = 80
grade_in = 0.030   # +3.0%
grade_out = -0.020 # -2.0%

# Calculate grade change
grade_change = abs(grade_out - grade_in)
a_value = grade_change * 100  # 5.0%

# Is this a crest or sag?
is_crest = (grade_in > grade_out)
curve_type = "CREST" if is_crest else "SAG"

# Get minimum K-value for design speed
if design_speed_kmh == 80:
    k_min = 29 if is_crest else 17
else:
    # Look up from AASHTO table
    pass

# Calculate required curve length
curve_length = calculate_required_curve_length(
    grade_change=grade_change,
    k_value=k_min
)

print(f"Design Speed: {design_speed_kmh} km/h")
print(f"Curve Type: {curve_type}")
print(f"Grade Change: {a_value:.1f}%")
print(f"Minimum K: {k_min}")
print(f"Required Length: {curve_length:.1f}m")

# Add to alignment with calculated length
va.add_pvi(
    station=pvi_station,
    elevation=pvi_elevation,
    curve_length=curve_length
)
```

### 9.3 Segment Iteration Pattern

```python
"""
Iterate through segments and process each type differently.
"""
from saikei.core.native_ifc_vertical_alignment import (
    TangentSegment, ParabolicSegment
)

for i, segment in enumerate(va.segments):
    print(f"\nSegment {i}:")
    print(f"  Type: {segment.segment_type}")
    print(f"  Station: {segment.start_station:.1f} → {segment.end_station:.1f}")
    print(f"  Length: {segment.length:.1f}m")
    
    if isinstance(segment, TangentSegment):
        print(f"  Grade: {segment.grade * 100:.2f}%")
        print(f"  Start Elevation: {segment.start_elevation:.3f}m")
        print(f"  End Elevation: {segment.end_elevation:.3f}m")
    
    elif isinstance(segment, ParabolicSegment):
        print(f"  Curve Type: {'CREST' if segment.is_crest_curve else 'SAG'}")
        print(f"  g₁: {segment.g1 * 100:.2f}%")
        print(f"  g₂: {segment.g2 * 100:.2f}%")
        print(f"  A-value: {segment.a_value:.2f}%")
        print(f"  K-value: {segment.k_value:.1f}")
        
        # Find high/low point
        tp = segment.get_high_low_point()
        if tp:
            tp_station, tp_elev = tp
            print(f"  High/Low Point: Station {tp_station:.1f}m, Elevation {tp_elev:.3f}m")
```

### 9.4 Profile Data Generation

```python
"""
Generate profile data for visualization or export.
"""
import numpy as np

def generate_profile_table(va, interval=10.0):
    """
    Generate tabulated profile data.
    
    Returns:
        List of dicts with station, elevation, grade, segment type
    """
    if not va.segments:
        return []
    
    start = va.segments[0].start_station
    end = va.segments[-1].end_station
    
    stations = np.arange(start, end + interval, interval)
    
    profile = []
    for station in stations:
        try:
            elev = va.get_elevation_at(station)
            grade = va.get_grade_at(station)
            segment = va.find_segment_at(station)
            
            profile.append({
                'station': station,
                'elevation': elev,
                'grade': grade,
                'grade_percent': grade * 100,
                'segment_type': segment.segment_type if segment else "N/A"
            })
        except ValueError:
            continue
    
    return profile

# Example usage
profile = generate_profile_table(va, interval=5.0)

print("\nStation | Elevation | Grade  | Type")
print("--------|-----------|--------|----------")
for p in profile:
    print(f"{p['station']:7.1f} | {p['elevation']:9.3f} | "
          f"{p['grade_percent']:6.2f}% | {p['segment_type']}")
```

---

## 10. Testing Strategy

### 10.1 Unit Test Structure

**File:** `tests/test_vertical_alignment.py`

```python
import unittest
from saikei.core.native_ifc_vertical_alignment import (
    PVI, TangentSegment, ParabolicSegment, VerticalAlignment
)

class TestPVI(unittest.TestCase):
    """Test PVI class"""
    
    def test_create_pvi(self):
        """Test basic PVI creation"""
        pvi = PVI(station=100.0, elevation=105.0, curve_length=80.0)
        self.assertEqual(pvi.station, 100.0)
        self.assertEqual(pvi.elevation, 105.0)
        self.assertEqual(pvi.curve_length, 80.0)
    
    def test_pvi_k_value(self):
        """Test K-value calculation"""
        pvi = PVI(station=100.0, elevation=105.0, curve_length=80.0)
        pvi.grade_in = 0.025
        pvi.grade_out = -0.018
        
        k = pvi.calculate_k_value()
        expected_k = 80 / (abs(0.025 - (-0.018)) * 100)
        self.assertAlmostEqual(k, expected_k, places=1)

class TestTangentSegment(unittest.TestCase):
    """Test constant grade segments"""
    
    def test_tangent_elevation(self):
        """Test linear elevation calculation"""
        seg = TangentSegment(
            start_station=0.0,
            end_station=200.0,
            start_elevation=100.0,
            grade=0.025
        )
        
        self.assertEqual(seg.get_elevation(0.0), 100.0)
        self.assertEqual(seg.get_elevation(100.0), 102.5)
        self.assertEqual(seg.get_elevation(200.0), 105.0)
    
    def test_tangent_grade_constant(self):
        """Test grade is constant throughout"""
        seg = TangentSegment(
            start_station=0.0,
            end_station=200.0,
            start_elevation=100.0,
            grade=0.025
        )
        
        self.assertEqual(seg.get_grade(0.0), 0.025)
        self.assertEqual(seg.get_grade(100.0), 0.025)
        self.assertEqual(seg.get_grade(200.0), 0.025)

class TestParabolicSegment(unittest.TestCase):
    """Test parabolic curve segments"""
    
    def test_parabolic_elevation(self):
        """Test parabolic elevation calculation"""
        seg = ParabolicSegment(
            start_station=160.0,
            end_station=240.0,
            start_elevation=104.0,
            g1=0.025,
            g2=-0.008
        )
        
        # Test at BVC
        self.assertAlmostEqual(seg.get_elevation(160.0), 104.0, places=3)
        
        # Test at midpoint (PVI)
        mid_elev = seg.get_elevation(200.0)
        self.assertAlmostEqual(mid_elev, 104.850, places=3)
    
    def test_parabolic_grade_transition(self):
        """Test grade changes linearly"""
        seg = ParabolicSegment(
            start_station=160.0,
            end_station=240.0,
            start_elevation=104.0,
            g1=0.025,
            g2=-0.008
        )
        
        # At BVC
        self.assertAlmostEqual(seg.get_grade(160.0), 0.025, places=4)
        
        # At midpoint
        mid_grade = seg.get_grade(200.0)
        expected = (0.025 + (-0.008)) / 2
        self.assertAlmostEqual(mid_grade, expected, places=4)
        
        # At EVC
        self.assertAlmostEqual(seg.get_grade(240.0), -0.008, places=4)

class TestVerticalAlignment(unittest.TestCase):
    """Test complete vertical alignment system"""
    
    def test_add_pvi_sorts_by_station(self):
        """Test PVIs are auto-sorted"""
        va = VerticalAlignment()
        va.add_pvi(200.0, 105.0)
        va.add_pvi(0.0, 100.0)
        va.add_pvi(400.0, 103.0)
        
        self.assertEqual(va.pvis[0].station, 0.0)
        self.assertEqual(va.pvis[1].station, 200.0)
        self.assertEqual(va.pvis[2].station, 400.0)
    
    def test_grade_calculation(self):
        """Test automatic grade calculation"""
        va = VerticalAlignment()
        va.add_pvi(0.0, 100.0)
        va.add_pvi(200.0, 105.0)
        
        expected_grade = (105 - 100) / (200 - 0)
        self.assertAlmostEqual(va.pvis[0].grade_out, expected_grade, places=6)
        self.assertAlmostEqual(va.pvis[1].grade_in, expected_grade, places=6)
    
    def test_segment_generation(self):
        """Test segments are generated correctly"""
        va = VerticalAlignment()
        va.add_pvi(0.0, 100.0, curve_length=0.0)
        va.add_pvi(200.0, 105.0, curve_length=80.0)
        va.add_pvi(400.0, 103.0, curve_length=0.0)
        va.generate_segments()
        
        # Should have: tangent, curve, tangent
        self.assertEqual(len(va.segments), 3)
        self.assertIsInstance(va.segments[0], TangentSegment)
        self.assertIsInstance(va.segments[1], ParabolicSegment)
        self.assertIsInstance(va.segments[2], TangentSegment)

if __name__ == '__main__':
    unittest.main()
```

### 10.2 Integration Tests

```python
class TestVerticalHorizontalIntegration(unittest.TestCase):
    """Test 3D alignment integration"""
    
    def test_station_overlap(self):
        """Test H and V alignments have compatible ranges"""
        # Create horizontal alignment (Sprint 1)
        h_alignment = create_test_horizontal_alignment()  # 0-500m
        
        # Create vertical alignment
        va = VerticalAlignment()
        va.add_pvi(0.0, 100.0)
        va.add_pvi(500.0, 110.0)
        
        # Create 3D alignment
        alignment_3d = Alignment3D(h_alignment, va)
        
        # Test 3D query
        x, y, z = alignment_3d.get_3d_position(250.0)
        self.assertIsNotNone(x)
        self.assertIsNotNone(y)
        self.assertIsNotNone(z)
```

### 10.3 Real-World Validation Test

```python
def test_worked_example():
    """
    Test complete worked example from documentation.
    
    Highway 101 Profile:
    - PVI 1: 0m, 100m, no curve
    - PVI 2: 200m, 105m, 80m crest curve
    - PVI 3: 450m, 103m, 100m sag curve
    - PVI 4: 650m, 110m, no curve
    """
    va = VerticalAlignment(name="Highway 101 Profile")
    va.add_pvi(0.0, 100.0, 0.0)
    va.add_pvi(200.0, 105.0, 80.0)
    va.add_pvi(450.0, 103.0, 100.0)
    va.add_pvi(650.0, 110.0, 0.0)
    va.generate_segments()
    
    # Test grades
    assert abs(va.pvis[0].grade_out - 0.025) < 0.0001  # 2.5%
    assert abs(va.pvis[1].grade_out - (-0.008)) < 0.0001  # -0.8%
    assert abs(va.pvis[2].grade_out - 0.035) < 0.0001  # 3.5%
    
    # Test segment count
    assert len(va.segments) == 5  # T-C-T-C-T
    
    # Test specific elevations
    elev_160 = va.get_elevation_at(160.0)  # BVC of first curve
    assert abs(elev_160 - 104.0) < 0.1
    
    print("✓ Worked example validated!")
```

---

## Appendix A: Quick Reference

### Common Formulas

```python
# Grade
grade = (elev₂ - elev₁) / (station₂ - station₁)

# Parabolic Elevation
E(x) = E_BVC + g₁×x + ((g₂-g₁)/(2L))×x²

# Parabolic Grade
g(x) = g₁ + ((g₂-g₁)/L)×x

# K-Value
K = L / A  where A = |g₂ - g₁| × 100

# BVC Station
S_BVC = S_PVI - L/2

# EVC Station
S_EVC = S_PVI + L/2

# BVC Elevation
E_BVC = E_PVI - g₁ × (L/2)

# Curve Type
is_crest = (g₁ > g₂)
```

### AASHTO K-Values (80 km/h)

```python
K_crest_min = 29 m/%
K_sag_min = 17 m/%
```

### Unit Conversions

```python
# Grade
decimal = percent / 100
percent = decimal × 100

# Always store DECIMAL internally!
grade_stored = 0.025  # NOT 2.5
```

---

## Appendix B: File Locations

```
saikei/
├── core/
│   ├── native_ifc_vertical_alignment.py    # MAIN MODULE
│   └── alignment_3d.py                     # H+V Integration
├── operators/
│   └── vertical_operators.py               # Blender operators
├── ui/
│   ├── vertical_properties.py              # Property groups
│   └── panels/
│       └── vertical_alignment_panel.py     # UI panels
└── tests/
    └── test_vertical_alignment.py          # Unit tests
```

---

## Appendix C: Key Constants

```python
# File: core/native_ifc_vertical_alignment.py

# AASHTO K-Values (m/%)
AASHTO_K_VALUES = {
    # speed_kmh: (K_crest, K_sag)
    40: (3, 6),
    50: (7, 9),
    60: (11, 11),
    70: (17, 14),
    80: (29, 17),
    90: (32, 20),
    100: (43, 24),
    110: (56, 29),
    120: (73, 33),
    130: (91, 38)
}

# Validation Tolerances
ELEVATION_TOLERANCE = 0.001  # 1mm
STATION_TOLERANCE = 0.001    # 1mm
GRADE_TOLERANCE = 1e-6       # Negligible

# IFC Entity Names
IFC_ALIGNMENT_VERTICAL = "IfcAlignmentVertical"
IFC_ALIGNMENT_SEGMENT = "IfcAlignmentSegment"
IFC_ALIGNMENT_VERTICAL_SEGMENT = "IfcAlignmentVerticalSegment"

# Segment Types
SEGMENT_TYPE_CONSTANTGRADIENT = "CONSTANTGRADIENT"
SEGMENT_TYPE_PARABOLICARC = "PARABOLICARC"
SEGMENT_TYPE_CIRCULARARC = "CIRCULARARC"  # Future
```

---

## Document Changelog

**v1.0 (2025-11-19):** Initial comprehensive reference document

---

**END OF REFERENCE DOCUMENT**

This document captures all essential knowledge about Saikei Civil's vertical alignment system. Use it as a reference when debugging, extending, or maintaining the codebase.
