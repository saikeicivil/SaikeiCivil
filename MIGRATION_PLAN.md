# Saikei Civil Migration Plan: Adopting Bonsai Architecture

## Overview

This plan migrates Saikei Civil from its current architecture to the Bonsai three-layer pattern while preserving existing functionality. The migration is designed to be incremental - each phase delivers working code.

**Current State:** ~8,000+ lines across monolithic modules with mixed concerns
**Target State:** Clean three-layer architecture (Core → Tool → BIM Module)

---

## Migration Phases

| Phase | Focus | Priority | Estimated Effort |
|-------|-------|----------|------------------|
| **Phase 1** | Foundation - Interfaces & Tool Layer | HIGH | First |
| **Phase 2** | Refactor Alignment Module (Proof of Concept) | HIGH | Second |
| **Phase 3** | Adopt ifcopenshell.api | HIGH | Third |
| **Phase 4** | Migrate Remaining Modules | MEDIUM | Fourth |
| **Phase 5** | Reorganize to bim/module/ Structure | MEDIUM | Fifth |
| **Phase 6** | Testing Infrastructure | MEDIUM | Sixth |
| **Phase 7** | Bonsai Compatibility & Cleanup | LOW | Last |

---

## Phase 1: Foundation - Interfaces & Tool Layer

**Goal:** Establish the architectural foundation without breaking existing code.

### Step 1.1: Create Interface Definitions

Create `core/tool.py` with abstract interfaces:

```python
# saikei_civil/core/tool.py
"""
Interface definitions for Saikei Civil tools.
Following Bonsai's pattern of separating interfaces from implementations.
"""
from typing import TYPE_CHECKING, Optional, List, Dict, Any
import abc

if TYPE_CHECKING:
    import bpy
    import ifcopenshell


def interface(cls):
    """Decorator that converts all public methods to @classmethod @abstractmethod"""
    for name, method in list(cls.__dict__.items()):
        if callable(method) and not name.startswith('_'):
            setattr(cls, name, classmethod(abc.abstractmethod(method)))
    cls.__original_qualname__ = cls.__qualname__
    return cls


@interface
class Ifc:
    """Interface for IFC file operations."""
    def get(cls) -> "ifcopenshell.file":
        """Get the current IFC file."""
        pass

    def run(cls, command: str, **kwargs) -> Any:
        """Run an ifcopenshell.api command."""
        pass

    def get_entity(cls, obj: "bpy.types.Object") -> "ifcopenshell.entity_instance":
        """Get IFC entity from Blender object."""
        pass

    def get_object(cls, entity: "ifcopenshell.entity_instance") -> "bpy.types.Object":
        """Get Blender object from IFC entity."""
        pass

    def link(cls, entity: "ifcopenshell.entity_instance", obj: "bpy.types.Object") -> None:
        """Link IFC entity to Blender object."""
        pass

    def get_schema(cls) -> str:
        """Get the IFC schema version."""
        pass


@interface
class Blender:
    """Interface for Blender operations."""
    def create_object(cls, name: str, data: Any = None) -> "bpy.types.Object":
        """Create a new Blender object."""
        pass

    def get_active_object(cls) -> Optional["bpy.types.Object"]:
        """Get the active object."""
        pass

    def get_selected_objects(cls) -> List["bpy.types.Object"]:
        """Get selected objects."""
        pass

    def set_active_object(cls, obj: "bpy.types.Object") -> None:
        """Set the active object."""
        pass

    def update_viewport(cls) -> None:
        """Force viewport update."""
        pass

    def get_collection(cls, name: str, create: bool = True) -> "bpy.types.Collection":
        """Get or create a collection."""
        pass


@interface
class Alignment:
    """Interface for horizontal alignment operations."""
    def create(cls, name: str, pis: List[Dict]) -> "ifcopenshell.entity_instance":
        """Create a new horizontal alignment."""
        pass

    def get_pis(cls, alignment: "ifcopenshell.entity_instance") -> List[Dict]:
        """Get PI data from alignment."""
        pass

    def set_pis(cls, alignment: "ifcopenshell.entity_instance", pis: List[Dict]) -> None:
        """Update alignment PIs."""
        pass

    def get_segments(cls, alignment: "ifcopenshell.entity_instance") -> List[Dict]:
        """Get computed segments from alignment."""
        pass

    def update_visualization(cls, alignment: "ifcopenshell.entity_instance") -> None:
        """Update Blender visualization from IFC data."""
        pass

    def get_station_at_point(cls, alignment: "ifcopenshell.entity_instance", point: tuple) -> float:
        """Get station value at a point."""
        pass


@interface
class VerticalAlignment:
    """Interface for vertical alignment operations."""
    def create(cls, horizontal: "ifcopenshell.entity_instance", pvis: List[Dict]) -> "ifcopenshell.entity_instance":
        """Create vertical alignment for a horizontal alignment."""
        pass

    def get_pvis(cls, alignment: "ifcopenshell.entity_instance") -> List[Dict]:
        """Get PVI data from vertical alignment."""
        pass

    def set_pvis(cls, alignment: "ifcopenshell.entity_instance", pvis: List[Dict]) -> None:
        """Update vertical alignment PVIs."""
        pass

    def get_elevation_at_station(cls, alignment: "ifcopenshell.entity_instance", station: float) -> float:
        """Get elevation at a station."""
        pass


@interface
class Georeference:
    """Interface for georeferencing operations."""
    def add_georeferencing(cls) -> None:
        """Add georeferencing to the IFC file."""
        pass

    def get_crs(cls) -> Optional[Dict]:
        """Get current CRS information."""
        pass

    def set_crs(cls, epsg_code: int) -> None:
        """Set the coordinate reference system."""
        pass

    def get_map_conversion(cls) -> Optional[Dict]:
        """Get map conversion parameters."""
        pass

    def set_map_conversion(cls, params: Dict) -> None:
        """Set map conversion parameters."""
        pass

    def transform_to_global(cls, local_coords: tuple) -> tuple:
        """Transform local coordinates to global."""
        pass

    def transform_to_local(cls, global_coords: tuple) -> tuple:
        """Transform global coordinates to local."""
        pass


@interface
class CrossSection:
    """Interface for cross-section operations."""
    def create_assembly(cls, name: str) -> Any:
        """Create a new road assembly."""
        pass

    def add_component(cls, assembly: Any, component_type: str, **params) -> Any:
        """Add a component to an assembly."""
        pass

    def get_profile_at_station(cls, assembly: Any, station: float) -> List[tuple]:
        """Get cross-section profile points at a station."""
        pass


@interface
class Corridor:
    """Interface for corridor operations."""
    def create(cls, alignment: "ifcopenshell.entity_instance", assembly: Any,
               start_station: float, end_station: float, interval: float) -> Any:
        """Create a corridor from alignment and assembly."""
        pass

    def generate_mesh(cls, corridor: Any) -> "bpy.types.Object":
        """Generate 3D mesh for corridor."""
        pass
```

