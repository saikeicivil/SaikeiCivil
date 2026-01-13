# CLAUDE.md - Saikei Civil Project Context

## Project Identity

**Name:** Saikei Civil (formerly BlenderCivil)  
**Pronunciation:** "SIGH-kay" (盆景 - Japanese for "planted landscape")  
**Tagline:** "The landscape around the buildings"  
**Repository:** `C:\GitHub\Saikei-Civil\saikei_civil`  
**Symlink:** `%APPDATA%\Blender Foundation\Blender\4.5\extensions\user_default\saikei_civil`

### Brand Philosophy
Saikei is the natural complement to Bonsai (BlenderBIM) in the open-source IFC ecosystem:
- **Bonsai** = Buildings (vertical construction)
- **Saikei** = Infrastructure (horizontal construction: roads, earthwork, drainage)

> "While Bonsai crafts the buildings, Saikei shapes the world around them."

---

## Mission & Vision

### Mission
Democratize professional civil engineering tools by providing free, open-source alternatives to expensive commercial software like Civil 3D ($2,500/year) and OpenRoads ($4,000/year).

### Target Users
- Small engineering firms seeking cost-effective tools
- Engineers in developing countries without software budgets
- Students and educators
- Land surveyors and GIS professionals

### Core Philosophy: Native IFC
**"We're not converting TO IFC. We ARE IFC."**

Unlike traditional CAD software that exports to IFC, Saikei Civil works **IN** IFC format from the very first action. The IFC file is the single source of truth, and Blender is the visualization/interaction layer.

---

## Bonsai Integration Strategy

### Primary Principle: Detect and Defer

**When Bonsai is installed and has an active IFC file, Saikei defers to Bonsai for:**
1. **IFC File Management** - Use Bonsai's `IfcStore` instead of `NativeIfcManager`
2. **Transaction/Undo System** - Use Bonsai's `execute_ifc_operator` wrapper
3. **Element Linking** - Use Bonsai's `id_map` and `guid_map`
4. **Georeferencing** - Use Bonsai's georeferencing UI and implementation (see below)

**When Bonsai is NOT installed, Saikei operates standalone** using its own `NativeIfcManager`.

### Georeferencing: Always Defer to Bonsai

Bonsai has mature, well-tested georeferencing features. **Saikei should NOT duplicate this functionality.**

```python
# Georeferencing strategy
def get_georeferencing_handler():
    """Get the appropriate georeferencing handler."""
    if is_bonsai_available():
        # Use Bonsai's georeferencing - it's more mature
        return BonsaiGeorefBridge()
    else:
        # Fallback to Saikei's implementation only if Bonsai unavailable
        return SaikeiGeorefHandler()

class BonsaiGeorefBridge:
    """Bridge to Bonsai's georeferencing features."""
    
    def get_map_conversion(self):
        """Get IfcMapConversion from Bonsai."""
        from bonsai.bim.ifc import IfcStore
        ifc = IfcStore.get_file()
        if ifc:
            conversions = ifc.by_type("IfcMapConversion")
            return conversions[0] if conversions else None
        return None
    
    def get_projected_crs(self):
        """Get IfcProjectedCRS from Bonsai."""
        from bonsai.bim.ifc import IfcStore
        ifc = IfcStore.get_file()
        if ifc:
            crs_list = ifc.by_type("IfcProjectedCRS")
            return crs_list[0] if crs_list else None
        return None
    
    def transform_to_local(self, easting, northing, elevation=0):
        """Transform global coords to local using Bonsai's conversion."""
        # Use Bonsai's existing transformation logic
        pass
    
    def transform_to_global(self, x, y, z=0):
        """Transform local coords to global using Bonsai's conversion."""
        pass
```

**UI Approach for Georeferencing:**
- When Bonsai is installed: Hide Saikei's georef panel, show message "Use Bonsai's Georeferencing panel"
- When standalone: Show Saikei's georef panel as fallback

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SAIKEI CIVIL                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    civil/ifc_operator.py                     │   │
│  │                   (Integration Bridge)                       │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│              ┌──────────────┴──────────────┐                       │
│              │                             │                        │
│              ▼                             ▼                        │
│  ┌─────────────────────┐       ┌─────────────────────┐             │
│  │   Bonsai Mode       │       │   Standalone Mode   │             │
│  │                     │       │                     │             │
│  │ • IfcStore          │       │ • NativeIfcManager  │             │
│  │ • Bonsai Georef     │       │ • Saikei Georef     │             │
│  │ • Bonsai Undo       │       │ • Saikei Undo       │             │
│  └─────────────────────┘       └─────────────────────┘             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Critical Code Patterns

### 1. IFC File Access (ALWAYS use this pattern)

