# Saikei Civil - Architecture & Features Summary
## AI Context Document

> **Purpose:** This document provides comprehensive context for AI agents working with the Saikei Civil codebase.

---

## Project Overview

| Property | Value |
|----------|-------|
| **Name** | Saikei Civil (栽景 - "planted landscape") |
| **Type** | Blender 4.5+ Extension for Civil Engineering |
| **Version** | 0.6.0 |
| **License** | GNU GPL v3 |
| **Repository** | `C:\GitHub\Saikei-Civil\saikei_civil` |
| **Developer** | Michael Yoder / Desert Springs Civil Engineering PLLC |

### Mission
Democratize professional civil engineering tools by providing free, open-source alternatives to commercial software like Civil 3D ($2,500/year) and OpenRoads ($4,000/year).

### Core Philosophy: Native IFC
**"We're not converting TO IFC. We ARE IFC."**

The IFC file is the **single source of truth**. Blender serves only as the visualization/interaction layer. All civil engineering data lives in the IFC file from the very first action.

---

## Architecture Overview

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: BIM Modules (operators/ & ui/)                       │
│  - Blender operators (user actions)                            │
│  - UI panels and properties                                     │
│  - Direct bpy usage allowed                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │ calls
┌───────────────────────────▼─────────────────────────────────────┐
│  LAYER 2: Tool (tool/)                                          │
│  - Blender-specific implementations                             │
│  - Bridge between core logic and Blender API                    │
│  - Dependency injection pattern                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ uses
┌───────────────────────────▼─────────────────────────────────────┐
│  LAYER 1: Core (core/)                                          │
│  - Pure Python business logic (NO bpy imports)                  │
│  - IFC operations and entity management                         │
│  - Geometry calculations and algorithms                          │
└─────────────────────────────────────────────────────────────────┘
```

### IFC Data Flow
```
IFC File (Source of Truth)
        ↓
   Design Work in Blender
        ↓
 (Already in IFC - no conversion)
        ↓
    Save IFC File
```

---

## Directory Structure

```
saikei_civil/
├── __init__.py                    # Extension entry point
├── blender_manifest.toml          # Blender 4.5+ manifest
├── preferences.py                 # User preferences
│
├── core/                          # LAYER 1: Pure Python logic
│   ├── ifc_manager/              # IFC lifecycle management
│   │   ├── manager.py            # NativeIfcManager (central controller)
│   │   ├── transaction.py        # Undo/redo system
│   │   ├── validation.py         # IFC validation
│   │   └── rebuilder_registry.py # Entity rebuild tracking
│   │
│   ├── horizontal_alignment/     # PI-driven horizontal design
│   │   ├── manager.py            # NativeIfcAlignment
│   │   ├── curve_geometry.py     # Arc calculations
│   │   ├── segment_builder.py    # Segment creation
│   │   └── stationing.py         # Station numbering
│   │
│   ├── vertical_alignment/       # PVI-driven vertical design
│   │   ├── pvi.py               # PVI dataclass
│   │   └── constants.py         # AASHTO design standards
│   │
│   ├── components/              # Cross-section components
│   │   ├── lane_component.py
│   │   ├── shoulder_component.py
│   │   ├── curb_component.py
│   │   ├── ditch_component.py
│   │   ├── median_component.py
│   │   ├── sidewalk_component.py
│   │   └── templates/           # Standard templates
│   │       ├── aashto.py        # USA standards
│   │       ├── austroads.py     # Australian standards
│   │       └── uk_dmrb.py       # UK standards
│   │
│   ├── corridor.py              # 3D corridor logic
│   ├── alignment_visualizer.py  # Real-time visualization
│   ├── alignment_registry.py    # Instance tracking
│   ├── crs_searcher.py          # 6000+ CRS database
│   └── ifc_api.py               # ifcopenshell wrappers
│
├── tool/                         # LAYER 2: Blender implementations
│   ├── ifc.py                   # IFC file operations
│   ├── blender.py               # Blender API wrapper
│   ├── alignment.py             # Alignment operations
│   ├── vertical_alignment.py    # Vertical operations
│   ├── georeference.py          # Georeferencing
│   ├── cross_section.py         # Cross-section operations
│   └── corridor.py              # Corridor operations
│
├── operators/                    # LAYER 3: User actions (75+ operators)
│   ├── file_operators.py        # New/Open/Save IFC
│   ├── alignment_operators.py   # Create alignments
│   ├── pi_operators.py          # Interactive PI placement
│   ├── curve_operators.py       # Curve management
│   ├── vertical_operators.py    # PVI operations
│   ├── georef_operators.py      # Georeferencing
│   ├── cross_section_operators.py
│   ├── corridor_operators.py
│   ├── profile_view_operators.py
│   └── base_operator.py         # Undo/redo operators
│
├── ui/                           # LAYER 3: UI panels & properties
│   ├── alignment_panel.py       # Main alignment panel
│   ├── alignment_properties.py  # Alignment data storage
│   ├── cross_section_properties.py
│   ├── corridor_properties.py
│   └── panels/                  # Organized subpanels
│       ├── georeferencing_panel.py
│       ├── vertical_alignment_panel.py
│       └── profile_view_panel.py
│
├── handlers/                     # Event handlers
│   └── undo_handler.py          # Undo/redo sync
│
└── tests/                        # Test suite
    └── core/
        ├── test_horizontal_alignment.py
        ├── test_vertical_alignment.py
        └── test_ifc_manager.py