### Step 1.2: Create Tool Directory Structure

```
saikei_civil/
├── tool/                    # NEW - Layer 2: Blender implementations
│   ├── __init__.py          # Exports all tool classes
│   ├── ifc.py               # Ifc tool implementation
│   ├── blender.py           # Blender tool implementation
│   ├── alignment.py         # Alignment tool implementation
│   ├── vertical_alignment.py
│   ├── georeference.py
│   ├── cross_section.py
│   └── corridor.py
```

### Step 1.3: Implement Ifc Tool (Wraps NativeIfcManager)

```python
# saikei_civil/tool/ifc.py
"""
Ifc tool implementation - bridges core interfaces with existing NativeIfcManager.
"""
import bpy
import ifcopenshell
import ifcopenshell.api

import saikei_civil.core.tool


class Ifc(saikei_civil.core.tool.Ifc):
    """Blender-specific IFC operations."""

    @classmethod
    def get(cls) -> ifcopenshell.file:
        from saikei_civil.core.ifc_manager import NativeIfcManager
        return NativeIfcManager.get_file()

    @classmethod
    def run(cls, command: str, **kwargs):
        """Run an ifcopenshell.api command.

        Example: Ifc.run("alignment.create", name="Main Road")
        """
        ifc = cls.get()
        if ifc is None:
            raise RuntimeError("No IFC file loaded")

        # Parse command: "module.function" -> ifcopenshell.api.module.function
        parts = command.split(".")
        if len(parts) != 2:
            raise ValueError(f"Invalid command format: {command}. Expected 'module.function'")

        module_name, func_name = parts
        module = getattr(ifcopenshell.api, module_name, None)
        if module is None:
            raise ValueError(f"Unknown ifcopenshell.api module: {module_name}")

        func = getattr(module, func_name, None)
        if func is None:
            raise ValueError(f"Unknown function: {module_name}.{func_name}")

        return func(ifc, **kwargs)

    @classmethod
    def get_entity(cls, obj: bpy.types.Object) -> ifcopenshell.entity_instance:
        entity_id = obj.get("ifc_definition_id")
        if entity_id is None:
            return None
        ifc = cls.get()
        if ifc is None:
            return None
        try:
            return ifc.by_id(entity_id)
        except RuntimeError:
            return None

    @classmethod
    def get_object(cls, entity: ifcopenshell.entity_instance) -> bpy.types.Object:
        entity_id = entity.id()
        for obj in bpy.data.objects:
            if obj.get("ifc_definition_id") == entity_id:
                return obj
        return None

    @classmethod
    def link(cls, entity: ifcopenshell.entity_instance, obj: bpy.types.Object) -> None:
        obj["ifc_definition_id"] = entity.id()
        obj["ifc_class"] = entity.is_a()
        if hasattr(entity, "GlobalId"):
            obj["ifc_global_id"] = entity.GlobalId

    @classmethod
    def get_schema(cls) -> str:
        ifc = cls.get()
        return ifc.schema if ifc else "IFC4X3"

    # Operator mixin for consistent IFC operation handling
    class Operator:
        """Base mixin for operators that modify IFC data."""

        def execute(self, context):
            # Could add transaction handling, undo support, etc.
            return self._execute(context)

        def _execute(self, context):
            raise NotImplementedError("Implement _execute in subclass")
```

### Step 1.4: Implement Blender Tool

```python
# saikei_civil/tool/blender.py
"""
Blender tool implementation - Blender-specific utilities.
"""
import bpy
from typing import Optional, List, Any

import saikei_civil.core.tool


class Blender(saikei_civil.core.tool.Blender):
    """Blender-specific utilities."""

    @classmethod
    def create_object(cls, name: str, data: Any = None) -> bpy.types.Object:
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        return obj

    @classmethod
    def get_active_object(cls) -> Optional[bpy.types.Object]:
        return bpy.context.active_object

    @classmethod
    def get_selected_objects(cls) -> List[bpy.types.Object]:
        return list(bpy.context.selected_objects)

    @classmethod
    def set_active_object(cls, obj: bpy.types.Object) -> None:
        bpy.context.view_layer.objects.active = obj

    @classmethod
    def update_viewport(cls) -> None:
        bpy.context.view_layer.update()

    @classmethod
    def get_collection(cls, name: str, create: bool = True) -> bpy.types.Collection:
        if name in bpy.data.collections:
            return bpy.data.collections[name]
        if create:
            collection = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(collection)
            return collection
        return None
```

### Step 1.5: Create Tool Package Init

