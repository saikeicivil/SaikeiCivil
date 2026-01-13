# Saikei Civil: Parametric Control Module
## Complete Implementation Reference for Claude Code

**Document Purpose:** Comprehensive knowledge base for implementing parametric constraints in Saikei Civil, including architectural decisions, IFC storage patterns, and integration with existing systems.

**Last Updated:** December 22, 2025  
**Target Sprint:** Phase 2 Enhancement (Post-Sprint 5)  
**Status:** Architecture Defined, Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [CRITICAL: Bonsai 3-Layer Architecture](#critical-bonsai-3-layer-architecture)
3. [Key Architectural Decisions](#key-architectural-decisions)
4. [OpenRoads-Style Constraint System](#openroads-style-constraint-system)
5. [IFC Storage Strategy](#ifc-storage-strategy)
6. [Cross Section Viewer Integration](#cross-section-viewer-integration)
7. [Implementation Architecture](#implementation-architecture)
8. [Data Structures](#data-structures)
9. [IFC Property Set Design](#ifc-property-set-design)
10. [External References](#external-references)
11. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

The Parametric Control Module enables station-based parameter variation for roadway cross-sections in Saikei Civil. This allows engineers to define width transitions, superelevation changes, and other cross-section modifications that vary along the alignment corridor.

### Core Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Implementation Approach** | Python + GUI | Professional software standard, engineering precision |
| **NOT Using** | Geometry Nodes | Complex debugging, difficult validation |
| **Constraint Style** | OpenRoads-style | More powerful than Civil 3D regions |
| **Data Storage** | IFC Property Sets | Native IFC, interoperable, simple |
| **UI Location** | Cross Section Viewer Panel | Leverage existing infrastructure |
| **Code Architecture** | Bonsai 3-Layer | Core/Tool/UI separation for testability |

---

## CRITICAL: Bonsai 3-Layer Architecture

**THIS IS MANDATORY FOR ALL SAIKEI CIVIL CODE**

Saikei Civil follows the same 3-layer architecture used by Bonsai BIM. This separation ensures testability, maintainability, and clean code organization. All code must follow this pattern.

### The Three Layers

```
+------------------------------------------------------------------+
|  LAYER 3: UI (User Interface)                                    |
|  Location: ui/ and ui/panels/                                    |
|  Contents: Panels, PropertyGroups, UILists                       |
|  Dependencies: Can import from Tool layer and Core layer         |
|  Blender-Specific: YES - Uses bpy.types, PropertyGroup, Panel    |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|  LAYER 2: TOOL (Operators & Blender Integration)                 |
|  Location: operators/                                            |
|  Contents: Operators, Blender-specific workflows                 |
|  Dependencies: Can import from Core layer only                   |
|  Blender-Specific: YES - Uses bpy.types.Operator, context        |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|  LAYER 1: CORE (Pure Python Business Logic)                      |
|  Location: core/                                                 |
|  Contents: Data classes, managers, calculations, IFC operations  |
|  Dependencies: NONE from Tool or UI layers                       |
|  Blender-Specific: NO - Pure Python, testable without Blender    |
+------------------------------------------------------------------+
```

### Layer Rules (MUST FOLLOW)

**Core Layer (core/):**
- Pure Python - NO bpy imports allowed
- Contains all business logic, calculations, data structures
- Contains all IFC read/write operations (using ifcopenshell)
- Can be tested without Blender running
- Example classes: `ParametricConstraint`, `ConstraintManager`, `ConstraintIFCHandler`

**Tool Layer (operators/):**
- Blender Operators that call Core layer functions
- Thin wrappers - minimal logic, delegates to Core
- Handles Blender context, selection, undo
- Example: `BC_OT_add_parametric_constraint` calls `ConstraintManager.add_constraint()`

**UI Layer (ui/):**
- PropertyGroups for data binding
- Panels for display
- UILists for collections
- Converts between Blender properties and Core data structures
- Example: `BC_ConstraintProperties`, `BC_PT_ParametricConstraintsPanel`

### Why This Matters

1. **Testability:** Core layer can be unit tested without Blender
2. **Maintainability:** Clear separation of concerns
3. **Reusability:** Core logic can be used by multiple operators/panels
4. **Consistency:** Matches Bonsai BIM patterns (familiar to contributors)
5. **Debugging:** Easier to isolate issues to specific layers

### Code Flow Example

```python
# USER CLICKS "Add Constraint" BUTTON

# UI Layer (panel) - Button definition
class BC_PT_ConstraintsPanel(Panel):
    def draw(self, context):
        layout.operator("bc.add_parametric_constraint")

# Tool Layer (operator) - Handles the click
class BC_OT_add_parametric_constraint(Operator):
    def execute(self, context):
        # Get data from UI properties
        props = context.scene.bc_cross_section
        
        # Create Core layer object
        constraint = ParametricConstraint(
            id=str(uuid.uuid4()),
            component_name=props.new_constraint_component,
            parameter_name=props.new_constraint_parameter,
            # ... etc
        )
        
        # Call Core layer method
        manager = get_constraint_manager()
        manager.add_constraint(constraint)
        
        # Update IFC (Core layer)
        handler = ConstraintIFCHandler(get_ifc_file())
        handler.export_constraints(manager, get_road_entity())
        
        return {'FINISHED'}

# Core Layer - Pure Python, no bpy
class ConstraintManager:
    def add_constraint(self, constraint: ParametricConstraint) -> None:
        """Add constraint and sort by station"""
        self.constraints.append(constraint)
        self.constraints.sort(key=lambda c: c.start_station)
```

### Layer Compliance Checklist

Before committing any code, verify:

**Core Layer Files (core/):**
- [ ] No `import bpy` statements anywhere
- [ ] No Blender types (Operator, Panel, PropertyGroup)
- [ ] All functions can be called without Blender running
- [ ] Unit tests run with pytest (no Blender required)

**Tool Layer Files (operators/):**
- [ ] Only imports from core/ (never from ui/)
- [ ] Operators are thin wrappers calling core functions
- [ ] All business logic delegated to core layer
- [ ] Handles Blender context appropriately

**UI Layer Files (ui/):**
- [ ] PropertyGroups mirror core data structures
- [ ] Panels only display data and call operators
- [ ] No direct IFC manipulation (delegate to operators)
- [ ] Conversion functions exist between PropertyGroups and core dataclasses

---

## Key Architectural Decisions

### Decision 1: Python-Based Parametric System (NOT Geometry Nodes)

**Critical Sprint 0 Decision - CONFIRMED AND FINAL**

Saikei Civil implements parametric assemblies using **Python code with a Blender UI**, explicitly **NOT** using Geometry Nodes for core functionality.

#### Rationale

1. **Professional Software Precedent:**
   - Autodesk Civil 3D: C#/.NET backend with GUI
   - Bentley OpenRoads: C++ with Python API
   - Both hide complexity behind friendly interfaces
   - Users never see code, but code powers everything

2. **Engineering Precision Requirements:**
   - Complex engineering calculations difficult to express in nodes
   - Debugging node networks is challenging
   - Standards validation easier in code
   - Sub-millimeter precision needed for survey-grade work

3. **Parametric != Visual Programming:**
   - "Parametric" means values can vary and trigger regeneration
   - Does NOT mean node-based procedural modeling
   - Professional tools prove code-based parametric is industry standard

4. **Future Role for Geometry Nodes (Optional, Sprint 7+):**
   - Real-time preview while editing alignment
   - Low-poly approximation for quick feedback
   - Presentation/visualization mode only
   - **Final generation ALWAYS uses Python for precision**

#### Project Documentation Quote
> "Don't assume 'parametric' means 'Geometry Nodes'. Professional software uses code backends universally. OpenRoads constraint system is more powerful than Civil 3D regions. GUI simplicity on top of code power is the winning pattern."

### Decision 2: OpenRoads-Style Constraints (Not Civil 3D Regions)

**Why OpenRoads Style:**
- More powerful than Civil 3D's region-based approach
- Can override ANY parameter at ANY station range
- Multiple constraints can overlap/combine
- Simpler to implement than visual subassembly snapping
- Better for programmatic control and scripting

**What It Enables:**
```
User can define:
- lane_width = 3.6m from Sta 0+00 to 5+00
- lane_width = 4.2m from Sta 5+00 to 10+00 (turn lane widening)
- shoulder_width = 3.0m from Sta 0+00 to 20+00
- cross_slope = 2% normal crown
- cross_slope varies from 2% to -4% (superelevation transition)
```

### Decision 3: Store Parametric Rules in IFC Property Sets

**Storage Strategy: Custom Property Sets**

Parametric constraints are stored natively in the IFC file using custom property sets. This ensures:
- Data persistence in the IFC file (source of truth)
- Interoperability with other IFC tools
- No external file dependencies
- Round-trip editing capability

**Important Naming Convention:**
```python
# WRONG - Implies standard IFC property set (causes validation errors)
Name="Pset_SaikeiParametricConstraint"  # DO NOT USE

# CORRECT - Custom prefix for custom properties
Name="SaikeiCivil_ParametricConstraint"  # USE THIS
Name="SaikeiCivil_CrossSection"          # USE THIS
```

### Decision 4: Integrate with Existing Cross Section Viewer

**UI Location: Cross Section Panel Extension**

Rather than creating a separate parametric constraint panel, extend the existing cross section viewer system:
- `cross_section_panel.py` - Add Constraints sub-panel
- `cross_section_operators.py` - Add constraint operators
- `cross_section_properties.py` - Add constraint PropertyGroups

**Benefits:**
- Unified workflow (design + constraints in same location)
- Visual feedback in cross section preview
- Leverage existing assembly management infrastructure
- Consistent UI patterns

---

## OpenRoads-Style Constraint System

### Constraint Types

#### 1. Point Constraints (Single Station)
```python
@dataclass
class PointConstraint:
    """Single-station parameter override"""
    station: float          # e.g., 500.0
    component: str          # e.g., "Right Travel Lane"
    parameter: str          # e.g., "width"
    value: float            # e.g., 4.2
```

#### 2. Range Constraints (Station Range with Interpolation)
```python
@dataclass
class RangeConstraint:
    """Constraint that interpolates between stations"""
    start_station: float    # e.g., 200.0
    end_station: float      # e.g., 300.0
    component: str          # e.g., "Right Travel Lane"
    parameter: str          # e.g., "width"
    start_value: float      # e.g., 3.6
    end_value: float        # e.g., 4.2
    interpolation: str      # 'LINEAR' or 'SMOOTH' (future)
```

### Processing Order (Critical)

From OpenRoads documentation, the processing order during corridor generation:
```
1. Template dropped, points placed per template constraints
2. Parametric constraints applied (template + corridor)
3. Horizontal feature constraints applied
4. Point controls applied (highest priority)
5. Component display rules solved
```

**Saikei Civil Implementation:**
```
1. Get base assembly at station
2. Apply all active parametric constraints for that station
3. Interpolate values for transitional constraints
4. Calculate section geometry with overridden values
5. Generate IFC profile entities
6. Create Blender visualization
```

### Constraint Resolution

When multiple constraints affect the same parameter:
```python
def get_effective_value(self, parameter: str, station: float, 
                       component: str, default: float) -> float:
    """
    Get effective parameter value at station, considering all constraints.
    Later constraints in list take priority (last-write-wins).
    """
    applicable = [c for c in self.constraints 
                 if c.component == component
                 and c.parameter == parameter
                 and c.applies_to_station(station)]
    
    if not applicable:
        return default
    
    # Apply in order, last one wins
    value = default
    for constraint in applicable:
        if isinstance(constraint, RangeConstraint):
            # Interpolate within range
            t = (station - constraint.start_station) / \
                (constraint.end_station - constraint.start_station)
            value = constraint.start_value + t * (constraint.end_value - constraint.start_value)
        else:
            value = constraint.value
    
    return value
```

---

## IFC Storage Strategy

### Property Set Design for Parametric Constraints

**Entity Structure:**
```
IfcRoad (or IfcAlignment)
  +-- IfcRelDefinesByProperties
      +-- IfcPropertySet (Name="SaikeiCivil_ParametricConstraints")
          +-- IfcPropertySingleValue (Name="ConstraintCount", Value=3)
          +-- IfcPropertySingleValue (Name="ConstraintsJSON", Value="[...]")
```

### Recommended Approach: Property Set with JSON-Encoded Constraints

Store constraints as structured data within a property set:

```python
def create_parametric_constraint_pset(self, ifc_file, constraints: List[ParametricConstraint]):
    """Create IFC property set for parametric constraints"""
    
    # Create constraint entries as property list
    properties = []
    
    # Metadata
    properties.append(ifc_file.create_entity(
        "IfcPropertySingleValue",
        Name="ConstraintCount",
        NominalValue=ifc_file.create_entity("IfcInteger", len(constraints))
    ))
    
    properties.append(ifc_file.create_entity(
        "IfcPropertySingleValue",
        Name="LastModified",
        NominalValue=ifc_file.create_entity("IfcDateTime", 
            datetime.now().isoformat())
    ))
    
    # Serialize all constraints as JSON
    constraints_data = [c.to_dict() for c in constraints]
    constraints_json = json.dumps(constraints_data)
    
    properties.append(ifc_file.create_entity(
        "IfcPropertySingleValue",
        Name="ConstraintsJSON",
        NominalValue=ifc_file.create_entity("IfcText", constraints_json)
    ))
    
    # Create property set
    pset = ifc_file.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="SaikeiCivil_ParametricConstraints",
        Description="Parametric cross-section constraints for corridor generation",
        HasProperties=properties
    )
    
    return pset
```

### Alternative Approach: Using IfcConstraint (More Complex)

IFC provides `IfcConstraint` and `IfcMetric` for formal constraints:

```python
# IfcConstraint structure (more complex but IFC-native)
IfcMetric
  +-- Name: "LaneWidth_Transition"
  +-- ConstraintGrade: ADVISORY/SOFT/HARD
  +-- Benchmark: IfcBenchmarkEnum (EQUALTO, GREATERTHAN, etc.)
  +-- DataValue: IfcMetricValueSelect
```

**Decision:** Use Property Sets (first approach) because:
- Simpler implementation
- Better tool support
- Easier debugging
- Sufficient for our use case
- IfcConstraint is designed for validation/checking, not parameter control

### Association with Entities

```python
def associate_constraints_with_assembly(self, ifc_file, assembly_entity, pset):
    """Associate constraint property set with road assembly"""
    
    ifc_file.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[assembly_entity],
        RelatingPropertyDefinition=pset
    )
```

---

## Cross Section Viewer Integration

### Existing Infrastructure to Leverage

**Files Already Implemented:**
```
blendercivil/
+-- core/
|   +-- native_ifc_cross_section.py      # RoadAssembly, ConstraintManager
|   +-- components/                       # Lane, Shoulder, Curb, etc.
+-- operators/
|   +-- cross_section_operators.py        # BC_OT_add_constraint exists
+-- ui/
|   +-- cross_section_properties.py       # BC_ConstraintProperties exists
|   +-- panels/
|       +-- cross_section_panel.py        # BC_PT_CrossSectionConstraintsPanel
+-- visualization/
    +-- cross_section_visualizer.py       # 3D preview
    +-- profile_view_overlay.py           # 2D profile view
```

### Enhanced Constraint Panel Design

```python
class BC_PT_ParametricConstraintsPanel(Panel):
    """Enhanced parametric constraint management panel"""
    bl_label = "Parametric Constraints"
    bl_idname = "BC_PT_parametric_constraints"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei Civil"
    bl_parent_id = "BC_PT_cross_section_main"  # Child of cross section panel
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.bc_cross_section
        
        # Constraint list with UIList
        row = layout.row()
        row.template_list(
            "BC_UL_ConstraintList", "",
            props, "constraints",
            props, "active_constraint_index"
        )
        
        # Add/Remove buttons
        col = row.column(align=True)
        col.operator("bc.add_parametric_constraint", icon='ADD', text="")
        col.operator("bc.remove_parametric_constraint", icon='REMOVE', text="")
        col.separator()
        col.operator("bc.move_constraint_up", icon='TRIA_UP', text="")
        col.operator("bc.move_constraint_down", icon='TRIA_DOWN', text="")
        
        # Active constraint properties
        if props.constraints and props.active_constraint_index >= 0:
            constraint = props.constraints[props.active_constraint_index]
            
            box = layout.box()
            box.label(text="Constraint Properties:")
            
            box.prop(constraint, "constraint_type")
            box.prop(constraint, "component_name")
            box.prop(constraint, "parameter_name")
            
            row = box.row()
            row.prop(constraint, "start_station")
            row.prop(constraint, "end_station")
            
            row = box.row()
            row.prop(constraint, "start_value")
            if constraint.constraint_type == 'RANGE':
                row.prop(constraint, "end_value")
        
        # Preview at station
        layout.separator()
        layout.label(text="Preview at Station:")
        row = layout.row(align=True)
        row.prop(props, "preview_station")
        row.operator("bc.preview_section_at_station", icon='VIEWZOOM')
```

### Visual Feedback in Cross Section Preview

The cross section visualizer should show constraint effects:

```python
def visualize_constraint_at_station(self, station: float):
    """
    Visualize cross-section with constraint effects highlighted.
    Color-codes modified parameters vs base assembly.
    """
    assembly = self.get_active_assembly()
    if not assembly:
        return
    
    # Get base section points (no constraints)
    base_points = assembly.calculate_section_points(station, apply_constraints=False)
    
    # Get section points with constraints
    constrained_points = assembly.calculate_section_points(station, apply_constraints=True)
    
    # Visualize both, highlighting differences
    self._draw_base_section(base_points, color=(0.3, 0.3, 0.3, 0.5))  # Gray, semi-transparent
    self._draw_constrained_section(constrained_points, color=(0.2, 0.6, 1.0, 1.0))  # Blue, solid
    
    # Show delta annotations where values differ
    self._draw_constraint_annotations(base_points, constrained_points)
```

---

## Implementation Architecture

### System Architecture Diagram

```
+-------------------------------------------------------------+
|                    BLENDER UI PANELS                        |
|               (Friendly GUI - No Code Visible)              |
|   - Cross Section Design Panel                              |
|   - Parametric Constraints Panel    <-- NEW ENHANCEMENT     |
|   - Assembly Builder Panel                                  |
|   - Material Layer Panel                                    |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                   PYTHON API LAYER                          |
|            (Blender PropertyGroups & Operators)             |
|   - ConstraintProperties (data storage)                     |
|   - AddConstraintOperator                                   |
|   - ConstraintManager (validation, resolution)              |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|               CORRIDOR GENERATION ENGINE                    |
|            (Python + ifcopenshell + NumPy)                  |
|   1. Sample alignment at stations                           |
|   2. Get assembly for station                               |
|   3. Apply parametric constraints  <-- CONSTRAINT SYSTEM    |
|   4. Calculate section geometry                             |
|   5. Transform to 3D coordinates                            |
|   6. Create IFC entities                                    |
|   7. Generate Blender mesh for preview                      |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                    IFC FILE STORAGE                         |
|                  (Native IFC - Source of Truth)             |
|   - SaikeiCivil_ParametricConstraints (PropertySet)         |
|   - IfcSectionedSolidHorizontal (3D corridor)               |
|   - IfcCompositeProfileDef (cross-sections)                 |
+-------------------------------------------------------------+
```

### Module File Structure (Following 3-Layer Architecture)

```
blendercivil/
|
+-- core/                                   # LAYER 1: CORE (Pure Python)
|   +-- native_ifc_cross_section.py         # Existing - enhance ConstraintManager
|   +-- parametric_constraints.py           # NEW - Constraint classes
|   |   +-- ParametricConstraint (dataclass)
|   |   +-- PointConstraint (dataclass)
|   |   +-- RangeConstraint (dataclass)
|   |   +-- ConstraintManager (class)
|   |   +-- ConstraintResolver (class)
|   +-- constraint_ifc_io.py                # NEW - IFC read/write for constraints
|       +-- ConstraintIFCHandler (class)
|       +-- export_constraints_to_pset()
|       +-- import_constraints_from_pset()
|       +-- associate_constraints()
|
+-- operators/                              # LAYER 2: TOOL (Operators)
|   +-- cross_section_operators.py          # Enhance with constraint operators
|       +-- BC_OT_add_parametric_constraint
|       +-- BC_OT_remove_parametric_constraint
|       +-- BC_OT_edit_parametric_constraint
|       +-- BC_OT_preview_constraint_effect
|       +-- BC_OT_export_constraints_to_ifc
|
+-- ui/                                     # LAYER 3: UI (Panels & Properties)
|   +-- cross_section_properties.py         # Enhance ConstraintProperties
|   |   +-- BC_ConstraintProperties (PropertyGroup)
|   |   +-- BC_ConstraintCollectionProperties
|   |   +-- constraint_props_to_dataclass()  # Conversion function
|   |   +-- dataclass_to_constraint_props()  # Conversion function
|   +-- panels/
|       +-- cross_section_panel.py          # Enhance with constraints UI
|           +-- BC_PT_ParametricConstraintsPanel
|           +-- BC_UL_ConstraintList
|
+-- tests/
    +-- test_parametric_constraints.py      # NEW - Core layer tests (no Blender)
    |   +-- test_point_constraint
    |   +-- test_range_constraint
    |   +-- test_constraint_interpolation
    |   +-- test_constraint_resolution
    |   +-- test_ifc_export
    |   +-- test_ifc_roundtrip
    +-- test_constraint_operators.py        # NEW - Operator tests (requires Blender)
```

---

## Data Structures

### Core Constraint Classes (core/parametric_constraints.py)

```python
# core/parametric_constraints.py
# LAYER 1: CORE - Pure Python, NO bpy imports

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

class ConstraintType(Enum):
    POINT = "POINT"      # Single station
    RANGE = "RANGE"      # Station range with interpolation

class InterpolationType(Enum):
    LINEAR = "LINEAR"    # Linear interpolation (default)
    SMOOTH = "SMOOTH"    # Smooth transition (future)
    STEP = "STEP"        # No interpolation, instant change

@dataclass
class ParametricConstraint:
    """
    Base parametric constraint for cross-section parameters.
    
    Allows overriding any component parameter at specific stations
    or across station ranges with interpolation.
    
    NOTE: This is a CORE layer class - no Blender dependencies.
    """
    id: str                              # Unique identifier
    component_name: str                  # e.g., "Right Travel Lane"
    parameter_name: str                  # e.g., "width"
    constraint_type: ConstraintType      # POINT or RANGE
    start_station: float                 # Start of constraint
    end_station: float                   # End (same as start for POINT)
    start_value: float                   # Value at start
    end_value: float                     # Value at end (same as start for POINT)
    interpolation: InterpolationType = InterpolationType.LINEAR
    description: str = ""                # User notes
    enabled: bool = True                 # Can be disabled without deleting
    
    def applies_to_station(self, station: float) -> bool:
        """Check if constraint is active at given station"""
        if not self.enabled:
            return False
        return self.start_station <= station <= self.end_station
    
    def get_value_at_station(self, station: float) -> Optional[float]:
        """Get interpolated value at station, or None if not applicable"""
        if not self.applies_to_station(station):
            return None
        
        if self.constraint_type == ConstraintType.POINT:
            return self.start_value
        
        # Range constraint - interpolate
        if self.interpolation == InterpolationType.STEP:
            return self.start_value if station < self.end_station else self.end_value
        
        # Linear interpolation
        t = (station - self.start_station) / (self.end_station - self.start_station)
        t = max(0.0, min(1.0, t))  # Clamp
        
        if self.interpolation == InterpolationType.LINEAR:
            return self.start_value + t * (self.end_value - self.start_value)
        
        # Smooth interpolation (smoothstep)
        t = t * t * (3 - 2 * t)
        return self.start_value + t * (self.end_value - self.start_value)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for IFC storage"""
        return {
            'id': self.id,
            'component_name': self.component_name,
            'parameter_name': self.parameter_name,
            'constraint_type': self.constraint_type.value,
            'start_station': self.start_station,
            'end_station': self.end_station,
            'start_value': self.start_value,
            'end_value': self.end_value,
            'interpolation': self.interpolation.value,
            'description': self.description,
            'enabled': self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ParametricConstraint':
        """Deserialize from dictionary"""
        return cls(
            id=data['id'],
            component_name=data['component_name'],
            parameter_name=data['parameter_name'],
            constraint_type=ConstraintType(data['constraint_type']),
            start_station=data['start_station'],
            end_station=data['end_station'],
            start_value=data['start_value'],
            end_value=data['end_value'],
            interpolation=InterpolationType(data.get('interpolation', 'LINEAR')),
            description=data.get('description', ''),
            enabled=data.get('enabled', True)
        )


@dataclass
class ConstraintManager:
    """
    Manages all parametric constraints for a corridor.
    
    Provides methods for:
    - Adding/removing constraints
    - Resolving effective values at stations
    - IFC import/export
    - Validation
    
    NOTE: This is a CORE layer class - no Blender dependencies.
    """
    constraints: List[ParametricConstraint] = field(default_factory=list)
    
    def add_constraint(self, constraint: ParametricConstraint) -> None:
        """Add constraint and sort by station"""
        self.constraints.append(constraint)
        self.constraints.sort(key=lambda c: c.start_station)
    
    def remove_constraint(self, constraint_id: str) -> bool:
        """Remove constraint by ID"""
        for i, c in enumerate(self.constraints):
            if c.id == constraint_id:
                del self.constraints[i]
                return True
        return False
    
    def get_constraints_at_station(self, station: float) -> List[ParametricConstraint]:
        """Get all active constraints at station"""
        return [c for c in self.constraints if c.applies_to_station(station)]
    
    def get_effective_value(self, component: str, parameter: str,
                           station: float, default: float) -> float:
        """
        Get effective parameter value at station.
        
        Applies all relevant constraints in order (last wins).
        """
        value = default
        
        for constraint in self.constraints:
            if (constraint.component_name == component and
                constraint.parameter_name == parameter):
                
                constraint_value = constraint.get_value_at_station(station)
                if constraint_value is not None:
                    value = constraint_value
        
        return value
    
    def get_modified_parameters(self, station: float) -> dict:
        """
        Get all parameters that are modified at this station.
        
        Returns: {(component, parameter): value}
        """
        active = self.get_constraints_at_station(station)
        modified = {}
        
        for constraint in active:
            key = (constraint.component_name, constraint.parameter_name)
            value = constraint.get_value_at_station(station)
            if value is not None:
                modified[key] = value
        
        return modified
    
    def validate(self) -> List[str]:
        """Validate all constraints, return list of issues"""
        issues = []
        
        for c in self.constraints:
            if c.start_station > c.end_station:
                issues.append(f"Constraint {c.id}: start_station > end_station")
            
            if c.constraint_type == ConstraintType.POINT and c.start_value != c.end_value:
                issues.append(f"Constraint {c.id}: POINT constraint has different start/end values")
        
        return issues
```

### Blender Property Groups (ui/cross_section_properties.py)

```python
# ui/cross_section_properties.py (enhancements)
# LAYER 3: UI - Blender-specific PropertyGroups

import bpy
from bpy.props import (
    StringProperty, FloatProperty, BoolProperty, 
    EnumProperty, CollectionProperty, IntProperty
)
from bpy.types import PropertyGroup

class BC_ConstraintProperties(PropertyGroup):
    """
    Property group for a single parametric constraint.
    
    NOTE: This is a UI layer class - mirrors core ParametricConstraint.
    Use conversion functions to translate between this and core dataclass.
    """
    
    constraint_id: StringProperty(
        name="ID",
        description="Unique constraint identifier",
        default=""
    )
    
    constraint_type: EnumProperty(
        name="Type",
        items=[
            ('POINT', "Point", "Single station override"),
            ('RANGE', "Range", "Station range with interpolation"),
        ],
        default='RANGE'
    )
    
    component_name: StringProperty(
        name="Component",
        description="Target component name",
        default="Right Travel Lane"
    )
    
    parameter_name: EnumProperty(
        name="Parameter",
        items=[
            ('width', "Width", "Component width"),
            ('cross_slope', "Cross Slope", "Cross slope percentage"),
            ('depth', "Depth", "Pavement depth"),
            ('offset', "Offset", "Lateral offset"),
        ],
        default='width'
    )
    
    start_station: FloatProperty(
        name="Start Station",
        description="Station where constraint begins",
        default=0.0,
        min=0.0,
        unit='LENGTH'
    )
    
    end_station: FloatProperty(
        name="End Station",
        description="Station where constraint ends",
        default=100.0,
        min=0.0,
        unit='LENGTH'
    )
    
    start_value: FloatProperty(
        name="Start Value",
        description="Value at start station",
        default=3.6,
        precision=3
    )
    
    end_value: FloatProperty(
        name="End Value",
        description="Value at end station",
        default=3.6,
        precision=3
    )
    
    interpolation: EnumProperty(
        name="Interpolation",
        items=[
            ('LINEAR', "Linear", "Linear interpolation"),
            ('SMOOTH', "Smooth", "Smooth transition"),
            ('STEP', "Step", "Instant change at end"),
        ],
        default='LINEAR'
    )
    
    enabled: BoolProperty(
        name="Enabled",
        description="Enable/disable this constraint",
        default=True
    )
    
    description: StringProperty(
        name="Description",
        description="User notes about this constraint",
        default=""
    )


# Conversion functions between UI PropertyGroup and Core dataclass

def constraint_props_to_dataclass(props: BC_ConstraintProperties) -> 'ParametricConstraint':
    """Convert Blender PropertyGroup to Core dataclass"""
    from ..core.parametric_constraints import (
        ParametricConstraint, ConstraintType, InterpolationType
    )
    
    return ParametricConstraint(
        id=props.constraint_id,
        component_name=props.component_name,
        parameter_name=props.parameter_name,
        constraint_type=ConstraintType(props.constraint_type),
        start_station=props.start_station,
        end_station=props.end_station,
        start_value=props.start_value,
        end_value=props.end_value,
        interpolation=InterpolationType(props.interpolation),
        description=props.description,
        enabled=props.enabled
    )


def dataclass_to_constraint_props(constraint: 'ParametricConstraint', 
                                  props: BC_ConstraintProperties) -> None:
    """Update Blender PropertyGroup from Core dataclass"""
    props.constraint_id = constraint.id
    props.component_name = constraint.component_name
    props.parameter_name = constraint.parameter_name
    props.constraint_type = constraint.constraint_type.value
    props.start_station = constraint.start_station
    props.end_station = constraint.end_station
    props.start_value = constraint.start_value
    props.end_value = constraint.end_value
    props.interpolation = constraint.interpolation.value
    props.description = constraint.description
    props.enabled = constraint.enabled
```

---

## IFC Property Set Design

### Complete IFC Export Implementation (core/constraint_ifc_io.py)

```python
# core/constraint_ifc_io.py
# LAYER 1: CORE - Pure Python, uses ifcopenshell (not bpy)

import ifcopenshell
import ifcopenshell.guid
import json
from typing import List, Optional
from datetime import datetime

from .parametric_constraints import ParametricConstraint, ConstraintManager


class ConstraintIFCHandler:
    """
    Handles IFC import/export of parametric constraints.
    
    Stores constraints in a custom property set attached to the
    IfcRoad or IfcAlignment entity.
    
    NOTE: This is a CORE layer class - no Blender dependencies.
    """
    
    PSET_NAME = "SaikeiCivil_ParametricConstraints"
    
    def __init__(self, ifc_file):
        self.ifc_file = ifc_file
    
    def export_constraints(self, manager: ConstraintManager,
                          target_entity) -> 'IfcPropertySet':
        """
        Export constraints to IFC property set.
        
        Args:
            manager: ConstraintManager with constraints to export
            target_entity: IfcRoad or IfcAlignment to attach to
            
        Returns:
            Created IfcPropertySet entity
        """
        properties = []
        
        # Metadata properties
        properties.append(self._create_property(
            "Version", "IfcLabel", "1.0"
        ))
        properties.append(self._create_property(
            "CreatedBy", "IfcLabel", "Saikei Civil"
        ))
        properties.append(self._create_property(
            "LastModified", "IfcDateTime", datetime.now().isoformat()
        ))
        properties.append(self._create_property(
            "ConstraintCount", "IfcInteger", len(manager.constraints)
        ))
        
        # Serialize all constraints as JSON in a single property
        constraints_data = [c.to_dict() for c in manager.constraints]
        constraints_json = json.dumps(constraints_data)
        
        properties.append(self._create_property(
            "ConstraintsJSON", "IfcText", constraints_json
        ))
        
        # Create property set
        pset = self.ifc_file.create_entity(
            "IfcPropertySet",
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=self._get_owner_history(),
            Name=self.PSET_NAME,
            Description="Parametric cross-section constraints for corridor generation",
            HasProperties=properties
        )
        
        # Associate with target entity
        self.ifc_file.create_entity(
            "IfcRelDefinesByProperties",
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=self._get_owner_history(),
            RelatedObjects=[target_entity],
            RelatingPropertyDefinition=pset
        )
        
        return pset
    
    def import_constraints(self, target_entity) -> Optional[ConstraintManager]:
        """
        Import constraints from IFC property set.
        
        Args:
            target_entity: IfcRoad or IfcAlignment to read from
            
        Returns:
            ConstraintManager with loaded constraints, or None if not found
        """
        # Find the property set
        pset = self._find_constraint_pset(target_entity)
        if not pset:
            return None
        
        # Find the JSON property
        constraints_json = None
        for prop in pset.HasProperties:
            if prop.Name == "ConstraintsJSON":
                constraints_json = prop.NominalValue.wrappedValue
                break
        
        if not constraints_json:
            return None
        
        # Parse and create constraints
        manager = ConstraintManager()
        try:
            constraints_data = json.loads(constraints_json)
            for data in constraints_data:
                constraint = ParametricConstraint.from_dict(data)
                manager.add_constraint(constraint)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing constraints: {e}")
            return None
        
        return manager
    
    def _create_property(self, name: str, value_type: str, value) -> 'IfcProperty':
        """Create an IFC property single value"""
        nominal_value = self.ifc_file.create_entity(value_type, value)
        return self.ifc_file.create_entity(
            "IfcPropertySingleValue",
            Name=name,
            NominalValue=nominal_value
        )
    
    def _find_constraint_pset(self, entity) -> Optional['IfcPropertySet']:
        """Find the constraint property set on an entity"""
        for rel in self.ifc_file.by_type("IfcRelDefinesByProperties"):
            if entity in rel.RelatedObjects:
                pset = rel.RelatingPropertyDefinition
                if hasattr(pset, 'Name') and pset.Name == self.PSET_NAME:
                    return pset
        return None
    
    def _get_owner_history(self):
        """Get or create owner history"""
        histories = self.ifc_file.by_type("IfcOwnerHistory")
        if histories:
            return histories[0]
        return None
```

---

## External References

### IFC Standards Documentation

| Source | URL | Notes |
|--------|-----|-------|
| **buildingSMART IFC 4.3** | https://ifc43-docs.standards.buildingsmart.org/ | Official IFC 4.3 documentation |
| **IfcSectionedSolidHorizontal** | https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcSectionedSolidHorizontal.htm | Cross-section sweep for corridors |
| **IfcConstraint** | https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD1/HTML/schema/ifcconstraintresource/lexical/ifcconstraint.htm | IFC constraint entity (alternative approach) |
| **IfcPropertySet** | https://standards.buildingsmart.org/IFC/RELEASE/IFC4/HTML/schema/ifckernel/lexical/ifcpropertyset.htm | Property set definition |
| **IFC Road WP3 Examples** | https://buildingsmart.org/standards/calls-for-participation/ifcroad/ | Conceptual model report with examples |

### Industry References

| Source | Notes |
|--------|-------|
| **BIM Corner - IFC 4.3 Changes** | Key changes in IFC schema for infrastructure |
| **Civil 3D Assembly Documentation** | Professional software implementation reference |
| **OpenRoads Template Documentation** | Parametric constraint system design reference |

### Project Knowledge Sources

| Document | Location | Content |
|----------|----------|---------|
| IFC_Roadway_Templates_Assemblies_Reference.md | /mnt/project/ | Comprehensive template/assembly reference |
| Template_architectural_decision.md | /mnt/project/ | Sprint 0 architecture decisions |
| Sprint4_Day1_IFC_CrossSection_Research.md | /mnt/project/ | Cross-section implementation research |
| Sprint4_Day4_Summary.md | /mnt/project/ | Visualization system implementation |
| PROFILE_VIEW_FINAL_SUMMARY.md | /mnt/project/ | Profile view system documentation |

---

## Implementation Roadmap

### Phase 1: Core Constraint System (2-3 days)

**Day 1: Data Structures (Core Layer)**
- [ ] Create `core/parametric_constraints.py` with core classes
- [ ] Implement `ParametricConstraint` dataclass
- [ ] Implement `ConstraintManager` class
- [ ] Write unit tests for constraint logic (no Blender required)

**Day 2: IFC Integration (Core Layer)**
- [ ] Create `core/constraint_ifc_io.py`
- [ ] Implement export to property sets
- [ ] Implement import from property sets
- [ ] Write IFC round-trip tests

**Day 3: Integration with Assembly (Core Layer)**
- [ ] Enhance `RoadAssembly.calculate_section_points()` to accept constraints
- [ ] Connect `ConstraintManager` to corridor generation
- [ ] Test constraint effects on geometry

### Phase 2: UI Implementation (2-3 days)

**Day 4: Property Groups (UI Layer)**
- [ ] Enhance `BC_ConstraintProperties` in `ui/cross_section_properties.py`
- [ ] Add constraint collection to scene properties
- [ ] Create conversion functions (PropertyGroup to/from dataclass)
- [ ] Create UIList for constraint display

**Day 5: Operators (Tool Layer)**
- [ ] Implement `BC_OT_add_parametric_constraint`
- [ ] Implement `BC_OT_remove_parametric_constraint`
- [ ] Implement `BC_OT_edit_parametric_constraint`
- [ ] Implement `BC_OT_preview_constraint_effect`
- [ ] Ensure operators are thin wrappers calling core functions

**Day 6: Panels (UI Layer)**
- [ ] Create `BC_PT_ParametricConstraintsPanel`
- [ ] Add constraint property editor
- [ ] Integrate with cross section panel

### Phase 3: Visualization & Polish (2 days)

**Day 7: Visual Feedback**
- [ ] Enhance cross section visualizer for constraint preview
- [ ] Add color-coded constraint regions
- [ ] Show interpolation curves in profile view

**Day 8: Testing & Documentation**
- [ ] Comprehensive integration tests
- [ ] User documentation
- [ ] Example files with constraints

---

## Success Criteria

### Functional Requirements
- [ ] Can add point constraints (single station override)
- [ ] Can add range constraints (interpolated transition)
- [ ] Constraints properly affect corridor geometry
- [ ] Constraints persist in IFC file
- [ ] Constraints survive round-trip (export then import)
- [ ] Visual preview of constraint effects

### Quality Requirements
- [ ] 100% unit test coverage for constraint classes
- [ ] IFC validation passes (no Pset_ naming violations)
- [ ] Performance: less than 100ms to apply all constraints at one station
- [ ] Follows existing Saikei Civil code patterns
- [ ] Follows Bonsai 3-layer architecture

### Architecture Compliance
- [ ] Core layer has NO bpy imports
- [ ] Core layer tests run without Blender
- [ ] Operators delegate to core layer (thin wrappers)
- [ ] PropertyGroups have conversion functions to/from core dataclasses

### User Experience Requirements
- [ ] Intuitive UI in cross section panel
- [ ] Clear visual feedback of constraint effects
- [ ] Undo/redo support for constraint operations
- [ ] Helpful error messages for invalid constraints

---

## Notes for Implementation

### Important Considerations

1. **3-Layer Architecture**: ALWAYS follow Core/Tool/UI separation. Core has no bpy imports.

2. **Property Set Naming**: Use `SaikeiCivil_` prefix, NOT `Pset_` (reserved for IFC standard property sets)

3. **Constraint Resolution Order**: Later constraints in list override earlier ones for the same parameter

4. **Station Precision**: Use consistent decimal precision (typically 3 decimal places for meters)

5. **Blender Integration**: Use PropertyGroups for UI data, convert to dataclasses for processing

6. **IFC Storage**: Store constraints at the IfcRoad level, not individual components

7. **Testing**: Test core layer with pytest (no Blender), test operators in Blender

### Common Pitfalls to Avoid

- DO NOT use Geometry Nodes for parametric control
- DO NOT use `Pset_` prefix for custom property sets
- DO NOT store constraints in Blender custom properties (use IFC)
- DO NOT put business logic in operators (delegate to core)
- DO NOT import bpy in core layer files
- DO NOT forget to handle disabled constraints
- DO NOT assume constraints are sorted (always sort by station)

---

*Document prepared for Claude Code integration. Follow the 3-layer architecture, implementation roadmap, and reference the data structures when building the parametric control module.*
