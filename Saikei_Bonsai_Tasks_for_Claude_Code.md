# Saikei Bonsai Integration - Step-by-Step Tasks

## For Claude Code - Execute in Order

**Repository:** `C:\Users\amish\OneDrive\OneDrive Documents\GitHub\BlenderCivil\blendercivil`

---

## Phase 1: Create Directory Structure

### Task 1.1: Create civil/ module directories
```
mkdir saikei_civil/civil
mkdir saikei_civil/civil/module
mkdir saikei_civil/civil/module/alignment
mkdir saikei_civil/civil/module/project
mkdir saikei_civil/civil/module/corridor
mkdir saikei_civil/civil/module/georef
mkdir saikei_civil/civil/module/cross_section
```

### Task 1.2: Create `__init__.py` files
Create empty `__init__.py` in each new directory.

---

## Phase 2: Core Integration Bridge

### Task 2.1: Create `saikei_civil/civil/ifc_operator.py`

This is the **KEY FILE** - the bridge between Saikei and Bonsai.

```python
"""
IFC Operator wrapper - integrates with Bonsai when available.
"""

import bpy
from typing import Optional


def is_bonsai_available() -> bool:
    """Check if Bonsai is installed and has an active IFC file"""
    try:
        from bonsai.bim.ifc import IfcStore
        return IfcStore.get_file() is not None
    except ImportError:
        return False


def get_ifc_file():
    """Get the IFC file, preferring Bonsai's if available."""
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
    """
    
    if is_bonsai_available():
        try:
            from bonsai.bim.ifc import IfcStore
            return IfcStore.execute_ifc_operator(operator, context)
        except Exception as e:
            operator.report({'ERROR'}, f"Bonsai operator error: {e}")
            return {"CANCELLED"}
    
    # Standalone mode
    try:
        from saikei_civil.core.ifc_manager.manager import NativeIfcManager
        manager = NativeIfcManager.get_instance()
        
        if not manager or not manager.file:
            operator.report({'ERROR'}, "No IFC file loaded")
            return {"CANCELLED"}
        
        manager.begin_transaction()
        
        try:
            result = operator._execute(context)
            manager.end_transaction()
            return result
        except Exception as e:
            manager.undo()
            operator.report({'ERROR'}, f"Operation failed: {e}")
            return {"CANCELLED"}
            
    except Exception as e:
        operator.report({'ERROR'}, f"Civil operator error: {e}")
        return {"CANCELLED"}


def link_element(ifc_entity, blender_object):
    """Link an IFC entity to a Blender object."""
    if is_bonsai_available():
        try:
            from bonsai.bim.ifc import IfcStore
            IfcStore.link_element(ifc_entity, blender_object)
        except Exception:
            pass
    
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

### Task 2.2: Update `saikei_civil/tool/ifc.py`

Replace or update the `Ifc` class to use the bridge:

```python
"""
IFC Tool - Saikei's interface to IFC operations.
"""

import bpy
from typing import Optional, List

try:
    import ifcopenshell
    import ifcopenshell.api
    HAS_IFCOPENSHELL = True
except ImportError:
    HAS_IFCOPENSHELL = False


class Ifc:
    """IFC access tool - primary interface for IFC operations."""
    
    @staticmethod
    def is_available() -> bool:
        return HAS_IFCOPENSHELL
    
    @staticmethod
    def has_file() -> bool:
        return Ifc.get() is not None
    
    @staticmethod
    def get():
        """Get current IFC file (Bonsai or standalone)."""
        from saikei_civil.civil.ifc_operator import get_ifc_file
        return get_ifc_file()
    
    @staticmethod
    def get_path() -> str:
        from saikei_civil.civil.ifc_operator import get_ifc_path
        return get_ifc_path()
    
    @staticmethod
    def is_bonsai_mode() -> bool:
        from saikei_civil.civil.ifc_operator import is_bonsai_available
        return is_bonsai_available()
    
    @staticmethod
    def get_entity(ifc_id: int):
        ifc_file = Ifc.get()
        if ifc_file and ifc_id:
            try:
                return ifc_file.by_id(ifc_id)
            except RuntimeError:
                return None
        return None
    
    @staticmethod
    def get_object(ifc_entity) -> Optional[bpy.types.Object]:
        """Get Blender object linked to IFC entity."""
        if not ifc_entity:
            return None
        
        ifc_id = ifc_entity.id()
        
        # Try Bonsai's map
        try:
            from bonsai.bim.ifc import IfcStore
            if IfcStore.id_map and ifc_id in IfcStore.id_map:
                return bpy.data.objects.get(IfcStore.id_map[ifc_id])
        except ImportError:
            pass
        
        # Try Saikei's map
        try:
            from saikei_civil.core.ifc_manager.manager import NativeIfcManager
            manager = NativeIfcManager.get_instance()
            if manager:
                return manager.get_object(ifc_id)
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def run(api_call: str, ifc_file=None, **kwargs):
        """Run an IfcOpenShell API call."""
        if not HAS_IFCOPENSHELL:
            raise RuntimeError("IfcOpenShell not available")
        
        if ifc_file is None:
            ifc_file = Ifc.get()
        
        if ifc_file is None:
            raise RuntimeError("No IFC file loaded")
        
        return ifcopenshell.api.run(api_call, ifc_file, **kwargs)
    
    @staticmethod
    def get_alignments() -> List:
        ifc_file = Ifc.get()
        if ifc_file:
            return ifc_file.by_type("IfcAlignment")
        return []