```python
# saikei_civil/tool/__init__.py
"""
Tool layer - Blender-specific implementations of core interfaces.

Usage:
    import saikei_civil.tool as tool

    ifc_file = tool.Ifc.get()
    tool.Ifc.run("alignment.create", name="My Alignment")
"""
from .ifc import Ifc
from .blender import Blender

# These will be added as we migrate each module
# from .alignment import Alignment
# from .vertical_alignment import VerticalAlignment
# from .georeference import Georeference
# from .cross_section import CrossSection
# from .corridor import Corridor

__all__ = [
    "Ifc",
    "Blender",
    # "Alignment",
    # "VerticalAlignment",
    # "Georeference",
    # "CrossSection",
    # "Corridor",
]
```

### Step 1.6: Update Core Package Init

```python
# Add to saikei_civil/core/__init__.py

# Export interfaces
from .tool import (
    interface,
    Ifc,
    Blender,
    Alignment,
    VerticalAlignment,
    Georeference,
    CrossSection,
    Corridor,
)
```

### Deliverables for Phase 1:
- [ ] `core/tool.py` - Interface definitions
- [ ] `tool/__init__.py` - Package init
- [ ] `tool/ifc.py` - Ifc tool wrapping NativeIfcManager
- [ ] `tool/blender.py` - Blender utilities
- [ ] Updated `core/__init__.py` with interface exports
- [ ] All existing functionality still works (no breaking changes)

---

## Phase 2: Refactor Alignment Module (Proof of Concept)

**Goal:** Demonstrate the full three-layer pattern with one complete module.

### Step 2.1: Create Pure Core Logic

Extract business logic from `NativeIfcAlignment` into pure functions:

```python
# saikei_civil/core/alignment.py (NEW - pure business logic)
"""
Horizontal alignment core logic.
Pure Python - no Blender imports (use TYPE_CHECKING only).
"""
from typing import TYPE_CHECKING, List, Dict, Any, Optional
import math

if TYPE_CHECKING:
    import saikei_civil.tool as tool
    import ifcopenshell


def create_horizontal_alignment(
    ifc: "type[tool.Ifc]",
    alignment: "type[tool.Alignment]",
    blender: "type[tool.Blender]",
    name: str,
    pis: List[Dict],
) -> "ifcopenshell.entity_instance":
    """
    Create a horizontal alignment using the PI method.

    Args:
        ifc: IFC tool for file operations
        alignment: Alignment tool for alignment-specific operations
        blender: Blender tool for visualization
        name: Alignment name
        pis: List of PI dictionaries with keys:
            - x, y: coordinates
            - radius: curve radius (0 for tangent points)

    Returns:
        The created IfcAlignment entity
    """
    # Validate inputs
    if len(pis) < 2:
        raise ValueError("Alignment requires at least 2 PIs")

    # Create alignment via ifcopenshell.api
    alignment_entity = ifc.run(
        "alignment.create_by_pi_method",
        name=name,
        horizontal_pi_data=_format_pi_data(pis)
    )

    # Create Blender visualization
    obj = blender.create_object(name)

    # Link IFC entity to Blender object
    ifc.link(alignment_entity, obj)

    # Update visualization from IFC data
    alignment.update_visualization(alignment_entity)

    return alignment_entity


def update_alignment_pis(
    ifc: "type[tool.Ifc]",
    alignment: "type[tool.Alignment]",
    alignment_entity: "ifcopenshell.entity_instance",
    pis: List[Dict],
) -> None:
    """Update an existing alignment's PI geometry."""
    # Use ifcopenshell.api to update
    ifc.run(
        "alignment.layout_horizontal_alignment_by_pi_method",
        alignment=alignment_entity,
        pi_data=_format_pi_data(pis)
    )

    # Refresh visualization
    alignment.update_visualization(alignment_entity)


def get_point_at_station(
    ifc: "type[tool.Ifc]",
    alignment_entity: "ifcopenshell.entity_instance",
    station: float,
) -> Optional[Dict]:
    """
    Get coordinates and direction at a station.

    Returns:
        Dictionary with x, y, direction (radians), or None if invalid station
    """
    # Get horizontal layout
    h_layout = ifc.run("alignment.get_horizontal_layout", alignment=alignment_entity)
    if not h_layout:
        return None

    # Get segments
    segments = ifc.run("alignment.get_layout_segments", layout=h_layout)

    # Find segment containing station and interpolate
    return _interpolate_station(segments, station)


def _format_pi_data(pis: List[Dict]) -> List[Dict]:
    """Format PI data for ifcopenshell.api."""
    return [
        {
            "Coordinates": (pi["x"], pi["y"]),
            "Radius": pi.get("radius", 0.0),
        }
        for pi in pis
    ]


def _interpolate_station(segments: List, station: float) -> Optional[Dict]:
    """Interpolate position at station from segments."""
    cumulative_length = 0.0

    for segment in segments:
        seg_length = segment.SegmentLength.wrappedValue if hasattr(segment.SegmentLength, 'wrappedValue') else segment.SegmentLength

        if cumulative_length + seg_length >= station:
            # Station is in this segment
            local_distance = station - cumulative_length
            return _interpolate_segment(segment, local_distance)

        cumulative_length += seg_length

    return None


def _interpolate_segment(segment, distance: float) -> Dict:
    """Interpolate position within a single segment."""
    # Get start point and direction
    start_x = segment.StartPoint.Coordinates[0]
    start_y = segment.StartPoint.Coordinates[1]
    start_dir = segment.StartDirection

    segment_type = segment.PredefinedType

    if segment_type == "LINE":
        # Linear interpolation
        x = start_x + distance * math.cos(start_dir)
        y = start_y + distance * math.sin(start_dir)
        direction = start_dir
    elif segment_type == "CIRCULARARC":
        # Arc interpolation
        radius = segment.Radius
        is_ccw = segment.IsCCW if hasattr(segment, 'IsCCW') else True

        # Calculate center point
        perp_dir = start_dir + (math.pi / 2 if is_ccw else -math.pi / 2)
        cx = start_x + radius * math.cos(perp_dir)
        cy = start_y + radius * math.sin(perp_dir)

        # Calculate angle subtended
        angle = distance / radius * (1 if is_ccw else -1)

        # Calculate new position
        start_angle = math.atan2(start_y - cy, start_x - cx)
        new_angle = start_angle + angle

        x = cx + radius * math.cos(new_angle)
        y = cy + radius * math.sin(new_angle)
        direction = new_angle + (math.pi / 2 if is_ccw else -math.pi / 2)
    else:
        # Fallback to linear
        x = start_x + distance * math.cos(start_dir)
        y = start_y + distance * math.sin(start_dir)
        direction = start_dir

    return {"x": x, "y": y, "direction": direction}
```

