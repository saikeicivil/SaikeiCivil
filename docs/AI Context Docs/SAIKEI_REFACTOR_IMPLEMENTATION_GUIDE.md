# Saikei Civil Refactor Implementation Guide

## Strategic Integration: IfcOpenShell Alignment API + Saikei Blender Frontend

**Version:** 1.0  
**Date:** January 12, 2026  
**Purpose:** Guide for Claude Code to create a refactor plan integrating the IfcOpenShell alignment API as Saikei's IFC backend

---

## 1. Executive Summary

### 1.1 Refactor Goal

Transform Saikei Civil from a monolithic IFC implementation to a layered architecture where:

- **Backend (IFC Operations):** The `ifcopenshell.api.alignment` module handles all IFC entity creation, relationship management, and geometric representation generation
- **Frontend (User Interface):** Saikei handles Blender UI, real-time visualization, constraint-based editing, and civil engineering design workflows
- **Business Logic:** Saikei retains design validation, AASHTO rules, and template management

### 1.2 Why This Refactor

IfcOpenShell alignment API (merged into IfcOpenShell v0.8.0, March 2025) provides:

- Automatic `IfcCompositeCurve` and `IfcGradientCurve` generation from semantic definitions
- Proper `IfcReferent` creation with `Pset_Stationing`
- Standards-compliant segment representations per IFC Concept Templates
- Active development on `IfcOpenCrossProfileDef` geometry (Issue #7338)

Saikei should leverage this rather than duplicate it.

---

## 2. Architecture Overview

### 2.1 Current Saikei Architecture (Before Refactor)

```
┌─────────────────────────────────────────────────────────┐
│                    SAIKEI CIVIL                          │
├─────────────────────────────────────────────────────────┤
│  Blender UI Layer                                        │
│    ├── Panels (alignment_panels.py)                      │
│    ├── Operators (alignment_operators.py)                │
│    └── Property Groups                                   │
├─────────────────────────────────────────────────────────┤
│  Business Logic Layer                                    │
│    ├── horizontal_alignment.py (PI math, tangent calc)   │
│    ├── vertical_alignment.py (PVI math, grades)          │
│    └── cross_sections.py (assembly definitions)          │
├─────────────────────────────────────────────────────────┤
│  IFC Layer (TO BE REPLACED)                              │
│    ├── Direct ifcopenshell entity creation               │
│    ├── Manual relationship building                      │
│    └── Custom geometric representation code              │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Target Architecture (After Refactor)

```
┌─────────────────────────────────────────────────────────┐
│                    SAIKEI CIVIL                          │
├─────────────────────────────────────────────────────────┤
│  Blender UI Layer (RETAIN)                               │
│    ├── Panels - alignment_panels.py                      │
│    ├── Operators - alignment_operators.py                │
│    ├── Property Groups - alignment_props.py              │
│    └── Visualizers - alignment_viz.py                    │
├─────────────────────────────────────────────────────────┤
│  Business Logic Layer (RETAIN + ENHANCE)                 │
│    ├── Design validation (AASHTO, sight distance)        │
│    ├── Template management (cross-section assemblies)    │
│    ├── Superelevation diagrams                           │
│    └── Quantity calculations                             │
├─────────────────────────────────────────────────────────┤
│  API Adapter Layer (NEW)                                 │
│    └── saikei_alignment_adapter.py                       │
│          ├── Translates Saikei data → the alignment API params  │
│          ├── Handles bidirectional sync                  │
│          └── Manages IFC file reference                  │
├─────────────────────────────────────────────────────────┤
│  IfcOpenShell Alignment API (EXTERNAL)                │
│    └── ifcopenshell.api.alignment                        │
│          ├── create_by_pi_method()                       │
│          ├── add_vertical_layout()                       │
│          ├── add_stationing_referent()                   │
│          └── create_representation()                     │
└─────────────────────────────────────────────────────────┘
```

---

## 3. IfcOpenShell Alignment API Reference

### 3.1 Key Functions to Use

These functions are available in `ifcopenshell.api.alignment` (v0.8.0+):

#### Creation Functions

| Function | Description | Saikei Use Case |
|----------|-------------|-----------------|
| `create()` | Creates alignment with horizontal layout, optional vertical/cant, automatic geometric representations | Primary alignment creation |
| `create_by_pi_method()` | Creates alignment using PI method for H+V simultaneously | **PRIMARY METHOD** - matches Saikei's PI/PVI workflow |
| `create_from_csv()` | Imports alignment from CSV | Future import feature |
| `create_representation()` | Creates geometric representation from semantic definition | Manual geometry refresh |

#### Layout Functions

| Function | Description | Saikei Use Case |
|----------|-------------|-----------------|
| `layout_horizontal_alignment_by_pi_method()` | Appends horizontal segments to existing IfcAlignmentHorizontal | Editing existing alignments |
| `layout_vertical_alignment_by_pi_method()` | Appends vertical segments to existing IfcAlignmentVertical | Editing existing profiles |
| `add_vertical_layout()` | Adds vertical layout per CT 4.1.4.4.1.2 | Multiple vertical profiles |
| `add_zero_length_segment()` | Adds mandatory zero-length terminator | Automatic (called by API) |

#### Getter Functions

| Function | Returns | Saikei Use Case |
|----------|---------|-----------------|
| `get_horizontal_layout()` | IfcAlignmentHorizontal | Reading back for visualization |
| `get_vertical_layout()` | IfcAlignmentVertical | Reading back for visualization |
| `get_layout_segments()` | Nested IfcAlignmentSegment entities | Iterating for display |
| `get_layout_curve()` | IfcCompositeCurve/IfcGradientCurve | 3D curve for Blender mesh |
| `get_basis_curve()` | Basis curve for vertical/cant | Vertical profile reference |

#### Stationing Functions

| Function | Description | Saikei Use Case |
|----------|-------------|-----------------|
| `add_stationing_referent()` | Creates IfcReferent with Pset_Stationing | Station markers |
| `register_referent_name_callback()` | Custom naming for PC/PT/PVI | Station labeling |
| `distance_along_from_station()` | Converts station to distance | Query operations |

### 3.2 API Call Pattern

```python
import ifcopenshell
import ifcopenshell.api.alignment as align_api

# Create IFC file (or use existing)
ifc_file = ifcopenshell.file(schema="IFC4X3_ADD2")

# Create alignment using PI method
alignment = align_api.create_by_pi_method(
    ifc_file,
    name="Main Alignment",
    hpoints=[(0, 0), (500, 0), (1000, 200), (1500, 200)],  # PI coordinates
    radii=[0, 300, 500, 0],  # Curve radii (0 = tangent point)
    vpoints=[(0, 100), (500, 105), (1000, 102)],  # PVI coordinates (station, elevation)
    lengths=[200, 300],  # Vertical curve lengths
    start_station=0.0
)

# Add stationing referents
align_api.add_stationing_referent(
    ifc_file,
    alignment=alignment,
    station=0.0,
    name="BEG"
)

# Get geometric representation for visualization
curve = align_api.get_layout_curve(alignment)
```

---

## 4. Refactor Tasks

### 4.1 Phase 1: Create API Adapter Layer

**File:** `saikei/core/alignment/saikei_alignment_adapter.py`

**Purpose:** Bridge between Saikei's internal data structures and the alignment API

```python
"""
Saikei Alignment Adapter

Bridges Saikei Civil's Blender-based alignment data structures 
to the IfcOpenShell alignment module's IfcOpenShell alignment API.

This adapter is the ONLY module that should import ifcopenshell.api.alignment.
All other Saikei modules interact with IFC through this adapter.
"""

import ifcopenshell
import ifcopenshell.api.alignment as align_api
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class SaikeiPI:
    """Saikei's internal PI representation"""
    x: float
    y: float
    radius: float
    name: Optional[str] = None


@dataclass  
class SaikeiPVI:
    """Saikei's internal PVI representation"""
    station: float
    elevation: float
    curve_length: float
    name: Optional[str] = None


class SaikeiAlignmentAdapter:
    """
    Adapter class that translates between Saikei's data model 
    and the IfcOpenShell alignment module's IfcOpenShell alignment API.
    """
    
    def __init__(self, ifc_file: ifcopenshell.file):
        """
        Initialize adapter with IFC file reference.
        
        Args:
            ifc_file: Active IfcOpenShell file object
        """
        self.ifc_file = ifc_file
        self._alignment_cache: Dict[str, Any] = {}
    
    def create_alignment_from_pis(
        self,
        name: str,
        pis: List[SaikeiPI],
        pvis: Optional[List[SaikeiPVI]] = None,
        start_station: float = 0.0
    ) -> Any:
        """
        Create IFC alignment from Saikei PI/PVI data.
        
        This is the PRIMARY method for creating alignments. It uses
        the alignment API's create_by_pi_method() which automatically generates:
        - IfcAlignmentHorizontal with segments
        - IfcAlignmentVertical with segments (if PVIs provided)
        - IfcCompositeCurve geometric representation
        - IfcGradientCurve (if vertical provided)
        
        Args:
            name: Alignment name
            pis: List of SaikeiPI objects from Blender UI
            pvis: Optional list of SaikeiPVI objects
            start_station: Starting station value
            
        Returns:
            IfcAlignment entity
        """
        # Convert Saikei PIs to the alignment API format
        hpoints = [(pi.x, pi.y) for pi in pis]
        radii = [pi.radius for pi in pis]
        
        # Build kwargs for API call
        kwargs = {
            "name": name,
            "hpoints": hpoints,
            "radii": radii,
            "start_station": start_station
        }
        
        # Add vertical if provided
        if pvis:
            kwargs["vpoints"] = [(pvi.station, pvi.elevation) for pvi in pvis]
            kwargs["lengths"] = [pvi.curve_length for pvi in pvis[1:-1]]  # Interior PVIs only
        
        # Call the alignment API
        alignment = align_api.create_by_pi_method(self.ifc_file, **kwargs)
        
        # Cache for later reference
        self._alignment_cache[name] = alignment
        
        return alignment
    
    def update_horizontal_alignment(
        self,
        alignment_name: str,
        pis: List[SaikeiPI]
    ) -> None:
        """
        Update existing horizontal alignment with new PI data.
        
        This clears existing segments and rebuilds from new PIs.
        """
        alignment = self._alignment_cache.get(alignment_name)
        if not alignment:
            raise ValueError(f"Alignment '{alignment_name}' not found in cache")
        
        # Get horizontal layout
        h_layout = align_api.get_horizontal_layout(alignment)
        
        # Clear existing segments (implementation depends on IfcOpenShell capabilities)
        # TODO: Check if the alignment API supports segment clearing or if we need to
        # recreate the entire alignment
        
        # Rebuild using PI method
        hpoints = [(pi.x, pi.y) for pi in pis]
        radii = [pi.radius for pi in pis]
        
        align_api.layout_horizontal_alignment_by_pi_method(
            self.ifc_file,
            horizontal_layout=h_layout,
            hpoints=hpoints,
            radii=radii
        )
        
        # Regenerate geometric representation
        align_api.create_representation(self.ifc_file, alignment=alignment)
    
    def add_stationing_referents(
        self,
        alignment_name: str,
        stations: List[Tuple[float, str]]
    ) -> List[Any]:
        """
        Add IfcReferent entities at specified stations.
        
        Args:
            alignment_name: Name of alignment to add referents to
            stations: List of (station, name) tuples
            
        Returns:
            List of created IfcReferent entities
        """
        alignment = self._alignment_cache.get(alignment_name)
        if not alignment:
            raise ValueError(f"Alignment '{alignment_name}' not found")
        
        referents = []
        for station, name in stations:
            ref = align_api.add_stationing_referent(
                self.ifc_file,
                alignment=alignment,
                station=station,
                name=name
            )
            referents.append(ref)
        
        return referents
    
    def get_alignment_curve_points(
        self,
        alignment_name: str,
        interval: float = 10.0
    ) -> List[Tuple[float, float, float]]:
        """
        Get 3D points along alignment curve for Blender visualization.
        
        This samples the IfcCompositeCurve/IfcGradientCurve at regular
        intervals to create a polyline for Blender display.
        
        Args:
            alignment_name: Name of alignment
            interval: Sampling interval in alignment units
            
        Returns:
            List of (x, y, z) tuples
        """
        alignment = self._alignment_cache.get(alignment_name)
        if not alignment:
            raise ValueError(f"Alignment '{alignment_name}' not found")
        
        # Get geometric curve from the alignment API
        curve = align_api.get_layout_curve(alignment)
        
        # Sample curve at intervals
        # TODO: Implement curve sampling - may need to use IfcOpenShell's
        # geometry processing capabilities or ifcopenshell.geom
        points = self._sample_curve(curve, interval)
        
        return points
    
    def _sample_curve(
        self,
        curve: Any,
        interval: float
    ) -> List[Tuple[float, float, float]]:
        """
        Sample an IFC curve at regular intervals.
        
        Implementation depends on curve type:
        - IfcCompositeCurve: Sample each segment
        - IfcGradientCurve: Sample with vertical interpolation
        """
        # TODO: Implement curve sampling
        # This may require ifcopenshell.geom or custom implementation
        raise NotImplementedError("Curve sampling not yet implemented")
    
    def get_alignment_from_ifc(
        self,
        alignment_entity: Any
    ) -> Tuple[List[SaikeiPI], List[SaikeiPVI]]:
        """
        Extract PI/PVI data from existing IFC alignment.
        
        Used for importing alignments from external IFC files.
        
        Returns:
            Tuple of (pis, pvis) in Saikei format
        """
        # Get horizontal segments
        h_layout = align_api.get_horizontal_layout(alignment_entity)
        h_segments = align_api.get_layout_segments(h_layout)
        
        # Convert to PIs (inverse of PI method)
        pis = self._segments_to_pis(h_segments)
        
        # Get vertical if present
        v_layout = align_api.get_vertical_layout(alignment_entity)
        pvis = []
        if v_layout:
            v_segments = align_api.get_layout_segments(v_layout)
            pvis = self._segments_to_pvis(v_segments)
        
        return pis, pvis
    
    def _segments_to_pis(self, segments: List[Any]) -> List[SaikeiPI]:
        """Convert IFC alignment segments back to PI representation."""
        # TODO: Implement reverse conversion
        # This requires understanding the segment types and extracting
        # the original PI coordinates
        raise NotImplementedError("Segment to PI conversion not yet implemented")
    
    def _segments_to_pvis(self, segments: List[Any]) -> List[SaikeiPVI]:
        """Convert IFC vertical segments back to PVI representation."""
        # TODO: Implement reverse conversion
        raise NotImplementedError("Segment to PVI conversion not yet implemented")
```

### 4.2 Phase 2: Refactor Blender Operators

**File:** `saikei/blender/operators/alignment_operators.py`

**Changes:** Replace direct IFC manipulation with adapter calls

```python
"""
Saikei Alignment Operators (Refactored)

Blender operators for alignment creation and editing.
All IFC operations go through SaikeiAlignmentAdapter.
"""

import bpy
from bpy.types import Operator
from ...core.alignment.saikei_alignment_adapter import (
    SaikeiAlignmentAdapter,
    SaikeiPI,
    SaikeiPVI
)


class SAIKEI_OT_create_alignment(Operator):
    """Create new IFC alignment from PI/PVI data"""
    bl_idname = "saikei.create_alignment"
    bl_label = "Create Alignment"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        saikei_props = scene.saikei_alignment
        
        # Get IFC file from Bonsai/BlenderBIM
        ifc_file = self._get_ifc_file(context)
        if not ifc_file:
            self.report({'ERROR'}, "No IFC file active. Create or open an IFC project first.")
            return {'CANCELLED'}
        
        # Initialize adapter
        adapter = SaikeiAlignmentAdapter(ifc_file)
        
        # Collect PI data from Blender UI
        pis = [
            SaikeiPI(
                x=pi.location_x,
                y=pi.location_y,
                radius=pi.radius,
                name=pi.name
            )
            for pi in saikei_props.horizontal_pis
        ]
        
        # Collect PVI data if vertical alignment exists
        pvis = None
        if saikei_props.has_vertical:
            pvis = [
                SaikeiPVI(
                    station=pvi.station,
                    elevation=pvi.elevation,
                    curve_length=pvi.curve_length,
                    name=pvi.name
                )
                for pvi in saikei_props.vertical_pvis
            ]
        
        # Create alignment through adapter (uses the alignment API)
        try:
            alignment = adapter.create_alignment_from_pis(
                name=saikei_props.alignment_name,
                pis=pis,
                pvis=pvis,
                start_station=saikei_props.start_station
            )
            
            # Update visualization
            self._update_visualization(context, adapter, saikei_props.alignment_name)
            
            self.report({'INFO'}, f"Created alignment: {saikei_props.alignment_name}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to create alignment: {str(e)}")
            return {'CANCELLED'}
    
    def _get_ifc_file(self, context):
        """Get active IFC file from Bonsai/BlenderBIM."""
        # Integration with Bonsai
        try:
            import blenderbim.tool as tool
            return tool.Ifc.get()
        except ImportError:
            return None
    
    def _update_visualization(self, context, adapter, alignment_name):
        """Update Blender viewport visualization."""
        # Get curve points from adapter
        try:
            points = adapter.get_alignment_curve_points(alignment_name, interval=5.0)
            
            # Create or update Blender curve object
            self._create_blender_curve(context, alignment_name, points)
            
        except NotImplementedError:
            # Fall back to segment-based visualization if curve sampling not available
            self._visualize_from_segments(context, alignment_name)
    
    def _create_blender_curve(self, context, name, points):
        """Create Blender curve from points."""
        # Implementation for Blender curve creation
        # This is Saikei's visualization layer - retained from current implementation
        pass
    
    def _visualize_from_segments(self, context, alignment_name):
        """Fallback visualization using segment endpoints."""
        # Implementation for segment-based visualization
        pass


class SAIKEI_OT_update_pi(Operator):
    """Update PI position and recalculate alignment"""
    bl_idname = "saikei.update_pi"
    bl_label = "Update PI"
    bl_options = {'REGISTER', 'UNDO'}
    
    pi_index: bpy.props.IntProperty()
    
    def execute(self, context):
        scene = context.scene
        saikei_props = scene.saikei_alignment
        
        # Get IFC file
        ifc_file = self._get_ifc_file(context)
        if not ifc_file:
            return {'CANCELLED'}
        
        # Initialize adapter
        adapter = SaikeiAlignmentAdapter(ifc_file)
        
        # Collect updated PI data
        pis = [
            SaikeiPI(
                x=pi.location_x,
                y=pi.location_y,
                radius=pi.radius,
                name=pi.name
            )
            for pi in saikei_props.horizontal_pis
        ]
        
        # Update through adapter
        try:
            adapter.update_horizontal_alignment(
                alignment_name=saikei_props.alignment_name,
                pis=pis
            )
            
            # Refresh visualization
            self._update_visualization(context, adapter, saikei_props.alignment_name)
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to update alignment: {str(e)}")
            return {'CANCELLED'}
    
    def _get_ifc_file(self, context):
        try:
            import blenderbim.tool as tool
            return tool.Ifc.get()
        except ImportError:
            return None
    
    def _update_visualization(self, context, adapter, alignment_name):
        # Reuse visualization code
        pass


class SAIKEI_OT_add_stationing(Operator):
    """Add station markers to alignment"""
    bl_idname = "saikei.add_stationing"
    bl_label = "Add Stationing"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        saikei_props = scene.saikei_alignment
        
        ifc_file = self._get_ifc_file(context)
        if not ifc_file:
            return {'CANCELLED'}
        
        adapter = SaikeiAlignmentAdapter(ifc_file)
        
        # Collect station data
        stations = [
            (marker.station, marker.name)
            for marker in saikei_props.station_markers
        ]
        
        try:
            adapter.add_stationing_referents(
                alignment_name=saikei_props.alignment_name,
                stations=stations
            )
            
            self.report({'INFO'}, f"Added {len(stations)} station markers")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to add stationing: {str(e)}")
            return {'CANCELLED'}
    
    def _get_ifc_file(self, context):
        try:
            import blenderbim.tool as tool
            return tool.Ifc.get()
        except ImportError:
            return None
```

### 4.3 Phase 3: Superelevation Integration

**File:** `saikei/core/alignment/superelevation_adapter.py`

**Purpose:** Extend adapter for superelevation control tied to cross-sections

```python
"""
Saikei Superelevation Adapter

Handles superelevation events and their connection to cross-section profiles.
This builds on the alignment API and the IfcOpenCrossProfileDef workflow.
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
import ifcopenshell
import ifcopenshell.api.alignment as align_api


@dataclass
class SuperelevationEvent:
    """Superelevation control point"""
    station: float
    e_left: float  # Superelevation rate for left side (positive = up)
    e_right: float  # Superelevation rate for right side
    pivot: str  # "CL", "EL", "ER" - centerline, edge left, edge right
    transition_type: str  # "LINEAR", "CLOTHOID", "BLOSS"


@dataclass
class OpenCrossProfile:
    """
    Represents an IfcOpenCrossProfileDef for a specific station.
    
    The Widths and Slopes arrays define the parametric cross-section
    that responds to superelevation changes.
    """
    station: float
    widths: List[float]  # Lateral widths of each segment
    slopes: List[float]  # Cross-slopes (ratios) of each segment
    tags: List[str]  # Labels for vertices: ["EPS_L", "EP_L", "CL", "EP_R", "EPS_R"]


class SuperelevationAdapter:
    """
    Manages superelevation events and their effect on cross-section profiles.
    
    Architecture:
    1. SuperelevationEvents define the superelevation diagram (design intent)
    2. OpenCrossProfiles are generated FROM the superelevation at each station
    3. IfcSectionedSurface uses the profiles for the parametric surface
    4. IfcSectionedSolidHorizontal is derived for pavement layer solids
    """
    
    def __init__(self, ifc_file: ifcopenshell.file, alignment_name: str):
        self.ifc_file = ifc_file
        self.alignment_name = alignment_name
        self._events: List[SuperelevationEvent] = []
        self._base_template: Optional[OpenCrossProfile] = None
    
    def set_base_template(self, template: OpenCrossProfile):
        """
        Set the base cross-section template (normal crown condition).
        
        This template defines the lane/shoulder configuration.
        Superelevation modifies the slopes while preserving widths.
        """
        self._base_template = template
    
    def add_superelevation_event(self, event: SuperelevationEvent):
        """Add a superelevation control point."""
        self._events.append(event)
        self._events.sort(key=lambda e: e.station)
    
    def get_profile_at_station(self, station: float) -> OpenCrossProfile:
        """
        Calculate the cross-section profile at a given station.
        
        This interpolates superelevation between events and applies
        it to the base template.
        """
        if not self._base_template:
            raise ValueError("Base template not set")
        
        # Find surrounding events
        before_event = None
        after_event = None
        
        for event in self._events:
            if event.station <= station:
                before_event = event
            if event.station > station and after_event is None:
                after_event = event
                break
        
        # Calculate interpolated superelevation
        if before_event is None:
            e_left = self._base_template.slopes[0]  # Normal crown
            e_right = self._base_template.slopes[-1]
        elif after_event is None:
            e_left = before_event.e_left
            e_right = before_event.e_right
        else:
            # Linear interpolation (can extend for other transition types)
            ratio = (station - before_event.station) / (after_event.station - before_event.station)
            e_left = before_event.e_left + ratio * (after_event.e_left - before_event.e_left)
            e_right = before_event.e_right + ratio * (after_event.e_right - before_event.e_right)
        
        # Apply superelevation to base template
        return self._apply_superelevation(station, e_left, e_right)
    
    def _apply_superelevation(
        self,
        station: float,
        e_left: float,
        e_right: float
    ) -> OpenCrossProfile:
        """
        Apply superelevation rates to base template.
        
        This modifies the slopes array based on which lanes are
        affected by the superelevation.
        """
        # Create modified slopes
        new_slopes = list(self._base_template.slopes)
        
        # Apply superelevation to travel lanes
        # Assumes template structure: [shoulder_l, lane_l, ..., lane_r, shoulder_r]
        # Implementation depends on specific template structure
        
        # Example for 2-lane road:
        # Base: [-0.02, -0.02, 0.02, 0.02, 0.04]
        # Full super (6% right): [0.06, 0.06, 0.06, 0.06, 0.08]
        
        # TODO: Implement actual slope modification based on pivot point
        # and superelevation values
        
        return OpenCrossProfile(
            station=station,
            widths=self._base_template.widths,
            slopes=new_slopes,
            tags=self._base_template.tags
        )
    
    def create_ifc_profiles(self, interval: float = 25.0) -> List[Tuple[float, any]]:
        """
        Generate IfcOpenCrossProfileDef entities at regular intervals.
        
        Args:
            interval: Station interval for profile generation
            
        Returns:
            List of (station, IfcOpenCrossProfileDef) tuples
        """
        # Get alignment length
        # TODO: Get from alignment adapter
        total_length = 1000.0  # Placeholder
        
        profiles = []
        station = 0.0
        
        while station <= total_length:
            profile = self.get_profile_at_station(station)
            
            # Create IFC entity
            ifc_profile = self.ifc_file.create_entity(
                "IfcOpenCrossProfileDef",
                ProfileType="CURVE",
                HorizontalWidths=True,
                Widths=profile.widths,
                Slopes=profile.slopes,
                Tags=profile.tags
            )
            
            profiles.append((station, ifc_profile))
            station += interval
        
        return profiles
    
    def create_sectioned_surface(self, profiles: List[Tuple[float, any]]) -> any:
        """
        Create IfcSectionedSurface from profiles.
        
        This is the parametric surface representation that responds
        to superelevation changes.
        """
        # Get alignment curve as directrix
        # TODO: Get from alignment adapter
        
        # Create IfcSectionedSurface
        # TODO: Implement when IfcOpenShell supports this
        # (relates to IfcOpenShell Issue #7338)
        
        raise NotImplementedError(
            "IfcSectionedSurface creation pending IfcOpenShell support. "
            "See GitHub Issue #7338."
        )
    
    def create_referent_events(self) -> List[any]:
        """
        Create IfcReferent entities for superelevation events.
        
        These are linked to profiles via IfcRelAssociatesProfileDef.
        """
        referents = []
        
        for event in self._events:
            # Create IfcReferent
            referent = self.ifc_file.create_entity(
                "IfcReferent",
                PredefinedType="SUPERELEVATIONEVENT"
            )
            
            # Add property set with superelevation values
            # TODO: Use ifcopenshell.api.pset functions
            
            referents.append(referent)
        
        return referents
```

### 4.4 Phase 4: Remove Deprecated Code

**Files to Remove/Deprecate:**

After the adapter layer is working, the following Saikei modules that directly manipulate IFC entities should be deprecated:

| Current File | Action | Replacement |
|-------------|--------|-------------|
| `saikei/ifc/alignment_entities.py` | **REMOVE** | `SaikeiAlignmentAdapter` |
| `saikei/ifc/segment_builders.py` | **REMOVE** | Alignment API handles segment creation |
| `saikei/ifc/curve_geometry.py` | **REMOVE** | `align_api.create_representation()` |
| `saikei/ifc/referent_builders.py` | **REMOVE** | `adapter.add_stationing_referents()` |

**Files to Retain (Saikei-specific functionality):**

| File | Purpose |
|------|---------|
| `saikei/core/alignment/pi_calculator.py` | **RETAIN** - PI intersection math for UI feedback |
| `saikei/core/alignment/pvi_calculator.py` | **RETAIN** - PVI grade calculations |
| `saikei/core/validation/aashto_rules.py` | **RETAIN** - Design validation |
| `saikei/blender/visualization/*` | **RETAIN** - All Blender visualization |
| `saikei/blender/panels/*` | **RETAIN** - All UI panels |
| `saikei/blender/operators/*` | **REFACTOR** - Use adapter instead of direct IFC |

---

## 5. Testing Strategy

### 5.1 Unit Tests for Adapter

```python
"""
Test cases for SaikeiAlignmentAdapter
"""

import pytest
import ifcopenshell
from saikei.core.alignment.saikei_alignment_adapter import (
    SaikeiAlignmentAdapter,
    SaikeiPI,
    SaikeiPVI
)


@pytest.fixture
def ifc_file():
    """Create fresh IFC file for each test."""
    return ifcopenshell.file(schema="IFC4X3_ADD2")


@pytest.fixture
def adapter(ifc_file):
    """Create adapter instance."""
    return SaikeiAlignmentAdapter(ifc_file)


class TestAlignmentCreation:
    """Test alignment creation through adapter."""
    
    def test_create_horizontal_only(self, adapter, ifc_file):
        """Test creating alignment with horizontal only."""
        pis = [
            SaikeiPI(x=0, y=0, radius=0),
            SaikeiPI(x=500, y=0, radius=300),
            SaikeiPI(x=1000, y=200, radius=0)
        ]
        
        alignment = adapter.create_alignment_from_pis(
            name="Test Alignment",
            pis=pis
        )
        
        # Verify IFC entities created
        assert alignment is not None
        assert alignment.is_a("IfcAlignment")
        
        # Verify horizontal layout exists
        h_alignments = ifc_file.by_type("IfcAlignmentHorizontal")
        assert len(h_alignments) == 1
        
        # Verify segments created
        segments = ifc_file.by_type("IfcAlignmentSegment")
        assert len(segments) >= 3  # At least start tangent, curve, end tangent
    
    def test_create_with_vertical(self, adapter, ifc_file):
        """Test creating alignment with horizontal and vertical."""
        pis = [
            SaikeiPI(x=0, y=0, radius=0),
            SaikeiPI(x=1000, y=0, radius=0)
        ]
        
        pvis = [
            SaikeiPVI(station=0, elevation=100, curve_length=0),
            SaikeiPVI(station=500, elevation=110, curve_length=200),
            SaikeiPVI(station=1000, elevation=105, curve_length=0)
        ]
        
        alignment = adapter.create_alignment_from_pis(
            name="Test Alignment",
            pis=pis,
            pvis=pvis
        )
        
        # Verify vertical layout exists
        v_alignments = ifc_file.by_type("IfcAlignmentVertical")
        assert len(v_alignments) == 1
        
        # Verify gradient curve exists
        gradient_curves = ifc_file.by_type("IfcGradientCurve")
        assert len(gradient_curves) == 1


class TestStationingReferents:
    """Test stationing referent creation."""
    
    def test_add_referents(self, adapter, ifc_file):
        """Test adding station markers."""
        # First create alignment
        pis = [
            SaikeiPI(x=0, y=0, radius=0),
            SaikeiPI(x=1000, y=0, radius=0)
        ]
        adapter.create_alignment_from_pis(name="Test", pis=pis)
        
        # Add referents
        stations = [
            (0.0, "BEG"),
            (500.0, "STA 5+00"),
            (1000.0, "END")
        ]
        
        referents = adapter.add_stationing_referents("Test", stations)
        
        assert len(referents) == 3
        
        # Verify IfcReferent entities
        ifc_referents = ifc_file.by_type("IfcReferent")
        assert len(ifc_referents) >= 3


class TestVisualizationData:
    """Test data extraction for Blender visualization."""
    
    @pytest.mark.skip(reason="Curve sampling not yet implemented")
    def test_get_curve_points(self, adapter):
        """Test extracting points for Blender curve."""
        pis = [
            SaikeiPI(x=0, y=0, radius=0),
            SaikeiPI(x=500, y=0, radius=300),
            SaikeiPI(x=1000, y=200, radius=0)
        ]
        adapter.create_alignment_from_pis(name="Test", pis=pis)
        
        points = adapter.get_alignment_curve_points("Test", interval=10.0)
        
        assert len(points) > 0
        assert all(len(p) == 3 for p in points)  # x, y, z tuples
```

### 5.2 Integration Tests

```python
"""
Integration tests verifying Blender operator → Adapter → IFC flow
"""

import bpy
import pytest


class TestBlenderIntegration:
    """Test full Blender workflow."""
    
    @pytest.fixture(autouse=True)
    def setup_scene(self):
        """Reset Blender scene before each test."""
        bpy.ops.wm.read_homefile(use_empty=True)
        yield
        bpy.ops.wm.read_homefile(use_empty=True)
    
    def test_create_alignment_operator(self):
        """Test SAIKEI_OT_create_alignment operator."""
        # Setup PI data in scene properties
        scene = bpy.context.scene
        # ... setup code ...
        
        # Execute operator
        result = bpy.ops.saikei.create_alignment()
        
        assert result == {'FINISHED'}
        
        # Verify Blender objects created
        # ... verification code ...
    
    def test_update_pi_regenerates_alignment(self):
        """Test that PI updates trigger alignment regeneration."""
        # Create initial alignment
        # Modify PI
        # Verify IFC updated
        pass
```

---

## 6. Migration Checklist

### 6.1 Pre-Migration

- [ ] Verify IfcOpenShell v0.8.0+ installed with alignment API
- [ ] Review the alignment API documentation and test notebooks
- [ ] Backup current Saikei codebase
- [ ] Create feature branch for refactor

### 6.2 Phase 1: Adapter Layer (Week 1-2)

- [ ] Create `saikei_alignment_adapter.py` with basic structure
- [ ] Implement `create_alignment_from_pis()` using the alignment API
- [ ] Implement `add_stationing_referents()`
- [ ] Write unit tests for adapter
- [ ] Verify IFC output matches current Saikei output

### 6.3 Phase 2: Operator Refactor (Week 2-3)

- [ ] Refactor `SAIKEI_OT_create_alignment` to use adapter
- [ ] Refactor `SAIKEI_OT_update_pi` to use adapter
- [ ] Refactor `SAIKEI_OT_add_stationing` to use adapter
- [ ] Update visualization code to work with adapter
- [ ] Run Blender integration tests

### 6.4 Phase 3: Superelevation (Week 3-4)

- [ ] Create `superelevation_adapter.py`
- [ ] Implement superelevation event management
- [ ] Implement profile generation at stations
- [ ] Coordinate with the IfcOpenShell team on IfcOpenCrossProfileDef support
- [ ] Create UI for superelevation diagram

### 6.5 Phase 4: Cleanup (Week 4-5)

- [ ] Remove deprecated IFC manipulation code
- [ ] Update documentation
- [ ] Performance testing
- [ ] User acceptance testing
- [ ] Merge to main branch

### 6.6 Post-Migration

- [ ] Monitor for issues
- [ ] Gather user feedback
- [ ] Plan collaboration with the IfcOpenShell team on shared gaps
- [ ] Document lessons learned

---

## 7. Collaboration Notes

### 7.1 Coordination with IfcOpenShell Community

**Recommended Communication:**

1. Share this implementation guide demonstrating integration approach
2. Offer to help test IfcOpenCrossProfileDef implementation (Issue #7338)
3. Propose regular sync calls during development
4. Coordinate on shared gap: transition spirals

**GitHub Issues to Follow:**

- `IfcOpenShell/IfcOpenShell#7338` - IfcOpenCrossProfileDef geometry support
- Any new issues related to alignment API

### 7.2 buildingSMART Alignment

Both projects should coordinate on buildingSMART community engagement:

- Joint testing against IFC validation checker
- Shared test cases for IFC 4.3 compliance
- Potential joint presentation to Infrastructure Room

---

## 8. Appendix: Alignment API Parameter Reference

### 8.1 create_by_pi_method() Parameters

```python
ifcopenshell.api.alignment.create_by_pi_method(
    ifc_file,                    # IfcOpenShell file object
    name: str,                   # Alignment name
    hpoints: List[Tuple],        # [(x1,y1), (x2,y2), ...] PI coordinates
    radii: List[float],          # Curve radii at each PI (0 = tangent point)
    vpoints: List[Tuple] = None, # [(sta1,elev1), ...] PVI coordinates
    lengths: List[float] = None, # Vertical curve lengths (interior PVIs only)
    start_station: float = 0.0,  # Starting station
    # Additional optional parameters TBD
)
```

### 8.2 Returned Entity Structure

```
IfcAlignment
├── IfcAlignmentHorizontal (nested via IfcRelNests)
│   └── IfcAlignmentSegment[] (nested via IfcRelNests)
│       └── DesignParameters: IfcAlignmentHorizontalSegment
├── IfcAlignmentVertical (nested via IfcRelNests, if vpoints provided)
│   └── IfcAlignmentSegment[] (nested via IfcRelNests)
│       └── DesignParameters: IfcAlignmentVerticalSegment
└── Representation: IfcProductDefinitionShape
    └── IfcShapeRepresentation
        └── Items: IfcCompositeCurve or IfcGradientCurve
```

---

*End of Implementation Guide*
