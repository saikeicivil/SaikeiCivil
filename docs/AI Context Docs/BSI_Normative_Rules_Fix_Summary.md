# buildingSMART Normative IFC Rules Fix Summary

**File Analyzed:** BSI_Val_edits.ifc  
**Validation Report Date:** 2025-12-15 19:39:13  
**IFC Schema:** IFC4X3_ADD2  
**MVD:** CoordinationView  
**Target Repository:** `C:\Users\amish\OneDrive\OneDrive Documents\GitHub\BlenderCivil\blendercivil`

---

## Executive Summary

After fixing the schema errors (GlobalId, EndGradient, etc.), the **Normative IFC Rules** validation identified **8 rule violations** across **12 instances**. These are higher-level semantic rules that ensure IFC files follow buildingSMART best practices for alignment modeling.

| Rule | Description | Count | Severity |
|------|-------------|-------|----------|
| ALB004 | Alignment not aggregated to Project | 1 | 🔴 ERROR |
| ALB015 | Missing zero-length final segment (business logic) | 2 | 🔴 ERROR |
| ALS012 | Wrong attribute types for segment start/length | 1 | 🔴 ERROR |
| ALS015 | Missing zero-length final segment (geometry) | 2 | 🔴 ERROR |
| IFC105 | Orphaned resource entity | 1 | 🔴 ERROR |
| OJT001 | Empty ObjectType attribute | 1 | 🔴 ERROR |
| PSE001 | Invalid Pset_Stationing properties | 3 | 🔴 ERROR |
| SPS007 | Invalid spatial containment | 1 | 🔴 ERROR |

---

## Issue 1: ALB004 - Alignment Not Aggregated to Project

**Severity:** 🔴 ERROR  
**Count:** 1 instance  
**IFC Entity ID:** #36 (IfcAlignment)

### Problem
The IfcAlignment is contained in spatial structure via `IfcRelContainedInSpatialStructure`, but it must ALSO be aggregated to IfcProject (directly or indirectly) via `IfcRelAggregates`.

### Rule Reference
> "Each IfcAlignment must be related to IfcProject using the IfcRelAggregates relationship - either directly or indirectly."

https://buildingsmart.github.io/ifc-gherkin-rules/branches/main/features/ALB004_Alignment-in-spatial-structure-relationships.html

### Current Hierarchy (Incorrect)
```
IfcProject
└── IfcSite (via IfcRelAggregates)
    └── IfcRoad (via IfcRelAggregates)
        └── IfcAlignment (via IfcRelContainedInSpatialStructure) ❌
```

### Required Hierarchy (Correct)
```
IfcProject
└── IfcSite (via IfcRelAggregates)
    └── IfcRoad (via IfcRelAggregates)
        └── IfcAlignment (via IfcRelAggregates) ✅
            └── Also: IfcRelContainedInSpatialStructure to IfcRoad (optional)
```

### Fix Required
Change how IfcAlignment is related to IfcRoad:

```python
# WRONG - Using containment only
ifc_file.create_entity(
    "IfcRelContainedInSpatialStructure",
    GlobalId=ifcopenshell.guid.new(),
    RelatingStructure=road,
    RelatedElements=[alignment]
)

# CORRECT - Use aggregation (alignment is part of road hierarchy)
ifc_file.create_entity(
    "IfcRelAggregates",
    GlobalId=ifcopenshell.guid.new(),
    Name="Road to Alignment",
    RelatingObject=road,
    RelatedObjects=[alignment]
)
```

### Files to Modify
- `core/ifc_manager/manager.py` (52KB) - Look for alignment spatial structure setup
- `core/horizontal_alignment/manager.py` (18KB) - `HorizontalAlignmentManager` may create this relationship

---

## Issue 2: ALB015 - Missing Zero-Length Final Segment (Business Logic)

**Severity:** 🔴 ERROR  
**Count:** 2 instances  
**IFC Entity IDs:** 
- #11293 (IfcAlignmentVertical) - Last segment length is 5, should be 0
- #43 (IfcAlignmentHorizontal) - Last segment length is 76.04, should be 0