### Step 2.2: Implement Alignment Tool

```python
# saikei_civil/tool/alignment.py
"""
Alignment tool implementation - bridges core interfaces with Blender.
"""
import bpy
import math
from typing import List, Dict, Optional

import saikei_civil.core.tool
from . import Ifc


class Alignment(saikei_civil.core.tool.Alignment):
    """Blender-specific alignment operations."""

    @classmethod
    def create(cls, name: str, pis: List[Dict]) -> "ifcopenshell.entity_instance":
        """Create alignment using ifcopenshell.api."""
        return Ifc.run(
            "alignment.create_by_pi_method",
            name=name,
            horizontal_pi_data=[
                {"Coordinates": (pi["x"], pi["y"]), "Radius": pi.get("radius", 0.0)}
                for pi in pis
            ]
        )

    @classmethod
    def get_pis(cls, alignment) -> List[Dict]:
        """Extract PI data from alignment."""
        # Get horizontal layout and segments
        h_layout = Ifc.run("alignment.get_horizontal_layout", alignment=alignment)
        if not h_layout:
            return []

        # Reconstruct PIs from segments
        # (This is a simplification - full implementation needs segment analysis)
        pis = []
        segments = Ifc.run("alignment.get_layout_segments", layout=h_layout)

        for seg in segments:
            pis.append({
                "x": seg.StartPoint.Coordinates[0],
                "y": seg.StartPoint.Coordinates[1],
                "radius": getattr(seg, "Radius", 0.0) or 0.0,
            })

        return pis

    @classmethod
    def set_pis(cls, alignment, pis: List[Dict]) -> None:
        """Update alignment PIs."""
        Ifc.run(
            "alignment.layout_horizontal_alignment_by_pi_method",
            alignment=alignment,
            pi_data=[
                {"Coordinates": (pi["x"], pi["y"]), "Radius": pi.get("radius", 0.0)}
                for pi in pis
            ]
        )
        cls.update_visualization(alignment)

    @classmethod
    def get_segments(cls, alignment) -> List[Dict]:
        """Get computed segments."""
        h_layout = Ifc.run("alignment.get_horizontal_layout", alignment=alignment)
        if not h_layout:
            return []

        segments = Ifc.run("alignment.get_layout_segments", layout=h_layout)
        return [cls._segment_to_dict(seg) for seg in segments]

    @classmethod
    def update_visualization(cls, alignment) -> None:
        """Update Blender curve from IFC alignment data."""
        obj = Ifc.get_object(alignment)
        if not obj:
            return

        # Get segments
        segments = cls.get_segments(alignment)
        if not segments:
            return

        # Create or update curve
        cls._update_curve_geometry(obj, segments)

    @classmethod
    def get_station_at_point(cls, alignment, point: tuple) -> float:
        """Get station at closest point on alignment."""
        # Implementation would project point onto alignment
        # Placeholder for now
        return 0.0

    @classmethod
    def _segment_to_dict(cls, segment) -> Dict:
        """Convert IFC segment to dictionary."""
        return {
            "type": segment.PredefinedType,
            "start_x": segment.StartPoint.Coordinates[0],
            "start_y": segment.StartPoint.Coordinates[1],
            "start_direction": segment.StartDirection,
            "length": segment.SegmentLength.wrappedValue if hasattr(segment.SegmentLength, 'wrappedValue') else segment.SegmentLength,
            "radius": getattr(segment, "Radius", None),
        }

    @classmethod
    def _update_curve_geometry(cls, obj: bpy.types.Object, segments: List[Dict]) -> None:
        """Update Blender curve object from segment data."""
        # Create curve data if needed
        if obj.type != 'CURVE':
            curve_data = bpy.data.curves.new(obj.name, 'CURVE')
            curve_data.dimensions = '3D'
            obj.data = curve_data

        curve = obj.data
        curve.splines.clear()

        # Generate points from segments
        points = cls._generate_curve_points(segments)

        if points:
            spline = curve.splines.new('POLY')
            spline.points.add(len(points) - 1)
            for i, (x, y, z) in enumerate(points):
                spline.points[i].co = (x, y, z, 1.0)

    @classmethod
    def _generate_curve_points(cls, segments: List[Dict], resolution: int = 10) -> List[tuple]:
        """Generate 3D points from segments."""
        points = []

        for seg in segments:
            seg_type = seg["type"]
            start_x = seg["start_x"]
            start_y = seg["start_y"]
            start_dir = seg["start_direction"]
            length = seg["length"]

            if seg_type == "LINE":
                # Add start and end points
                if not points:
                    points.append((start_x, start_y, 0.0))
                end_x = start_x + length * math.cos(start_dir)
                end_y = start_y + length * math.sin(start_dir)
                points.append((end_x, end_y, 0.0))

            elif seg_type == "CIRCULARARC":
                radius = seg["radius"]
                # Add points along arc
                num_points = max(2, int(length / 5.0))  # Point every 5 units
                for i in range(num_points + 1):
                    t = i / num_points
                    # Arc interpolation
                    angle = length * t / radius
                    # Simplified - would need proper arc calculation
                    x = start_x + length * t * math.cos(start_dir)
                    y = start_y + length * t * math.sin(start_dir)
                    points.append((x, y, 0.0))

        return points
```

