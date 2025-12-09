# Saikei Civil Architecture Alignment Report

## Executive Summary

This report analyzes the IfcOpenShell/Bonsai architecture to guide Saikei Civil's development. Bonsai represents best-in-class design for IFC-based Blender extensions. Saikei should adopt its core architectural patterns while maintaining appropriate scope for civil infrastructure.

---

## 1. IfcOpenShell Repository Overview

### Structure
```
IfcOpenShell/
├── src/
│   ├── ifcopenshell-python/    # Core Python library
│   │   ├── ifcopenshell/
│   │   │   ├── api/            # High-level IFC authoring API (37+ modules)
│   │   │   ├── util/           # Utility functions (30+ modules)
│   │   │   ├── file.py         # IFC file class
│   │   │   └── entity_instance.py
│   │   └── test/
│   │
│   ├── bonsai/                 # Blender addon
│   │   └── bonsai/
│   │       ├── core/           # Platform-agnostic business logic
│   │       ├── tool/           # Blender-specific implementations
│   │       └── bim/module/     # UI modules (58 modules)
│   │
│   ├── ifcgeom/                # C++ geometry engine
│   ├── ifcparse/               # C++ parser
│   └── [18+ other tools]       # ifc4d, ifc5d, ifcclash, etc.
│
└── test/                       # Core tests
```

---

## 2. Bonsai's Three-Layer Architecture (ADOPT THIS)

### The Pattern Saikei Must Follow

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 3: BIM MODULES                        │
│  bonsai/bim/module/{module}/                                   │
│  ├── operator.py   (Blender operators - user actions)          │
│  ├── ui.py         (Panels, menus)                             │
│  ├── prop.py       (Property groups)                           │
│  └── __init__.py   (Registration)                              │
│                                                                 │
│  Operators call CORE functions with TOOL implementations       │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 2: TOOLS                              │
│  bonsai/tool/                                                  │
│                                                                 │
│  Blender-specific implementations of core interfaces           │
│  @classmethod pattern for all methods                          │
│                                                                 │
│  Example: tool.Ifc.get_entity(obj) → ifcopenshell.entity       │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 1: CORE                               │
│  bonsai/core/                                                  │
│                                                                 │
│  Pure Python business logic                                    │
│  NO Blender imports (use TYPE_CHECKING)                        │
│  Receives tools via dependency injection                       │
│  Testable without Blender                                      │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 IFCOPENSHELL API                               │
│  ifcopenshell.api.{module}.{function}()                        │
│                                                                 │
│  All IFC modifications go through here                         │
│  Handles schema differences, relationships, cleanup            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Key Patterns to Adopt

### Pattern 1: Interface-First Design

**Define interfaces in `core/tool.py`:**
```python
# bonsai/core/tool.py
@interface  # Converts all methods to @classmethod @abstractmethod
class Georeference:
    def add_georeferencing(cls): pass
    def import_projected_crs(cls): pass
    def export_coordinate_operation(cls): pass
    def set_model_origin(cls): pass
```

**Implement in `tool/georeference.py`:**
```python
# bonsai/tool/georeference.py
class Georeference(bonsai.core.tool.Georeference):
    @classmethod
    def add_georeferencing(cls):
        ifc = tool.Ifc.get()
        ifcopenshell.api.georeference.add_georeferencing(ifc)

    @classmethod
    def import_projected_crs(cls):
        # Blender-specific implementation
        props = bpy.context.scene.BIMGeoreferenceProperties
        # ... populate from IFC
```

### Pattern 2: Core Functions with Dependency Injection

```python
# bonsai/core/georeference.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import bonsai.tool as tool

def edit_georeferencing(ifc: type[tool.Ifc], georeference: type[tool.Georeference]) -> None:
    ifc.run(
        "georeference.edit_georeferencing",
        projected_crs=georeference.export_projected_crs(),
        coordinate_operation=georeference.export_coordinate_operation(),
    )
    georeference.disable_editing()
    georeference.set_model_origin()
```

### Pattern 3: Operators Call Core with Tools