### Problem
Per IFC 4.3 specification, **each alignment layout must end with a zero-length segment**. This segment marks the endpoint and provides end-of-alignment data (like final gradient for vertical).

### Rule Reference
> "Each layout (horizontal, vertical, cant) of the alignment business logic ends with a segment of length = 0."

https://buildingsmart.github.io/ifc-gherkin-rules/branches/main/features/ALB015_Alignment-business-logic-zero-length-final-segment.html

### IFC Specification Context
From the project knowledge (1_Introduction.md):
> "An interesting caveat of IfcAlignmentHorizontal and IfcAlignmentVertical is that the last IfcAlignmentSegment.DesignParameters must be zero length."

### Fix Required
After creating all alignment segments, add a final zero-length segment:

```python
def finalize_alignment_layout(ifc_file, alignment_layout, segments, layout_type="horizontal"):
    """
    Add zero-length final segment to alignment layout.
    
    Args:
        alignment_layout: IfcAlignmentHorizontal or IfcAlignmentVertical
        segments: List of existing segments
        layout_type: "horizontal" or "vertical"
    """
    # Get end point data from last real segment
    last_segment = segments[-1]
    
    if layout_type == "horizontal":
        # Create zero-length horizontal segment at endpoint
        end_segment_params = ifc_file.create_entity(
            "IfcAlignmentHorizontalSegment",
            StartPoint=last_segment.EndPoint,  # Start at previous endpoint
            StartDirection=last_segment.EndDirection,
            StartRadiusOfCurvature=0.0,
            EndRadiusOfCurvature=0.0,
            SegmentLength=0.0,  # ✅ ZERO LENGTH
            PredefinedType="LINE"
        )
    elif layout_type == "vertical":
        # Create zero-length vertical segment at endpoint
        last_params = last_segment.DesignParameters
        end_dist = last_params.StartDistAlong + last_params.HorizontalLength
        end_height = calculate_end_height(last_params)
        end_gradient = last_params.EndGradient
        
        end_segment_params = ifc_file.create_entity(
            "IfcAlignmentVerticalSegment",
            StartDistAlong=end_dist,
            HorizontalLength=0.0,  # ✅ ZERO LENGTH
            StartHeight=end_height,
            StartGradient=end_gradient,
            EndGradient=end_gradient,
            RadiusOfCurvature=None,
            PredefinedType="CONSTANTGRADIENT"
        )
    
    # Wrap in IfcAlignmentSegment
    final_segment = ifc_file.create_entity(
        "IfcAlignmentSegment",
        GlobalId=ifcopenshell.guid.new(),
        Name="End Segment",
        ObjectType="ENDPOINT",  # Descriptive type
        DesignParameters=end_segment_params
    )
    
    # Add to existing RelNests relationship
    # (or create new one including final segment)
    return final_segment
```

### Files to Modify
- `core/horizontal_alignment/manager.py` (18KB) - Add zero-length final segment for horizontal
- `core/vertical_alignment/manager.py` (35KB) - Add zero-length final segment for vertical
- `core/vertical_alignment/segments.py` (20KB) - May need helper for endpoint calculation

---

## Issue 3: ALS012 - Wrong Attribute Types for SegmentStart/Length

**Severity:** 🔴 ERROR  
**Count:** 1 instance  
**IFC Entity ID:** #36 (IfcAlignment)

### Problem
The geometric representation curve segments use `IfcParameterValue` for SegmentStart and SegmentLength, but they should use `IfcLengthMeasure`.

### Rule Reference
> "An alignment segment uses the correct IfcLengthMeasure type for attributes SegmentStart and SegmentLength."

https://buildingsmart.github.io/ifc-gherkin-rules/branches/main/features/ALS012_Alignment-segment-start-and-length-attribute-types.html

### Fix Required
When creating `IfcCurveSegment` entities for alignment geometry:

```python
# WRONG - Using IfcParameterValue
curve_segment = ifc_file.create_entity(
    "IfcCurveSegment",
    Transition="CONTINUOUS",
    Placement=placement,
    SegmentStart=ifc_file.create_entity("IfcParameterValue", 0.0),  # ❌
    SegmentLength=ifc_file.create_entity("IfcParameterValue", length),  # ❌
    ParentCurve=parent_curve
)

# CORRECT - Using IfcLengthMeasure (or raw float which defaults to length)
curve_segment = ifc_file.create_entity(
    "IfcCurveSegment",
    Transition="CONTINUOUS",
    Placement=placement,
    SegmentStart=ifc_file.create_entity("IfcLengthMeasure", 0.0),  # ✅
    SegmentLength=ifc_file.create_entity("IfcLengthMeasure", length),  # ✅
    ParentCurve=parent_curve
)

# OR simply use float values (IfcOpenShell may handle typing)
curve_segment = ifc_file.create_entity(
    "IfcCurveSegment",
    Transition="CONTINUOUS",
    Placement=placement,
    SegmentStart=0.0,  # Let IfcOpenShell infer IfcLengthMeasure
    SegmentLength=float(length),
    ParentCurve=parent_curve
)
```

### Files to Modify
- `core/horizontal_alignment/manager.py` - Look for IfcCurveSegment creation
- `core/horizontal_alignment/segment_builder.py` - May create curve segments here

---

## Issue 4: ALS015 - Missing Zero-Length Final Segment (Geometry)

**Severity:** 🔴 ERROR  
**Count:** 2 instances  
**IFC Entity ID:** #36 (IfcAlignment)
- Expected: DISCONTINUOUS transition, Observed: CONTINUOUS
- Expected: Length 0, Observed: 5.08

### Problem
The alignment geometry curve (IfcCompositeCurve or IfcGradientCurve) must end with a **discontinuous segment of zero length**. This mirrors the business logic requirement but applies to the geometric representation.

### Rule Reference
> "The alignment geometry (representation) curve ends with a discontinuous segment with length = 0."

https://buildingsmart.github.io/ifc-gherkin-rules/branches/main/features/ALS015_Alignment-representation-zero-length-final-segment.html

### Fix Required
Add zero-length final curve segment with DISCONTINUOUS transition:

```python
def create_final_curve_segment(ifc_file, end_point, end_direction):
    """
    Create zero-length discontinuous final segment for alignment geometry.
    """
    # Create a zero-length line as parent curve
    parent_curve = ifc_file.create_entity(
        "IfcLine",
        Pnt=end_point,
        Dir=ifc_file.create_entity("IfcVector", Orientation=end_direction, Magnitude=1.0)
    )
    
    # Create placement at endpoint
    placement = ifc_file.create_entity(
        "IfcAxis2Placement2D",  # or 3D depending on context
        Location=end_point
    )
    
    # Create zero-length DISCONTINUOUS segment
    final_segment = ifc_file.create_entity(
        "IfcCurveSegment",
        Transition="DISCONTINUOUS",  # ✅ Must be DISCONTINUOUS
        Placement=placement,
        SegmentStart=0.0,
        SegmentLength=0.0,  # ✅ Must be ZERO
        ParentCurve=parent_curve
    )
    
    return final_segment

# When building IfcCompositeCurve:
all_segments = [...existing_segments..., create_final_curve_segment(...)]
composite_curve = ifc_file.create_entity(
    "IfcCompositeCurve",
    Segments=all_segments,
    SelfIntersect=False
)
```

### Files to Modify
- `core/horizontal_alignment/manager.py` - Add final segment to IfcCompositeCurve
- `core/vertical_alignment/manager.py` - Add final segment to IfcGradientCurve (if creating geometry)

---

## Issue 5: IFC105 - Orphaned Resource Entity

**Severity:** 🔴 ERROR  
**Count:** 1 instance  
**IFC Entity ID:** #6085 (IfcCartesianPoint)

### Problem
An `IfcCartesianPoint` exists in the file but is not referenced by any rooted entity. Resource entities must be connected to the entity graph.

### Rule Reference
> "Resource entities are directly or indirectly related to at least one rooted entity instance."

https://buildingsmart.github.io/ifc-gherkin-rules/branches/main/features/IFC105_Resource-entities-need-to-be-referenced-by-rooted-entity.html