```

---

## Key Classes & Components

### 1. NativeIfcManager (Singleton)
**Location:** `core/ifc_manager/manager.py`

Central controller for IFC file lifecycle.

```python
# Key methods
NativeIfcManager.get_file()          # Get active IFC file
NativeIfcManager.new_file()          # Create new IFC with project hierarchy
NativeIfcManager.open_file(path)     # Load IFC
NativeIfcManager.save_file(path)     # Save IFC
NativeIfcManager.get_entity(obj)     # Get IFC entity from Blender object
NativeIfcManager.link_object(obj, entity)  # Link Blender object to IFC
```

### 2. NativeIfcAlignment
**Location:** `core/horizontal_alignment/manager.py`

PI-driven horizontal alignment design engine.

```python
# Key methods
alignment = NativeIfcAlignment(ifc, "Road Name")
alignment.add_pi(x, y)                    # Add control point
alignment.insert_curve_at_pi(idx, radius) # Add curve
alignment.set_pi_location(idx, x, y)      # Move PI
alignment.get_segments()                   # Get all segments
alignment.auto_generate_segments()         # Regenerate geometry
```

### 3. TransactionManager
**Location:** `core/ifc_manager/transaction.py`

Undo/redo system with nested transaction support.

```python
# Key methods
TransactionManager.begin_transaction("Operation Name")
TransactionManager.end_transaction()
TransactionManager.undo()
TransactionManager.redo()
```

### 4. PVI (Point of Vertical Intersection)
**Location:** `core/vertical_alignment/pvi.py`

Dataclass for vertical control points.

```python
@dataclass
class PVI:
    station: float      # Position along alignment (m)
    elevation: float    # Height (m)
    grade_in: float     # Incoming grade (decimal)
    grade_out: float    # Outgoing grade (decimal)
    curve_length: float # Vertical curve length (m)
    k_value: float      # K-value for parabolic curves
```

### 5. Component System
**Location:** `core/components/`

Modular cross-section building blocks:

| Component | Purpose |
|-----------|---------|
| `LaneComponent` | Travel lanes, parking, turn lanes |
| `ShoulderComponent` | Paved or gravel shoulders |
| `CurbComponent` | Edge control (vertical, mountable, sloped) |
| `DitchComponent` | Drainage channels |
| `MedianComponent` | Center dividers |
| `SidewalkComponent` | Pedestrian paths |

---

## IFC Entity Hierarchy

```
IfcProject
└── IfcSite
    └── IfcRoad
        └── IfcAlignment
            ├── IfcAlignmentHorizontal
            │   ├── IfcAlignmentSegment (tangent - LINE)
            │   └── IfcAlignmentSegment (curve - CIRCULARARC)
            └── IfcAlignmentVertical
                ├── IfcAlignmentVerticalSegment (grade)
                └── IfcAlignmentVerticalSegment (parabolic curve)