```python
# bonsai/bim/module/georeference/operator.py
class EditGeoreferencing(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.edit_georeferencing"
    bl_label = "Edit Georeferencing"
    bl_options = {"REGISTER", "UNDO"}

    def _execute(self, context):
        core.edit_georeferencing(tool.Ifc, tool.Georeference)  # Pass CLASSES, not instances
```

### Pattern 4: IFC Operator Base Class

```python
# bonsai/tool/ifc.py
class Ifc(bonsai.core.tool.Ifc):
    class Operator:
        """Base class for IFC-modifying operators"""

        @final
        def execute(self, context):
            IfcStore.execute_ifc_operator(self, context)
            return {"FINISHED"}

        def _execute(self, context):
            raise NotImplementedError("Implement _execute method")
```

---

## 4. ifcopenshell.api Usage

### The Alignment API (Most Relevant for Saikei)

Located in `src/ifcopenshell-python/ifcopenshell/api/alignment/`:

```python
# Available functions
ifcopenshell.api.alignment.create(ifc_file, name="My Alignment")
ifcopenshell.api.alignment.create_by_pi_method(ifc_file, ...)
ifcopenshell.api.alignment.add_vertical_layout(ifc_file, alignment=..., pvis=[...])
ifcopenshell.api.alignment.layout_horizontal_alignment_by_pi_method(ifc_file, ...)
ifcopenshell.api.alignment.layout_vertical_alignment_by_pi_method(ifc_file, ...)
ifcopenshell.api.alignment.get_horizontal_layout(ifc_file, alignment)
ifcopenshell.api.alignment.get_vertical_layout(ifc_file, alignment)
ifcopenshell.api.alignment.get_layout_segments(ifc_file, layout)
# ... 45+ alignment functions
```

### The Georeference API

```python
ifcopenshell.api.georeference.add_georeferencing(ifc_file)
ifcopenshell.api.georeference.edit_georeferencing(ifc_file, projected_crs={...}, coordinate_operation={...})
ifcopenshell.api.georeference.edit_true_north(ifc_file, true_north=[...])
ifcopenshell.api.georeference.edit_wcs(ifc_file, ...)
ifcopenshell.api.georeference.remove_georeferencing(ifc_file)
```

### Other Relevant APIs

```python
# Spatial
ifcopenshell.api.spatial.assign_container(ifc_file, products=[...], relating_structure=site)

# Root entity creation
ifcopenshell.api.root.create_entity(ifc_file, ifc_class="IfcRoad", name="Highway 1")

# Geometry
ifcopenshell.api.geometry.add_representation(ifc_file, context=..., items=[...])
```

---

## 5. Testing Patterns

### Bonsai's Prophecy Pattern (Mock Framework)

```python
# test/core/bootstrap.py - Creates mock fixtures
@pytest.fixture
def georeference():
    prophet = Prophecy(bonsai.core.tool.Georeference)
    yield prophet
    prophet.verify()

# test/core/test_georeference.py - Uses mocks
class TestEditGeoreferencing:
    def test_run(self, ifc, georeference):
        georeference.export_projected_crs().should_be_called().will_return("crs_attrs")
        georeference.export_coordinate_operation().should_be_called().will_return("op_attrs")
        ifc.run("georeference.edit_georeferencing",
                projected_crs="crs_attrs",
                coordinate_operation="op_attrs").should_be_called()
        georeference.disable_editing().should_be_called()
        georeference.set_model_origin().should_be_called()

        subject.edit_georeferencing(ifc, georeference)
```

### Test Directory Structure
```
bonsai/test/
├── core/           # Core logic tests (NO Blender)
│   ├── bootstrap.py  # Prophecy fixtures
│   └── test_*.py     # Pure Python tests
├── tool/           # Tool tests (WITH Blender via pytest-blender)
└── bim/            # Integration tests
```

---

## 6. Recommended Saikei Architecture

### Directory Structure