### Fix Required
This is likely a cleanup issue - a point was created but never used. Options:

1. **Don't create unused entities** - Review code to avoid creating orphaned geometry
2. **Clean up before export** - Remove unreferenced resource entities

```python
def cleanup_orphaned_resources(ifc_file):
    """
    Remove resource entities that aren't referenced by any rooted entity.
    Call this before writing the IFC file.
    """
    # Get all rooted entities
    rooted = set()
    for entity in ifc_file.by_type("IfcRoot"):
        rooted.add(entity.id())
    
    # Find referenced resources (simplified - real impl needs graph traversal)
    referenced = set()
    for entity in ifc_file:
        for attr in entity:
            if hasattr(attr, 'id'):
                referenced.add(attr.id())
    
    # Remove orphaned resources
    for entity in ifc_file.by_type("IfcCartesianPoint"):
        if entity.id() not in referenced:
            ifc_file.remove(entity)
```

**Better approach:** Find where #6085 is created and ensure it's used or not created.

### Files to Modify
- Search for where IfcCartesianPoint entities are created without being used
- Possibly `core/horizontal_alignment/curve_geometry.py` or similar

---

## Issue 6: OJT001 - Empty ObjectType Attribute

**Severity:** 🔴 ERROR  
**Count:** 1 instance  
**IFC Entity ID:** #11904 (IfcAlignmentSegment)

### Problem
When `PredefinedType` is set to `USERDEFINED`, the `ObjectType` attribute **must have a value** (cannot be null/empty).

### Rule Reference
> "The value of attribute .ObjectType. must be ^not empty^"

https://buildingsmart.github.io/ifc-gherkin-rules/branches/main/features/OJT001_Object-predefined-type.html

### Fix Required
Either:
1. **Set ObjectType** when using USERDEFINED
2. **Use a standard PredefinedType** instead of USERDEFINED

```python
# Option 1: Provide ObjectType for USERDEFINED
segment = ifc_file.create_entity(
    "IfcAlignmentSegment",
    GlobalId=ifcopenshell.guid.new(),
    Name="Segment 1",
    ObjectType="CustomSegmentType",  # ✅ Required when PredefinedType is USERDEFINED
    DesignParameters=params
)

# Option 2: Use standard type (no ObjectType needed)
# Note: IfcAlignmentSegment doesn't have PredefinedType directly,
# it's on the DesignParameters (IfcAlignmentHorizontalSegment, etc.)
```

### Files to Modify
- `core/vertical_alignment/segments.py` - Check IfcAlignmentSegment creation
- `core/horizontal_alignment/segment_builder.py` - Check segment creation

---

## Issue 7: PSE001 - Invalid Pset_Stationing Properties

**Severity:** 🔴 ERROR  
**Count:** 3 instances  
**IFC Entity ID:** #14295 (IfcPropertySet)

### Problem
The `Pset_Stationing` property set has incorrect property names and the code is also using a non-standard property set name.

**Errors:**
1. Property "DistanceAlong" not valid - should be: IncomingStation, Station, or HasIncreasingStation
2. Property "IncrementOrder" not valid - should be: IncomingStation, Station, or HasIncreasingStation  
3. PropertySet name "Pset_SaikeiCrossSection" is not a standard IFC property set name

### Rule Reference
> "Each IfcPropertySet starting with 'Pset_' is defined correctly."

https://buildingsmart.github.io/ifc-gherkin-rules/branches/main/features/PSE001_Standard-properties-and-property-sets-validation.html

### IFC Standard Pset_Stationing Properties
Per IFC 4.3 specification:
- `Station` - The station/chainage value
- `IncomingStation` - For station equations, the incoming station value
- `HasIncreasingStation` - Boolean indicating if station increases along alignment

### Fix Required

