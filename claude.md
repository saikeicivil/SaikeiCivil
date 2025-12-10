# CLAUDE.md - Saikei Civil Project Context

## Project Identity

**Name:** Saikei Civil (formerly BlenderCivil)  
**Pronunciation:** "SIGH-kay" (栽景 - Japanese for "planted landscape")  
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

3. **Golden Pattern**
   ```python
   # 1. GET IFC FILE
   ifc = NativeIfcManager.get_file()
   
   # 2. CREATE/MODIFY IFC ENTITY
   entity = ifc.create_entity("IfcAlignment", ...)
   
   # 3. CREATE BLENDER VISUALIZATION
   obj = create_blender_object(...)
   
   # 4. LINK THEM
   NativeIfcManager.link_object(obj, entity)
   ```

### Directory Structure
```
saikei_civil/
├── __init__.py                    # Extension entry point
├── blender_manifest.toml          # Blender extension manifest
│
├── core/                          # Business logic (IFC operations)
│   ├── __init__.py
│   ├── native_ifc_manager.py      # IFC file lifecycle management
│   ├── native_ifc_alignment.py    # Horizontal alignment (PI-driven)
│   ├── native_ifc_vertical_alignment.py  # Vertical alignment (PVI-driven)
│   ├── native_ifc_georeferencing.py      # Coordinate transformations
│   ├── native_ifc_cross_section.py       # Cross-section assemblies
│   ├── crs_searcher.py            # CRS database search
│   ├── alignment_visualizer.py    # 3D visualization
│   ├── dependency_manager.py      # Alignment connectivity
│   └── components/                # Cross-section components
│       ├── __init__.py
│       ├── base_component.py
│       ├── lane_component.py
│       ├── shoulder_component.py
│       ├── curb_component.py
│       └── ditch_component.py
│
├── operators/                     # Blender operators (user actions)
│   ├── __init__.py
│   ├── file_operators.py          # Save/Load IFC
│   ├── alignment_operators.py     # Horizontal alignment ops
│   ├── pi_operators.py            # PI management
│   ├── vertical_operators.py      # Vertical alignment ops
│   ├── georef_operators.py        # Georeferencing ops
│   ├── cross_section_operators.py # Cross-section ops
│   └── validation_operators.py    # Design validation
│
├── ui/                            # User interface
│   ├── __init__.py
│   ├── alignment_panel.py         # Main alignment panel
│   ├── georef_properties.py       # Georeferencing properties
│   ├── vertical_properties.py     # Vertical alignment properties
│   ├── cross_section_properties.py # Cross-section properties
│   ├── dependency_panel.py
│   ├── validation_panel.py
│   └── panels/
│       ├── __init__.py
│       ├── georeferencing_panel.py
│       ├── vertical_alignment_panel.py
│       └── cross_section_panel.py
│
├── templates/                     # AASHTO standard templates
│   ├── __init__.py
│   ├── aashto_templates.py
│   └── custom_templates.json
│
└── tests/                         # Test suite
    ├── __init__.py
    ├── test_alignment.py
    ├── test_vertical_alignment.py
    ├── test_georeferencing.py
    └── test_cross_section.py
```

---

## Development Progress

### Phase 1: Foundation (COMPLETE ✅)
| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 0 | Native IFC Foundation | ✅ Complete |
| Sprint 1 | Horizontal Alignments (PI-driven) | ✅ Complete |
| Sprint 2 | Georeferencing | ✅ Complete |
| Sprint 3 | Vertical Alignments (PVI-driven) | ✅ Complete |

### Phase 2: Corridor Modeling (IN PROGRESS)
| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 4 | Cross-Sections | ✅ Complete |
| Sprint 5 | Corridor Generation | 🚧 In Progress |
| Sprint 6 | Advanced Geometry | 📋 Planned |
| Sprint 7 | Materials & Quantities | 📋 Planned |
| Sprint 8 | Polish & Testing | 📋 Planned |

### Phase 3 & 4: Industry Integration & Market Leadership
Sprints 9-16 planned for import/export, collaboration, visualization, and advanced features.

---

## Key Technical Implementations

### Horizontal Alignments (Sprint 1)
- **PI-Driven Design**: Control points (Points of Intersection) drive geometry
- **Automatic Segment Generation**: Tangents and curves generated from PIs
- **Curve Types**: LINE, CIRCULARARC (CLOTHOID planned)
- **IFC Entities**: IfcAlignment, IfcAlignmentHorizontal, IfcAlignmentSegment

### Vertical Alignments (Sprint 3)
- **PVI-Driven Design**: Points of Vertical Intersection control grades
- **Parabolic Curves**: Standard vertical curves with K-value design
- **AASHTO Compliance**: Design speed, sight distance calculations
- **IFC Entities**: IfcAlignmentVertical, IfcAlignmentVerticalSegment

### Georeferencing (Sprint 2)
- **6,000+ CRS Support**: Via PyProj integration
- **Sub-millimeter Precision**: At 20km from false origin
- **IFC Entities**: IfcMapConversion, IfcProjectedCRS
- **Digital Twin Ready**: Cesium, QGIS compatibility

### Cross-Sections (Sprint 4)
- **Component-Based Assembly**: Modular design system
- **AASHTO Templates**: Standard road sections
- **Parametric Constraints**: Station-based variations
- **IFC Entities**: IfcOpenCrossProfileDef, IfcCompositeProfileDef