```python
from saikei_civil.tool.ifc import Ifc

# Get IFC file (automatically uses Bonsai or standalone)
ifc_file = Ifc.get()

# Check if file exists
if Ifc.has_file():
    ...

# Check mode
if Ifc.is_bonsai_mode():
    print("Using Bonsai's IFC file")
```

**NEVER do this:**
```python
# WRONG - bypasses integration
from saikei_civil.core.ifc_manager.manager import NativeIfcManager
ifc = NativeIfcManager.get_file()  # Don't access directly!
```

### 2. Operator Pattern (ALWAYS use for IFC operations)

```python
from saikei_civil.civil.ifc_operator import execute_civil_operator

class CIVIL_OT_my_operation(bpy.types.Operator):
    bl_idname = "civil.my_operation"
    bl_label = "My Operation"
    bl_options = {"REGISTER", "UNDO"}  # ← Required for undo
    
    def execute(self, context):
        return execute_civil_operator(self, context)  # ← Wrapper handles Bonsai/standalone
    
    def _execute(self, context):  # ← Actual implementation
        from saikei_civil.tool.ifc import Ifc
        ifc_file = Ifc.get()
        # ... do work ...
        return {"FINISHED"}
```

### 3. Element Linking

```python
from saikei_civil.civil.ifc_operator import link_element, unlink_element

# After creating IFC entity and Blender object
link_element(ifc_entity, blender_object)

# Before removing
unlink_element(ifc_entity=entity)
```

### 4. Georeferencing Access

```python
from saikei_civil.tool.ifc import Ifc

# Check if georeferencing is available
def has_georeferencing():
    ifc = Ifc.get()
    if not ifc:
        return False
    return len(ifc.by_type("IfcMapConversion")) > 0

# Get CRS info (works with Bonsai or standalone)
def get_crs_name():
    ifc = Ifc.get()
    if not ifc:
        return None
    crs_list = ifc.by_type("IfcProjectedCRS")
    if crs_list:
        return crs_list[0].Name
    return None
```

### 5. Data Caching (for UI performance)

```python
class AlignmentData:
    data = {}
    is_loaded = False
    
    @classmethod
    def refresh(cls):
        cls.is_loaded = False
    
    @classmethod
    def ensure_loaded(cls):
        if not cls.is_loaded:
            cls.load()
```

---

## Technical Architecture

### Data Flow Pattern
```
IFC File (Source of Truth)
        ↓
   Design Work
        ↓
 (Already in IFC)
        ↓
    Save IFC
        ↓
No conversion needed!
```

### Three Data Stores (Must Stay in Sync)

| Store | Contents | Undo Mechanism |
|-------|----------|----------------|
| **IFC File** | Actual data (IfcAlignment, etc.) | `ifc_file.undo()` |
| **Element Maps** | `id_map`, `guid_map` | Custom `rollback()` / `commit()` |
| **Blender Objects** | Visual representation | `bl_options = {"UNDO"}` |

### Key Architectural Principles

1. **IFC-First Design**
   - ALL civil engineering data lives in the IFC file
   - ZERO data stored in Blender's custom properties (except linking)
   - IFC file kept in memory during session

2. **Minimal Blender Storage**
   - Blender objects store only 3 properties:
     - `ifc_definition_id` - Link to IFC entity
     - `ifc_class` - Type of IFC entity  
     - `GlobalId` - IFC standard identifier
   - Everything else comes from IFC

3. **Bonsai Deference**
   - When Bonsai is available, USE IT
   - Don't duplicate what Bonsai already does well
   - Especially: file management, undo/redo, georeferencing

---

## Target Directory Structure

```
saikei_civil/
├── __init__.py                    # Extension entry point
├── blender_manifest.toml          # Blender extension manifest
├── preferences.py
│
├── core/                          # Layer 1: Pure Python (NO bpy imports)
│   ├── ifc_manager/
│   │   ├── manager.py             # NativeIfcManager (standalone fallback)
│   │   ├── transaction.py         # TransactionManager
│   │   └── ...
│   ├── horizontal_alignment/
│   ├── vertical_alignment/
│   └── components/
│
├── tool/                          # Layer 2: Blender implementations
│   ├── ifc.py                     # ← KEY: Unified IFC access (Bonsai bridge)
│   ├── blender.py
│   ├── alignment.py
│   └── georeference.py            # ← Defers to Bonsai when available
│
├── civil/                         # Layer 3: UI (mirrors Bonsai's bim/)
│   ├── __init__.py                # Registration hub
│   ├── prop.py                    # Global CivilProperties
│   ├── handler.py                 # Event handlers
│   ├── ifc_operator.py            # ← KEY: Bonsai integration bridge
│   │
│   └── module/                    # Feature modules
│       ├── project/
│       │   ├── prop.py            # CivilObjectProperties
│       │   └── ...
│       ├── alignment/
│       │   ├── prop.py            # CivilAlignmentProperties
│       │   ├── data.py            # AlignmentData cache
│       │   ├── ui.py              # Panels (N-panel + Properties Editor)
│       │   └── operator.py
│       ├── corridor/
│       ├── georef/                # ← Minimal: mostly defers to Bonsai
│       └── cross_section/
│
└── tools/                         # Toolbar tools (optional)
    ├── pi_tool.py
    └── pvi_tool.py
```