### Step 2.3: Create Alignment Operators Using New Pattern

```python
# saikei_civil/operators/alignment_operators_v2.py (NEW - alongside existing)
"""
Alignment operators using the new three-layer architecture.
"""
import bpy
from bpy.props import StringProperty, FloatProperty, CollectionProperty

import saikei_civil.core.alignment as core
import saikei_civil.tool as tool


class SAIKEI_OT_create_alignment_v2(bpy.types.Operator, tool.Ifc.Operator):
    """Create a new horizontal alignment using the new architecture."""
    bl_idname = "saikei.create_alignment_v2"
    bl_label = "Create Alignment (v2)"
    bl_options = {"REGISTER", "UNDO"}

    name: StringProperty(
        name="Name",
        default="Alignment",
        description="Name for the new alignment"
    )

    def _execute(self, context):
        # Get PIs from UI properties
        props = context.scene.bc_alignment
        pis = self._get_pis_from_props(props)

        if len(pis) < 2:
            self.report({'ERROR'}, "At least 2 PIs required")
            return {'CANCELLED'}

        try:
            # Call core function with tool implementations
            alignment = core.create_horizontal_alignment(
                tool.Ifc,
                tool.Alignment,
                tool.Blender,
                name=self.name,
                pis=pis
            )

            self.report({'INFO'}, f"Created alignment: {self.name}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

    def _get_pis_from_props(self, props) -> list:
        """Extract PI data from UI properties."""
        pis = []
        # Adapt to existing property structure
        for pi_item in props.alignment_list:
            pis.append({
                "x": pi_item.x if hasattr(pi_item, 'x') else 0.0,
                "y": pi_item.y if hasattr(pi_item, 'y') else 0.0,
                "radius": pi_item.radius if hasattr(pi_item, 'radius') else 0.0,
            })
        return pis


class SAIKEI_OT_update_alignment_v2(bpy.types.Operator, tool.Ifc.Operator):
    """Update alignment from PI objects."""
    bl_idname = "saikei.update_alignment_v2"
    bl_label = "Update Alignment (v2)"
    bl_options = {"REGISTER", "UNDO"}

    def _execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}

        alignment = tool.Ifc.get_entity(obj)
        if not alignment or not alignment.is_a("IfcAlignment"):
            self.report({'ERROR'}, "Active object is not an alignment")
            return {'CANCELLED'}

        # Get updated PI positions from Blender objects
        pis = self._collect_pi_positions(alignment)

        # Update via core function
        core.update_alignment_pis(
            tool.Ifc,
            tool.Alignment,
            alignment,
            pis
        )

        self.report({'INFO'}, "Alignment updated")
        return {'FINISHED'}

    def _collect_pi_positions(self, alignment) -> list:
        """Collect PI positions from linked Blender objects."""
        # Implementation depends on how PIs are stored
        pis = []
        # ... collect from Blender objects
        return pis


# Registration
classes = [
    SAIKEI_OT_create_alignment_v2,
    SAIKEI_OT_update_alignment_v2,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

### Deliverables for Phase 2:
- [ ] `core/alignment.py` - Pure business logic (no Blender imports)
- [ ] `tool/alignment.py` - Blender-specific implementation
- [ ] `operators/alignment_operators_v2.py` - New operators using pattern
- [ ] Updated `tool/__init__.py` to export Alignment
- [ ] Tests demonstrating core logic works without Blender
- [ ] Old operators still work (parallel operation)

---

## Phase 3: Adopt ifcopenshell.api

**Goal:** Replace direct IFC entity creation with ifcopenshell.api calls.

### Step 3.1: Audit Current Direct IFC Usage

Search for patterns like:
- `ifc.create_entity("IfcAlignment", ...)`
- `ifc.createIfcAlignment(...)`
- Direct attribute manipulation

Replace with:
- `ifcopenshell.api.alignment.create(...)`
- `ifcopenshell.api.root.create_entity(...)`

### Step 3.2: Create API Wrapper Functions

For any operations not covered by ifcopenshell.api, create wrapper functions in `tool/ifc.py`:

```python
# In tool/ifc.py, add helper methods

@classmethod
def ensure_spatial_structure(cls) -> tuple:
    """Ensure project, site, and road exist."""
    ifc = cls.get()

    # Get or create project
    projects = ifc.by_type("IfcProject")
    if projects:
        project = projects[0]
    else:
        project = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcProject", name="Project")

    # Get or create site
    sites = ifc.by_type("IfcSite")
    if sites:
        site = sites[0]
    else:
        site = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcSite", name="Site")
        ifcopenshell.api.aggregate.assign_object(ifc, products=[site], relating_object=project)

    # Get or create road
    roads = ifc.by_type("IfcRoad")
    if roads:
        road = roads[0]
    else:
        road = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcRoad", name="Road")
        ifcopenshell.api.aggregate.assign_object(ifc, products=[road], relating_object=site)

    return project, site, road
```

### Step 3.3: Update NativeIfcAlignment to Use API

Modify `core/horizontal_alignment/manager.py`:

```python
# Before (direct entity creation):
self.alignment = self.ifc.create_entity("IfcAlignment", GlobalId=ifcopenshell.guid.new(), Name=name)

