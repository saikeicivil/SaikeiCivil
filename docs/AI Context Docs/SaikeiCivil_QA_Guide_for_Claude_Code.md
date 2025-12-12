# Saikei Civil QA Guide for Claude Code

**Version:** 2.0  
**Date:** December 2025  
**Author:** Michael Yoder  
**Company:** Desert Springs Civil Engineering, PLLC  
**Purpose:** Code Quality Assurance Reference for Claude Code  
**Architecture:** Bonsai-Style Three-Layer Pattern

---

## 🎯 Role Definition

You are an **expert Python software developer** specializing in:

1. **Python Best Practices** - PEP 8 compliance, clean code architecture, efficient algorithms
2. **Blender Extension Development** - Following Blender 4.x extension guidelines and Bonsai patterns
3. **IFC 4.3 Schema Knowledge** - buildingSMART's Industry Foundation Classes for BIM/infrastructure
4. **IfcOpenShell API** - Proper usage of `ifcopenshell.api` for all IFC modifications

Your **primary mission** is to review codebases and make suggestions to organize and create code that is:
- **Simple** - Easy to understand at a glance
- **Professional** - Production-ready quality
- **Efficient** - Optimal performance without premature optimization
- **Well-documented** - Clear comments, docstrings, and headers
- **Bonsai-Compatible** - Follows IfcOpenShell/Bonsai architectural patterns

---

## 🏗️ Three-Layer Architecture (CRITICAL)

Saikei Civil follows Bonsai's proven three-layer architecture. **All code must fit into one of these layers:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 3: BIM MODULES                         │
│  saikei_civil/bim/module/{module}/                              │
│  ├── operator.py   (Blender operators - user actions)           │
│  ├── ui.py         (Panels, menus)                              │
│  ├── prop.py       (Property groups)                            │
│  └── __init__.py   (Registration)                               │
│                                                                  │
│  Operators call CORE functions with TOOL implementations        │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 2: TOOLS                               │
│  saikei_civil/tool/                                             │
│                                                                  │
│  Blender-specific implementations of core interfaces            │
│  @classmethod pattern for all methods                           │
│  CAN import bpy and Blender-specific code                       │
│                                                                  │
│  Example: tool.Alignment.update_visualization(alignment)        │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 1: CORE                                │
│  saikei_civil/core/                                             │
│                                                                  │
│  Pure Python business logic                                     │
│  NO Blender imports (use TYPE_CHECKING only)                    │
│  Receives tools via dependency injection                        │
│  Testable without Blender running                               │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 IFCOPENSHELL API                                │
│  ifcopenshell.api.{module}.{function}()                         │
│                                                                  │
│  ALL IFC modifications go through here - NEVER direct entity    │
│  manipulation. Handles schema, relationships, cleanup.          │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Rules

| Layer | Can Import bpy? | Can Import ifcopenshell? | Purpose |
|-------|-----------------|--------------------------|---------|
| Core | ❌ NO (TYPE_CHECKING only) | ✅ YES | Business logic, algorithms |
| Tool | ✅ YES | ✅ YES | Blender-specific implementations |
| BIM Module | ✅ YES | Via tools only | UI, operators, properties |

---

## 📁 Repository Structure

### Expected Saikei Civil Directory Layout

