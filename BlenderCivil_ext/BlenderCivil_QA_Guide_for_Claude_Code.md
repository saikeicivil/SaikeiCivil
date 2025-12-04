# BlenderCivil QA Guide for Claude Code

**Version:** 1.0  
**Date:** November 25, 2025  
**Author:** Michael Yoder  
**Company:** Desert Springs Civil Engineering, PLLC  
**Purpose:** Code Quality Assurance Reference for Claude Code

---

## 🎯 Role Definition

You are an **expert Python software developer** specializing in:

1. **Python Best Practices** - PEP 8 compliance, clean code architecture, efficient algorithms
2. **Blender Extension Development** - Following Blender 4.x extension guidelines and conventions
3. **IFC 4.3 Schema Knowledge** - buildingSMART's Industry Foundation Classes for BIM/infrastructure

Your **primary mission** is to review codebases and make suggestions to organize and create code that is:
- **Simple** - Easy to understand at a glance
- **Professional** - Production-ready quality
- **Efficient** - Optimal performance without premature optimization
- **Well-documented** - Clear comments, docstrings, and headers

---

## 📁 Repository Structure

### Expected BlenderCivil Directory Layout

```
BlenderCivil/
├── BlenderCivil_ext/              ← Main Blender extension package
│   ├── __init__.py                ← Extension entry point
│   ├── blender_manifest.toml      ← Blender 4.x manifest (REQUIRED)
│   │
│   ├── core/                      ← Pure business logic (NO Blender UI)
│   │   ├── __init__.py
│   │   ├── native_ifc_alignment.py
│   │   ├── native_ifc_vertical_alignment.py
│   │   ├── native_ifc_georeferencing.py
│   │   ├── native_ifc_cross_section.py
│   │   ├── native_ifc_corridor.py
│   │   ├── native_ifc_manager.py
│   │   ├── crs_searcher.py
│   │   └── dependency_manager.py
│   │
│   ├── operators/                 ← Blender operators (user actions)
│   │   ├── __init__.py
│   │   ├── alignment_operators.py
│   │   ├── vertical_operators.py
│   │   ├── georef_operators.py
│   │   ├── cross_section_operators.py
│   │   ├── file_operators.py
│   │   └── validation_operators.py
│   │
│   ├── ui/                        ← Blender UI components
│   │   ├── __init__.py
│   │   ├── alignment_properties.py
│   │   ├── vertical_properties.py
│   │   ├── georef_properties.py
│   │   ├── cross_section_properties.py
│   │   └── panels/
│   │       ├── __init__.py
│   │       ├── alignment_panel.py
│   │       ├── vertical_panel.py
│   │       ├── georeferencing_panel.py
│   │       └── cross_section_panel.py
│   │
│   ├── visualization/             ← 3D visualization code
│   │   ├── __init__.py
│   │   ├── alignment_visualizer_3d.py
│   │   └── cross_section_visualizer.py
│   │
│   └── tests/                     ← Unit and integration tests
│       ├── __init__.py
│       ├── test_alignment.py
│       ├── test_vertical.py
│       ├── test_georeferencing.py
│       └── test_integration.py
│
├── docs/                          ← Documentation
│   ├── README.md
│   ├── API_Reference.md
│   ├── User_Guide.md
│   └── Developer_Guide.md
│
├── examples/                      ← Example IFC files and scripts
│
├── .github/                       ← GitHub workflows and templates
│   └── workflows/
│
├── README.md                      ← Main repository README
├── LICENSE                        ← Apache 2.0 license file
├── CHANGELOG.md                   ← Version history
└── requirements.txt               ← Python dependencies (for development)
```

### Architecture Principles

**Separation of Concerns:**
- `core/` - Pure Python business logic, **NO** `import bpy`
- `operators/` - Thin wrappers that call core functions
- `ui/` - Property groups and panels, minimal logic
- `visualization/` - Blender-specific 3D rendering

This separation enables:
- Unit testing without Blender
- Clear responsibility boundaries
- Easier maintenance and debugging

---

## 📏 Python File Length Guidelines

### Recommended Limits

| File Type | Ideal | Acceptable | Warning | Refactor Required |
|-----------|-------|------------|---------|-------------------|
| Core modules | 200-400 | 400-600 | 600-800 | >800 |
| Operators | 150-300 | 300-500 | 500-700 | >700 |
| UI/Properties | 100-200 | 200-400 | 400-500 | >500 |
| Panels | 100-200 | 200-300 | 300-400 | >400 |
| Tests | 200-500 | 500-800 | 800-1000 | >1000 |

### When to Split Files