```
saikei_civil/
├── __init__.py                 # Entry point, registration
├── blender_manifest.toml       # Blender 4.2+ extension manifest
│
├── core/                       # Layer 1: Business Logic
│   ├── __init__.py
│   ├── tool.py                 # Interface definitions
│   ├── alignment.py            # Horizontal alignment logic
│   ├── vertical_alignment.py   # Vertical alignment logic
│   ├── georeferencing.py       # CRS and coordinate logic
│   ├── cross_section.py        # Cross-section logic
│   └── corridor.py             # Corridor generation logic
│
├── tool/                       # Layer 2: Blender Implementations
│   ├── __init__.py             # Exports all tool classes
│   ├── ifc.py                  # IFC file operations
│   ├── blender.py              # Blender utilities
│   ├── alignment.py            # Alignment tool implementation
│   ├── georeferencing.py       # Georef tool implementation
│   └── visualizer.py           # 3D visualization
│
├── bim/                        # Layer 3: Blender Integration
│   ├── __init__.py             # Module registration
│   └── module/
│       ├── alignment/
│       │   ├── __init__.py
│       │   ├── operator.py
│       │   ├── prop.py
│       │   └── ui.py
│       ├── vertical_alignment/
│       ├── georeferencing/
│       ├── cross_section/
│       └── corridor/
│
└── tests/
    ├── core/
    └── tool/
```

### Core Interface Definitions

```python
# saikei_civil/core/tool.py

def interface(cls):
    """Decorator that converts all methods to @classmethod @abstractmethod"""
    import abc
    for name, method in cls.__dict__.items():
        if callable(method) and not name.startswith('_'):
            setattr(cls, name, classmethod(abc.abstractmethod(method)))
    cls.__original_qualname__ = cls.__qualname__
    return cls

@interface
class Ifc:
    def get(cls): pass
    def run(cls, command: str, **kwargs): pass
    def get_entity(cls, obj): pass
    def get_object(cls, entity): pass
    def link(cls, entity, obj): pass

@interface
class Blender:
    def create_ifc_object(cls, ifc_class, name): pass
    def get_selected_objects(cls): pass
    def get_active_object(cls): pass
    def update_viewport(cls): pass

@interface
class Alignment:
    def create_horizontal(cls, name, pis): pass
    def get_pis(cls, alignment): pass
    def compute_curve_geometry(cls, pi_data): pass
    def update_visualization(cls, alignment): pass

@interface
class Georeference:
    def add_georeferencing(cls): pass
    def get_crs(cls): pass
    def set_crs(cls, epsg_code): pass
    def transform_coordinates(cls, local_coords): pass
```

---

## 7. Compatibility with Bonsai

### Shared Infrastructure

| Component | Bonsai Uses | Saikei Should Use |
|-----------|-------------|-------------------|
| IFC Library | ifcopenshell | ifcopenshell (same) |
| API Layer | ifcopenshell.api | ifcopenshell.api (same) |
| Georeference | bonsai.tool.Georeference | Can integrate/extend |
| Spatial | bonsai.tool.Spatial | Can leverage |
| IFC Store | bonsai.bim.ifc.IfcStore | Consider sharing or mirroring pattern |

### Integration Points

1. **Same IFC File**: Both addons can work on the same .ifc file
   - Bonsai handles buildings, sites, spatial structure
   - Saikei handles alignments, corridors, earthwork
   - No conflicts as long as both use ifcopenshell.api

2. **Shared Georeferencing**:
   - Bonsai already has `ifcopenshell.api.georeference`
   - Saikei should use the same API, not duplicate
   - Consider UI that complements rather than duplicates Bonsai's

3. **Complementary Entities**:
   ```
   IfcProject (shared)
   └── IfcSite (shared)
       ├── IfcBuilding (Bonsai)
       │   └── IfcBuildingStorey
       │       └── IfcWall, IfcSlab, etc.
       └── IfcRoad (Saikei)
           ├── IfcAlignment
           │   ├── IfcAlignmentHorizontal
           │   └── IfcAlignmentVertical
           └── IfcFacilityPart
   ```

### Recommended Integration Strategy

1. **Don't Duplicate**: If Bonsai has a feature (georeferencing, spatial structure), use or extend it
2. **Namespace Separation**: Use `SAIKEI_` prefix (not `BIM_`) to avoid conflicts
3. **Panel Integration**: Consider placing Saikei panels in Bonsai's sidebar category or create "Saikei Civil" tab
4. **IFC Store**: Either:
   - Option A: Import and use `bonsai.bim.ifc.IfcStore` directly
   - Option B: Create compatible `saikei.bim.ifc.SaikeiStore` that mirrors the pattern