```
saikei_civil/
├── __init__.py                    ← Extension entry point
├── blender_manifest.toml          ← Blender 4.x manifest (REQUIRED)
│
├── core/                          ← LAYER 1: Pure business logic
│   ├── __init__.py
│   ├── tool.py                    ← Interface definitions (@interface decorator)
│   ├── alignment.py               ← Alignment business logic
│   ├── vertical.py                ← Vertical alignment logic
│   ├── georeference.py            ← Georeferencing logic
│   ├── cross_section.py           ← Cross-section logic
│   └── corridor.py                ← Corridor generation logic
│
├── tool/                          ← LAYER 2: Blender implementations
│   ├── __init__.py                ← Imports all tools for easy access
│   ├── ifc.py                     ← IFC file handling (mirrors Bonsai pattern)
│   ├── blender.py                 ← Blender object operations
│   ├── alignment.py               ← Alignment visualization/Blender ops
│   ├── vertical.py                ← Vertical alignment tools
│   ├── georeference.py            ← CRS/coordinate tools
│   ├── cross_section.py           ← Cross-section tools
│   └── corridor.py                ← Corridor tools
│
├── bim/                           ← LAYER 3: UI Modules
│   ├── __init__.py
│   ├── ifc.py                     ← IFC Store (file state management)
│   │
│   └── module/                    ← Feature modules
│       ├── __init__.py
│       │
│       ├── alignment/             ← Horizontal alignment module
│       │   ├── __init__.py        ← Registration
│       │   ├── operator.py        ← Blender operators
│       │   ├── ui.py              ← Panels
│       │   └── prop.py            ← Property groups
│       │
│       ├── vertical/              ← Vertical alignment module
│       │   ├── __init__.py
│       │   ├── operator.py
│       │   ├── ui.py
│       │   └── prop.py
│       │
│       ├── georeference/          ← Georeferencing module
│       │   ├── __init__.py
│       │   ├── operator.py
│       │   ├── ui.py
│       │   └── prop.py
│       │
│       ├── cross_section/         ← Cross-section module
│       │   ├── __init__.py
│       │   ├── operator.py
│       │   ├── ui.py
│       │   └── prop.py
│       │
│       └── corridor/              ← Corridor module
│           ├── __init__.py
│           ├── operator.py
│           ├── ui.py
│           └── prop.py
│
├── libs/                          ← Bundled dependencies (if any)
│
└── test/                          ← Tests
    ├── __init__.py
    ├── core/                      ← Core logic tests (no Blender needed)
    │   ├── bootstrap.py           ← Mock fixtures (Prophecy pattern)
    │   ├── test_alignment.py
    │   ├── test_vertical.py
    │   └── test_georeference.py
    │
    └── bim/                       ← Integration tests (need Blender)
        ├── test_alignment_integration.py
        └── test_corridor_integration.py
```

### Architecture Principles

**Why This Structure?**

1. **Testability** - Core logic tests run without Blender
2. **Maintainability** - Clear responsibility boundaries
3. **Bonsai Compatibility** - Same patterns enable potential integration
4. **Separation of Concerns** - UI changes don't affect business logic
5. **Dependency Injection** - Tools passed to core functions, not imported

---

## 🔧 Key Patterns to Follow

### Pattern 1: Interface Definitions in `core/tool.py`

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
    """Interface for IFC file operations."""
    def get(cls): pass
    def run(cls, command: str, **kwargs): pass
    def get_entity(cls, obj): pass
    def get_object(cls, entity): pass
    def link(cls, entity, obj): pass


@interface
class Blender:
    """Interface for Blender operations."""
    def create_ifc_object(cls, ifc_class: str, name: str): pass
    def get_selected_objects(cls): pass
    def get_active_object(cls): pass
    def update_viewport(cls): pass


@interface
class Alignment:
    """Interface for alignment operations."""
    def create_horizontal(cls, name: str, pis: list): pass
    def get_pis(cls, alignment): pass
    def compute_curve_geometry(cls, pi_data: dict): pass
    def update_visualization(cls, alignment): pass


@interface
class Georeference:
    """Interface for georeferencing operations."""
    def add_georeferencing(cls): pass
    def get_crs(cls): pass
    def set_crs(cls, epsg_code: int): pass
    def transform_coordinates(cls, local_coords: tuple): pass
```

### Pattern 2: Core Functions with Dependency Injection

```python
# saikei_civil/core/alignment.py

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import saikei_civil.tool as tool

def create_horizontal_alignment(
    ifc: "type[tool.Ifc]",
    alignment_tool: "type[tool.Alignment]",
    blender: "type[tool.Blender]",
    name: str,
    pis: list[dict],
) -> "ifcopenshell.entity_instance":
    """
    Create horizontal alignment using PI method.
    
    Args:
        ifc: IFC tool class for file operations
        alignment_tool: Alignment tool class for visualization
        blender: Blender tool class for object creation
        name: Name for the alignment
        pis: List of PI dictionaries with station, easting, northing, radius
        
    Returns:
        The created IfcAlignment entity
    """
    # 1. Create IFC entities via API
    alignment = ifc.run(
        "alignment.create_by_pi_method",
        name=name,
        horizontal_pi_data=pis
    )
    
    # 2. Create Blender visualization object
    obj = blender.create_ifc_object("IfcAlignment", name)
    
    # 3. Link IFC entity to Blender object
    ifc.link(alignment, obj)
    
    # 4. Update visualization from IFC data
    alignment_tool.update_visualization(alignment)
    
    return alignment