```

---

## Phase 3: Property Registration

### Task 3.1: Create `saikei_civil/civil/prop.py`

```python
"""Global Civil Properties"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, StringProperty, PointerProperty


class CivilProperties(PropertyGroup):
    """Global civil engineering settings"""
    
    use_bonsai_ifc: BoolProperty(
        name="Use Bonsai IFC",
        default=True,
    )
    
    is_initialized: BoolProperty(default=False)
    status_message: StringProperty(default="")


def register():
    bpy.utils.register_class(CivilProperties)
    bpy.types.Scene.CivilProperties = PointerProperty(type=CivilProperties)


def unregister():
    del bpy.types.Scene.CivilProperties
    bpy.utils.unregister_class(CivilProperties)
```

### Task 3.2: Create `saikei_civil/civil/module/project/prop.py`

```python
"""Object-level properties"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty, IntProperty, PointerProperty


class CivilObjectProperties(PropertyGroup):
    """Properties on each Blender object linked to IFC"""
    
    ifc_definition_id: IntProperty(name="IFC Definition ID", default=0)
    ifc_class: StringProperty(name="IFC Class", default="")
    global_id: StringProperty(name="GlobalId", default="")


def register():
    bpy.utils.register_class(CivilObjectProperties)
    bpy.types.Object.CivilObjectProperties = PointerProperty(type=CivilObjectProperties)


def unregister():
    del bpy.types.Object.CivilObjectProperties
    bpy.utils.unregister_class(CivilObjectProperties)
```

---

## Phase 4: Alignment Module

### Task 4.1: Create `saikei_civil/civil/module/alignment/prop.py`

(See full implementation in main refactoring guide)

### Task 4.2: Create `saikei_civil/civil/module/alignment/data.py`

(See full implementation in main refactoring guide)

### Task 4.3: Create `saikei_civil/civil/module/alignment/ui.py`

(See full implementation in main refactoring guide)

### Task 4.4: Create `saikei_civil/civil/module/alignment/operator.py`

(See full implementation in main refactoring guide)

### Task 4.5: Create `saikei_civil/civil/module/alignment/__init__.py`

```python
"""Alignment Module"""

from . import prop, data, ui, operator

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

---

## Phase 5: Civil Module Registration

### Task 5.1: Create `saikei_civil/civil/handler.py`

```python
"""Blender event handlers"""

import bpy
from bpy.app.handlers import persistent


@persistent
def on_load_post(dummy):
    """Called after .blend file loads"""
    try:
        from .module.alignment.data import AlignmentData
        AlignmentData.refresh()
    except Exception as e:
        print(f"Saikei: Error refreshing data: {e}")


def register():
    bpy.app.handlers.load_post.append(on_load_post)


def unregister():
    if on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_load_post)
```

### Task 5.2: Create `saikei_civil/civil/__init__.py`

```python
"""Saikei Civil UI Layer"""

from . import prop, handler, ifc_operator
from .module import alignment, project

modules = (project, alignment)

def register():
    prop.register()
    handler.register()
    for module in modules:
        module.register()

def unregister():
    for module in reversed(modules):
        module.unregister()
    handler.unregister()
    prop.unregister()
```

---

## Phase 6: Update Main Registration

### Task 6.1: Update `saikei_civil/__init__.py`

Add civil module registration:

```python
from . import civil

def register():
    # ... existing code ...
    civil.register()
    
    # Check Bonsai status
    try:
        from bonsai.bim.ifc import IfcStore
        print("  → Bonsai detected, integration enabled")
    except ImportError:
        print("  → Standalone mode")

def unregister():
    civil.unregister()
    # ... existing code ...
```

---

## Phase 7: Testing

### Task 7.1: Test in Blender

```python
# Run in Blender console:

# Test 1: Check properties registered
import bpy
assert hasattr(bpy.types.Scene, 'CivilProperties')
assert hasattr(bpy.types.Scene, 'CivilAlignmentProperties')
assert hasattr(bpy.types.Object, 'CivilObjectProperties')
print("✓ Properties registered")

# Test 2: Check Bonsai detection
from saikei_civil.tool.ifc import Ifc
print(f"Bonsai mode: {Ifc.is_bonsai_mode()}")
print(f"Has file: {Ifc.has_file()}")

# Test 3: Check panels exist
panels = [c for c in bpy.types.Panel.__subclasses__() if c.__name__.startswith('CIVIL_')]
print(f"✓ Found {len(panels)} Civil panels")
```

---

## Completion Checklist

- [ ] Phase 1: Directory structure created
- [ ] Phase 2: ifc_operator.py bridge created
- [ ] Phase 2: tool/ifc.py updated
- [ ] Phase 3: CivilProperties registered
- [ ] Phase 3: CivilObjectProperties registered
- [ ] Phase 4: Alignment module created
- [ ] Phase 5: Civil module __init__.py created
- [ ] Phase 6: Main __init__.py updated
- [ ] Phase 7: All tests pass

---

## Notes for Claude Code

1. **Don't delete old files yet** - Keep `operators/` and `ui/` until migration complete
2. **Test after each phase** - Reload addon in Blender to verify
3. **Check imports** - Use full module paths (`saikei_civil.civil.ifc_operator`)
4. **bl_options = {"REGISTER", "UNDO"}** - Required on ALL IFC operators
5. **Reference existing code** - Look at current `operators/` for implementation details