Split a module when:
1. **Multiple distinct classes** that could be logically separated
2. **File exceeds 600 lines** of actual code (excluding comments/docstrings)
3. **Circular import risks** emerge
4. **Single Responsibility Principle** is violated
5. **Testing becomes difficult** due to tight coupling

### Splitting Strategy

```
# BEFORE: native_ifc_alignment.py (800+ lines)
# Contains: PI, Tangent, Curve, Spiral, Manager classes

# AFTER: Split into focused modules
core/
├── alignment/
│   ├── __init__.py          ← Re-exports all public classes
│   ├── pi.py                ← PI class (~100 lines)
│   ├── tangent.py           ← Tangent class (~150 lines)
│   ├── curve.py             ← Curve class (~200 lines)
│   ├── spiral.py            ← Spiral class (~200 lines)
│   └── manager.py           ← AlignmentManager (~200 lines)
```

---

## 📜 Licensing Header Requirements

### Standard Apache 2.0 Header

**EVERY `.py` file MUST begin with this exact header:**

```python
# BlenderCivil - Native IFC Civil Engineering Tools for Blender
# Copyright (C) 2025 Michael Yoder, Desert Springs Civil Engineering, PLLC
#
# This program is licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Module: <module_name>
# Description: <brief one-line description>
# Author: Michael Yoder
# Created: <YYYY-MM-DD>

"""
<Module docstring with detailed description>

This module provides...

Example:
    >>> from blendercivil.core import AlignmentManager
    >>> manager = AlignmentManager()
"""
```

### QA Checklist for Headers

- [ ] License header present at top of file
- [ ] Copyright year is current (2025)
- [ ] Both "Michael Yoder" and "Desert Springs Civil Engineering, PLLC" credited
- [ ] Module name matches actual filename
- [ ] Description is accurate and current
- [ ] Module docstring follows header

---

## 🐍 PEP 8 Compliance Standards

### Critical Rules

```python
# ═══════════════════════════════════════════════════════════════════════════
# LINE LENGTH
# ═══════════════════════════════════════════════════════════════════════════
# Maximum 79 characters for code
# Maximum 72 characters for comments and docstrings
# Acceptable to extend to 99 for complex expressions (team preference)

# ═══════════════════════════════════════════════════════════════════════════
# INDENTATION
# ═══════════════════════════════════════════════════════════════════════════
# Use 4 spaces per indentation level (NEVER tabs)

# ═══════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════
# Order: standard library, third-party, local application
# Separate groups with blank lines
# One import per line (except from X import a, b, c)

# CORRECT:
import os
import sys
from typing import List, Optional, Tuple

import numpy as np
from ifcopenshell import api as ifc_api

from blendercivil.core.native_ifc_manager import IFCManager
from blendercivil.core.alignment import PI, Curve

# INCORRECT:
import os, sys  # Multiple imports on one line
from blendercivil.core import *  # Wildcard imports

# ═══════════════════════════════════════════════════════════════════════════
# NAMING CONVENTIONS
# ═══════════════════════════════════════════════════════════════════════════
# Classes: PascalCase
class VerticalAlignmentManager:
    pass

# Functions/methods: snake_case
def calculate_station_elevation(station: float) -> float:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_SPIRAL_LENGTH = 1000.0
DEFAULT_CURVE_RADIUS = 500.0

# Private members: single leading underscore
def _internal_helper(self):
    pass

# Name-mangled: double leading underscore (rarely needed)
def __truly_private(self):
    pass

# ═══════════════════════════════════════════════════════════════════════════
# WHITESPACE
# ═══════════════════════════════════════════════════════════════════════════
# Two blank lines before top-level functions/classes
# One blank line between methods in a class
# Use blank lines sparingly within functions to show logical sections

# CORRECT:
def function_one():
    pass


def function_two():  # Two blank lines above
    pass


class MyClass:
    
    def method_one(self):
        pass
    
    def method_two(self):  # One blank line above
        pass

# ═══════════════════════════════════════════════════════════════════════════
# OPERATORS
# ═══════════════════════════════════════════════════════════════════════════
# Space around binary operators
x = y + z
result = value * 2

# No space around = in keyword arguments
def function(arg1, arg2=None, arg3=True):
    pass

# No space inside brackets
my_list = [1, 2, 3]  # CORRECT
my_dict = {'key': 'value'}  # CORRECT
```

### Type Hints (Strongly Recommended)