```

### Pattern 3: Tool Implementations

```python
# saikei_civil/tool/alignment.py

import bpy
import ifcopenshell
import saikei_civil.core.tool
import saikei_civil.tool as tool


class Alignment(saikei_civil.core.tool.Alignment):
    """Blender-specific implementation of Alignment interface."""
    
    @classmethod
    def update_visualization(cls, alignment):
        """Update Blender curve from IFC alignment data."""
        obj = tool.Ifc.get_object(alignment)
        if not obj:
            return
        
        # Get horizontal layout from IFC
        ifc_file = tool.Ifc.get()
        h_layout = ifcopenshell.api.alignment.get_horizontal_layout(
            ifc_file, alignment
        )
        
        # Get segments and update Blender curve
        segments = ifcopenshell.api.alignment.get_layout_segments(
            ifc_file, h_layout
        )
        
        cls._update_curve_from_segments(obj, segments)
    
    @classmethod
    def _update_curve_from_segments(cls, obj, segments):
        """Internal: Update curve geometry from IFC segments."""
        # Implementation...
        pass
    
    @classmethod
    def get_pis(cls, alignment):
        """Get PI data from IFC alignment."""
        ifc_file = tool.Ifc.get()
        # Extract PI information from alignment entity
        # ...
```

### Pattern 4: Operators Call Core with Tools

```python
# saikei_civil/bim/module/alignment/operator.py

import bpy
import saikei_civil.core.alignment as core
import saikei_civil.tool as tool


class SAIKEI_OT_create_alignment(bpy.types.Operator, tool.Ifc.Operator):
    """Create a new horizontal alignment from PIs"""
    bl_idname = "saikei.create_alignment"
    bl_label = "Create Alignment"
    bl_options = {"REGISTER", "UNDO"}
    
    name: bpy.props.StringProperty(
        name="Name",
        default="Alignment 1"
    )
    
    def _execute(self, context):
        # Get PI data from properties
        props = context.scene.SaikeiAlignmentProperties
        pis = self._get_pis_from_props(props)
        
        # Call core function with tool classes (NOT instances)
        core.create_horizontal_alignment(
            tool.Ifc,
            tool.Alignment,
            tool.Blender,
            name=self.name,
            pis=pis
        )
        
        return {"FINISHED"}
    
    def _get_pis_from_props(self, props):
        """Convert Blender properties to PI list."""
        pis = []
        for pi_prop in props.pis:
            pis.append({
                "station": pi_prop.station,
                "easting": pi_prop.easting,
                "northing": pi_prop.northing,
                "radius": pi_prop.radius,
            })
        return pis
```

### Pattern 5: IFC Operator Base Class

```python
# saikei_civil/tool/ifc.py

import bpy
from typing import final
import saikei_civil.core.tool
from saikei_civil.bim.ifc import SaikeiStore


class Ifc(saikei_civil.core.tool.Ifc):
    """Blender-specific IFC operations."""
    
    class Operator:
        """Base class for IFC-modifying operators."""
        
        @final
        def execute(self, context):
            """Execute wrapper that handles IFC transactions."""
            SaikeiStore.execute_ifc_operator(self, context)
            return {"FINISHED"}
        
        def _execute(self, context):
            """Override this in subclasses."""
            raise NotImplementedError("Implement _execute method")
    
    @classmethod
    def get(cls):
        """Get the active IFC file."""
        return SaikeiStore.get_file()
    
    @classmethod
    def run(cls, command: str, **kwargs):
        """Run an ifcopenshell.api command."""
        import ifcopenshell.api
        ifc_file = cls.get()
        module, function = command.rsplit(".", 1)
        return ifcopenshell.api.run(module, function, ifc_file, **kwargs)
    
    @classmethod
    def get_entity(cls, obj):
        """Get IFC entity linked to Blender object."""
        return SaikeiStore.get_element(obj)
    
    @classmethod
    def get_object(cls, entity):
        """Get Blender object linked to IFC entity."""
        return SaikeiStore.get_object(entity)
    
    @classmethod
    def link(cls, entity, obj):
        """Link IFC entity to Blender object."""
        SaikeiStore.link_element(entity, obj)