---

## 8. Key Recommendations

### MUST DO

1. **Adopt Three-Layer Architecture**: Core → Tool → BIM Module
2. **Use ifcopenshell.api**: Never manipulate IFC entities directly
3. **Interface-First Design**: Define interfaces before implementations
4. **IFC-First Philosophy**: IFC file is the database, Blender is visualization
5. **TYPE_CHECKING Pattern**: Avoid circular imports

### SHOULD DO

1. **Mirror Bonsai's Naming**: Study their conventions for consistency
2. **Use Same Testing Pattern**: Prophecy-based mocks for core tests
3. **Leverage Existing APIs**: Use `ifcopenshell.api.alignment` extensively
4. **Consider Bonsai Integration**: Design for potential future merging/compatibility

### AVOID

1. ❌ Storing data in Blender custom properties (use IFC)
2. ❌ Direct entity manipulation (use ifcopenshell.api)
3. ❌ Tight coupling to Blender APIs in core logic
4. ❌ Duplicating Bonsai functionality (georeferencing, spatial)
5. ❌ Different architectural patterns (stay consistent)

---

## 9. Example Implementation

### Creating an Alignment (Full Stack)

**Step 1: Core Logic** (`core/alignment.py`):
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import saikei_civil.tool as tool

def create_horizontal_alignment(
    ifc: type[tool.Ifc],
    alignment_tool: type[tool.Alignment],
    blender: type[tool.Blender],
    name: str,
    pis: list[dict],
) -> "ifcopenshell.entity_instance":
    """Create horizontal alignment using PI method."""

    # 1. Create IFC entities via API
    alignment = ifc.run("alignment.create_by_pi_method",
        name=name,
        horizontal_pi_data=pis
    )

    # 2. Create Blender visualization
    obj = blender.create_alignment_curve(name)

    # 3. Link entity to object
    ifc.link(alignment, obj)

    # 4. Update visualization from IFC data
    alignment_tool.update_visualization(alignment)

    return alignment
```

**Step 2: Tool Implementation** (`tool/alignment.py`):
```python
import saikei_civil.core.tool

class Alignment(saikei_civil.core.tool.Alignment):
    @classmethod
    def update_visualization(cls, alignment):
        import bpy
        obj = tool.Ifc.get_object(alignment)
        if not obj:
            return

        # Get horizontal layout
        h_layout = ifcopenshell.api.alignment.get_horizontal_layout(
            tool.Ifc.get(), alignment
        )

        # Get segments and create curve
        segments = ifcopenshell.api.alignment.get_layout_segments(
            tool.Ifc.get(), h_layout
        )

        # Update Blender curve from segments
        cls._update_curve_from_segments(obj, segments)
```

**Step 3: Operator** (`bim/module/alignment/operator.py`):
```python
import saikei_civil.core.alignment as core
import saikei_civil.tool as tool

class SAIKEI_OT_create_alignment(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "saikei.create_alignment"
    bl_label = "Create Alignment"
    bl_options = {"REGISTER", "UNDO"}

    name: bpy.props.StringProperty(name="Name", default="Alignment")

    def _execute(self, context):
        props = context.scene.SaikeiAlignmentProperties
        pis = self._get_pis_from_props(props)

        core.create_horizontal_alignment(
            tool.Ifc,
            tool.Alignment,
            tool.Blender,
            name=self.name,
            pis=pis
        )
```

---

## 10. Conclusion

Saikei Civil should fully embrace the Bonsai architectural pattern:

1. **Architecture**: Three-layer separation (Core → Tool → BIM)
2. **IFC Handling**: Use ifcopenshell.api exclusively
3. **Testing**: Mock-based core tests, integration tests with Blender
4. **Compatibility**: Design for seamless operation alongside Bonsai
5. **Scope**: Focus on civil infrastructure, don't duplicate Bonsai features

The Bonsai architecture has proven itself with 58 modules, 100k+ lines of code, and a growing community. By following the same patterns, Saikei will be maintainable, testable, and compatible with the broader OpenBIM ecosystem.

---

*Report generated: December 2025*
*Based on analysis of IfcOpenShell v0.8.0 / Bonsai*