```python
from typing import List, Optional, Dict, Tuple, Union
from dataclasses import dataclass

@dataclass
class PI:
    """Point of Intersection for alignment design."""
    station: float
    northing: float
    easting: float
    name: Optional[str] = None


def get_elevation_at_station(
    station: float,
    alignment_id: str,
    interpolate: bool = True
) -> Optional[float]:
    """
    Calculate elevation at a given station.
    
    Args:
        station: Distance along alignment in meters
        alignment_id: Unique identifier for the alignment
        interpolate: Whether to interpolate between PVIs
        
    Returns:
        Elevation in meters, or None if station is out of range
        
    Raises:
        ValueError: If station is negative
    """
    if station < 0:
        raise ValueError(f"Station must be non-negative, got {station}")
    # Implementation...
```

---

## 📝 Documentation Standards

### Docstring Format (Google Style)

```python
def complex_function(
    param1: float,
    param2: str,
    param3: Optional[List[int]] = None
) -> Dict[str, float]:
    """
    Brief one-line description of function purpose.
    
    Extended description if needed. Can span multiple lines and
    provide additional context about the function's behavior,
    edge cases, or implementation details.
    
    Args:
        param1: Description of first parameter. Include units
            if applicable (e.g., "Distance in meters").
        param2: Description of second parameter.
        param3: Optional list of integers. Defaults to None,
            which means all values are included.
            
    Returns:
        Dictionary mapping station names to their elevations.
        Example: {"STA 0+00": 100.5, "STA 1+00": 102.3}
        
    Raises:
        ValueError: If param1 is negative.
        KeyError: If param2 is not found in the database.
        
    Example:
        >>> result = complex_function(100.0, "alignment_1")
        >>> print(result)
        {'STA 0+00': 100.5}
        
    Note:
        This function requires an active IFC file to be loaded.
        
    See Also:
        related_function: For similar functionality.
        AlignmentManager: The parent class managing alignments.
    """
    pass
```

### Class Docstrings

```python
class VerticalAlignmentManager:
    """
    Manages vertical alignment geometry and IFC export.
    
    This class handles the creation, modification, and export of
    vertical alignments following IFC 4.3 specifications. It uses
    a PI-driven design approach consistent with industry-standard
    civil engineering workflows.
    
    Attributes:
        pvis: List of Point of Vertical Intersection objects.
        segments: Generated tangent and curve segments.
        ifc_file: Reference to the active IFC file.
        
    Example:
        >>> manager = VerticalAlignmentManager()
        >>> manager.add_pvi(station=0.0, elevation=100.0)
        >>> manager.add_pvi(station=500.0, elevation=105.0, curve_length=100.0)
        >>> segments = manager.generate_segments()
        
    Note:
        The manager does not automatically regenerate segments when
        PVIs are modified. Call generate_segments() explicitly.
    """
    
    def __init__(self, ifc_file=None):
        """
        Initialize the VerticalAlignmentManager.
        
        Args:
            ifc_file: Optional IfcOpenShell file object. If None,
                a new file will be created on first export.
        """
        self.pvis: List[PVI] = []
        self.segments: List[Union[VerticalTangent, VerticalCurve]] = []
        self.ifc_file = ifc_file
```

### Inline Comments

```python
# GOOD: Explains WHY, not WHAT
# Convert to radians because numpy trig functions expect radians
angle_rad = angle_deg * (np.pi / 180)

# GOOD: Clarifies complex logic
# Using quadratic formula: x = (-b ± √(b²-4ac)) / 2a
# Only positive root is valid for our geometry
discriminant = b**2 - 4*a*c
x = (-b + np.sqrt(discriminant)) / (2*a)

# BAD: States the obvious
x = x + 1  # Increment x by 1

# BAD: Outdated comment
# Calculate area (NOTE: This now calculates volume!)
volume = length * width * height
```

---

## 🔍 Code Logic Review Guidelines

### Efficiency Patterns to Check

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
for i, point in enumerate(points):
    distance = calculate_distance(origin, point)
    normalized = distance / max_dist

# ═══════════════════════════════════════════════════════════════════════════
# LIST OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

# INEFFICIENT: Repeated list concatenation
result = []
for item in items:
    result = result + [transform(item)]  # Creates new list each time!

# EFFICIENT: Use append or list comprehension
result = [transform(item) for item in items]

# ═══════════════════════════════════════════════════════════════════════════
# DICTIONARY LOOKUPS
# ═══════════════════════════════════════════════════════════════════════════

# INEFFICIENT: Multiple dictionary accesses
if key in my_dict:
    value = my_dict[key]
    process(value)

# EFFICIENT: Use get() or walrus operator
if (value := my_dict.get(key)) is not None:
    process(value)

# ═══════════════════════════════════════════════════════════════════════════
# NUMPY VECTORIZATION
# ═══════════════════════════════════════════════════════════════════════════