```

---

## 📏 Python File Length Guidelines

### Recommended Limits

| File Type | Ideal | Acceptable | Warning | Refactor Required |
|-----------|-------|------------|---------|-------------------|
| core/*.py | 150-300 | 300-500 | 500-700 | >700 |
| tool/*.py | 150-300 | 300-500 | 500-700 | >700 |
| operator.py | 100-250 | 250-400 | 400-600 | >600 |
| ui.py | 100-200 | 200-350 | 350-500 | >500 |
| prop.py | 50-150 | 150-250 | 250-350 | >350 |
| Tests | 200-500 | 500-800 | 800-1000 | >1000 |

### When to Split Files

Split a module when:
1. **Multiple distinct classes** that could be logically separated
2. **File exceeds 500 lines** of actual code (excluding comments/docstrings)
3. **Single Responsibility Principle** is violated
4. **Testing becomes difficult** due to tight coupling
5. **A BIM module grows too large** - split into sub-modules

---

## 📜 Licensing Header Requirements

### Standard GPL v3 Header (Required for Bonsai Compatibility)

Saikei Civil uses **GPL v3** to maintain compatibility with Bonsai/IfcOpenShell, enabling bidirectional code sharing within the OpenBIM ecosystem.

**EVERY `.py` file MUST begin with this exact header:**

```python
# Saikei Civil - Native IFC Civil Engineering Tools for Blender
# Copyright (C) 2025 Michael Yoder, Desert Springs Civil Engineering, PLLC
#
# This file is part of Saikei Civil.
#
# Saikei Civil is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Saikei Civil is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Saikei Civil.  If not, see <https://www.gnu.org/licenses/>.
#
# Module: <module_name>
# Description: <brief one-line description>
# Author: Michael Yoder
# Created: <YYYY-MM-DD>

"""
<Module docstring with detailed description>

This module provides...
"""
```

### Why GPL v3?

- **Bonsai Compatibility**: Bonsai uses GPL v3; using the same license enables code sharing
- **Copyleft Protection**: Ensures derivatives remain open source
- **OSArch Ecosystem**: Standard license for OpenBIM tools
- **Commercial Viability**: GPL v3 is commercially viable for Blender extensions

---

## 🐍 PEP 8 Compliance Standards

### Critical Rules

```python
# ═══════════════════════════════════════════════════════════════════════════
# LINE LENGTH
# ═══════════════════════════════════════════════════════════════════════════
# Maximum 79 characters for code (99 acceptable for complex expressions)
# Maximum 72 characters for comments and docstrings

# ═══════════════════════════════════════════════════════════════════════════
# INDENTATION
# ═══════════════════════════════════════════════════════════════════════════
# Use 4 spaces per indentation level (NEVER tabs)

# ═══════════════════════════════════════════════════════════════════════════
# IMPORTS - Follow this exact order
# ═══════════════════════════════════════════════════════════════════════════
from typing import TYPE_CHECKING  # Always first if used

import os
import sys
from typing import List, Optional, Tuple

import bpy  # Third-party (Blender)
import numpy as np
import ifcopenshell
import ifcopenshell.api

import saikei_civil.core.alignment as core  # Local - core
import saikei_civil.tool as tool  # Local - tool

if TYPE_CHECKING:
    # Imports only for type hints - avoids circular imports
    import saikei_civil.tool as tool

# ═══════════════════════════════════════════════════════════════════════════
# NAMING CONVENTIONS
# ═══════════════════════════════════════════════════════════════════════════
# Classes: PascalCase
class VerticalAlignmentManager:
    pass

# Blender Operators: PREFIX_OT_action_name
class SAIKEI_OT_create_alignment(bpy.types.Operator):
    pass

# Blender Panels: PREFIX_PT_panel_name
class SAIKEI_PT_alignment_main(bpy.types.Panel):
    pass

# Blender Properties: PREFIX_PG_property_group
class SAIKEI_PG_alignment_properties(bpy.types.PropertyGroup):
    pass

# Functions/methods: snake_case
def calculate_station_elevation(station: float) -> float:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_SPIRAL_LENGTH = 1000.0
DEFAULT_CURVE_RADIUS = 500.0

# ═══════════════════════════════════════════════════════════════════════════
# TYPE_CHECKING PATTERN (Critical for Core modules)
# ═══════════════════════════════════════════════════════════════════════════
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import saikei_civil.tool as tool
    import bpy  # ONLY in TYPE_CHECKING block for core modules!

def some_core_function(
    ifc: "type[tool.Ifc]",  # String annotation for forward reference
    blender: "type[tool.Blender]",
) -> None:
    pass
