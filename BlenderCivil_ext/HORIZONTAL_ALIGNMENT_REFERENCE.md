# Saikei Civil Horizontal Alignment - Complete Reference Guide

**Document Purpose:** Comprehensive reference for Claude Code when editing, debugging, or extending horizontal alignment functionality in Saikei Civil.

**Last Updated:** November 19, 2025  
**Status:** Production Reference  
**Scope:** Horizontal Alignment Creation, IFC Storage, Visualization, and Interaction

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Architecture Overview](#architecture-overview)
3. [IFC 4.3 Standard Compliance](#ifc-43-standard-compliance)
4. [Data Structures](#data-structures)
5. [Key Components](#key-components)
6. [Professional Workflows](#professional-workflows)
7. [Common Patterns](#common-patterns)
8. [Known Issues & Fixes](#known-issues--fixes)
9. [Testing Procedures](#testing-procedures)
10. [Integration Points](#integration-points)

---

## Core Principles

### 1. Native IFC Authoring Paradigm

**CRITICAL:** Saikei Civil is NOT an IFC exporter. It is a native IFC authoring tool.

```
❌ WRONG: Create data in memory → Export to IFC on save
✅ RIGHT: IFC file is the single source of truth from creation
```

**What this means:**
- IFC entities are created IMMEDIATELY when user places a PI
- All geometry data lives in IFC entities, not Python variables
- Blender objects are VISUALIZATION ONLY (linked to IFC via properties)
- Save operation = write IFC file (no conversion step)

**Code Implications:**
```python
# ❌ WRONG - Storing data in Python
self.pis = [(x, y, radius), ...]  # Data lost on reload!

# ✅ CORRECT - Data in IFC immediately
ifc_point = ifc.create_entity("IfcCartesianPoint", Coordinates=[x, y])
pi_data = {'ifc_point': ifc_point, 'position': Vector(x, y)}
```

### 2. PI-Driven Constraint-Based Geometry

**CRITICAL:** PIs (Points of Intersection) are the ONLY user-controlled geometry.

**Professional Civil Engineering Concepts:**

**What is a PI?**
- PI = Point where two tangent lines WOULD intersect (if extended)
- PIs have NO radius property (this was a past mistake - fixed!)
- PIs define bearing changes in the roadway
- User places PIs; system generates everything else

**What is a Curve?**
- A circular arc INSERTED between two tangents
- Curves have radius, BC (Begin Curve), EC (End Curve)
- Curves are SEPARATE from PIs (not "attached to" them)
- Tangents are TRIMMED when curves are inserted

**Constraint System:**
```
User places PIs (control points)
    ↓
System auto-generates tangent segments (LINE type)
    ↓
User optionally adds curves between tangents
    ↓
System calculates curve geometry and trims tangents
    ↓
Result: Connected alignment with geometric continuity
```

### 3. Separation of Concerns

**CRITICAL:** Clean separation between core logic, operators, and visualization.

```
core/
├── native_ifc_alignment.py     ← IFC operations, geometry math
├── alignment_visualizer.py     ← Blender visualization ONLY
└── alignment_registry.py       ← Tracks Python object instances

operators/
├── pi_operators.py             ← PI placement, editing
├── curve_operators.py          ← Curve insertion, editing
└── alignment_operators.py      ← Alignment creation, management

ui/
└── alignment_panel.py          ← Blender UI panels
```

**Never mix these concerns:**
- IFC operations should NOT import Blender operators
- Visualizers should NOT modify IFC directly
- Operators coordinate between IFC and visualization

---

## Architecture Overview

### System Flow

```
┌─────────────────┐
│  User Action    │  (Click to place PI, move marker, etc.)
└────────┬────────┘
         ↓
┌─────────────────┐
│  Blender        │  (Operator.execute(), Modal events)
│  Operator       │
└────────┬────────┘
         ↓
┌─────────────────┐
│  IFC File       │  (NativeIfcAlignment creates/updates entities)
│  Updated        │  ← SINGLE SOURCE OF TRUTH
└────────┬────────┘
         ↓
┌─────────────────┐
│  Visualization  │  (AlignmentVisualizer updates Blender objects)
│  Updated        │
└────────┬────────┘
         ↓
┌─────────────────┐
│  Blender Scene  │  (User sees updated geometry)
│  Refreshed      │
└─────────────────┘
```

### Key Classes & Responsibilities

#### NativeIfcManager (from Bonsai BIM pattern)
```python
# Location: core/native_ifc_alignment.py (top of file)
class NativeIfcManager:
    """Manages IFC file lifecycle and entity linking"""
    
    @staticmethod
    def new_file(name="Untitled"):
        """Create new IFC4X3_ADD2 file"""
    
    @staticmethod
    def get_file():
        """Get current active IFC file"""
    
    @staticmethod
    def get_entity(blender_obj):
        """Get IFC entity from Blender object"""
```

**Usage Pattern:**
```python
# Always start with this
ifc = NativeIfcManager.get_file()
if not ifc:
    # No IFC file loaded - create one or error
    pass
```

#### NativeIfcAlignment (Core Business Logic)
```python
# Location: core/native_ifc_alignment.py
class NativeIfcAlignment:
    """
    Manages PI-driven horizontal alignments in native IFC.
    
    Key Attributes:
        ifc: IfcOpenShell file object
        alignment: IfcAlignment entity
        horizontal: IfcAlignmentHorizontal entity
        pis: List[dict] - PI data with IFC entities
        segments: List[dict] - Segment data with IFC entities
    """
    
    def __init__(self, ifc_file, name="New Alignment"):
        self.ifc = ifc_file
        self.pis = []
        self.segments = []
        # Creates IfcAlignment and IfcAlignmentHorizontal
        self.create_alignment_structure(name)
    
    def add_pi(self, x, y):
        """
        Add PI at location (NO RADIUS PARAMETER!)
        
        Creates:
            - IfcCartesianPoint in IFC
            - Adds to self.pis list
            - Calls regenerate_segments()
        
        Returns: pi_data dict with IFC references
        """
    
    def regenerate_segments(self):
        """
        THE CORE METHOD - Generates all alignment geometry.
        
        Logic:
            1. Loop through PIs
            2. Create LINE segments between consecutive PIs
            3. If PI has curve, insert CIRCULARARC segment
            4. Trim adjacent tangents at BC/EC
            5. Update IFC relationships
        """
    
    def insert_curve_at_pi(self, pi_index, radius):
        """
        Add circular curve at PI (SEPARATE from PI creation!)
        
        Calculates:
            - Deflection angle from tangent bearings
            - Tangent length: T = R * tan(Δ/2)
            - Arc length: L = R * Δ
            - BC and EC points
        
        Updates:
            - pi_data['curve'] with curve geometry
            - Calls regenerate_segments()
        """
```

**CRITICAL Implementation Details:**

```python
# PI Structure (NO RADIUS!)
pi_data = {
    'id': 0,
    'position': SimpleVector(x, y),
    'ifc_point': ifc_entity,  # IfcCartesianPoint
    'curve': None,  # Populated if curve added
    'blender_object': None,  # Set by visualizer
    'connected_segments': {
        'incoming': None,  # Segment ID ending at this PI
        'outgoing': None   # Segment ID starting from this PI
    }
}

# Curve Structure (stored in pi_data['curve'])
curve_data = {
    'radius': 150.0,
    'deflection_angle': 0.785,  # radians
    'turn_direction': 'LEFT',  # or 'RIGHT'
    'tangent_length': 35.4,
    'arc_length': 117.8,
    'bc': SimpleVector(x1, y1),  # Begin Curve
    'ec': SimpleVector(x2, y2),  # End Curve
    'start_direction': 0.0,  # radians
    'end_direction': 0.785
}

# Segment Structure
segment = {
    'id': 0,
    'type': 'LINE',  # or 'CIRCULARARC'
    'start_point': SimpleVector(x1, y1),
    'end_point': SimpleVector(x2, y2),
    'length': 100.0,
    'ifc_segment': ifc_entity,  # IfcAlignmentSegment
    'blender_curve': None,  # Set by visualizer
    'dependencies': {
        'start_pi': 0,
        'end_pi': 1,
        'trimmed_by': 'curve_at_pi_1'
    }
}
```

#### AlignmentVisualizer (Blender Visualization)
```python
# Location: core/alignment_visualizer.py
class AlignmentVisualizer:
    """
    Creates and manages Blender visualization of IFC alignment.
    
    Key Principle: READ-ONLY view of IFC data!
    Does NOT modify IFC entities.
    """
    
    def __init__(self, native_alignment):
        self.alignment = native_alignment
        self.collection = None
        self.pi_objects = []
        self.segment_curves = []
    
    def create_pi_object(self, pi_data):
        """
        Create Blender Empty (sphere) for PI marker.
        
        Object Properties (for linking):
            - obj['ifc_pi_id'] = PI index
            - obj['ifc_alignment_id'] = Alignment IFC ID
        
        NO DATA STORED IN BLENDER OBJECT!
        All data comes from IFC.
        """
    
    def create_segment_curve(self, segment):
        """
        Create Blender Curve object for segment visualization.
        
        Color Coding:
            - Blue = Tangent (LINE)
            - Red = Curve (CIRCULARARC)
        
        Links to IFC:
            - obj['ifc_definition_id'] = Segment IFC ID
        """
    
    def update_all(self):
        """
        Refresh all visualizations after IFC changes.
        
        Called when:
            - PI moved
            - Curve added/edited
            - Segment regenerated
        """
```

#### Alignment Registry (Python Object Tracking)
```python
# Location: core/alignment_registry.py
# PURPOSE: Track Python object instances since IFC only stores IFC entities

_alignments = {}  # {global_id: NativeIfcAlignment instance}
_visualizers = {}  # {global_id: AlignmentVisualizer instance}

def get_or_create_alignment(ifc_entity):
    """Get existing or create new NativeIfcAlignment wrapper"""
    global_id = ifc_entity.GlobalId
    if global_id not in _alignments:
        alignment = NativeIfcAlignment.from_ifc_entity(ifc_entity)
        _alignments[global_id] = alignment
    return _alignments[global_id]
```

**Why needed:** Operators need to work with Python objects, but IFC file only stores IFC entities. Registry bridges this gap.

---

## IFC 4.3 Standard Compliance

### Required IFC Hierarchy

**From IFC 4.3 Specification:**

```
IfcProject
└─ IfcSite
   └─ IfcAlignment (GlobalId, Name)
      └─ IfcAlignmentHorizontal (via IfcRelNests)
         └─ [IfcAlignmentSegment]
            └─ DesignParameters: IfcAlignmentHorizontalSegment
```

**Our Implementation:**

```python
# Step 1: Create IfcAlignment
self.alignment = self.ifc.create_entity("IfcAlignment",
    GlobalId=ifcopenshell.guid.new(),
    Name=name,
    ObjectType="Horizontal Alignment"
)

# Step 2: Create IfcAlignmentHorizontal  
self.horizontal = self.ifc.create_entity("IfcAlignmentHorizontal",
    GlobalId=ifcopenshell.guid.new()
)

# Step 3: Link with IfcRelNests
self.ifc.create_entity("IfcRelNests",
    GlobalId=ifcopenshell.guid.new(),
    RelatingObject=self.alignment,
    RelatedObjects=[self.horizontal]
)
```

### Segment Types & Geometry

**From buildingSMART Documentation:**

| Business Logic (PredefinedType) | Should Have ParentCurve | What We Have |
|--------------------------------|-------------------------|--------------|
| LINE                           | IfcLine                 | ❌ Missing   |
| CIRCULARARC                    | IfcCircle               | ❌ Missing   |
| CLOTHOID (spiral)              | IfcClothoid             | ❌ Not impl. |

**IMPORTANT GAP:** We're currently only creating `IfcAlignmentHorizontalSegment` (business logic) without the geometric `ParentCurve` entities.

**What should happen (per IFC standard):**

```python
# 1. Create ParentCurve (geometric representation)
if segment_type == "LINE":
    parent_curve = ifc.create_entity("IfcLine",
        Pnt=ifc.create_entity("IfcCartesianPoint", 
            Coordinates=[start_x, start_y, 0]),
        Dir=ifc.create_entity("IfcVector",
            Orientation=ifc.create_entity("IfcDirection",
                DirectionRatios=[cos(angle), sin(angle), 0]),
            Magnitude=length
        )
    )

# 2. Create IfcCurveSegment (links semantic to geometric)
curve_segment = ifc.create_entity("IfcCurveSegment",
    Transition="CONTINUOUS",
    Placement=axis2placement,
    SegmentStart=0.0,
    SegmentLength=length,
    ParentCurve=parent_curve  # ← THE CRITICAL LINK!
)

# 3. Create IfcCompositeCurve (collection of segments)
composite_curve = ifc.create_entity("IfcCompositeCurve",
    Segments=[curve_segment1, curve_segment2, ...]
)

# 4. THEN create business logic (IfcAlignmentHorizontalSegment)
horizontal_segment = ifc.create_entity("IfcAlignmentHorizontalSegment",
    CurveGeometry=composite_curve,  # ← Link to geometry!
    PredefinedType="LINE",
    StartPoint=...,
    StartDirection=...,
    SegmentLength=...
)
```

**Current Implementation (Simplified):**

```python
# We're only doing step 4 - missing the geometric representation!
segment = self.ifc.create_entity("IfcAlignmentSegment",
    GlobalId=ifcopenshell.guid.new(),
    Name=f"Tangent_{i}",
    DesignParameters=self.ifc.create_entity(
        "IfcAlignmentHorizontalSegment",
        PredefinedType="LINE",
        StartPoint=...,
        StartDirection=...,
        SegmentLength=...
    )
)
```

**Impact:**
- ✅ Works for viewing in IFC viewers (they use DesignParameters)
- ✅ Works for Saikei Civil visualization
- ❌ May not work for advanced IFC operations that expect geometric representation
- 📋 TODO for Phase 2: Add full geometric representation

### Property Sets

**Standard Property Set (Pset_AlignmentDesign):**

```python
pset = ifc.create_entity("IfcPropertySet",
    GlobalId=ifcopenshell.guid.new(),
    Name="Pset_AlignmentDesign",
    Properties=[
        ifc.create_entity("IfcPropertySingleValue",
            Name="DesignSpeed",
            NominalValue=ifc.create_entity("IfcReal", 100.0)
        ),
        ifc.create_entity("IfcPropertySingleValue",
            Name="SuperelevationRate",
            NominalValue=ifc.create_entity("IfcReal", 0.0)
        ),
        ifc.create_entity("IfcPropertySingleValue",
            Name="SegmentType",
            NominalValue=ifc.create_entity("IfcLabel", "TANGENT")
        )
    ]
)

# Link to segment
ifc.create_entity("IfcRelDefinesByProperties",
    GlobalId=ifcopenshell.guid.new(),
    RelatedObjects=[segment],
    RelatingPropertyDefinition=pset
)
```

---

## Data Structures

### PI Data Dictionary

```python
{
    'id': int,                          # Index in pis list
    'position': SimpleVector,           # (x, y) coordinates
    'ifc_point': IfcCartesianPoint,    # IFC entity
    'curve': dict | None,               # Curve data if exists
    'blender_object': bpy.types.Object | None,  # Empty marker
    'connected_segments': {
        'incoming': int | None,         # Segment ID
        'outgoing': int | None          # Segment ID
    }
}
```

**Common Operations:**

```python
# Get PI position
pos = pi_data['position']  # SimpleVector(x, y)
x, y = pos.x, pos.y

# Check if PI has curve
if pi_data['curve']:
    radius = pi_data['curve']['radius']

# Get IFC entity
ifc_point = pi_data['ifc_point']
coords = ifc_point.Coordinates  # [x, y]

# Update Blender visualization
if pi_data['blender_object']:
    pi_data['blender_object'].location = (x, y, 0)
```

### Curve Data Dictionary

```python
{
    'radius': float,              # Curve radius in meters
    'deflection_angle': float,    # Radians (NOT degrees!)
    'turn_direction': str,        # 'LEFT' or 'RIGHT'
    'tangent_length': float,      # T = R * tan(Δ/2)
    'arc_length': float,          # L = R * Δ
    'bc': SimpleVector,           # Begin Curve point
    'ec': SimpleVector,           # End Curve point
    'start_direction': float,     # Bearing at BC (radians)
    'end_direction': float,       # Bearing at EC (radians)
    'center': SimpleVector        # Curve center point
}
```

**Civil Engineering Formulas:**

```python
# Deflection angle (from tangent vectors)
deflection = math.acos(t1.dot(t2))  # Result in radians

# Tangent length
tangent_length = radius * math.tan(deflection / 2)

# Arc length
arc_length = radius * deflection

# Determine turn direction (cross product)
cross = t1.x * t2.y - t1.y * t2.x
turn_direction = 'LEFT' if cross > 0 else 'RIGHT'
```

### Segment Data Dictionary

```python
{
    'id': int,                    # Unique segment ID
    'type': str,                  # 'LINE' or 'CIRCULARARC'
    'start_point': SimpleVector,  # Segment start
    'end_point': SimpleVector,    # Segment end
    'length': float,              # Segment length
    'ifc_segment': IfcAlignmentSegment,  # IFC entity
    'blender_curve': bpy.types.Object | None,  # Curve object
    'dependencies': {
        'start_pi': int,          # PI index at start
        'end_pi': int,            # PI index at end
        'trimmed_by': str | None  # 'curve_at_pi_X' if trimmed
    }
}
```

**For CIRCULARARC segments, additional fields:**

```python
{
    ...
    'radius': float,
    'deflection_angle': float,
    'bc': SimpleVector,
    'ec': SimpleVector,
    'center': SimpleVector
}
```

---

## Key Components

### File Locations

```
saikei/
├── core/
│   ├── native_ifc_alignment.py      ← Main alignment logic (625 lines)
│   │   ├── NativeIfcManager
│   │   ├── SimpleVector
│   │   └── NativeIfcAlignment
│   ├── alignment_visualizer.py      ← Blender visualization
│   └── alignment_registry.py        ← Python object tracking
│
├── operators/
│   ├── pi_operators.py              ← PI placement, editing
│   ├── curve_operators.py           ← Curve insertion (if separate)
│   └── alignment_operators.py       ← Create/manage alignments
│
└── ui/
    └── alignment_panel.py           ← Blender UI panels
```

### Critical Methods to Understand

#### 1. `NativeIfcAlignment.regenerate_segments()`

**Location:** `core/native_ifc_alignment.py` (~line 200)

**Purpose:** THE CORE METHOD that generates all alignment geometry from PIs.

**Logic Flow:**

```python
def regenerate_segments(self):
    """Generate all alignment segments from PIs"""
    
    # Clear existing segments
    self.segments = []
    
    # Need at least 2 PIs for segments
    if len(self.pis) < 2:
        return
    
    # Loop through PI pairs
    for i in range(len(self.pis) - 1):
        curr_pi = self.pis[i]
        next_pi = self.pis[i + 1]
        
        # Check if current PI has a curve
        if curr_pi.get('curve'):
            # THREE segments needed:
            # 1. Tangent from prev PI to BC
            # 2. Circular arc from BC to EC
            # 3. Tangent from EC to next PI
            
            curve_data = curr_pi['curve']
            
            # Tangent to BC
            if i == 0:
                start_pos = curr_pi['position']
            else:
                start_pos = prev_ec  # End of previous curve
            
            seg1 = self.create_line_segment(start_pos, curve_data['bc'])
            self.segments.append(seg1)
            
            # Curve segment
            seg2 = self.create_curve_segment(curve_data)
            self.segments.append(seg2)
            
            # Remember EC for next iteration
            prev_ec = curve_data['ec']
            
        else:
            # Simple tangent line
            if i == 0:
                start_pos = curr_pi['position']
            else:
                start_pos = prev_ec if prev_ec else curr_pi['position']
            
            seg = self.create_line_segment(start_pos, next_pi['position'])
            self.segments.append(seg)
    
    # Update IFC relationships
    self.update_ifc_nesting()
```

**Common Issues:**
- Forgetting to track `prev_ec` (end of previous curve)
- Not handling first PI specially
- Creating duplicate segments

#### 2. `NativeIfcAlignment.insert_curve_at_pi()`

**Location:** `core/native_ifc_alignment.py` (~line 350)

**Purpose:** Calculate and insert circular curve at PI.

**Mathematics:**

```python
def insert_curve_at_pi(self, pi_index, radius):
    """Insert circular curve at PI"""
    
    # Need 3 PIs for curve (prev, curr, next)
    if pi_index == 0 or pi_index >= len(self.pis) - 1:
        raise ValueError("Cannot add curve at first or last PI")
    
    prev_pi = self.pis[pi_index - 1]
    curr_pi = self.pis[pi_index]
    next_pi = self.pis[pi_index + 1]
    
    # Calculate tangent vectors
    t1 = (curr_pi['position'] - prev_pi['position']).normalized()
    t2 = (next_pi['position'] - curr_pi['position']).normalized()
    
    # Deflection angle (RADIANS!)
    deflection = math.acos(max(-1, min(1, t1.dot(t2))))
    
    # Tangent length: T = R * tan(Δ/2)
    tangent_length = radius * math.tan(deflection / 2)
    
    # BC = PI - T * t1
    bc = curr_pi['position'] - t1 * tangent_length
    
    # EC = PI + T * t2  
    ec = curr_pi['position'] + t2 * tangent_length
    
    # Arc length: L = R * Δ
    arc_length = radius * deflection
    
    # Turn direction (cross product)
    cross = t1.x * t2.y - t1.y * t2.x
    turn_direction = 'LEFT' if cross > 0 else 'RIGHT'
    
    # Calculate curve center
    # ... (perpendicular offset from PI)
    
    # Store curve data in PI
    curr_pi['curve'] = {
        'radius': radius,
        'deflection_angle': deflection,
        'tangent_length': tangent_length,
        'arc_length': arc_length,
        'bc': bc,
        'ec': ec,
        'turn_direction': turn_direction,
        'center': center,
        'start_direction': math.atan2(t1.y, t1.x),
        'end_direction': math.atan2(t2.y, t2.x)
    }
    
    # Regenerate all segments
    self.regenerate_segments()
```

**CRITICAL MATH NOTES:**
- `math.acos()` expects value in range [-1, 1], use `max(-1, min(1, value))`
- Deflection angle is in RADIANS (not degrees)
- BC and EC are calculated using VECTOR MATH, not just coordinates
- Cross product determines left/right turn (sign matters!)

#### 3. `AlignmentVisualizer.create_pi_object()`

**Location:** `core/alignment_visualizer.py` (~line 80)

**Purpose:** Create Blender Empty marker for PI visualization.

```python
def create_pi_object(self, pi_data):
    """Create PI marker in Blender"""
    
    # Create Empty object (sphere display)
    obj = bpy.data.objects.new(f"PI_{pi_data['id']:03d}", None)
    obj.empty_display_type = 'SPHERE'
    obj.empty_display_size = 3.0
    
    # Set position (2D → 3D with Z=0)
    pos = pi_data['position']
    obj.location = (pos.x, pos.y, 0)
    
    # Link to IFC data (ONLY store IDs, not data!)
    obj['ifc_pi_id'] = pi_data['id']
    obj['ifc_alignment_id'] = self.alignment.alignment.id()
    
    # Color: All PIs are green now (no radius-based coloring)
    obj.color = (0.0, 1.0, 0.0, 1.0)  # Green
    
    # Add to collection
    self.collection.objects.link(obj)
    
    # Store reference in pi_data for updates
    pi_data['blender_object'] = obj
    
    return obj
```

**CRITICAL:** Only store linking IDs in Blender object properties! Never duplicate data.

#### 4. Modal Operator Pattern (Interactive PI Placement)

**Location:** `operators/pi_operators.py`

**Purpose:** Handle user mouse clicks to place PIs interactively.

```python
class BC_OT_add_pi_interactive(bpy.types.Operator):
    """Interactive PI placement operator"""
    bl_idname = "saikei.add_pi_interactive"
    bl_label = "Click to Place PIs"
    
    def invoke(self, context, event):
        """Start modal operation"""
        
        # Get or create alignment instance
        ifc_entity = get_active_alignment_entity()
        self.alignment = get_or_create_alignment(ifc_entity)
        self.visualizer = get_or_create_visualizer(self.alignment)
        
        # Track placed points
        self._points_placed = []
        
        # Start modal
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        """Handle mouse events"""
        
        # Left click = place PI
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Get 3D location from mouse
            location = self.get_3d_location_from_mouse(context, event)
            
            # Add PI immediately (creates IFC entity!)
            self.add_pi_at_location(location)
            
            return {'RUNNING_MODAL'}
        
        # Right click or Enter = finish
        elif event.type in {'RIGHTMOUSE', 'RET'}:
            return self.finish(context)
        
        # ESC = cancel
        elif event.type == 'ESC':
            return self.cancel(context)
        
        return {'RUNNING_MODAL'}
    
    def add_pi_at_location(self, location):
        """Add PI at location with immediate visualization"""
        
        # 1. Add to IFC (creates entity immediately!)
        pi_data = self.alignment.add_pi(location.x, location.y)
        
        # 2. Create visualization immediately
        pi_marker = self.visualizer.create_pi_object(pi_data)
        
        # 3. If we have 2+ PIs, create tangent line
        if len(self.alignment.pis) >= 2:
            last_segment = self.alignment.segments[-1]
            self.visualizer.create_segment_curve(last_segment)
        
        # Track placement
        self._points_placed.append(pi_data)
```

**KEY INSIGHT:** With native IFC, we create IFC entities AND visualization on EACH CLICK, not at the end!

---

## Professional Workflows

### Workflow 1: Create New Horizontal Alignment

**User Steps:**
1. Click "Create Horizontal Alignment"
2. Enter alignment name
3. Alignment created in IFC file

**Code Flow:**

```python
# operators/alignment_operators.py
class BC_OT_create_horizontal_alignment(bpy.types.Operator):
    
    def execute(self, context):
        # 1. Get or create IFC file
        ifc = NativeIfcManager.get_file()
        if not ifc:
            ifc = NativeIfcManager.new_file()
        
        # 2. Create alignment (IFC entities created!)
        alignment = NativeIfcAlignment(ifc, name=self.alignment_name)
        
        # 3. Register instance
        register_alignment(alignment)
        
        # 4. Create visualizer
        visualizer = AlignmentVisualizer(alignment)
        register_visualizer(visualizer, alignment.alignment.GlobalId)
        
        # 5. Store reference in scene
        context.scene.active_alignment_id = alignment.alignment.GlobalId
        
        return {'FINISHED'}
```

### Workflow 2: Place PIs Interactively

**User Steps:**
1. Click "Click to Place PIs"
2. Left-click in viewport to place each PI
3. See PI marker appear immediately
4. See tangent line appear between consecutive PIs
5. Press Enter or Right-click to finish

**Code Flow:**

```
User left-clicks
    ↓
modal() captures LEFTMOUSE event
    ↓
get_3d_location_from_mouse() - Raycast to XY plane
    ↓
add_pi_at_location()
    ├─ alignment.add_pi(x, y)
    │  ├─ Creates IfcCartesianPoint
    │  ├─ Adds to pis list
    │  └─ Calls regenerate_segments()
    │     └─ Creates IfcAlignmentSegment (LINE) if 2+ PIs
    │
    └─ visualizer.create_pi_object(pi_data)
       ├─ Creates Blender Empty (green sphere)
       ├─ Links to IFC via properties
       └─ If 2+ PIs:
          └─ visualizer.create_segment_curve(last_segment)
             └─ Creates Blender Curve (blue line)
```

**Result:** Real-time visualization as user places PIs!

### Workflow 3: Add Curve Between Tangents

**User Steps:**
1. Click "Add Curve"
2. Click first tangent segment
3. Click second tangent segment (must be adjacent)
4. Enter radius in dialog
5. See curve appear, tangents trim

**Code Flow:**

```python
# operators/curve_operators.py (if separate)
class BC_OT_add_curve_interactive(bpy.types.Operator):
    
    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Get clicked object
            obj = raycast_to_object(context, event)
            
            if obj and 'ifc_definition_id' in obj:
                # Get segment from IFC
                segment = get_segment_from_obj(obj)
                
                if not self.first_segment:
                    self.first_segment = segment
                    # Highlight in viewport
                    obj.color = (1, 1, 0, 1)  # Yellow
                else:
                    self.second_segment = segment
                    
                    # Check adjacency
                    if self.are_adjacent(self.first_segment, self.second_segment):
                        # Open radius dialog
                        bpy.ops.saikei.enter_curve_radius('INVOKE_DEFAULT')
                    else:
                        self.report({'ERROR'}, "Segments must be adjacent!")
            
            return {'RUNNING_MODAL'}
    
    def add_curve_with_radius(self, radius):
        """Called after dialog closes with radius value"""
        
        # Find PI between the two segments
        pi_index = self.get_pi_between_segments(
            self.first_segment, self.second_segment
        )
        
        # Insert curve in IFC
        self.alignment.insert_curve_at_pi(pi_index, radius)
        
        # Update visualization
        self.visualizer.update_all()
```

### Workflow 4: Move PI (Real-Time Updates)

**User Steps:**
1. Select PI marker (Empty sphere)
2. Press G to move (Blender standard)
3. Move mouse
4. Click to confirm

**Code Flow (with update handler):**

```python
# core/alignment_update_handler.py
@persistent
def alignment_update_handler(scene, depsgraph):
    """Called by Blender when objects change"""
    
    for update in depsgraph.updates:
        obj = update.id
        
        # Check if it's a PI marker
        if isinstance(obj, bpy.types.Object) and 'ifc_pi_id' in obj:
            # Get alignment instance
            alignment_id = obj['ifc_alignment_id']
            alignment = get_alignment(alignment_id)
            
            if alignment and alignment.auto_update:
                # Get PI data
                pi_id = obj['ifc_pi_id']
                pi_data = alignment.pis[pi_id]
                
                # Update position in IFC
                new_pos = obj.location
                pi_data['position'].x = new_pos.x
                pi_data['position'].y = new_pos.y
                
                # Update IFC entity
                ifc_point = pi_data['ifc_point']
                ifc_point.Coordinates = [new_pos.x, new_pos.y]
                
                # Regenerate geometry
                alignment.regenerate_segments()
                
                # Update visualization
                visualizer = get_visualizer(alignment_id)
                if visualizer:
                    visualizer.update_all()
```

**Result:** As user drags PI marker, tangents and curves update in real-time!

---

## Common Patterns

### Pattern 1: Get Active Alignment

```python
def get_active_alignment():
    """Get the currently active alignment instance"""
    
    # Option A: From scene property
    active_id = bpy.context.scene.get('active_alignment_id')
    if active_id:
        alignment = get_alignment(active_id)
        if alignment:
            return alignment
    
    # Option B: From selected object
    obj = bpy.context.active_object
    if obj and 'ifc_alignment_id' in obj:
        alignment_id = obj['ifc_alignment_id']
        return get_alignment(alignment_id)
    
    # Option C: Get first alignment in IFC file
    ifc = NativeIfcManager.get_file()
    if ifc:
        alignments = ifc.by_type("IfcAlignment")
        if alignments:
            return get_or_create_alignment(alignments[0])
    
    return None
```

### Pattern 2: Safe IFC Entity Access

```python
def safe_get_entity_property(entity, property_name, default=None):
    """Safely access IFC entity property"""
    try:
        value = getattr(entity, property_name, None)
        return value if value is not None else default
    except:
        return default

# Usage
design_speed = safe_get_entity_property(segment, 'DesignSpeed', 100.0)
```

### Pattern 3: Coordinate Between IFC and Blender

```python
def update_from_ifc_to_blender(alignment, visualizer):
    """Update Blender visualization from IFC data"""
    
    # Update PI markers
    for pi_data in alignment.pis:
        if pi_data['blender_object']:
            obj = pi_data['blender_object']
            pos = pi_data['position']
            obj.location = (pos.x, pos.y, 0)
    
    # Regenerate segment curves
    visualizer.update_segment_curves()

def update_from_blender_to_ifc(alignment, pi_id):
    """Update IFC data from Blender object position"""
    
    pi_data = alignment.pis[pi_id]
    obj = pi_data['blender_object']
    
    if obj:
        # Update our data structure
        pi_data['position'].x = obj.location.x
        pi_data['position'].y = obj.location.y
        
        # Update IFC entity
        ifc_point = pi_data['ifc_point']
        ifc_point.Coordinates = [obj.location.x, obj.location.y]
        
        # Regenerate geometry
        alignment.regenerate_segments()
```

### Pattern 4: Error Handling Template

```python
def safe_alignment_operation(context):
    """Template for operations that might fail"""
    try:
        # 1. Check prerequisites
        ifc = NativeIfcManager.get_file()
        if not ifc:
            self.report({'ERROR'}, "No IFC file loaded")
            return {'CANCELLED'}
        
        alignment = get_active_alignment()
        if not alignment:
            self.report({'ERROR'}, "No active alignment")
            return {'CANCELLED'}
        
        # 2. Perform operation
        result = alignment.some_operation()
        
        # 3. Update visualization
        visualizer = get_visualizer(alignment.alignment.GlobalId)
        if visualizer:
            visualizer.update_all()
        
        # 4. Confirm success
        self.report({'INFO'}, "Operation completed")
        return {'FINISHED'}
        
    except ValueError as e:
        self.report({'ERROR'}, f"Invalid value: {str(e)}")
        return {'CANCELLED'}
    except Exception as e:
        self.report({'ERROR'}, f"Operation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'CANCELLED'}
```

---

## Known Issues & Fixes

### Issue 1: Modal Operator Gets Stuck

**Symptom:** Click "Click to Place PIs", but can't exit modal mode. ESC doesn't work.

**Root Cause:** Modal operator not properly returning from `modal()` method.

**Fix:**

```python
def modal(self, context, event):
    # ALWAYS return a status set
    if event.type == 'ESC':
        return {'CANCELLED'}  # ✅ Correct
        # return None  # ❌ WRONG - causes stuck modal
    
    return {'RUNNING_MODAL'}  # ✅ Always return something
```

**Prevention:** Always test ESC key exit path!

### Issue 2: PIs Have Radius (Conceptually Wrong)

**Symptom:** Old code had `radius` property on PI objects.

**Why It's Wrong:** 
- PIs are intersection points (just X, Y coordinates)
- Curves are separate geometric elements with radius
- Mixing concepts makes code confusing

**Fix Applied:** Removed `radius` from PI structure, moved to separate `curve_data`.

**If You See This:**

```python
# ❌ WRONG (old code)
pi_data = {'position': (x, y), 'radius': 150}

# ✅ CORRECT (current code)
pi_data = {
    'position': SimpleVector(x, y),
    'curve': {
        'radius': 150,
        ...
    } if has_curve else None
}
```

### Issue 3: Visualization Not Updating

**Symptom:** Move a PI marker, but tangent lines don't update.

**Cause:** Update handler not registered or auto_update disabled.

**Fix:**

```python
# Check if handler is registered
from saikei.core.alignment_update_handler import AlignmentUpdateHandler

if alignment_update_handler not in bpy.app.handlers.depsgraph_update_post:
    AlignmentUpdateHandler.register()

# Check if auto-update is enabled
alignment = get_active_alignment()
if not alignment.auto_update:
    alignment.auto_update = True
```

### Issue 4: IFC File Not Saving

**Symptom:** Make changes, click save, but .ifc file doesn't update.

**Cause:** Not calling IFC write operation.

**Fix:**

```python
# Ensure save operator writes IFC file
class BC_OT_save_ifc(bpy.types.Operator):
    def execute(self, context):
        ifc = NativeIfcManager.get_file()
        if not ifc:
            return {'CANCELLED'}
        
        filepath = context.scene.get('ifc_filepath')
        if not filepath:
            # Open file browser
            bpy.ops.saikei.save_ifc_as('INVOKE_DEFAULT')
            return {'FINISHED'}
        
        # Write IFC file
        ifc.write(filepath)
        self.report({'INFO'}, f"Saved to {filepath}")
        return {'FINISHED'}
```

### Issue 5: Circular Import Errors

**Symptom:** `ImportError: cannot import name 'X' from partially initialized module`

**Cause:** Circular dependencies between modules.

**Fix:**

```python
# ❌ WRONG - Importing at module level
from .alignment_visualizer import AlignmentVisualizer

class NativeIfcAlignment:
    def __init__(self):
        self.visualizer = AlignmentVisualizer(self)

# ✅ CORRECT - Import inside method
class NativeIfcAlignment:
    def create_visualizer(self):
        from .alignment_visualizer import AlignmentVisualizer
        self.visualizer = AlignmentVisualizer(self)
```

**Or use TYPE_CHECKING:**

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .alignment_visualizer import AlignmentVisualizer

class NativeIfcAlignment:
    visualizer: 'AlignmentVisualizer' = None  # String annotation
```

### Issue 6: Curve Calculation Fails with `math.acos()` Error

**Symptom:** `ValueError: math domain error` when inserting curve.

**Cause:** Dot product outside valid range [-1, 1] due to floating-point precision.

**Fix:**

```python
# ❌ WRONG - Can fail with precision errors
deflection = math.acos(t1.dot(t2))

# ✅ CORRECT - Clamp to valid range
dot_product = t1.dot(t2)
dot_product = max(-1.0, min(1.0, dot_product))  # Clamp to [-1, 1]
deflection = math.acos(dot_product)
```

### Issue 7: Segments Not Appearing in IFC Viewers

**Symptom:** IFC file opens, but no geometry visible.

**Cause:** Missing `IfcRelNests` relationships or incorrect hierarchy.

**Fix:**

```python
def update_ifc_nesting(self):
    """Ensure all segments are properly nested"""
    
    # Remove old nesting
    for rel in self.ifc.by_type("IfcRelNests"):
        if rel.RelatingObject == self.horizontal:
            self.ifc.remove(rel)
    
    # Create new nesting
    if self.segments:
        segment_entities = [seg['ifc_segment'] for seg in self.segments]
        self.ifc.create_entity("IfcRelNests",
            GlobalId=ifcopenshell.guid.new(),
            RelatingObject=self.horizontal,
            RelatedObjects=segment_entities
        )
```

---

## Testing Procedures

### Unit Test Template

```python
import unittest
import ifcopenshell
from saikei.core.native_ifc_alignment import NativeIfcAlignment

class TestHorizontalAlignment(unittest.TestCase):
    
    def setUp(self):
        """Create test IFC file"""
        self.ifc = ifcopenshell.file(schema="IFC4X3_ADD2")
        self.alignment = NativeIfcAlignment(self.ifc, "Test Alignment")
    
    def test_add_pi_creates_ifc_entity(self):
        """Test that adding PI creates IFC entity"""
        pi_data = self.alignment.add_pi(0, 0)
        
        self.assertIsNotNone(pi_data['ifc_point'])
        self.assertEqual(pi_data['ifc_point'].Coordinates, [0, 0])
    
    def test_two_pis_create_tangent(self):
        """Test that 2 PIs generate tangent segment"""
        self.alignment.add_pi(0, 0)
        self.alignment.add_pi(100, 0)
        
        self.assertEqual(len(self.alignment.segments), 1)
        self.assertEqual(self.alignment.segments[0]['type'], 'LINE')
    
    def test_curve_insertion(self):
        """Test curve insertion between tangents"""
        self.alignment.add_pi(0, 0)
        self.alignment.add_pi(100, 0)
        self.alignment.add_pi(200, 100)
        
        # Insert curve at middle PI
        self.alignment.insert_curve_at_pi(1, 150.0)
        
        self.assertIsNotNone(self.alignment.pis[1]['curve'])
        self.assertEqual(self.alignment.pis[1]['curve']['radius'], 150.0)
```

### Integration Test Procedure

**Manual Testing Workflow:**

1. **Fresh Start**
   - File → New → General
   - Install Saikei Civil addon
   - Open Python Console

2. **Create Alignment**
   ```python
   import bpy
   bpy.ops.saikei.create_horizontal_alignment(name="Test")
   ```
   - ✅ Check: Alignment appears in outliner
   - ✅ Check: IFC file created (scene property)

3. **Place PIs**
   ```python
   bpy.ops.saikei.add_pi_interactive('INVOKE_DEFAULT')
   ```
   - Click 4 points in viewport
   - ✅ Check: Green sphere appears at each click
   - ✅ Check: Blue lines connect consecutive points
   - Press Enter

4. **Add Curve**
   ```python
   bpy.ops.saikei.add_curve_interactive('INVOKE_DEFAULT')
   ```
   - Click first tangent
   - Click adjacent tangent
   - Enter radius: 150
   - ✅ Check: Red curve appears
   - ✅ Check: Blue tangents trimmed at BC/EC

5. **Move PI**
   - Select PI marker
   - Press G, move mouse
   - ✅ Check: Tangents update in real-time
   - ✅ Check: Curve updates if PI has curve

6. **Save IFC**
   ```python
   bpy.ops.saikei.save_ifc_file()
   ```
   - ✅ Check: .ifc file written to disk
   - Open in IFC viewer (e.g., BlenderBIM)
   - ✅ Check: Alignment geometry visible

7. **Reload**
   - Close Blender (don't save .blend)
   - Reopen Blender
   - Load .ifc file
   - ✅ Check: All PIs restored
   - ✅ Check: All segments restored
   - ✅ Check: Geometry matches original

### Validation Checks

```python
def validate_alignment(alignment):
    """Comprehensive alignment validation"""
    
    issues = []
    
    # Check IFC hierarchy
    if not alignment.alignment:
        issues.append("Missing IfcAlignment entity")
    
    if not alignment.horizontal:
        issues.append("Missing IfcAlignmentHorizontal entity")
    
    # Check nesting
    rels = [r for r in alignment.ifc.by_type("IfcRelNests")
            if r.RelatingObject == alignment.horizontal]
    if not rels:
        issues.append("Missing IfcRelNests relationship")
    
    # Check geometric continuity
    for i in range(len(alignment.segments) - 1):
        seg1 = alignment.segments[i]
        seg2 = alignment.segments[i + 1]
        
        gap = seg1['end_point'].distance_to(seg2['start_point'])
        if gap > 0.001:  # 1mm tolerance
            issues.append(f"Gap between segments {i} and {i+1}: {gap}m")
    
    # Check curve geometry
    for pi_data in alignment.pis:
        if pi_data.get('curve'):
            curve = pi_data['curve']
            
            # Validate deflection angle
            if curve['deflection_angle'] <= 0:
                issues.append(f"Invalid deflection angle at PI {pi_data['id']}")
            
            # Validate tangent length
            expected_t = curve['radius'] * math.tan(curve['deflection_angle'] / 2)
            if abs(curve['tangent_length'] - expected_t) > 0.001:
                issues.append(f"Incorrect tangent length at PI {pi_data['id']}")
    
    return issues

# Usage
issues = validate_alignment(alignment)
if issues:
    for issue in issues:
        print(f"⚠️ {issue}")
else:
    print("✅ Alignment validation passed!")
```

---

## Integration Points

### Vertical Alignment Integration (Sprint 3)

**Connection Point:** Station-based referencing

```python
# Horizontal alignment provides baseline
horizontal = NativeIfcAlignment(ifc, "Highway 101 H")

# Vertical alignment references horizontal
vertical = NativeIfcVerticalAlignment(ifc, horizontal, "Highway 101 V")

# Link in IFC
ifc.create_entity("IfcRelNests",
    RelatingObject=horizontal.alignment,
    RelatedObjects=[vertical.vertical_alignment]
)
```

**Shared Concepts:**
- Station values (distance along horizontal)
- PI-driven design (PVIs for vertical)
- Constraint-based geometry
- Native IFC storage

### Georeferencing Integration (Sprint 2)

**Connection Point:** Map coordinates for PIs

```python
class NativeIfcAlignmentGeo(NativeIfcAlignment):
    """Horizontal alignment with georeferencing"""
    
    def __init__(self, ifc_file, name="New Alignment"):
        super().__init__(ifc_file, name)
        self.georef = NativeIfcGeoreferencing(ifc_file)
    
    def add_pi_map_coords(self, easting, northing, elevation=0):
        """Add PI using map coordinates"""
        
        # Convert to local
        local = self.georef.map_to_local((easting, northing, elevation))
        
        # Add PI in local space
        pi_data = self.add_pi(local[0], local[1])
        
        # Store map coordinates in property set
        self.add_map_properties(pi_data, easting, northing, elevation)
        
        return pi_data
```

### Cross-Section Integration (Sprint 4)

**Connection Point:** Station-based cross-section placement

```python
# Apply cross-section at specific station
cross_section = CrossSection.from_template("AASHTO_2Lane")

# Place along alignment
for station in range(0, int(alignment.total_length), 25):
    # Get position and bearing at station
    pos, bearing = alignment.get_position_at_station(station)
    
    # Apply cross-section perpendicular to alignment
    cross_section.apply_at_station(station, pos, bearing)
```

### Corridor Integration (Sprint 5)

**Connection Point:** Sweep cross-sections along alignment

```python
# Create corridor from alignment + cross-sections
corridor = CorridorModeler(alignment, cross_sections)

# Generate 3D mesh
mesh = corridor.generate_mesh(lod='medium')

# Export as IfcSectionedSolidHorizontal
corridor.export_to_ifc()
```

---

## Debugging Checklist

When things go wrong, check these in order:

### 1. IFC File Status
```python
ifc = NativeIfcManager.get_file()
print(f"IFC File: {ifc}")
print(f"Schema: {ifc.schema if ifc else 'None'}")
print(f"Entities: {len(ifc) if ifc else 0}")
```

### 2. Alignment Instance
```python
alignment = get_active_alignment()
print(f"Alignment: {alignment}")
if alignment:
    print(f"PIs: {len(alignment.pis)}")
    print(f"Segments: {len(alignment.segments)}")
    print(f"IFC Entity: {alignment.alignment}")
```

### 3. Visualizer Status
```python
if alignment:
    visualizer = get_visualizer(alignment.alignment.GlobalId)
    print(f"Visualizer: {visualizer}")
    if visualizer:
        print(f"PI Objects: {len(visualizer.pi_objects)}")
        print(f"Segment Curves: {len(visualizer.segment_curves)}")
        print(f"Collection: {visualizer.collection}")
```

### 4. Update Handler
```python
from saikei.core.alignment_update_handler import alignment_update_handler

handlers = bpy.app.handlers.depsgraph_update_post
is_registered = alignment_update_handler in handlers
print(f"Update Handler Registered: {is_registered}")

if alignment:
    print(f"Auto-Update Enabled: {alignment.auto_update}")
```

### 5. Console Output
Enable Python console output in Blender:
- Window → Toggle System Console (Windows)
- Check terminal (Linux/Mac)

Add debug prints strategically:

```python
def regenerate_segments(self):
    print(f"🔧 Regenerating segments for {len(self.pis)} PIs")
    
    for i, pi in enumerate(self.pis):
        print(f"  PI {i}: {pi['position']}, Curve: {pi.get('curve') is not None}")
    
    # ... regeneration logic ...
    
    print(f"✅ Generated {len(self.segments)} segments")
```

### 6. Blender Info Area
Check the Info area (usually hidden) for warnings:
- View → Area → Information
- Look for Python errors or warnings

---

## Quick Reference Card

**Essential Functions:**

```python
# Get IFC file
ifc = NativeIfcManager.get_file()

# Get active alignment
alignment = get_active_alignment()

# Add PI (NO RADIUS!)
pi_data = alignment.add_pi(x, y)

# Insert curve at PI
alignment.insert_curve_at_pi(pi_index=1, radius=150.0)

# Regenerate segments
alignment.regenerate_segments()

# Update visualization
visualizer = get_visualizer(alignment.alignment.GlobalId)
visualizer.update_all()

# Save IFC
ifc.write(filepath)
```

**Common Properties:**

```python
# PI data
pi['position']        # SimpleVector(x, y)
pi['ifc_point']       # IfcCartesianPoint
pi['curve']           # dict or None
pi['blender_object']  # Empty marker

# Curve data
curve['radius']       # float
curve['bc']          # SimpleVector (Begin Curve)
curve['ec']          # SimpleVector (End Curve)
curve['deflection_angle']  # radians

# Segment data
seg['type']          # 'LINE' or 'CIRCULARARC'
seg['start_point']   # SimpleVector
seg['end_point']     # SimpleVector
seg['length']        # float
seg['ifc_segment']   # IfcAlignmentSegment
```

---

## Document Maintenance

**When to Update This Document:**

- ✅ When adding new PI operators
- ✅ When changing alignment data structures
- ✅ When fixing bugs (add to Known Issues)
- ✅ When discovering new IFC compliance issues
- ✅ When integration points change

**How to Update:**

1. Search for relevant section
2. Add new information under appropriate heading
3. Update code examples if API changed
4. Add cross-references if needed
5. Update Table of Contents if structure changed

**Document Owner:** Michael (Saikei Civil project lead)

**Review Frequency:** After each sprint or major feature addition

---

## Additional Resources

**IFC Standards:**
- [IFC 4.3 Specification](https://ifc43-docs.standards.buildingsmart.org/)
- [buildingSMART Alignment Guide](https://github.com/buildingSMART/ProductData-IFC)
- Project file: `/mnt/project/1_Introduction.md` through `/mnt/project/9_Precision_and_Tolerance.md`

**Saikei Civil Documentation:**
- Sprint summaries in `/mnt/project/Sprint1_*_Summary.md`
- Architecture decisions in `/mnt/project/*_Architecture.md`
- Professional patterns in `/mnt/project/Professional_*.md`

**Debugging:**
- `/mnt/project/TROUBLESHOOTING_GUIDE.md`
- `/mnt/project/Integration_Guide.md`

**Related Systems:**
- Vertical Alignments: `/mnt/project/Saikei Civil_Developer_API_Vertical_Alignments.md`
- Georeferencing: `/mnt/project/Saikei Civil_Georeferencing_Developer_API.md`

---

**End of Reference Document**

*This document captures the knowledge built over Sprint 0 and Sprint 1 of the Saikei Civil Native IFC implementation. Use it as your primary reference when working with horizontal alignment code.*