---

## Property Naming Conventions

| Type | Prefix | Example |
|------|--------|---------|
| Scene PropertyGroup | `Civil*Properties` | `CivilAlignmentProperties` |
| Object PropertyGroup | `CivilObjectProperties` | - |
| Panel class | `CIVIL_PT_*` | `CIVIL_PT_alignments` |
| Operator class | `CIVIL_OT_*` | `CIVIL_OT_add_alignment` |
| UIList class | `CIVIL_UL_*` | `CIVIL_UL_alignments` |

**Note:** Use `Civil*` prefix, NOT `BIM*` or `BC_*` to avoid conflicts with Bonsai.

---

## Development Progress

### Phase 1: Foundation (COMPLETE ✅)
| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 0 | Native IFC Foundation | ✅ Complete |
| Sprint 1 | Horizontal Alignments (PI-driven) | ✅ Complete |
| Sprint 2 | Georeferencing | ✅ Complete (deferring to Bonsai) |
| Sprint 3 | Vertical Alignments (PVI-driven) | ✅ Complete |

### Phase 2: Corridor Modeling (IN PROGRESS)
| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 4 | Cross-Sections | ✅ Complete |
| Sprint 5 | Corridor Generation | 🚧 In Progress |
| Sprint 6 | Advanced Geometry | 📋 Planned |

### Current Refactoring: Bonsai Integration
- [ ] Create `civil/` module structure
- [ ] Implement `ifc_operator.py` bridge
- [ ] Update `tool/ifc.py` with Bonsai detection
- [ ] Migrate operators to use `execute_civil_operator`
- [ ] Add georeferencing deferral to Bonsai
- [ ] Create multi-location UI panels

---

## IFC 4.3 Compliance

### Supported Entities
- IfcProject, IfcSite, IfcRoad
- IfcAlignment, IfcAlignmentHorizontal, IfcAlignmentVertical
- IfcAlignmentSegment, IfcAlignmentHorizontalSegment, IfcAlignmentVerticalSegment
- IfcMapConversion, IfcProjectedCRS (via Bonsai when available)
- IfcOpenCrossProfileDef, IfcCompositeProfileDef
- IfcSectionedSolidHorizontal (corridor)

### Spatial Hierarchy
```
IfcProject
└── IfcSite
    └── IfcRoad
        └── IfcAlignment
            ├── IfcAlignmentHorizontal
            │   └── IfcAlignmentSegment(s)
            └── IfcAlignmentVertical
                └── IfcAlignmentSegment(s)
```

---

## Testing Commands

```python
# In Blender Python console:

# Test 1: Check Bonsai detection
from saikei_civil.tool.ifc import Ifc
print(f"Bonsai mode: {Ifc.is_bonsai_mode()}")
print(f"Has file: {Ifc.has_file()}")

# Test 2: Check properties registered
import bpy
print(hasattr(bpy.types.Scene, 'CivilProperties'))
print(hasattr(bpy.types.Scene, 'CivilAlignmentProperties'))
print(hasattr(bpy.types.Object, 'CivilObjectProperties'))

# Test 3: Check georeferencing
ifc = Ifc.get()
if ifc:
    print(f"Has georef: {len(ifc.by_type('IfcMapConversion')) > 0}")
```

---

## Debugging Tips

1. **Check IFC file exists**: `Ifc.has_file()`
2. **Check mode**: `Ifc.is_bonsai_mode()` 
3. **Verify linking**: `obj.BIMObjectProperties.ifc_definition_id` or `obj.CivilObjectProperties.ifc_definition_id`
4. **Console logging**: Check Blender System Console (Window > Toggle System Console on Windows)
5. **IFC validation**: Open saved IFC in external viewer (Solibri, FreeCAD, BIMcollab)

---

## Resources

### Documentation
- IFC 4.3 Spec: https://ifc43-docs.standards.buildingsmart.org/
- IfcOpenShell: https://docs.ifcopenshell.org/
- Bonsai Docs: https://docs.bonsaibim.org/
- Bonsai Wiki: https://wiki.osarch.org/
- AASHTO Green Book (design standards)

### Community
- OSArch Forum: https://community.osarch.org/
- buildingSMART: https://www.buildingsmart.org/

---

## Contact & Ownership

**Developer:** Michael Holtz (Desert Springs Civil Engineering PLLC)  
**Project:** Open-source, community-driven  
**License:** GPL v3 (for Bonsai ecosystem compatibility)

---

*Last Updated: January 2026*  
*Saikei Civil - Native IFC for Horizontal Construction*