```

### Supported IFC 4.3 Entities

**Project Structure:**
- `IfcProject`, `IfcSite`, `IfcRoad`
- `IfcUnitAssignment`, `IfcGeometricRepresentationContext`

**Alignments:**
- `IfcAlignment`, `IfcAlignmentHorizontal`, `IfcAlignmentVertical`
- `IfcAlignmentSegment`, `IfcAlignmentHorizontalSegment`, `IfcAlignmentVerticalSegment`
- `IfcCompositeCurve`, `IfcCurveSegment`, `IfcCircularArcSegment`

**Cross-Sections:**
- `IfcOpenCrossProfileDef`, `IfcCompositeProfileDef`
- `IfcMaterialProfileSet`, `IfcMaterial`

**Corridors:**
- `IfcSectionedSolidHorizontal`

**Georeferencing:**
- `IfcMapConversion`, `IfcProjectedCRS`

**Relationships:**
- `IfcRelNests`, `IfcRelAggregates`, `IfcRelAssociatesMaterial`

---

## Available Operators (User Actions)

### File Management (6 operators)
| Operator | Purpose |
|----------|---------|
| `bc.new_ifc_file` | Create new IFC with project hierarchy |
| `bc.open_ifc` | Load IFC from disk |
| `bc.save_ifc` | Save current IFC |
| `bc.clear_ifc` | Remove IFC from scene |
| `bc.reload_ifc` | Refresh from disk |

### Alignment Operations (7 operators)
| Operator | Purpose |
|----------|---------|
| `bc.create_native_alignment` | Create new IfcAlignment |
| `bc.add_pi_interactive` | Click to place PIs (modal) |
| `bc.add_native_pi` | Add PI at 3D cursor |
| `bc.delete_native_pi` | Remove selected PI |
| `bc.add_curve_interactive` | Click to add curves |
| `bc.edit_curve_radius` | Modify curve geometry |
| `bc.rebuild_alignment_visualizations` | Regenerate visuals |

### Vertical Alignment (10 operators)
| Operator | Purpose |
|----------|---------|
| `bc.add_pvi` | Add vertical control point |
| `bc.remove_pvi` | Delete control point |
| `bc.edit_pvi` | Modify PVI properties |
| `bc.design_vertical_curve` | K-value based design |
| `bc.calculate_grades` | Auto-compute grades |
| `bc.validate_vertical` | Check AASHTO standards |
| `bc.trace_terrain_as_vertical` | Sample terrain mesh |

### Cross-Section (10 operators)
| Operator | Purpose |
|----------|---------|
| `bc.create_assembly` | New cross-section |
| `bc.add_component` | Add lane/shoulder/etc. |
| `bc.remove_component` | Delete component |
| `bc.add_constraint` | Parametric variation |
| `bc.validate_assembly` | Check design rules |

### Georeferencing (7 operators)
| Operator | Purpose |
|----------|---------|
| `bc.search_crs` | Find by name/EPSG (6000+ CRS) |
| `bc.setup_georeferencing` | Initialize CRS |
| `bc.pick_false_origin` | Set origin point |
| `bc.validate_georeferencing` | Check configuration |

### Profile View (12 operators)
| Operator | Purpose |
|----------|---------|
| `bc.profile_view_toggle` | Show/hide profile view |
| `bc.profile_view_load_terrain` | Sample terrain mesh |
| `bc.profile_view_add_pvi` | Place PVI in view |
| `bc.profile_view_fit_to_data` | Auto-zoom |

### Undo/Redo (3 operators)
| Operator | Purpose |
|----------|---------|
| `bc.undo_ifc` | Undo last IFC transaction |
| `bc.redo_ifc` | Redo last transaction |

**Total: 75+ operators**

---

## UI Panels

### Main Sidebar Tab: "Saikei Civil"

| Panel | Purpose |
|-------|---------|
| **File Management** | New/Open/Save/Clear IFC |
| **Alignment Design** | Alignment list, PI tools, curves |
| **Vertical Alignment** | PVI management, grades, curves |
| **Georeferencing** | CRS search, origin setup |
| **Cross-Sections** | Component assembly editor |
| **Corridor** | 3D corridor generation |
| **Profile View** | 2D elevation profile |
| **Validation** | Design standard checks |

---

## Template System

### Available Standards

**AASHTO (American):**
- Two-Lane Rural Highway (60 mph)
- Interstate Highway (70 mph)
- Urban Arterial (45 mph)
- Rural Collector (50 mph)
- Local Road (30 mph)

**Austroads (Australian):**
- Rural Single Carriageway
- Motorway
- Urban Arterial

**UK DMRB (British):**
- Single Carriageway
- Dual Carriageway
- Motorway

### Template Access
```python
from core.components.templates import registry
templates = registry.get_all_templates()
assembly = templates['AASHTO Two-Lane Rural']()
```

---

## Key Patterns & Conventions

### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `NativeIfcManager` |
| Functions | snake_case | `create_alignment` |
| Operators | `BC_OT_*` | `BC_OT_create_alignment` |
| Panels | `VIEW3D_PT_bc_*` | `VIEW3D_PT_bc_alignment` |

### IFC Operations Pattern
```python
# 1. Get IFC file
ifc = NativeIfcManager.get_file()