```

### Type Hints (Required for Core, Recommended Elsewhere)

```python
from typing import List, Optional, Dict, Tuple, Union, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    import ifcopenshell
    import saikei_civil.tool as tool


@dataclass
class PIData:
    """Point of Intersection data structure."""
    station: float
    easting: float
    northing: float
    radius: Optional[float] = None
    spiral_in: Optional[float] = None
    spiral_out: Optional[float] = None


def create_alignment(
    ifc: "type[tool.Ifc]",
    name: str,
    pis: List[PIData],
) -> "ifcopenshell.entity_instance":
    """
    Create alignment from PI data.
    
    Args:
        ifc: IFC tool class for file operations
        name: Alignment name
        pis: List of PI data objects
        
    Returns:
        Created IfcAlignment entity
    """
    pass
```

---

## 📝 Documentation Standards

### Docstring Format (Google Style)

```python
def complex_function(
    ifc: "type[tool.Ifc]",
    param1: float,
    param2: str,
    param3: Optional[List[int]] = None
) -> Dict[str, float]:
    """
    Brief one-line description of function purpose.
    
    Extended description if needed. Can span multiple lines.
    
    Args:
        ifc: IFC tool class for file operations
        param1: Description of first parameter. Include units
            if applicable (e.g., "Distance in meters").
        param2: Description of second parameter.
        param3: Optional list of integers. Defaults to None.
            
    Returns:
        Dictionary mapping station names to their elevations.
        
    Raises:
        ValueError: If param1 is negative.
        
    Example:
        >>> result = complex_function(tool.Ifc, 100.0, "alignment_1")
        >>> print(result)
        {'STA 0+00': 100.5}
    """
    pass
```

---

## 🔍 Code Logic Review Guidelines

### Efficiency Patterns

```python
# ═══════════════════════════════════════════════════════════════════════════
# LOOP OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════════

# INEFFICIENT: Repeated calculations in loop
for i in range(len(points)):
    distance = calculate_distance(origin, points[i])
    normalized = distance / max(distances)  # max() called every iteration!

# EFFICIENT: Calculate once before loop
max_dist = max(distances)
for point in points:
    distance = calculate_distance(origin, point)
    normalized = distance / max_dist

# ═══════════════════════════════════════════════════════════════════════════
# USE IFCOPENSHELL.API - Never Direct Entity Manipulation
# ═══════════════════════════════════════════════════════════════════════════

# WRONG: Direct entity manipulation
alignment = ifc_file.create_entity("IfcAlignment")
alignment.Name = "My Alignment"
# ... manually setting up relationships

# CORRECT: Use ifcopenshell.api
alignment = ifcopenshell.api.alignment.create(ifc_file, name="My Alignment")

# WRONG: Direct attribute access for modification
entity.Name = "New Name"

# CORRECT: Use API for modifications
ifcopenshell.api.attribute.edit_attributes(ifc_file, product=entity, attributes={"Name": "New Name"})

# ═══════════════════════════════════════════════════════════════════════════
# NUMPY VECTORIZATION (for geometry calculations)
# ═══════════════════════════════════════════════════════════════════════════

# INEFFICIENT: Python loop
elevations = []
for station in stations:
    elev = grade * station + start_elev
    elevations.append(elev)

# EFFICIENT: Vectorized numpy
elevations = grade * np.array(stations) + start_elev
```

### Common Anti-Patterns to Flag

```python
# ═══════════════════════════════════════════════════════════════════════════
# ANTI-PATTERN: Importing bpy in core modules
# ═══════════════════════════════════════════════════════════════════════════

# WRONG: Direct bpy import in core
# saikei_civil/core/alignment.py
import bpy  # ❌ NEVER in core!

# CORRECT: TYPE_CHECKING only
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bpy  # ✅ Only for type hints

# ═══════════════════════════════════════════════════════════════════════════
# ANTI-PATTERN: Bypassing tool layer
# ═══════════════════════════════════════════════════════════════════════════

# WRONG: Operator directly manipulating IFC
class SAIKEI_OT_bad(bpy.types.Operator):
    def execute(self, context):
        import ifcopenshell
        ifc = ifcopenshell.open("file.ifc")  # ❌ Should use tool.Ifc.get()
        # ...

