# Saikei Civil → Bonsai Integration: Refactoring Guide

## For Claude Code Implementation

**Repository Path:** `C:\Users\amish\OneDrive\OneDrive Documents\GitHub\BlenderCivil\blendercivil`

**Objective:** Refactor Saikei Civil to integrate seamlessly with Bonsai BIM while maintaining standalone functionality when Bonsai is not installed.

---

## Table of Contents

1. [Current Architecture](#1-current-architecture)
2. [Target Architecture](#2-target-architecture)
3. [Phase 1: Core Infrastructure](#3-phase-1-core-infrastructure)
4. [Phase 2: IFC Bridge Layer](#4-phase-2-ifc-bridge-layer)
5. [Phase 3: UI Restructuring](#5-phase-3-ui-restructuring)
6. [Phase 4: Operator Refactoring](#6-phase-4-operator-refactoring)
7. [Phase 5: Property Registration](#7-phase-5-property-registration)
8. [Phase 6: Toolbar Tools](#8-phase-6-toolbar-tools)
9. [Testing Requirements](#9-testing-requirements)
10. [Migration Checklist](#10-migration-checklist)

---

## 1. Current Architecture

### Current Directory Structure

```
saikei_civil/
├── __init__.py
├── blender_manifest.toml
├── preferences.py
│
├── core/                          # Layer 1: Pure Python ✓ KEEP
│   ├── tool.py
│   ├── logging_config.py
│   ├── station_formatting.py
│   ├── ifc_manager/
│   │   ├── manager.py             # NativeIfcManager
│   │   ├── transaction.py         # TransactionManager
│   │   ├── ifc_entities.py
│   │   └── blender_hierarchy.py
│   ├── horizontal_alignment/
│   ├── vertical_alignment/
│   └── components/
│
├── tool/                          # Layer 2: Blender implementations ✓ KEEP
│   ├── ifc.py
│   ├── blender.py
│   ├── alignment.py
│   └── ...
│
├── operators/                     # ⚠ REFACTOR → civil/module/*/operator.py
│   ├── alignment_operators.py
│   ├── pi_operators.py
│   ├── curve_operators.py
│   ├── vertical_operators.py
│   └── ...
│
└── ui/                            # ⚠ REFACTOR → civil/module/*/ui.py
    ├── alignment_panel.py
    ├── corridor_panel.py
    └── panels/
        └── ...
```

### Current Property Registration

```python
# Currently in __init__.py or scattered files
bpy.types.Scene.bc_alignment  # AlignmentProperties
# ... other scattered registrations
```

### Current IFC Access Pattern

```python
# Current: Direct manager access
from saikei_civil.core.ifc_manager.manager import NativeIfcManager
manager = NativeIfcManager.get_instance()
ifc_file = manager.file
```

---

## 2. Target Architecture

### Target Directory Structure

```
saikei_civil/
├── __init__.py                    # Main entry, delegates to civil/
├── blender_manifest.toml
├── preferences.py
│
├── core/                          # Layer 1: Pure Python (UNCHANGED)
│   └── ... (keep as-is)
│
├── tool/                          # Layer 2: Blender implementations
│   ├── ifc.py                     # ⚠ UPDATE: Add Bonsai bridge
│   ├── blender.py
│   ├── alignment.py
│   └── ...
│
├── civil/                         # Layer 3: UI (NEW - mirrors Bonsai's bim/)
│   ├── __init__.py                # Registration hub
│   ├── prop.py                    # Global CivilProperties
│   ├── handler.py                 # Event handlers
│   ├── ifc_operator.py            # Operator wrapper (NEW)
│   │
│   └── module/                    # Feature modules
│       ├── project/
│       │   ├── __init__.py
│       │   ├── prop.py
│       │   ├── data.py
│       │   ├── ui.py
│       │   └── operator.py
│       │
│       ├── alignment/
│       │   ├── __init__.py
│       │   ├── prop.py            # CivilAlignmentProperties
│       │   ├── data.py            # AlignmentData cache
│       │   ├── ui.py              # Panels (N-panel + Properties Editor)
│       │   └── operator.py        # All alignment operators
│       │
│       ├── corridor/
│       │   └── ...
│       │
│       ├── georef/
│       │   └── ...
│       │
│       └── cross_section/
│           └── ...
│
├── tools/                         # Toolbar tools (NEW)
│   ├── __init__.py
│   ├── pi_tool.py
│   ├── pvi_tool.py
│   └── cross_section_tool.py
│
├── operators/                     # DEPRECATED - migrate to civil/module/
└── ui/                            # DEPRECATED - migrate to civil/module/
```

---

## 3. Phase 1: Core Infrastructure

### 3.1 Create the civil/ module structure

**Create these files:**

#### `saikei_civil/civil/__init__.py`

```python
"""
Saikei Civil UI Layer - mirrors Bonsai's bim/ structure.
Handles all Blender UI, operators, and property registration.
"""

import bpy

from . import prop
from . import handler
from . import ifc_operator
from .module import project
from .module import alignment
from .module import corridor
from .module import georef
from .module import cross_section

modules = (
    project,
    alignment,
    corridor,
    georef,
    cross_section,
)


def register():
    """Register all civil UI components"""
    # Register global properties
    prop.register()
    
    # Register handlers
    handler.register()
    
    # Register each module
    for module in modules:
        module.register()


def unregister():
    """Unregister all civil UI components"""
    for module in reversed(modules):
        module.unregister()
    
    handler.unregister()
    prop.unregister()
```

#### `saikei_civil/civil/prop.py`

```python
"""
Global Civil Properties - registered at Scene level.
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    BoolProperty,
    StringProperty,
    IntProperty,
    PointerProperty,
)


class CivilProperties(PropertyGroup):
    """Global civil engineering settings"""
    
    # Integration mode
    use_bonsai_ifc: BoolProperty(
        name="Use Bonsai IFC",
        description="When enabled, use Bonsai's IFC file instead of standalone",
        default=True,
    )
    
    # Status
    is_initialized: BoolProperty(
        name="Initialized",
        default=False,
    )
    
    status_message: StringProperty(
        name="Status",
        default="",
    )


def register():
    bpy.utils.register_class(CivilProperties)
    bpy.types.Scene.CivilProperties = PointerProperty(type=CivilProperties)


def unregister():
    del bpy.types.Scene.CivilProperties
    bpy.utils.unregister_class(CivilProperties)
```

#### `saikei_civil/civil/handler.py`

```python
"""
Blender event handlers for Civil integration.
"""

import bpy
from bpy.app.handlers import persistent


@persistent
def on_load_post(dummy):
    """Called after a .blend file is loaded"""
    # Refresh civil data caches
    try:
        from .module.alignment.data import AlignmentData
        AlignmentData.refresh()
    except Exception as e:
        print(f"Saikei: Error refreshing alignment data: {e}")


@persistent  
def on_depsgraph_update(scene, depsgraph):
    """Called on depsgraph updates - handle object renames, etc."""
    # Check for object renames that might affect element maps
    pass


def register():
    bpy.app.handlers.load_post.append(on_load_post)
    # bpy.app.handlers.depsgraph_update_post.append(on_depsgraph_update)


def unregister():
    if on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_load_post)
```

#### `saikei_civil/civil/ifc_operator.py`

```python
"""
IFC Operator wrapper - integrates with Bonsai when available.
This is the KEY integration point.
"""

import bpy
from typing import Optional, Any


def is_bonsai_available() -> bool:
    """Check if Bonsai is installed and has an active IFC file"""
    try:
        from bonsai.bim.ifc import IfcStore
        return IfcStore.get_file() is not None
    except ImportError:
        return False


def get_ifc_file():
    """
    Get the IFC file, preferring Bonsai's if available.
    This is the primary way to access the IFC file throughout Saikei.
    """
    # Try Bonsai first
    try:
        from bonsai.bim.ifc import IfcStore
        file = IfcStore.get_file()
        if file:
            return file
    except ImportError:
        pass
    
    # Fall back to Saikei's manager
    try:
        from saikei_civil.core.ifc_manager.manager import NativeIfcManager
        manager = NativeIfcManager.get_instance()
        if manager:
            return manager.file
    except Exception:
        pass
    
    return None


def get_ifc_path() -> str:
    """Get the current IFC file path"""
    try:
        from bonsai.bim.ifc import IfcStore
        if IfcStore.path:
            return IfcStore.path
    except ImportError:
        pass
    
    try:
        from saikei_civil.core.ifc_manager.manager import NativeIfcManager
        manager = NativeIfcManager.get_instance()
        if manager:
            return manager.filepath or ""
    except Exception:
        pass
    
    return ""


def execute_civil_operator(operator, context) -> set:
    """
    Execute a Civil operator with proper transaction handling.
    
    Works with Bonsai if installed, otherwise uses Saikei's manager.
    
    Usage in operators:
        def execute(self, context):
            return execute_civil_operator(self, context)
        
        def _execute(self, context):
            # Your actual implementation
            return {"FINISHED"}
    """
    
    # Check if Bonsai is available and has a file
    if is_bonsai_available():
        # Use Bonsai's transaction system
        try:
            from bonsai.bim.ifc import IfcStore
            return IfcStore.execute_ifc_operator(operator, context)
        except Exception as e:
            operator.report({'ERROR'}, f"Bonsai operator error: {e}")
            return {"CANCELLED"}
    
    # Use Saikei's standalone transaction system
    try:
        from saikei_civil.core.ifc_manager.manager import NativeIfcManager
        manager = NativeIfcManager.get_instance()
        
        if not manager or not manager.file:
            operator.report({'ERROR'}, "No IFC file loaded")
            return {"CANCELLED"}
        
        # Begin transaction
        manager.begin_transaction()
        
        try:
            # Execute the operator's implementation
            result = operator._execute(context)
            
            # End transaction (commits)
            manager.end_transaction()
            
            return result
            
        except Exception as e:
            # Rollback on error
            manager.undo()
            operator.report({'ERROR'}, f"Operation failed: {e}")
            return {"CANCELLED"}
            
    except Exception as e:
        operator.report({'ERROR'}, f"Civil operator error: {e}")
        return {"CANCELLED"}


def link_element(ifc_entity, blender_object):
    """
    Link an IFC entity to a Blender object.
    Updates both Bonsai and Saikei element maps.
    """
    if is_bonsai_available():
        try:
            from bonsai.bim.ifc import IfcStore
            IfcStore.link_element(ifc_entity, blender_object)
        except Exception:
            pass
    
    # Also update Saikei's maps
    try:
        from saikei_civil.core.ifc_manager.manager import NativeIfcManager
        manager = NativeIfcManager.get_instance()
        if manager:
            manager.link_object(ifc_entity, blender_object)
    except Exception:
        pass
    
    # Set object properties
    if hasattr(blender_object, 'BIMObjectProperties'):
        blender_object.BIMObjectProperties.ifc_definition_id = ifc_entity.id()
    
    if hasattr(blender_object, 'CivilObjectProperties'):
        blender_object.CivilObjectProperties.ifc_definition_id = ifc_entity.id()
        blender_object.CivilObjectProperties.ifc_class = ifc_entity.is_a()
        if hasattr(ifc_entity, 'GlobalId'):
            blender_object.CivilObjectProperties.global_id = ifc_entity.GlobalId


def unlink_element(ifc_entity=None, blender_object=None):
    """Unlink an IFC entity from a Blender object"""
    if is_bonsai_available():
        try:
            from bonsai.bim.ifc import IfcStore
            if blender_object:
                IfcStore.unlink_element(obj=blender_object)
            elif ifc_entity:
                IfcStore.unlink_element(element=ifc_entity)
        except Exception:
            pass
    
    try:
        from saikei_civil.core.ifc_manager.manager import NativeIfcManager
        manager = NativeIfcManager.get_instance()
        if manager and ifc_entity:
            manager.unlink_element(ifc_entity.id())
    except Exception:
        pass
```

---

## 4. Phase 2: IFC Bridge Layer

### 4.1 Update `saikei_civil/tool/ifc.py`

**Replace the current implementation with:**

```python
"""
IFC Tool - Saikei's interface to IFC operations.
Bridges to Bonsai when available, uses NativeIfcManager standalone.
"""

import bpy
from typing import Optional, Any, List

# Check for IfcOpenShell
try:
    import ifcopenshell
    import ifcopenshell.api
    import ifcopenshell.util.element
    HAS_IFCOPENSHELL = True
except ImportError:
    HAS_IFCOPENSHELL = False


class Ifc:
    """
    IFC access tool - the primary interface for IFC operations.
    
    Always use this class to access IFC data, never access
    NativeIfcManager or IfcStore directly from operators/UI.
    """
    
    @staticmethod
    def is_available() -> bool:
        """Check if IFC functionality is available"""
        return HAS_IFCOPENSHELL
    
    @staticmethod
    def has_file() -> bool:
        """Check if an IFC file is currently loaded"""
        return Ifc.get() is not None
    
    @staticmethod
    def get():
        """
        Get the current IFC file.
        Prefers Bonsai's file when available.
        """
        from saikei_civil.civil.ifc_operator import get_ifc_file
        return get_ifc_file()
    
    @staticmethod
    def get_path() -> str:
        """Get the current IFC file path"""
        from saikei_civil.civil.ifc_operator import get_ifc_path
        return get_ifc_path()
    
    @staticmethod
    def is_bonsai_mode() -> bool:
        """Check if we're using Bonsai's IFC file"""
        from saikei_civil.civil.ifc_operator import is_bonsai_available
        return is_bonsai_available()
    
    @staticmethod
    def get_entity(ifc_id: int):
        """Get an IFC entity by ID"""
        ifc_file = Ifc.get()
        if ifc_file and ifc_id:
            try:
                return ifc_file.by_id(ifc_id)
            except RuntimeError:
                return None
        return None
    
    @staticmethod
    def get_entity_by_guid(guid: str):
        """Get an IFC entity by GlobalId"""
        ifc_file = Ifc.get()
        if ifc_file and guid:
            try:
                return ifc_file.by_guid(guid)
            except RuntimeError:
                return None
        return None
    
    @staticmethod
    def get_object(ifc_entity) -> Optional[bpy.types.Object]:
        """Get the Blender object linked to an IFC entity"""
        if not ifc_entity:
            return None
        
        ifc_id = ifc_entity.id()
        
        # Try Bonsai's element map
        try:
            from bonsai.bim.ifc import IfcStore
            if IfcStore.id_map and ifc_id in IfcStore.id_map:
                obj_name = IfcStore.id_map[ifc_id]
                return bpy.data.objects.get(obj_name)
        except ImportError:
            pass
        
        # Try Saikei's element map
        try:
            from saikei_civil.core.ifc_manager.manager import NativeIfcManager
            manager = NativeIfcManager.get_instance()
            if manager:
                return manager.get_object(ifc_id)
        except Exception:
            pass
        
        # Fallback: search by ifc_definition_id
        for obj in bpy.data.objects:
            if hasattr(obj, 'BIMObjectProperties'):
                if obj.BIMObjectProperties.ifc_definition_id == ifc_id:
                    return obj
            if hasattr(obj, 'CivilObjectProperties'):
                if obj.CivilObjectProperties.ifc_definition_id == ifc_id:
                    return obj
        
        return None
    
    @staticmethod
    def get_ifc_entity(blender_object: bpy.types.Object):
        """Get the IFC entity linked to a Blender object"""
        if not blender_object:
            return None
        
        ifc_id = None
        
        # Check BIMObjectProperties (Bonsai)
        if hasattr(blender_object, 'BIMObjectProperties'):
            ifc_id = blender_object.BIMObjectProperties.ifc_definition_id
        
        # Check CivilObjectProperties (Saikei)
        if not ifc_id and hasattr(blender_object, 'CivilObjectProperties'):
            ifc_id = blender_object.CivilObjectProperties.ifc_definition_id
        
        if ifc_id:
            return Ifc.get_entity(ifc_id)
        
        return None
    
    @staticmethod
    def run(api_call: str, ifc_file=None, **kwargs):
        """
        Run an IfcOpenShell API call.
        
        Example:
            Ifc.run("root.create_entity", ifc_class="IfcAlignment", name="Main Road")
        """
        if not HAS_IFCOPENSHELL:
            raise RuntimeError("IfcOpenShell not available")
        
        if ifc_file is None:
            ifc_file = Ifc.get()
        
        if ifc_file is None:
            raise RuntimeError("No IFC file loaded")
        
        return ifcopenshell.api.run(api_call, ifc_file, **kwargs)
    
    @staticmethod
    def get_alignments() -> List:
        """Get all IfcAlignment entities"""
        ifc_file = Ifc.get()
        if ifc_file:
            return ifc_file.by_type("IfcAlignment")
        return []
    
    @staticmethod
    def get_alignment_by_name(name: str):
        """Get an alignment by name"""
        for alignment in Ifc.get_alignments():
            if alignment.Name == name:
                return alignment
        return None
    
    @staticmethod
    def get_schema() -> Optional[str]:
        """Get the IFC schema version"""
        ifc_file = Ifc.get()
        if ifc_file:
            return ifc_file.schema
        return None
```

---

## 5. Phase 3: UI Restructuring

### 5.1 Create Module Template

Each module follows this pattern. Start with the alignment module:

#### `saikei_civil/civil/module/__init__.py`

```python
"""Civil module package"""
```

#### `saikei_civil/civil/module/alignment/__init__.py`

```python
"""
Alignment Module - Horizontal and Vertical alignment editing.
"""

import bpy

from . import prop
from . import data
from . import ui
from . import operator

classes = []


def register():
    prop.register()
    data.register()
    ui.register()
    operator.register()


def unregister():
    operator.unregister()
    ui.unregister()
    data.unregister()
    prop.unregister()
```

#### `saikei_civil/civil/module/alignment/prop.py`

```python
"""
Alignment Properties - UI state and settings.
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    StringProperty,
    IntProperty,
    FloatProperty,
    BoolProperty,
    EnumProperty,
    CollectionProperty,
    PointerProperty,
    FloatVectorProperty,
)


class CivilAlignmentItem(PropertyGroup):
    """Single alignment in the list"""
    name: StringProperty(name="Name")
    ifc_id: IntProperty(name="IFC ID")
    global_id: StringProperty(name="GlobalId")
    length: FloatProperty(name="Length", unit='LENGTH')
    pi_count: IntProperty(name="PI Count")


class CivilPIItem(PropertyGroup):
    """Single PI point"""
    name: StringProperty(name="Name")
    ifc_id: IntProperty(name="IFC ID")
    station: FloatProperty(name="Station", unit='LENGTH')
    northing: FloatProperty(name="Northing", unit='LENGTH')
    easting: FloatProperty(name="Easting", unit='LENGTH')
    curve_radius: FloatProperty(name="Curve Radius", unit='LENGTH')
    has_curve: BoolProperty(name="Has Curve")


class CivilAlignmentProperties(PropertyGroup):
    """Alignment module UI state"""
    
    # Alignment list
    alignments: CollectionProperty(type=CivilAlignmentItem)
    active_alignment_index: IntProperty(
        name="Active Alignment Index",
        default=0,
    )
    
    # PI list for active alignment
    pi_points: CollectionProperty(type=CivilPIItem)
    active_pi_index: IntProperty(
        name="Active PI Index",
        default=0,
    )
    
    # Settings
    default_curve_radius: FloatProperty(
        name="Default Curve Radius",
        default=100.0,
        min=1.0,
        unit='LENGTH',
        description="Default radius for new curves",
    )
    
    auto_regenerate: BoolProperty(
        name="Auto Regenerate",
        default=True,
        description="Automatically regenerate alignment when PIs change",
    )
    
    # Visualization
    show_pi_labels: BoolProperty(
        name="Show PI Labels",
        default=True,
    )
    
    show_station_markers: BoolProperty(
        name="Show Station Markers",
        default=True,
    )
    
    station_interval: FloatProperty(
        name="Station Interval",
        default=100.0,
        min=10.0,
        unit='LENGTH',
    )
    
    # Colors
    tangent_color: FloatVectorProperty(
        name="Tangent Color",
        subtype='COLOR',
        default=(0.0, 0.8, 0.0),
        min=0.0,
        max=1.0,
    )
    
    curve_color: FloatVectorProperty(
        name="Curve Color", 
        subtype='COLOR',
        default=(0.0, 0.5, 1.0),
        min=0.0,
        max=1.0,
    )
    
    @property
    def active_alignment(self):
        """Get the active alignment item"""
        if self.alignments and 0 <= self.active_alignment_index < len(self.alignments):
            return self.alignments[self.active_alignment_index]
        return None


classes = (
    CivilAlignmentItem,
    CivilPIItem,
    CivilAlignmentProperties,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.CivilAlignmentProperties = PointerProperty(
        type=CivilAlignmentProperties
    )


def unregister():
    del bpy.types.Scene.CivilAlignmentProperties
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

#### `saikei_civil/civil/module/alignment/data.py`

```python
"""
Alignment Data Cache - avoids repeated IFC queries during UI draws.
"""

from typing import Dict, List, Any, Optional


class AlignmentData:
    """
    Cached alignment data for UI performance.
    
    Call refresh() when IFC data changes.
    Data is loaded lazily on first access.
    """
    
    data: Dict[str, Any] = {}
    is_loaded: bool = False
    
    @classmethod
    def load(cls):
        """Load alignment data from IFC file"""
        from saikei_civil.tool.ifc import Ifc
        
        cls.data = {
            "alignments": [],
            "has_file": False,
            "schema": None,
        }
        
        ifc_file = Ifc.get()
        if not ifc_file:
            cls.is_loaded = True
            return
        
        cls.data["has_file"] = True
        cls.data["schema"] = ifc_file.schema
        
        # Load alignments
        try:
            alignments = ifc_file.by_type("IfcAlignment")
            for alignment in alignments:
                alignment_data = {
                    "id": alignment.id(),
                    "name": alignment.Name or f"Alignment {alignment.id()}",
                    "global_id": alignment.GlobalId,
                    "description": alignment.Description or "",
                    "horizontal": cls._load_horizontal(alignment),
                    "vertical": cls._load_vertical(alignment),
                }
                cls.data["alignments"].append(alignment_data)
        except Exception as e:
            print(f"Error loading alignments: {e}")
        
        cls.is_loaded = True
    
    @classmethod
    def refresh(cls):
        """Mark data as stale - will reload on next access"""
        cls.is_loaded = False
        cls.data = {}
    
    @classmethod
    def ensure_loaded(cls):
        """Ensure data is loaded"""
        if not cls.is_loaded:
            cls.load()
    
    @classmethod
    def get_alignments(cls) -> List[Dict]:
        """Get list of alignments"""
        cls.ensure_loaded()
        return cls.data.get("alignments", [])
    
    @classmethod
    def get_alignment_by_id(cls, ifc_id: int) -> Optional[Dict]:
        """Get alignment data by IFC ID"""
        for alignment in cls.get_alignments():
            if alignment["id"] == ifc_id:
                return alignment
        return None
    
    @classmethod
    def _load_horizontal(cls, alignment) -> Dict:
        """Load horizontal alignment data"""
        data = {
            "segments": [],
            "pi_points": [],
            "length": 0.0,
        }
        
        # Get nested horizontal alignment
        try:
            if hasattr(alignment, 'IsNestedBy'):
                for rel in alignment.IsNestedBy:
                    for nested in rel.RelatedObjects:
                        if nested.is_a("IfcAlignmentHorizontal"):
                            # Load segments
                            if hasattr(nested, 'IsNestedBy'):
                                for seg_rel in nested.IsNestedBy:
                                    for seg in seg_rel.RelatedObjects:
                                        if seg.is_a("IfcAlignmentSegment"):
                                            data["segments"].append({
                                                "id": seg.id(),
                                                "type": cls._get_segment_type(seg),
                                            })
        except Exception as e:
            print(f"Error loading horizontal alignment: {e}")
        
        return data
    
    @classmethod
    def _load_vertical(cls, alignment) -> Dict:
        """Load vertical alignment data"""
        data = {
            "segments": [],
            "pvi_points": [],
        }
        # Similar implementation for vertical
        return data
    
    @classmethod
    def _get_segment_type(cls, segment) -> str:
        """Get segment type string"""
        try:
            if hasattr(segment, 'DesignParameters'):
                params = segment.DesignParameters
                if params:
                    return params.is_a()
        except:
            pass
        return "Unknown"


def register():
    pass


def unregister():
    AlignmentData.data = {}
    AlignmentData.is_loaded = False
```

#### `saikei_civil/civil/module/alignment/ui.py`

```python
"""
Alignment UI Panels - Properties Editor and N-Panel.
"""

import bpy
from bpy.types import Panel, UIList

from .data import AlignmentData


# ════════════════════════════════════════════════════════════════════════════
# UI LISTS
# ════════════════════════════════════════════════════════════════════════════

class CIVIL_UL_alignments(UIList):
    """UI List for alignments"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "name", text="", emboss=False, icon='CURVE_PATH')
            row.label(text=f"{item.length:.1f}")
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.name, icon='CURVE_PATH')


class CIVIL_UL_pi_points(UIList):
    """UI List for PI points"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.label(text=item.name, icon='HANDLETYPE_AUTO_VEC')
            row.label(text=f"Sta {item.station:.2f}")
            if item.has_curve:
                row.label(text=f"R={item.curve_radius:.1f}")


# ════════════════════════════════════════════════════════════════════════════
# PROPERTIES EDITOR PANELS (Scene Properties)
# ════════════════════════════════════════════════════════════════════════════

class CIVIL_PT_alignments(Panel):
    """Main alignment panel in Properties Editor"""
    bl_label = "Alignments"
    bl_idname = "CIVIL_PT_alignments"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 100  # After Bonsai panels
    
    @classmethod
    def poll(cls, context):
        from saikei_civil.tool.ifc import Ifc
        return Ifc.has_file()
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.CivilAlignmentProperties
        
        # Alignment list
        row = layout.row()
        row.template_list(
            "CIVIL_UL_alignments", "",
            props, "alignments",
            props, "active_alignment_index",
            rows=4,
        )
        
        col = row.column(align=True)
        col.operator("civil.add_alignment", icon='ADD', text="")
        col.operator("civil.remove_alignment", icon='REMOVE', text="")
        col.separator()
        col.operator("civil.refresh_alignments", icon='FILE_REFRESH', text="")


class CIVIL_PT_alignment_horizontal(Panel):
    """Horizontal alignment sub-panel"""
    bl_label = "Horizontal Alignment"
    bl_idname = "CIVIL_PT_alignment_horizontal"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_parent_id = "CIVIL_PT_alignments"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        props = context.scene.CivilAlignmentProperties
        return props.active_alignment is not None
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.CivilAlignmentProperties
        
        # PI points list
        layout.label(text="PI Points:")
        row = layout.row()
        row.template_list(
            "CIVIL_UL_pi_points", "",
            props, "pi_points",
            props, "active_pi_index",
            rows=3,
        )
        
        col = row.column(align=True)
        col.operator("civil.add_pi", icon='ADD', text="")
        col.operator("civil.remove_pi", icon='REMOVE', text="")
        
        # Active PI properties
        if props.pi_points and props.active_pi_index < len(props.pi_points):
            pi = props.pi_points[props.active_pi_index]
            box = layout.box()
            box.label(text="Active PI:")
            col = box.column(align=True)
            col.prop(pi, "northing")
            col.prop(pi, "easting")
            if pi.has_curve:
                col.prop(pi, "curve_radius")


class CIVIL_PT_alignment_vertical(Panel):
    """Vertical alignment sub-panel"""
    bl_label = "Vertical Alignment"
    bl_idname = "CIVIL_PT_alignment_vertical"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_parent_id = "CIVIL_PT_alignments"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Vertical alignment controls...")


class CIVIL_PT_alignment_settings(Panel):
    """Alignment settings sub-panel"""
    bl_label = "Settings"
    bl_idname = "CIVIL_PT_alignment_settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_parent_id = "CIVIL_PT_alignments"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.CivilAlignmentProperties
        
        col = layout.column()
        col.prop(props, "default_curve_radius")
        col.prop(props, "auto_regenerate")
        
        layout.separator()
        layout.label(text="Visualization:")
        col = layout.column()
        col.prop(props, "show_pi_labels")
        col.prop(props, "show_station_markers")
        col.prop(props, "station_interval")
        
        layout.separator()
        layout.label(text="Colors:")
        col = layout.column()
        col.prop(props, "tangent_color")
        col.prop(props, "curve_color")


# ════════════════════════════════════════════════════════════════════════════
# N-PANEL (Quick Access)
# ════════════════════════════════════════════════════════════════════════════

class CIVIL_PT_alignment_quick(Panel):
    """Quick alignment tools in N-panel sidebar"""
    bl_label = "Alignment"
    bl_idname = "CIVIL_PT_alignment_quick"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei"
    bl_order = 0
    
    def draw(self, context):
        layout = self.layout
        
        from saikei_civil.tool.ifc import Ifc
        
        # Status
        if not Ifc.has_file():
            layout.label(text="No IFC file loaded", icon='ERROR')
            layout.operator("civil.new_project", text="New Civil Project")
            return
        
        props = context.scene.CivilAlignmentProperties
        
        # Mode indicator
        if Ifc.is_bonsai_mode():
            layout.label(text="Using Bonsai IFC", icon='CHECKMARK')
        else:
            layout.label(text="Standalone Mode", icon='FILE_3D')
        
        layout.separator()
        
        # Active alignment selector
        if props.alignments:
            layout.prop_search(
                props, "active_alignment_index",
                props, "alignments",
                text="Active",
                icon='CURVE_PATH'
            )
        
        # Quick actions
        col = layout.column(align=True)
        col.operator("civil.add_pi", text="Add PI", icon='ADD')
        col.operator("civil.insert_curve", text="Insert Curve", icon='SPHERECURVE')
        
        # Active alignment info
        if props.active_alignment:
            box = layout.box()
            al = props.active_alignment
            box.label(text=f"Length: {al.length:.2f}")
            box.label(text=f"PIs: {al.pi_count}")


# ════════════════════════════════════════════════════════════════════════════
# REGISTRATION
# ════════════════════════════════════════════════════════════════════════════

classes = (
    CIVIL_UL_alignments,
    CIVIL_UL_pi_points,
    CIVIL_PT_alignments,
    CIVIL_PT_alignment_horizontal,
    CIVIL_PT_alignment_vertical,
    CIVIL_PT_alignment_settings,
    CIVIL_PT_alignment_quick,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

#### `saikei_civil/civil/module/alignment/operator.py`

```python
"""
Alignment Operators - All alignment-related operations.
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, FloatProperty, IntProperty

from saikei_civil.civil.ifc_operator import execute_civil_operator
from saikei_civil.tool.ifc import Ifc


class CIVIL_OT_add_alignment(Operator):
    """Add a new alignment"""
    bl_idname = "civil.add_alignment"
    bl_label = "Add Alignment"
    bl_options = {"REGISTER", "UNDO"}
    
    name: StringProperty(
        name="Name",
        default="Alignment",
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        return execute_civil_operator(self, context)
    
    def _execute(self, context):
        import ifcopenshell.api
        from saikei_civil.civil.ifc_operator import link_element
        
        ifc_file = Ifc.get()
        
        # Create IfcAlignment
        alignment = ifcopenshell.api.run(
            "root.create_entity",
            ifc_file,
            ifc_class="IfcAlignment",
            name=self.name,
        )
        
        # Create Blender empty
        empty = bpy.data.objects.new(f"{self.name} (IfcAlignment)", None)
        empty.empty_display_type = 'ARROWS'
        context.scene.collection.objects.link(empty)
        
        # Link them
        link_element(alignment, empty)
        
        # Refresh UI data
        from .data import AlignmentData
        AlignmentData.refresh()
        
        # Update properties
        props = context.scene.CivilAlignmentProperties
        item = props.alignments.add()
        item.name = self.name
        item.ifc_id = alignment.id()
        item.global_id = alignment.GlobalId
        
        self.report({'INFO'}, f"Created alignment: {self.name}")
        return {"FINISHED"}


class CIVIL_OT_remove_alignment(Operator):
    """Remove the active alignment"""
    bl_idname = "civil.remove_alignment"
    bl_label = "Remove Alignment"
    bl_options = {"REGISTER", "UNDO"}
    
    @classmethod
    def poll(cls, context):
        props = context.scene.CivilAlignmentProperties
        return props.active_alignment is not None
    
    def execute(self, context):
        return execute_civil_operator(self, context)
    
    def _execute(self, context):
        import ifcopenshell.api
        from saikei_civil.civil.ifc_operator import unlink_element
        
        props = context.scene.CivilAlignmentProperties
        item = props.active_alignment
        
        ifc_file = Ifc.get()
        entity = Ifc.get_entity(item.ifc_id)
        
        if entity:
            # Get linked object
            obj = Ifc.get_object(entity)
            
            # Unlink
            unlink_element(ifc_entity=entity)
            
            # Remove from IFC
            ifcopenshell.api.run("root.remove_product", ifc_file, product=entity)
            
            # Remove Blender object
            if obj:
                bpy.data.objects.remove(obj)
        
        # Remove from list
        props.alignments.remove(props.active_alignment_index)
        props.active_alignment_index = max(0, props.active_alignment_index - 1)
        
        from .data import AlignmentData
        AlignmentData.refresh()
        
        return {"FINISHED"}


class CIVIL_OT_refresh_alignments(Operator):
    """Refresh alignment list from IFC"""
    bl_idname = "civil.refresh_alignments"
    bl_label = "Refresh Alignments"
    
    def execute(self, context):
        from .data import AlignmentData
        
        # Reload data
        AlignmentData.refresh()
        AlignmentData.load()
        
        # Update UI properties
        props = context.scene.CivilAlignmentProperties
        props.alignments.clear()
        
        for al_data in AlignmentData.get_alignments():
            item = props.alignments.add()
            item.name = al_data["name"]
            item.ifc_id = al_data["id"]
            item.global_id = al_data["global_id"]
        
        self.report({'INFO'}, f"Found {len(props.alignments)} alignments")
        return {"FINISHED"}


class CIVIL_OT_add_pi(Operator):
    """Add a PI point to the active alignment"""
    bl_idname = "civil.add_pi"
    bl_label = "Add PI"
    bl_options = {"REGISTER", "UNDO"}
    
    northing: FloatProperty(name="Northing", default=0.0)
    easting: FloatProperty(name="Easting", default=0.0)
    
    @classmethod
    def poll(cls, context):
        props = context.scene.CivilAlignmentProperties
        return props.active_alignment is not None
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        return execute_civil_operator(self, context)
    
    def _execute(self, context):
        # TODO: Implement PI creation in IFC
        # This will use the horizontal alignment manager
        
        props = context.scene.CivilAlignmentProperties
        
        # Add to UI list for now
        pi = props.pi_points.add()
        pi.name = f"PI-{len(props.pi_points)}"
        pi.northing = self.northing
        pi.easting = self.easting
        
        self.report({'INFO'}, f"Added PI at ({self.easting:.2f}, {self.northing:.2f})")
        return {"FINISHED"}


class CIVIL_OT_remove_pi(Operator):
    """Remove the active PI point"""
    bl_idname = "civil.remove_pi"
    bl_label = "Remove PI"
    bl_options = {"REGISTER", "UNDO"}
    
    @classmethod
    def poll(cls, context):
        props = context.scene.CivilAlignmentProperties
        return props.pi_points and props.active_pi_index < len(props.pi_points)
    
    def execute(self, context):
        return execute_civil_operator(self, context)
    
    def _execute(self, context):
        props = context.scene.CivilAlignmentProperties
        props.pi_points.remove(props.active_pi_index)
        props.active_pi_index = max(0, props.active_pi_index - 1)
        return {"FINISHED"}


class CIVIL_OT_insert_curve(Operator):
    """Insert a curve at the active PI"""
    bl_idname = "civil.insert_curve"
    bl_label = "Insert Curve"
    bl_options = {"REGISTER", "UNDO"}
    
    radius: FloatProperty(
        name="Radius",
        default=100.0,
        min=1.0,
        unit='LENGTH',
    )
    
    @classmethod
    def poll(cls, context):
        props = context.scene.CivilAlignmentProperties
        if not props.pi_points:
            return False
        if props.active_pi_index >= len(props.pi_points):
            return False
        return not props.pi_points[props.active_pi_index].has_curve
    
    def invoke(self, context, event):
        props = context.scene.CivilAlignmentProperties
        self.radius = props.default_curve_radius
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        return execute_civil_operator(self, context)
    
    def _execute(self, context):
        props = context.scene.CivilAlignmentProperties
        pi = props.pi_points[props.active_pi_index]
        pi.has_curve = True
        pi.curve_radius = self.radius
        
        self.report({'INFO'}, f"Inserted curve with radius {self.radius:.2f}")
        return {"FINISHED"}


# Registration
classes = (
    CIVIL_OT_add_alignment,
    CIVIL_OT_remove_alignment,
    CIVIL_OT_refresh_alignments,
    CIVIL_OT_add_pi,
    CIVIL_OT_remove_pi,
    CIVIL_OT_insert_curve,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

---

## 6. Phase 4: Object Properties

### Create `saikei_civil/civil/module/project/prop.py`

```python
"""
Project and Object Properties.
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    StringProperty,
    IntProperty,
    PointerProperty,
)


class CivilObjectProperties(PropertyGroup):
    """Properties stored on each Blender object linked to IFC"""
    
    ifc_definition_id: IntProperty(
        name="IFC Definition ID",
        description="The IFC entity ID this object is linked to",
        default=0,
    )
    
    ifc_class: StringProperty(
        name="IFC Class",
        description="The IFC class type (e.g., IfcAlignment)",
        default="",
    )
    
    global_id: StringProperty(
        name="GlobalId",
        description="IFC GlobalId",
        default="",
    )


class CivilProjectProperties(PropertyGroup):
    """Project-level settings"""
    
    has_ifc_file: bpy.props.BoolProperty(
        name="Has IFC File",
        default=False,
    )
    
    standalone_filepath: StringProperty(
        name="IFC File Path",
        description="Path to IFC file (standalone mode)",
        subtype='FILE_PATH',
    )


classes = (
    CivilObjectProperties,
    CivilProjectProperties,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Object.CivilObjectProperties = PointerProperty(
        type=CivilObjectProperties
    )
    bpy.types.Scene.CivilProjectProperties = PointerProperty(
        type=CivilProjectProperties
    )


def unregister():
    del bpy.types.Scene.CivilProjectProperties
    del bpy.types.Object.CivilObjectProperties
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

---

## 7. Phase 5: Update Main `__init__.py`

### Update `saikei_civil/__init__.py`

```python
"""
Saikei Civil - Native IFC Civil Engineering for Blender

Integrates with Bonsai BIM when available, works standalone otherwise.
"""

bl_info = {
    "name": "Saikei Civil",
    "author": "Michael Holtz / Desert Springs Civil Engineering PLLC",
    "version": (0, 6, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Saikei, Properties > Scene",
    "description": "Native IFC civil engineering tools - roads, alignments, corridors",
    "doc_url": "https://github.com/...",
    "category": "3D View",
}

import bpy

# Import registration modules
from . import preferences
from . import civil  # NEW: Main UI module


def register():
    """Register the addon"""
    preferences.register()
    civil.register()
    
    print(f"Saikei Civil {'.'.join(map(str, bl_info['version']))} registered")
    
    # Check Bonsai status
    try:
        from bonsai.bim.ifc import IfcStore
        print("  → Bonsai detected, integration enabled")
    except ImportError:
        print("  → Standalone mode (Bonsai not found)")


def unregister():
    """Unregister the addon"""
    civil.unregister()
    preferences.unregister()
    
    print("Saikei Civil unregistered")


if __name__ == "__main__":
    register()
```

---

## 8. Phase 6: Toolbar Tools (Optional Enhancement)

### Create `saikei_civil/tools/__init__.py`

```python
"""
Toolbar Tools - Interactive viewport tools.
"""

import bpy
from bpy.types import WorkSpaceTool

from . import pi_tool


def register():
    pi_tool.register()


def unregister():
    pi_tool.unregister()
```

### Create `saikei_civil/tools/pi_tool.py`

```python
"""
PI Placement Tool - Interactive PI placement in viewport.
"""

import bpy
from bpy.types import WorkSpaceTool


class CivilPITool(WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_idname = "civil.pi_tool"
    bl_label = "PI Placement"
    bl_description = "Click to place Points of Intersection for alignments"
    bl_icon = "ops.gpencil.primitive_curve"
    bl_widget = None
    bl_keymap = (
        ("civil.place_pi_interactive", {"type": 'LEFTMOUSE', "value": 'PRESS'}, None),
        ("civil.finish_pi_placement", {"type": 'RIGHTMOUSE', "value": 'PRESS'}, None),
        ("civil.cancel_pi_placement", {"type": 'ESC', "value": 'PRESS'}, None),
    )
    
    def draw_settings(context, layout, tool):
        props = context.scene.CivilAlignmentProperties
        layout.prop(props, "default_curve_radius")


def register():
    # Register after Bonsai tools if available
    try:
        bpy.utils.register_tool(CivilPITool, after={"bim.wall_tool"}, separator=True)
    except Exception:
        try:
            bpy.utils.register_tool(CivilPITool, after={"builtin.transform"}, separator=True)
        except Exception as e:
            print(f"Could not register PI tool: {e}")


def unregister():
    try:
        bpy.utils.unregister_tool(CivilPITool)
    except Exception:
        pass
```

---

## 9. Testing Requirements

### Test Cases to Verify

1. **Standalone Mode (No Bonsai)**
   - [ ] New project creates IFC file
   - [ ] Add alignment works
   - [ ] Undo/redo works
   - [ ] Save/load works
   - [ ] UI panels appear correctly

2. **Bonsai Integration Mode**
   - [ ] Detects Bonsai automatically
   - [ ] Uses Bonsai's IFC file
   - [ ] Alignments appear in both UIs
   - [ ] Undo/redo syncs with Bonsai
   - [ ] No duplicate element maps

3. **UI Locations**
   - [ ] Properties Editor > Scene > Alignments panel appears
   - [ ] N-Panel > Saikei tab appears
   - [ ] Sub-panels expand/collapse correctly

4. **Operators**
   - [ ] All operators have UNDO option
   - [ ] Transactions wrap correctly
   - [ ] Error handling works

---

## 10. Migration Checklist

### Files to Create

- [ ] `saikei_civil/civil/__init__.py`
- [ ] `saikei_civil/civil/prop.py`
- [ ] `saikei_civil/civil/handler.py`
- [ ] `saikei_civil/civil/ifc_operator.py`
- [ ] `saikei_civil/civil/module/__init__.py`
- [ ] `saikei_civil/civil/module/alignment/__init__.py`
- [ ] `saikei_civil/civil/module/alignment/prop.py`
- [ ] `saikei_civil/civil/module/alignment/data.py`
- [ ] `saikei_civil/civil/module/alignment/ui.py`
- [ ] `saikei_civil/civil/module/alignment/operator.py`
- [ ] `saikei_civil/civil/module/project/__init__.py`
- [ ] `saikei_civil/civil/module/project/prop.py`

### Files to Update

- [ ] `saikei_civil/__init__.py` - New registration
- [ ] `saikei_civil/tool/ifc.py` - Bonsai bridge

### Files to Deprecate (Later)

- [ ] `saikei_civil/operators/` - Move to civil/module/*/operator.py
- [ ] `saikei_civil/ui/` - Move to civil/module/*/ui.py

### Property Renames

| Old | New |
|-----|-----|
| `bc_alignment` | `CivilAlignmentProperties` |
| (object props) | `CivilObjectProperties` |

---

## Execution Order for Claude Code

1. **First:** Create the `civil/` directory structure and base files
2. **Second:** Create `ifc_operator.py` (the integration bridge)
3. **Third:** Update `tool/ifc.py` with Bonsai detection
4. **Fourth:** Create alignment module (prop, data, ui, operator)
5. **Fifth:** Create project module (object properties)
6. **Sixth:** Update main `__init__.py`
7. **Seventh:** Test in Blender
8. **Eighth:** Migrate remaining operators/panels

**Important:** Keep the old `operators/` and `ui/` directories during migration - only remove after everything works.