# After (via API):
import ifcopenshell.api
self.alignment = ifcopenshell.api.alignment.create(self.ifc, name=name)
```

### Step 3.4: Document API Coverage

Create a mapping document showing which operations use which API:

| Operation | Current Code | ifcopenshell.api |
|-----------|-------------|------------------|
| Create alignment | `create_entity("IfcAlignment")` | `alignment.create()` |
| Add horizontal | Manual segment creation | `alignment.create_by_pi_method()` |
| Add vertical | Manual creation | `alignment.add_vertical_layout()` |
| Georeferencing | Manual | `georeference.add_georeferencing()` |

### Deliverables for Phase 3:
- [ ] Audit document of all direct IFC usage
- [ ] Updated NativeIfcAlignment using ifcopenshell.api
- [ ] Updated NativeIfcManager using ifcopenshell.api
- [ ] Updated georeferencing using ifcopenshell.api
- [ ] All tests still pass
- [ ] External viewer compatibility verified

---

## Phase 4: Migrate Remaining Modules

**Goal:** Apply the pattern to all feature modules.

### Step 4.1: Vertical Alignment

```
core/vertical_alignment.py (NEW - pure logic)
tool/vertical_alignment.py (NEW - Blender implementation)
```

### Step 4.2: Georeferencing

```
core/georeferencing.py (NEW - pure logic)
tool/georeference.py (NEW - Blender implementation)
```

### Step 4.3: Cross-Sections

```
core/cross_section.py (NEW - pure logic)
tool/cross_section.py (NEW - Blender implementation)
```

### Step 4.4: Corridors

```
core/corridor.py (NEW - pure logic)
tool/corridor.py (NEW - Blender implementation)
```

### Migration Pattern for Each Module:

1. **Extract pure logic** into `core/{module}.py`
   - No Blender imports (use TYPE_CHECKING)
   - Functions receive tool interfaces as parameters
   - Return IFC entities or data, not Blender objects

2. **Create tool implementation** in `tool/{module}.py`
   - Implement interface from `core/tool.py`
   - Handle Blender-specific visualization
   - Bridge between core logic and Blender

3. **Update operators** to use new pattern
   - Inherit from `tool.Ifc.Operator`
   - Call core functions with tool implementations
   - Keep existing operators working during transition

4. **Update tests**
   - Core tests run without Blender
   - Tool tests use pytest-blender

### Deliverables for Phase 4:
- [ ] `core/vertical_alignment.py` + `tool/vertical_alignment.py`
- [ ] `core/georeferencing.py` + `tool/georeference.py`
- [ ] `core/cross_section.py` + `tool/cross_section.py`
- [ ] `core/corridor.py` + `tool/corridor.py`
- [ ] All existing functionality preserved
- [ ] Tests for each module

---

## Phase 5: Reorganize to bim/module/ Structure

**Goal:** Group related code into self-contained modules.

### Step 5.1: Create Module Structure

```
saikei_civil/
├── bim/                         # NEW - Layer 3: Blender integration
│   ├── __init__.py
│   └── module/
│       ├── __init__.py
│       ├── alignment/
│       │   ├── __init__.py      # Registration
│       │   ├── operator.py      # Operators
│       │   ├── prop.py          # PropertyGroups
│       │   └── ui.py            # Panels
│       ├── vertical_alignment/
│       │   ├── __init__.py
│       │   ├── operator.py
│       │   ├── prop.py
│       │   └── ui.py
│       ├── georeferencing/
│       │   ├── __init__.py
│       │   ├── operator.py
│       │   ├── prop.py
│       │   └── ui.py
│       ├── cross_section/
│       │   ├── __init__.py
│       │   ├── operator.py
│       │   ├── prop.py
│       │   └── ui.py
│       └── corridor/
│           ├── __init__.py
│           ├── operator.py
│           ├── prop.py
│           └── ui.py
```

### Step 5.2: Module Init Pattern

```python
# saikei_civil/bim/module/alignment/__init__.py
"""Alignment module - horizontal alignment functionality."""

from . import operator
from . import prop
from . import ui


def register():
    prop.register()      # Properties first (operators depend on them)
    operator.register()
    ui.register()


def unregister():
    ui.unregister()
    operator.unregister()
    prop.unregister()
```

### Step 5.3: BIM Package Init

```python
# saikei_civil/bim/__init__.py
"""BIM integration layer - Blender UI modules."""

from .module import alignment
from .module import vertical_alignment
from .module import georeferencing
from .module import cross_section
from .module import corridor

modules = [
    alignment,
    vertical_alignment,
    georeferencing,
    cross_section,
    corridor,
]


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
```

### Step 5.4: Migrate Code to New Locations

| Current Location | New Location |
|-----------------|--------------|
| `operators/alignment_operators.py` | `bim/module/alignment/operator.py` |
| `ui/alignment_properties.py` | `bim/module/alignment/prop.py` |
| `ui/alignment_panel.py` | `bim/module/alignment/ui.py` |
| ... | ... |

### Step 5.5: Update Main Init

```python
# saikei_civil/__init__.py (updated registration)

from . import core
from . import tool
from . import bim  # NEW

def register():
    core.register()
    tool.register()
    bim.register()  # Registers all modules

def unregister():
    bim.unregister()
    tool.unregister()
    core.unregister()
```

### Step 5.6: Deprecation Layer

Keep old imports working during transition:

```python
# saikei_civil/operators/__init__.py (deprecation shim)
"""
DEPRECATED: Use saikei_civil.bim.module.{module}.operator instead.
This module remains for backwards compatibility.
"""
import warnings