# CORRECT: Use tools
class SAIKEI_OT_good(bpy.types.Operator, tool.Ifc.Operator):
    def _execute(self, context):
        core.some_function(tool.Ifc, tool.Alignment)  # ✅ Pass tool classes

# ═══════════════════════════════════════════════════════════════════════════
# ANTI-PATTERN: Storing data in Blender custom properties
# ═══════════════════════════════════════════════════════════════════════════

# WRONG: Using Blender as database
obj["alignment_station"] = 100.0  # ❌ Data should live in IFC

# CORRECT: Store in IFC, read for display
# Data lives in IfcAlignment entity, Blender just visualizes

# ═══════════════════════════════════════════════════════════════════════════
# ANTI-PATTERN: Mutable default arguments
# ═══════════════════════════════════════════════════════════════════════════

# WRONG
def add_point(point, points=[]):  # ❌ Shared across calls!
    points.append(point)

# CORRECT
def add_point(point, points=None):
    if points is None:
        points = []
    points.append(point)

# ═══════════════════════════════════════════════════════════════════════════
# ANTI-PATTERN: Bare except clauses
# ═══════════════════════════════════════════════════════════════════════════

# WRONG
try:
    risky_operation()
except:  # ❌ Catches everything!
    pass

# CORRECT
try:
    risky_operation()
except (ValueError, TypeError) as e:
    logger.error(f"Operation failed: {e}")
    raise
```

---

## 🧹 Debug Code Cleanup

### Identifying Debug Code

```python
# ═══════════════════════════════════════════════════════════════════════════
# PRINT STATEMENTS (should be logging or removed)
# ═══════════════════════════════════════════════════════════════════════════
print(f"DEBUG: station = {station}")  # ❌ Remove or convert to logging
print("HERE!")  # ❌ Definitely remove

# CORRECT: Use logging
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Processing station {station}")

# ═══════════════════════════════════════════════════════════════════════════
# COMMENTED-OUT CODE
# ═══════════════════════════════════════════════════════════════════════════
# Old implementation:
# def old_function():
#     pass
# ❌ Remove - use git history instead

# ═══════════════════════════════════════════════════════════════════════════
# TODO/FIXME/HACK COMMENTS - Track and address
# ═══════════════════════════════════════════════════════════════════════════
# TODO: Implement this properly  # ⚠️ Track
# FIXME: This breaks with negative values  # ⚠️ Priority fix
# HACK: Temporary workaround  # ⚠️ Needs proper solution
```

---

## ✅ Blender Extension Guidelines

### Blender 4.x Manifest Requirements

**File: `blender_manifest.toml`**

```toml
schema_version = "1.0.0"

id = "saikei_civil"
name = "Saikei Civil"
tagline = "Native IFC civil engineering design tools"
version = "0.6.0"
type = "add-on"

maintainer = "Michael Yoder, Desert Springs Civil Engineering, PLLC"
license = ["SPDX:GPL-3.0-or-later"]

blender_version_min = "4.2.0"
blender_version_max = "5.0.0"

website = "https://saikeicivil.org"

[permissions]
files = "Import/export IFC files"
network = "Download CRS databases"

[build]
paths_exclude_pattern = [
    "__pycache__/",
    "*.pyc",
    ".git/",
    ".vscode/",
    "test/",
    "docs/",
]
```

### Naming Conventions (SAIKEI_ prefix)

```python
# Operators: SAIKEI_OT_action_name
class SAIKEI_OT_create_alignment(bpy.types.Operator):
    bl_idname = "saikei.create_alignment"
    bl_label = "Create Alignment"
    bl_options = {"REGISTER", "UNDO"}

# Panels: SAIKEI_PT_panel_name
class SAIKEI_PT_alignment_main(bpy.types.Panel):
    bl_idname = "SAIKEI_PT_alignment_main"
    bl_label = "Alignment"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei Civil"  # Tab name in N-panel

# Property Groups: SAIKEI_PG_property_name
class SAIKEI_PG_alignment_properties(bpy.types.PropertyGroup):
    pass

# UILists: SAIKEI_UL_list_name
class SAIKEI_UL_pi_list(bpy.types.UIList):
    pass
```

### BIM Module Registration Pattern

```python
# saikei_civil/bim/module/alignment/__init__.py

import bpy
from . import operator, ui, prop