### Corridor Modeling (Sprint 5)
- **IfcSectionedSolidHorizontal**: 3D corridor geometry
- **Multi-LOD Performance**: Optimized mesh generation
- **Integration**: Combines H+V alignments with cross-sections

---

## Code Style & Patterns

### Naming Conventions
- **Classes**: PascalCase (`NativeIfcManager`, `CrossSectionAssembly`)
- **Functions/Methods**: snake_case (`create_alignment`, `add_pi`)
- **Properties**: snake_case (`ifc_definition_id`)
- **Operators**: `BC_OT_*` pattern (`BC_OT_create_alignment`)
- **Panels**: `VIEW3D_PT_*` pattern (`VIEW3D_PT_bc_alignment`)

### Blender Extension Patterns
Follow Bonsai/BlenderBIM patterns:
- Operators in `operators/` directory
- UI panels in `ui/panels/` directory
- Properties in `ui/*_properties.py`
- Core logic in `core/` directory

### IFC Operations Pattern
```python
# Always get file first
ifc = NativeIfcManager.get_file()
if not ifc:
    return {'CANCELLED'}

# Create IFC entity
entity = ifc.create_entity("IfcSomeEntity",
    GlobalId=ifcopenshell.guid.new(),
    Name="My Entity"
)

# Create Blender visualization
obj = bpy.data.objects.new("My Object", mesh)

# Link them
NativeIfcManager.link_object(obj, entity)
```

### Registration Pattern
```python
classes = (
    MyOperator,
    MyPanel,
    MyPropertyGroup,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # Register properties
    bpy.types.Scene.my_props = bpy.props.PointerProperty(type=MyPropertyGroup)

def unregister():
    del bpy.types.Scene.my_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

---

## Dependencies

### Required
- **Blender 4.5+**: Extension system
- **IfcOpenShell**: IFC file operations
- **NumPy**: Mathematical calculations

### Optional
- **PyProj**: Coordinate transformations (georeferencing)

### Python Packages Location
Dependencies are managed via `blender_manifest.toml` wheels or pip with `--break-system-packages`.

---

## Testing

### Test Structure
- Unit tests in `tests/` directory
- Integration tests for complete workflows
- 100% pass rate target

### Running Tests
```python
# In Blender Python console
import sys
sys.path.insert(0, "C:/GitHub/Saikei-Civil/saikei_civil")
from tests import test_alignment
test_alignment.run_tests()
```

---

## IFC 4.3 Compliance

### Supported Entities
- IfcProject, IfcSite, IfcRoad
- IfcAlignment, IfcAlignmentHorizontal, IfcAlignmentVertical
- IfcAlignmentSegment, IfcAlignmentHorizontalSegment, IfcAlignmentVerticalSegment
- IfcMapConversion, IfcProjectedCRS
- IfcOpenCrossProfileDef, IfcCompositeProfileDef
- IfcSectionedSolidHorizontal (corridor)
- IfcRelNests, IfcRelAggregates

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

## Common Tasks

### Adding a New Operator
1. Create operator class in `operators/` (follow `BC_OT_` naming)
2. Add to `operators/__init__.py` imports and registration
3. Add button in appropriate panel

### Adding a New Panel
1. Create panel class in `ui/panels/` (follow `VIEW3D_PT_bc_` naming)
2. Set `bl_category = "Saikei Civil"` for sidebar tab
3. Add to `ui/panels/__init__.py` registration

### Adding New IFC Entity Support
1. Add creation logic in appropriate `core/` module
2. Create Blender visualization
3. Link using `NativeIfcManager.link_object()`
4. Add UI for user interaction

---

## Important Files to Know

| File | Purpose |
|------|---------|
| `__init__.py` | Extension entry, bl_info, registration |
| `blender_manifest.toml` | Blender 4.5+ extension manifest |
| `core/native_ifc_manager.py` | Central IFC file management |
| `core/native_ifc_alignment.py` | Horizontal alignment engine |
| `core/native_ifc_vertical_alignment.py` | Vertical alignment engine |
| `ui/panels/*.py` | All UI panels |
| `operators/*.py` | All user operations |

---

## Quick Reference: IFC Entity Retrieval

```python
# Get IFC file
ifc = NativeIfcManager.get_file()

# Get entity from Blender object
entity = NativeIfcManager.get_entity(blender_obj)

# Get all alignments
alignments = ifc.by_type("IfcAlignment")

# Get entity by ID
entity = ifc.by_id(entity_id)
```

---

## Debugging Tips

1. **Check IFC file exists**: `NativeIfcManager.get_file() is not None`
2. **Verify linking**: `obj.get("ifc_definition_id")` should return entity ID
3. **Console logging**: Use `print()` statements, check Blender System Console
4. **IFC validation**: Open saved IFC in external viewer (Solibri, FreeCAD)

---

## Resources

### Documentation
- IFC 4.3 Spec: https://ifc43-docs.standards.buildingsmart.org/
- IfcOpenShell: https://docs.ifcopenshell.org/
- Bonsai Wiki: https://wiki.osarch.org/
- AASHTO Green Book (design standards)

### Community
- OSArch Forum: https://community.osarch.org/
- buildingSMART: https://www.buildingsmart.org/

---

## Contact & Ownership

**Developer:** Michael (Desert Springs Civil Engineering PLLC)  
**Project:** Open-source, community-driven  
**License:** [Specify license]

---

*Last Updated: December 2025*  
*Saikei Civil - Native IFC for Horizontal Construction*
