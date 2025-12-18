# BSI IFC Validation Fix Summary

**Date:** December 2025
**Status:** All BSI normative rule fixes implemented and tested successfully
**Result:** Full workflow (IFC creation → alignment → corridor generation) now working

---

## Overview

This document summarizes the BSI normative IFC validation rule fixes implemented in Saikei Civil. Use this to continue validation testing in a new chat session.

---

## BSI Normative Rules Fixed

### 1. ALB004 - Alignment Aggregation
**Rule:** Alignments should use IfcRelAggregates, not spatial containment
**File:** `core/ifc_api.py`
**Fix:** Use `IfcRelAggregates` to nest alignment under IfcRoad instead of `IfcRelContainedInSpatialStructure`

### 2. ALB015 - Zero-Length Final Segment (Business Logic)
**Rule:** Each alignment layout must end with a zero-length segment
**Files:**
- `core/horizontal_alignment/manager.py` (lines 494-605)
- `core/vertical_alignment/manager.py` (lines 758-785)
**Fix:** Added `_add_zero_length_final_segment()` method that creates:
- IfcAlignmentSegment with Name="Endpoint", ObjectType="ENDPOINT"
- IfcAlignmentHorizontalSegment/IfcAlignmentVerticalSegment with SegmentLength=0

### 3. ALS015 - Zero-Length DISCONTINUOUS Final Curve Segment (Geometry)
**Rule:** Alignment geometry must end with DISCONTINUOUS zero-length IfcCurveSegment
**Files:**
- `core/horizontal_alignment/manager.py` (lines 570-605)
- `core/vertical_alignment/manager.py` (lines 801-845)
**Fix:** After all curve segments, append:
```python
final_curve_seg = ifc.create_entity(
    "IfcCurveSegment",
    Transition="DISCONTINUOUS",
    Placement=placement,
    SegmentStart=ifc.create_entity("IfcLengthMeasure", 0.0),
    SegmentLength=ifc.create_entity("IfcLengthMeasure", 0.0),
    ParentCurve=parent_line
)
```

### 4. ALS012 - SegmentStart/Length Must Use IfcLengthMeasure
**Rule:** IfcCurveSegment.SegmentStart and SegmentLength must be wrapped entity instances (IfcCurveMeasureSelect)
**File:** `core/ifc_geometry_builders.py` (lines 386-398)
**Fix:**
```python
segment_start_val = ifc_file.create_entity("IfcLengthMeasure", float(segment_start))
segment_length_val = ifc_file.create_entity("IfcLengthMeasure", float(segment_length))
```
**Note:** IFC4X3_ADD2 requires wrapped entities, NOT raw floats. Using raw floats causes: `TypeError: attribute 'SegmentStart' expecting 'ENTITY INSTANCE', got 'float'`

### 5. PSE001 - Pset_Stationing Property Names
**Rule:** Use correct property names per IFC 4.3 spec
**File:** `core/horizontal_alignment/stationing.py`
**Fix:** Property names corrected to match IFC standard:
- `Station` (was correct)
- `IncomingStation` (was correct)
- `HasIncreasingStation` (added)

### 6. SPS007 - IfcAlignmentSegment Not in Spatial Containment
**Rule:** IfcAlignmentSegment entities must NOT be added to IfcRelContainedInSpatialStructure
**File:** `core/ifc_api.py`
**Fix:** Added safeguard in `contain_in_spatial()` to skip IfcAlignmentSegment entities

### 7. IFC105 - Orphaned Resource Entities
**Rule:** Resource entities should not be orphaned in the IFC file
**File:** `core/ifc_api.py`
**Fix:** Added cleanup functions:
- `cleanup_misplaced_alignment_segments()`
- `cleanup_orphaned_resources()`

### 8. OJT001 - ObjectType Required on IfcAlignmentSegment
**Rule:** IfcAlignmentSegment.ObjectType must have a value
**Files:**
- `core/horizontal_alignment/segment_builder.py` (line 111)
- `core/vertical_alignment/manager.py` (line 753)
**Fix:** Set `ObjectType` to segment type (e.g., "LINE", "CIRCULARARC", "CONSTANTGRADIENT", "ENDPOINT")

---

## Critical Bug Fix: Tangent Visualization

### Problem
After implementing ALB015/ALS015 (zero-length final segments), the PI operators tried to visualize `segments[-1]` which was now the Endpoint, not the actual tangent.