# 2. Create IFC entity
entity = ifc.create_entity("IfcAlignment",
    GlobalId=ifcopenshell.guid.new(),
    Name="My Alignment"
)

# 3. Create Blender visualization
obj = bpy.data.objects.new("My Object", mesh)

# 4. Link them
NativeIfcManager.link_object(obj, entity)
```

### Blender Object Properties
Blender objects store minimal data (IFC is source of truth):
```python
obj["ifc_definition_id"]  # IFC entity ID
obj["ifc_class"]          # IFC entity type
obj["GlobalId"]           # IFC GlobalId
```

---

## Real-Time Update System

### PI Movement Detection
1. Blender frame-update handler monitors PI locations
2. When PI moves, IFC coordinates are updated
3. Segments are regenerated automatically
4. Visualizer refreshes in real-time

### Alignment Registry
```python
# Track instantiated alignments
alignment_registry.register_alignment(alignment_obj)
alignment_registry.get_alignment(global_id)
alignment_registry.get_or_create_visualizer(alignment)
```

---

## Dependencies

### Required
- **Blender 4.5+** - Extension system
- **IfcOpenShell** - IFC file operations
- **NumPy** - Mathematical calculations

### Optional
- **PyProj** - Coordinate transformations (georeferencing)

---

## Development Status

### Completed ✅
- Sprint 0: Native IFC Foundation
- Sprint 1: Horizontal Alignments (PI-driven)
- Sprint 2: Georeferencing (6000+ CRS)
- Sprint 3: Vertical Alignments (PVI-driven)
- Sprint 4: Cross-Sections (component-based)

### In Progress 🚧
- Sprint 5: Corridor Generation (3D modeling)

### Planned 📋
- Sprint 6: Advanced Geometry (clothoids)
- Sprint 7: Materials & Quantities
- Sprint 8: Polish & Testing
- Sprints 9+: Industry Integration

---

## Debugging Tips

1. **Check IFC file exists:** `NativeIfcManager.get_file() is not None`
2. **Verify linking:** `obj.get("ifc_definition_id")` should return entity ID
3. **Console logging:** Use `print()`, check Blender System Console
4. **IFC validation:** Open saved IFC in Solibri or FreeCAD

---

## Resources

- **IFC 4.3 Spec:** https://ifc43-docs.standards.buildingsmart.org/
- **IfcOpenShell:** https://docs.ifcopenshell.org/
- **Bonsai Wiki:** https://wiki.osarch.org/
- **OSArch Forum:** https://community.osarch.org/

---

*Last Updated: December 2025*
*Saikei Civil - Native IFC for Horizontal Construction*