def __getattr__(name):
    warnings.warn(
        f"saikei_civil.operators.{name} is deprecated. "
        f"Use saikei_civil.bim.module.*.operator instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # Return from new location
    ...
```

### Deliverables for Phase 5:
- [ ] `bim/` directory structure created
- [ ] All operators migrated to `bim/module/*/operator.py`
- [ ] All properties migrated to `bim/module/*/prop.py`
- [ ] All panels migrated to `bim/module/*/ui.py`
- [ ] Deprecation warnings for old import paths
- [ ] Main `__init__.py` updated
- [ ] All functionality preserved

---

## Phase 6: Testing Infrastructure

**Goal:** Establish testing patterns matching Bonsai.

### Step 6.1: Create Test Bootstrap

```python
# saikei_civil/tests/core/bootstrap.py
"""Test fixtures and mock infrastructure."""
import pytest
from unittest.mock import MagicMock


class Prophecy:
    """Simple mock framework inspired by Bonsai's pattern."""

    def __init__(self, interface_class):
        self.interface = interface_class
        self.mock = MagicMock()
        self.expectations = []

    def __getattr__(self, name):
        return ProphecyMethod(self, name)

    def verify(self):
        for expectation in self.expectations:
            expectation.verify()


class ProphecyMethod:
    def __init__(self, prophecy, name):
        self.prophecy = prophecy
        self.name = name
        self._should_call = False
        self._return_value = None

    def __call__(self, *args, **kwargs):
        return getattr(self.prophecy.mock, self.name)(*args, **kwargs)

    def should_be_called(self):
        self._should_call = True
        return self

    def will_return(self, value):
        self._return_value = value
        getattr(self.prophecy.mock, self.name).return_value = value
        return self


# Fixtures
@pytest.fixture
def ifc():
    from saikei_civil.core.tool import Ifc
    prophet = Prophecy(Ifc)
    yield prophet
    prophet.verify()


@pytest.fixture
def alignment():
    from saikei_civil.core.tool import Alignment
    prophet = Prophecy(Alignment)
    yield prophet
    prophet.verify()


@pytest.fixture
def blender():
    from saikei_civil.core.tool import Blender
    prophet = Prophecy(Blender)
    yield prophet
    prophet.verify()
```

### Step 6.2: Core Logic Tests (No Blender)

```python
# saikei_civil/tests/core/test_alignment.py
"""Tests for alignment core logic - runs without Blender."""
import pytest
from unittest.mock import MagicMock

import saikei_civil.core.alignment as subject


class TestCreateHorizontalAlignment:

    def test_creates_alignment_via_api(self, ifc, alignment, blender):
        # Setup
        mock_entity = MagicMock()
        mock_entity.id.return_value = 123

        ifc.mock.run.return_value = mock_entity
        blender.mock.create_object.return_value = MagicMock()

        pis = [
            {"x": 0.0, "y": 0.0, "radius": 0.0},
            {"x": 100.0, "y": 0.0, "radius": 0.0},
        ]

        # Execute
        result = subject.create_horizontal_alignment(
            ifc.mock, alignment.mock, blender.mock,
            name="Test Alignment",
            pis=pis
        )

        # Verify
        ifc.mock.run.assert_called_once()
        call_args = ifc.mock.run.call_args
        assert call_args[0][0] == "alignment.create_by_pi_method"
        assert call_args[1]["name"] == "Test Alignment"

    def test_requires_minimum_two_pis(self, ifc, alignment, blender):
        pis = [{"x": 0.0, "y": 0.0, "radius": 0.0}]

        with pytest.raises(ValueError, match="at least 2 PIs"):
            subject.create_horizontal_alignment(
                ifc.mock, alignment.mock, blender.mock,
                name="Test",
                pis=pis
            )

    def test_links_entity_to_object(self, ifc, alignment, blender):
        mock_entity = MagicMock()
        mock_entity.id.return_value = 123
        mock_obj = MagicMock()

        ifc.mock.run.return_value = mock_entity
        blender.mock.create_object.return_value = mock_obj

        pis = [
            {"x": 0.0, "y": 0.0},
            {"x": 100.0, "y": 0.0},
        ]

        subject.create_horizontal_alignment(
            ifc.mock, alignment.mock, blender.mock,
            name="Test",
            pis=pis
        )

        ifc.mock.link.assert_called_once_with(mock_entity, mock_obj)
```

### Step 6.3: Tool Tests (With Blender)

```python
# saikei_civil/tests/tool/test_alignment.py
"""Tests for alignment tool - requires Blender (pytest-blender)."""
import pytest
import bpy

from saikei_civil.tool import Alignment, Ifc


@pytest.fixture
def ifc_file():
    """Create a fresh IFC file for testing."""
    import ifcopenshell
    from saikei_civil.core.ifc_manager import NativeIfcManager

    NativeIfcManager.new_file()
    yield NativeIfcManager.get_file()
    NativeIfcManager.file = None


class TestAlignmentTool:

    def test_update_visualization_creates_curve(self, ifc_file):
        # Create a simple alignment
        alignment = Alignment.create(
            name="Test",
            pis=[
                {"x": 0.0, "y": 0.0, "radius": 0.0},
                {"x": 100.0, "y": 0.0, "radius": 0.0},
            ]
        )

        # Get linked object
        obj = Ifc.get_object(alignment)

        # Verify curve was created
        assert obj is not None
        assert obj.type == 'CURVE'
```

### Step 6.4: Test Directory Structure

```
saikei_civil/tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── core/                    # Core logic tests (NO Blender)
│   ├── __init__.py
│   ├── bootstrap.py         # Mock infrastructure
│   ├── test_alignment.py
│   ├── test_vertical_alignment.py
│   ├── test_georeferencing.py
│   └── test_cross_section.py
├── tool/                    # Tool tests (WITH Blender)
│   ├── __init__.py
│   ├── test_alignment.py
│   ├── test_ifc.py
│   └── test_blender.py
└── integration/             # Full integration tests
    ├── __init__.py
    └── test_full_workflow.py
```

### Deliverables for Phase 6:
- [ ] `tests/core/bootstrap.py` - Mock infrastructure
- [ ] `tests/core/test_*.py` - Core tests (no Blender)
- [ ] `tests/tool/test_*.py` - Tool tests (with Blender)
- [ ] `tests/conftest.py` - Shared fixtures
- [ ] pytest configuration for both test types
- [ ] CI configuration to run tests

---

## Phase 7: Bonsai Compatibility & Cleanup

**Goal:** Ensure seamless operation alongside Bonsai and clean up legacy code.

### Step 7.1: Namespace Audit

Ensure all identifiers use `SAIKEI_` prefix:

| Type | Pattern | Example |
|------|---------|---------|
| Operators | `SAIKEI_OT_*` | `SAIKEI_OT_create_alignment` |
| Panels | `SAIKEI_PT_*` | `SAIKEI_PT_alignment` |
| Properties | `SAIKEI_*` | `SAIKEI_alignment_properties` |
| bl_idname | `saikei.*` | `saikei.create_alignment` |

### Step 7.2: Remove BC_ Prefixes

Search and replace:
- `BC_OT_` → `SAIKEI_OT_`
- `BC_PT_` → `SAIKEI_PT_`
- `bc.` → `saikei.`
- `bc_alignment` → `saikei_alignment`

### Step 7.3: Panel Category

Verify all panels use:
```python
bl_category = "Saikei Civil"
```

### Step 7.4: Bonsai Integration Points

If Bonsai is installed:
1. Don't duplicate georeferencing UI (use Bonsai's)
2. Share the same IFC file when possible
3. Complement spatial structure, don't override

```python
# In tool/ifc.py, add Bonsai detection

@classmethod
def get(cls) -> ifcopenshell.file:
    """Get IFC file, preferring Bonsai's if available."""
    try:
        from bonsai.bim.ifc import IfcStore
        if IfcStore.get_file():
            return IfcStore.get_file()
    except ImportError:
        pass

    # Fall back to Saikei's own file
    from saikei_civil.core.ifc_manager import NativeIfcManager
    return NativeIfcManager.get_file()
```

### Step 7.5: Remove Deprecated Code

After migration is complete:
1. Remove backwards compatibility shims (`native_ifc_*.py`)
2. Remove old `operators/` directory (replaced by `bim/module/`)
3. Remove old `ui/` directory (replaced by `bim/module/`)
4. Update documentation

### Step 7.6: Documentation Update

Update CLAUDE.md and other docs to reflect:
- New three-layer architecture
- New directory structure
- New import paths
- Integration with Bonsai

### Deliverables for Phase 7:
- [ ] All BC_ prefixes replaced with SAIKEI_
- [ ] Bonsai detection and integration
- [ ] Deprecated code removed
- [ ] Documentation updated
- [ ] Final testing pass
- [ ] Release notes prepared

---

## Implementation Checklist

### Phase 1: Foundation
- [ ] Create `core/tool.py` with interfaces
- [ ] Create `tool/` directory
- [ ] Implement `tool/ifc.py`
- [ ] Implement `tool/blender.py`
- [ ] Create `tool/__init__.py`
- [ ] Verify existing code still works

### Phase 2: Alignment (Proof of Concept)
- [ ] Create `core/alignment.py` (pure logic)
- [ ] Create `tool/alignment.py` (Blender implementation)
- [ ] Create v2 operators using new pattern
- [ ] Write core tests (no Blender)
- [ ] Verify visualization works

### Phase 3: ifcopenshell.api
- [ ] Audit direct IFC usage
- [ ] Replace in NativeIfcAlignment
- [ ] Replace in NativeIfcManager
- [ ] Replace in georeferencing
- [ ] Verify external viewer compatibility

### Phase 4: Remaining Modules
- [ ] Vertical alignment migration
- [ ] Georeferencing migration
- [ ] Cross-section migration
- [ ] Corridor migration

### Phase 5: Directory Reorganization
- [ ] Create `bim/module/` structure
- [ ] Migrate operators
- [ ] Migrate properties
- [ ] Migrate panels
- [ ] Update registration

### Phase 6: Testing
- [ ] Create test bootstrap
- [ ] Core logic tests
- [ ] Tool tests
- [ ] Integration tests
- [ ] CI configuration

### Phase 7: Cleanup
- [ ] Rename BC_ → SAIKEI_
- [ ] Bonsai integration
- [ ] Remove deprecated code
- [ ] Update documentation

---

## Risk Mitigation

### Risk: Breaking Existing Functionality
**Mitigation:**
- Each phase maintains backwards compatibility
- Old and new code run in parallel during transition
- Comprehensive testing at each phase

### Risk: ifcopenshell.api Doesn't Support All Operations
**Mitigation:**
- Audit API coverage before starting Phase 3
- Create wrapper functions for unsupported operations
- Consider contributing missing functions upstream

### Risk: Complex Interdependencies
**Mitigation:**
- Detailed dependency mapping before migration
- Incremental migration (one module at a time)
- Continuous integration testing

---

## Success Criteria

1. **All existing functionality works** - No regressions
2. **Core logic testable without Blender** - Unit tests pass in CI
3. **Clean separation of concerns** - No Blender imports in `core/`
4. **ifcopenshell.api used throughout** - No direct entity creation
5. **Compatible with Bonsai** - Can run alongside Bonsai
6. **Consistent naming** - All SAIKEI_ prefixes
7. **Documentation updated** - CLAUDE.md reflects new architecture

---

*Migration Plan Version: 1.0*
*Created: December 2025*
*For: Saikei Civil - Cultivating Open Infrastructure*