**Fix 1: Correct Pset_Stationing property names:**
```python
# WRONG - Non-standard property names
properties = [
    ifc_file.create_entity("IfcPropertySingleValue",
        Name="DistanceAlong",  # ❌ Not valid
        NominalValue=ifc_file.create_entity("IfcLengthMeasure", 0.0)
    ),
    ifc_file.create_entity("IfcPropertySingleValue",
        Name="IncrementOrder",  # ❌ Not valid
        NominalValue=ifc_file.create_entity("IfcBoolean", True)
    )
]

# CORRECT - Standard property names
properties = [
    ifc_file.create_entity("IfcPropertySingleValue",
        Name="Station",  # ✅ Standard name
        NominalValue=ifc_file.create_entity("IfcLengthMeasure", 10000.0)
    ),
    ifc_file.create_entity("IfcPropertySingleValue",
        Name="HasIncreasingStation",  # ✅ Standard name
        NominalValue=ifc_file.create_entity("IfcBoolean", True)
    )
]

pset = ifc_file.create_entity(
    "IfcPropertySet",
    GlobalId=ifcopenshell.guid.new(),
    Name="Pset_Stationing",
    HasProperties=properties
)
```

**Fix 2: Use custom property set prefix for non-standard properties:**
```python
# For custom/non-standard properties, DON'T use "Pset_" prefix
# Use your own prefix or no prefix

# WRONG - Implies it's a standard IFC property set
ifc_file.create_entity("IfcPropertySet",
    Name="Pset_SaikeiCrossSection",  # ❌ Pset_ prefix implies standard
    ...
)

# CORRECT - Custom prefix for custom properties
ifc_file.create_entity("IfcPropertySet",
    Name="SaikeiCivil_CrossSection",  # ✅ Clear it's custom
    ...
)

# OR use the standard approach:
ifc_file.create_entity("IfcPropertySet",
    Name="CrossSection",  # ✅ No prefix = custom
    ...
)
```

### Files to Modify
- `core/horizontal_alignment/stationing.py` (17KB) - Pset_Stationing creation
- `core/native_ifc_cross_section.py` (22KB) - Custom property sets
- Search for "Pset_" to find all property set definitions

---

## Issue 8: SPS007 - Invalid Spatial Containment

**Severity:** 🔴 ERROR  
**Count:** 1 instance  
**IFC Entity ID:** #11904 (IfcAlignmentSegment)

### Problem
`IfcAlignmentSegment` should NOT be directly contained in spatial structure. It should only be nested within its parent alignment layout (IfcAlignmentHorizontal or IfcAlignmentVertical) via IfcRelNests.

### Rule Reference
> "Spatial containment via IfcRelContainedInSpatialStructure is utilised in accordance with Concept Template for Spatial Containment."

https://buildingsmart.github.io/ifc-gherkin-rules/branches/main/features/SPS007_Spatial-containment.html

### Correct Structure
```
IfcAlignment (contained in IfcRoad)
├── IfcAlignmentHorizontal (nested in IfcAlignment)
│   └── IfcAlignmentSegment (nested in IfcAlignmentHorizontal) ✅
└── IfcAlignmentVertical (nested in IfcAlignment)
    └── IfcAlignmentSegment (nested in IfcAlignmentVertical) ✅
```

IfcAlignmentSegment should **only** appear in IfcRelNests, **never** in IfcRelContainedInSpatialStructure.

### Fix Required
Remove IfcAlignmentSegment from any spatial containment relationships:

```python
# WRONG - Segment contained in spatial structure
ifc_file.create_entity(
    "IfcRelContainedInSpatialStructure",
    RelatingStructure=road,
    RelatedElements=[alignment, alignment_segment]  # ❌ Segment shouldn't be here
)

# CORRECT - Only alignment in spatial structure, segments in nests
ifc_file.create_entity(
    "IfcRelContainedInSpatialStructure",
    RelatingStructure=road,
    RelatedElements=[alignment]  # ✅ Only the alignment
)

ifc_file.create_entity(
    "IfcRelNests",
    RelatingObject=alignment_horizontal,
    RelatedObjects=[segment1, segment2, ...]  # ✅ Segments nested, not contained
)
```

### Files to Modify
- `core/ifc_manager/manager.py` - Check spatial structure creation
- `core/horizontal_alignment/manager.py` - Ensure segments only use IfcRelNests
- `core/vertical_alignment/manager.py` - Ensure segments only use IfcRelNests