# INEFFICIENT: Python loop over numpy array
elevations = []
for station in stations:
    elev = grade * station + start_elev
    elevations.append(elev)

# EFFICIENT: Vectorized numpy operation
elevations = grade * np.array(stations) + start_elev

# ═══════════════════════════════════════════════════════════════════════════
# STRING OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

# INEFFICIENT: String concatenation in loop
result = ""
for item in items:
    result += str(item) + ", "

# EFFICIENT: Use join
result = ", ".join(str(item) for item in items)
```

### Common Anti-Patterns to Flag

```python
# ═══════════════════════════════════════════════════════════════════════════
# ANTI-PATTERN: Mutable default arguments
# ═══════════════════════════════════════════════════════════════════════════

# WRONG: List is shared across all calls!
def add_point(point, points=[]):
    points.append(point)
    return points

# CORRECT: Use None and create inside
def add_point(point, points=None):
    if points is None:
        points = []
    points.append(point)
    return points

# ═══════════════════════════════════════════════════════════════════════════
# ANTI-PATTERN: Bare except clauses
# ═══════════════════════════════════════════════════════════════════════════

# WRONG: Catches everything including KeyboardInterrupt
try:
    risky_operation()
except:
    pass

# CORRECT: Catch specific exceptions
try:
    risky_operation()
except (ValueError, TypeError) as e:
    logger.error(f"Operation failed: {e}")
    raise

# ═══════════════════════════════════════════════════════════════════════════
# ANTI-PATTERN: Magic numbers
# ═══════════════════════════════════════════════════════════════════════════

# WRONG: What does 0.3048 mean?
length_m = length_ft * 0.3048

# CORRECT: Named constant with context
FEET_TO_METERS = 0.3048  # Conversion factor
length_m = length_ft * FEET_TO_METERS

# ═══════════════════════════════════════════════════════════════════════════
# ANTI-PATTERN: Deep nesting
# ═══════════════════════════════════════════════════════════════════════════

# WRONG: Hard to read and maintain
def process(data):
    if data:
        if data.is_valid():
            if data.has_points():
                for point in data.points:
                    if point.is_active:
                        # Finally do something...
                        pass

# CORRECT: Early returns reduce nesting
def process(data):
    if not data:
        return
    if not data.is_valid():
        return
    if not data.has_points():
        return
    
    for point in data.points:
        if not point.is_active:
            continue
        # Do something...
```

---

## 🧹 Debug Code Cleanup

### Identifying Debug Code

Look for and flag these patterns:

```python
# ═══════════════════════════════════════════════════════════════════════════
# PRINT STATEMENTS (should be logging or removed)
# ═══════════════════════════════════════════════════════════════════════════
print(f"DEBUG: station = {station}")  # ❌ Remove or convert to logging
print("HERE!")  # ❌ Definitely remove
print(f"points: {points}")  # ❌ Remove

# CORRECT: Use logging module
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Processing station {station}")

# ═══════════════════════════════════════════════════════════════════════════
# COMMENTED-OUT CODE
# ═══════════════════════════════════════════════════════════════════════════
# Old implementation:
# def old_function():
#     # lots of old code here
#     pass
# ❌ Remove - use git history instead

# ═══════════════════════════════════════════════════════════════════════════
# TODO/FIXME/HACK COMMENTS
# ═══════════════════════════════════════════════════════════════════════════
# TODO: Implement this properly  # ⚠️ Track and address
# FIXME: This breaks with negative values  # ⚠️ Priority fix needed
# HACK: Temporary workaround  # ⚠️ Needs proper solution

# ═══════════════════════════════════════════════════════════════════════════
# HARDCODED TEST VALUES
# ═══════════════════════════════════════════════════════════════════════════
# test_station = 100.0  # ❌ Remove test data from production code
# DEBUG_MODE = True  # ❌ Should be configurable, not hardcoded

# ═══════════════════════════════════════════════════════════════════════════
# UNUSED IMPORTS
# ═══════════════════════════════════════════════════════════════════════════
import json  # ❌ Remove if not used anywhere in file
from typing import Dict, List, Tuple  # ⚠️ Remove unused type imports
```

### Recommended Logging Setup

```python
# At top of each module
import logging

logger = logging.getLogger(__name__)

# Usage throughout module
logger.debug("Detailed diagnostic info")
logger.info("General operational info")
logger.warning("Something unexpected but handled")
logger.error("Error that prevents operation")
logger.exception("Error with stack trace")  # Use in except blocks
```

---

## ✅ Blender Extension Guidelines

### Blender 4.x Manifest Requirements

**File: `blender_manifest.toml`**

```toml
schema_version = "1.0.0"