### Root Cause
1. `segments[-1]` returns the zero-length Endpoint segment
2. PI operators were calling `create_segment_curve(segments[-1])`
3. This created invisible/broken visualization

### Solution
**Files Modified:**
- `operators/pi_operators.py` (lines 203-209, 369-376)
- `tool/alignment_visualizer.py` (multiple locations)
- `core/alignment_registry.py` (lines 144-197)

**Fixes:**
1. Changed PI operators to use `segments[-2]` for the actual tangent
2. Added zero-length segment filtering in visualizer:
   ```python
   visual_segments = [
       s for s in self.alignment.segments
       if s.DesignParameters and s.DesignParameters.SegmentLength > 0
   ]
   ```
3. Fixed `reconstruct_alignment_from_ifc()` to initialize all required attributes:
   - `curve_segments = []`
   - `auto_update = True`
   - `stationing = StationingManager(...)`

---

## Key Technical Details

### IFC4X3_ADD2 IfcCurveMeasureSelect
The `IfcCurveMeasureSelect` type requires wrapped entity instances:
- `IfcLengthMeasure` - for length-based parameters (alignment segments)
- `IfcParameterValue` - for parametric curves (NURBS, etc.)

**Correct:**
```python
ifc.create_entity("IfcLengthMeasure", 100.0)  # Returns entity instance
```

**Wrong:**
```python
100.0  # Raw float - causes TypeError in IFC4X3_ADD2
```

### Three-Layer Architecture
- **Layer 1 (Core):** IFC operations, business logic - `core/`
- **Layer 2 (Tool):** Blender-specific code - `tool/`
- **Layer 3 (Operators):** User-facing operators - `operators/`

### Alignment Segment Structure After Fixes
For an alignment with 3 PIs (2 tangents):
```
segments = [
    Tangent_0 (IfcAlignmentSegment, LINE),
    Tangent_1 (IfcAlignmentSegment, LINE),
    Endpoint  (IfcAlignmentSegment, ENDPOINT, SegmentLength=0)
]
```

---

## Files Modified (Complete List)

| File | Changes |
|------|---------|
| `core/ifc_geometry_builders.py` | IfcLengthMeasure wrapping for SegmentStart/Length |
| `core/horizontal_alignment/manager.py` | Zero-length final segment (ALB015/ALS015) |
| `core/horizontal_alignment/segment_builder.py` | ObjectType on segments (OJT001) |
| `core/horizontal_alignment/stationing.py` | Pset_Stationing property names (PSE001) |
| `core/vertical_alignment/manager.py` | Zero-length final segment, ObjectType |
| `core/vertical_alignment/segments.py` | Segment export fixes |
| `core/ifc_api.py` | Cleanup functions, spatial containment safeguard |
| `core/alignment_registry.py` | Full attribute initialization in reconstruct |
| `operators/pi_operators.py` | Get correct tangent segment (not Endpoint) |
| `tool/alignment_visualizer.py` | Filter zero-length segments from visualization |

---

## Testing Status

| Test | Status |
|------|--------|
| Create new IFC file | ✅ Pass |
| Create alignment | ✅ Pass |
| Add PIs interactively | ✅ Pass |
| Tangent visualization | ✅ Pass |
| Add curves at PIs | ✅ Pass |
| Create vertical alignment | ✅ Pass |
| Create cross-sections | ✅ Pass |
| Generate corridor | ✅ Pass |
| Save IFC file | ✅ Pass |

---

## Next Steps for Validation

1. **Run BSI validation tool** on generated IFC files
2. **Test edge cases:**
   - Single PI alignment
   - Alignment with only curves (no tangents)
   - Very short segments
3. **Verify IFC interoperability:**
   - Open in Solibri
   - Open in FreeCAD
   - Open in BlenderBIM/Bonsai
4. **Check corridor IFC output:**
   - IfcSectionedSolidHorizontal validation
   - Cross-section profile validation

---

## Quick Reference: Running Validation

```python
# In Blender Python console
from saikei_civil.core.ifc_api import (
    cleanup_misplaced_alignment_segments,
    cleanup_orphaned_resources
)

# Run cleanup before saving
cleanup_misplaced_alignment_segments()
cleanup_orphaned_resources()
```

---

*Last Updated: December 2025*