---

## Summary: Files to Modify

| File | Issues | Primary Changes |
|------|--------|-----------------|
| `core/ifc_manager/manager.py` | 1, 8 | Fix alignment aggregation, spatial containment |
| `core/horizontal_alignment/manager.py` | 1, 2, 3, 4, 8 | Zero-length segments, aggregation, curve types |
| `core/horizontal_alignment/stationing.py` | 7 | Fix Pset_Stationing property names |
| `core/vertical_alignment/manager.py` | 2, 4, 8 | Zero-length segments, spatial containment |
| `core/native_ifc_cross_section.py` | 7 | Rename custom property sets |
| Various | 5, 6 | Cleanup orphaned entities, set ObjectType |

---

## Implementation Priority

**High Priority (Core IFC Compliance):**
1. ⚡ Issue 1 (ALB004) - Alignment aggregation
2. ⚡ Issue 2 (ALB015) - Zero-length final segments (business logic)
3. ⚡ Issue 4 (ALS015) - Zero-length final segments (geometry)

**Medium Priority (Data Quality):**
4. Issue 3 (ALS012) - SegmentStart/Length types
5. Issue 7 (PSE001) - Property set names
6. Issue 8 (SPS007) - Spatial containment

**Lower Priority (Cleanup):**
7. Issue 5 (IFC105) - Orphaned entities
8. Issue 6 (OJT001) - ObjectType attribute

---

## Key Concept: Zero-Length Final Segments

This is a critical IFC 4.3 alignment requirement that appears in both Issues 2 and 4. Here's the complete pattern:

```python
class AlignmentFinalizer:
    """Helper to add required zero-length final segments."""
    
    @staticmethod
    def add_horizontal_endpoint(ifc_file, h_alignment, last_segment):
        """Add zero-length final segment to horizontal alignment."""
        # Get endpoint from last segment
        last_params = last_segment.DesignParameters
        end_point = calculate_endpoint(last_params)
        end_direction = calculate_end_direction(last_params)
        
        # Business logic segment (zero length)
        end_params = ifc_file.create_entity(
            "IfcAlignmentHorizontalSegment",
            StartPoint=end_point,
            StartDirection=end_direction,
            StartRadiusOfCurvature=0.0,
            EndRadiusOfCurvature=0.0,
            SegmentLength=0.0,  # MUST be zero
            PredefinedType="LINE"
        )
        
        end_segment = ifc_file.create_entity(
            "IfcAlignmentSegment",
            GlobalId=ifcopenshell.guid.new(),
            Name="Endpoint",
            ObjectType="ENDPOINT",
            DesignParameters=end_params
        )
        
        return end_segment
    
    @staticmethod
    def add_curve_endpoint(ifc_file, composite_curve, last_curve_segment):
        """Add zero-length DISCONTINUOUS final segment to curve geometry."""
        end_point = get_curve_endpoint(last_curve_segment)
        
        # Create zero-length line at endpoint
        parent_line = ifc_file.create_entity(
            "IfcLine",
            Pnt=end_point,
            Dir=ifc_file.create_entity("IfcVector", ...)
        )
        
        # DISCONTINUOUS, zero-length final segment
        final_curve_segment = ifc_file.create_entity(
            "IfcCurveSegment",
            Transition="DISCONTINUOUS",  # Must be discontinuous
            Placement=...,
            SegmentStart=0.0,
            SegmentLength=0.0,  # Must be zero
            ParentCurve=parent_line
        )
        
        return final_curve_segment
```

---

## Testing After Fix

After implementing fixes, revalidate:
1. Export new IFC file from Saikei Civil
2. Submit to BSI Validation Service: https://validate.buildingsmart.org/
3. Check both **IFC Schema** and **Normative IFC Rules** reports
4. Test import in IFC viewers (BlenderBIM, FZK Viewer)

---

*Document generated for Claude Code implementation*  
*Date: 2025-12-15*
*Previous fixes: Schema validation (600+ → 0 errors)*