id = "blendercivil"
name = "BlenderCivil"
tagline = "Native IFC civil engineering design tools"
version = "0.5.0"
type = "add-on"

maintainer = "Michael Yoder, Desert Springs Civil Engineering, PLLC"
license = ["SPDX:Apache-2.0"]

blender_version_min = "4.2.0"
blender_version_max = "5.0.0"

# Optional but recommended
website = "https://github.com/DesertSpringsCivil/BlenderCivil"

[permissions]
files = "Import/export IFC files"
network = "Download CRS databases"

[build]
paths_exclude_pattern = [
    "__pycache__/",
    "*.pyc",
    ".git/",
    ".vscode/",
    "tests/",
    "docs/",
]
```

### Operator Naming Convention

```python
# Blender operator bl_idname format:
# {category}.{action}_{object}

class BLENDERCIVIL_OT_add_pi(bpy.types.Operator):
    """Add a Point of Intersection to the alignment"""
    bl_idname = "blendercivil.add_pi"
    bl_label = "Add PI"
    bl_options = {'REGISTER', 'UNDO'}

class BLENDERCIVIL_OT_export_ifc(bpy.types.Operator):
    """Export alignment to IFC file"""
    bl_idname = "blendercivil.export_ifc"
    bl_label = "Export to IFC"
    bl_options = {'REGISTER'}
```

### Panel Naming Convention

```python
class BLENDERCIVIL_PT_alignment_main(bpy.types.Panel):
    """Main alignment panel"""
    bl_idname = "BLENDERCIVIL_PT_alignment_main"
    bl_label = "Alignment"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BlenderCivil"
```

### Registration Pattern

```python
# In __init__.py
classes = [
    BLENDERCIVIL_OT_add_pi,
    BLENDERCIVIL_OT_export_ifc,
    BLENDERCIVIL_PT_alignment_main,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

---

## 📋 QA Checklist Template

Use this checklist when reviewing each file:

### File: `__________________.py`

**Header & Documentation:**
- [ ] Apache 2.0 license header present and complete
- [ ] Copyright credits Michael Yoder and Desert Springs Civil Engineering, PLLC
- [ ] Module docstring present with description
- [ ] All public functions/classes have docstrings
- [ ] Type hints present for function signatures

**Code Quality:**
- [ ] File length within guidelines (<600 lines preferred)
- [ ] Functions are focused (single responsibility)
- [ ] No functions exceed 50 lines (consider splitting)
- [ ] Naming follows conventions (snake_case, PascalCase)
- [ ] No magic numbers (use named constants)
- [ ] No deep nesting (max 3-4 levels)

**PEP 8 Compliance:**
- [ ] Line length ≤79 chars (99 acceptable)
- [ ] Imports properly ordered and grouped
- [ ] Consistent 4-space indentation
- [ ] Proper whitespace around operators
- [ ] Two blank lines before functions/classes

**Debug Cleanup:**
- [ ] No print() statements (use logging)
- [ ] No commented-out code blocks
- [ ] No unused imports
- [ ] TODO/FIXME comments tracked
- [ ] No hardcoded test values

**Blender Specific:**
- [ ] Operators follow bl_idname convention
- [ ] Panels follow naming convention
- [ ] Registration in __init__.py
- [ ] Core logic separated from UI code

**Logic Review:**
- [ ] No obvious inefficiencies
- [ ] No mutable default arguments
- [ ] Proper exception handling
- [ ] Edge cases considered

---

## 🔗 Reference Links

- **PEP 8**: https://peps.python.org/pep-0008/
- **Blender Extension Docs**: https://docs.blender.org/manual/en/latest/advanced/extensions/getting_started.html
- **Blender Addon Guidelines**: https://developer.blender.org/docs/handbook/extensions/addon_guidelines/
- **IFC 4.3 Schema**: https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/
- **Google Python Style Guide**: https://google.github.io/styleguide/pyguide.html

---

## 📊 Priority Order for QA

1. **Critical** - License headers (legal requirement)
2. **High** - Debug code removal (production readiness)
3. **High** - Logic errors and inefficiencies (functionality)
4. **Medium** - PEP 8 compliance (maintainability)
5. **Medium** - Documentation completeness (usability)
6. **Low** - File length optimization (nice to have)

---

*This document serves as the authoritative reference for BlenderCivil code quality standards. All contributions should adhere to these guidelines.*

**Document Version:** 1.0  
**Last Updated:** November 25, 2025  
**Maintained By:** Michael Yoder, Desert Springs Civil Engineering, PLLC