classes = (
    # Properties first
    prop.SAIKEI_PG_pi_item,
    prop.SAIKEI_PG_alignment_properties,
    # Then operators
    operator.SAIKEI_OT_create_alignment,
    operator.SAIKEI_OT_add_pi,
    operator.SAIKEI_OT_remove_pi,
    # Then UI
    ui.SAIKEI_PT_alignment_main,
    ui.SAIKEI_UL_pi_list,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Register scene properties
    bpy.types.Scene.SaikeiAlignmentProperties = bpy.props.PointerProperty(
        type=prop.SAIKEI_PG_alignment_properties
    )


def unregister():
    del bpy.types.Scene.SaikeiAlignmentProperties
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

---

## 📋 QA Checklist Template

Use this checklist when reviewing each file:

### File: `__________________.py`

**Architecture Compliance:**
- [ ] File is in correct layer (core/tool/bim)
- [ ] Core files have NO `import bpy` (only in TYPE_CHECKING)
- [ ] Tool files implement core interfaces
- [ ] Operators inherit from `tool.Ifc.Operator`
- [ ] Operators call core functions with tool classes

**Header & Documentation:**
- [ ] GPL v3 license header present and complete
- [ ] Copyright credits Michael Yoder and Desert Springs Civil Engineering, PLLC
- [ ] Module docstring present with description
- [ ] All public functions/classes have docstrings
- [ ] Type hints present for function signatures

**Code Quality:**
- [ ] File length within guidelines (<500 lines preferred)
- [ ] Functions are focused (single responsibility)
- [ ] No functions exceed 50 lines
- [ ] Uses `ifcopenshell.api` (no direct entity manipulation)
- [ ] No magic numbers (use named constants)

**PEP 8 Compliance:**
- [ ] Line length ≤79 chars (99 acceptable)
- [ ] Imports properly ordered (TYPE_CHECKING first)
- [ ] Consistent 4-space indentation
- [ ] Naming follows SAIKEI_ prefix convention

**Debug Cleanup:**
- [ ] No print() statements (use logging)
- [ ] No commented-out code blocks
- [ ] No unused imports
- [ ] TODO/FIXME comments tracked

**Blender Specific:**
- [ ] Operators follow `SAIKEI_OT_` convention
- [ ] Panels follow `SAIKEI_PT_` convention
- [ ] Properties follow `SAIKEI_PG_` convention
- [ ] Registration in module's `__init__.py`

---

## 🔗 Reference Links

- **Bonsai Source**: https://github.com/IfcOpenShell/IfcOpenShell/tree/v0.8.0/src/bonsai
- **IfcOpenShell API**: https://blenderbim.org/docs-python/ifcopenshell-python/api.html
- **PEP 8**: https://peps.python.org/pep-0008/
- **Blender Extension Docs**: https://docs.blender.org/manual/en/latest/advanced/extensions/getting_started.html
- **IFC 4.3 Schema**: https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/

---

## 📊 Priority Order for QA

1. **Critical** - Architecture compliance (three-layer pattern)
2. **Critical** - License headers (legal requirement)
3. **High** - No bpy in core modules
4. **High** - Using ifcopenshell.api (not direct manipulation)
5. **High** - Debug code removal (production readiness)
6. **Medium** - PEP 8 compliance (maintainability)
7. **Medium** - Documentation completeness (usability)
8. **Low** - File length optimization (nice to have)

---

## ⚠️ Critical Rules Summary

### MUST DO
1. ✅ Adopt Three-Layer Architecture: Core → Tool → BIM Module
2. ✅ Use `ifcopenshell.api` for ALL IFC modifications
3. ✅ Define interfaces in `core/tool.py` before implementations
4. ✅ Use TYPE_CHECKING pattern in core modules
5. ✅ Pass tool classes (not instances) to core functions
6. ✅ Use `SAIKEI_` prefix for all Blender classes

### MUST AVOID
1. ❌ Importing bpy in core modules (except TYPE_CHECKING)
2. ❌ Direct IFC entity manipulation (use ifcopenshell.api)
3. ❌ Storing data in Blender custom properties (use IFC)
4. ❌ Duplicating Bonsai functionality (georeferencing, spatial)
5. ❌ Using different architectural patterns
6. ❌ Creating circular imports between layers

---

*This document serves as the authoritative reference for Saikei Civil code quality standards. All contributions should adhere to these guidelines.*

**Document Version:** 2.0  
**Last Updated:** December 2025  
**Maintained By:** Michael Yoder, Desert Springs Civil Engineering, PLLC
