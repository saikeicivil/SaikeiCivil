# BSI Normative Rules Fix Summary - Round 3

**File Analyzed:** BSI_Val_edits_norm.ifc  
**Validation Report Date:** 2025-12-15 20:33:41  
**Progress:** 12 errors → 3 errors (75% reduction!)

---

## Remaining Issues (3 total)

| Rule | Entity | Problem |
|------|--------|---------|
| IFC105 | IfcCartesianPoint #12236 | Orphaned resource entity |
| OJT001 | IfcCourse #16797 | Empty ObjectType |
| SPS002 | IfcRoadPart #16148 | Wrong spatial parent (IfcAlignment instead of IfcRoad) |

---

## Issue 1: IFC105 - Orphaned IfcCartesianPoint

**Severity:** 🔴 ERROR  
**Entity ID:** #12236

### Problem
An `IfcCartesianPoint` exists but isn't referenced by any rooted entity. This is a "dangling" geometry entity.

### Root Cause
Somewhere in the code, a point is being created but never used. This could be:
- A temporary point created during calculations but not cleaned up
- A point created for a feature that was later removed
- A point created in error

### Fix Options

**Option A: Find and remove the creation (Preferred)**
Search for where this orphaned point is being created and either:
1. Don't create it if it's not needed
2. Ensure it gets used by something

**Option B: Add cleanup before file write**
```python
def remove_orphaned_cartesian_points(ifc_file):
    """Remove IfcCartesianPoint entities not referenced by anything."""
    
    # Build set of all referenced entity IDs
    referenced_ids = set()
    for entity in ifc_file:
        for attr in entity:
            if hasattr(attr, 'id'):
                referenced_ids.add(attr.id())
            elif isinstance(attr, (list, tuple)):
                for item in attr:
                    if hasattr(item, 'id'):
                        referenced_ids.add(item.id())
    
    # Find and remove orphaned points
    orphaned = []
    for point in ifc_file.by_type("IfcCartesianPoint"):
        if point.id() not in referenced_ids:
            orphaned.append(point)
    
    for point in orphaned:
        ifc_file.remove(point)
    
    return len(orphaned)

# Call before writing file:
# removed = remove_orphaned_cartesian_points(ifc_file)
# print(f"Removed {removed} orphaned points")
```

### Files to Check
- `core/native_ifc_corridor.py` - Corridor generation creates many points
- `core/horizontal_alignment/curve_geometry.py` - Curve calculations
- `core/native_ifc_cross_section.py` - Cross-section profiles

---

## Issue 2: OJT001 - IfcCourse Missing ObjectType

**Severity:** 🔴 ERROR  
**Entity ID:** #16797 (IfcCourse)

### Problem
`IfcCourse` has `PredefinedType=USERDEFINED` but `ObjectType` is empty/null. When using USERDEFINED, you **must** provide a descriptive ObjectType.

### IFC Rule
> "When PredefinedType is USERDEFINED, ObjectType must be non-empty."

### Fix Required

```python
# WRONG - USERDEFINED without ObjectType
course = ifc_file.create_entity(
    "IfcCourse",
    GlobalId=ifcopenshell.guid.new(),
    Name="Corridor Surface",
    ObjectType=None,  # ❌ Empty!
    PredefinedType="USERDEFINED"
)

# CORRECT - Option 1: Provide ObjectType for USERDEFINED
course = ifc_file.create_entity(
    "IfcCourse",
    GlobalId=ifcopenshell.guid.new(),
    Name="Corridor Surface",
    ObjectType="PAVEMENT_SURFACE",  # ✅ Descriptive type
    PredefinedType="USERDEFINED"
)

# CORRECT - Option 2: Use standard PredefinedType (no ObjectType needed)
course = ifc_file.create_entity(
    "IfcCourse",
    GlobalId=ifcopenshell.guid.new(),
    Name="Corridor Surface",
    ObjectType=None,  # OK when using standard type
    PredefinedType="PAVEMENT"  # ✅ Standard type from IfcCourseTypeEnum
)
```

### IfcCourseTypeEnum Standard Values
Per IFC 4.3, valid PredefinedType values for IfcCourse include:
- `ARMOUR`
- `BALLASTBED`
- `CORE`
- `FILTER`
- `PAVEMENT`
- `PROTECTION`
- `USERDEFINED`
- `NOTDEFINED`

**Recommendation:** Use `PAVEMENT` instead of `USERDEFINED` for road corridor surfaces.

### Files to Modify
- `core/native_ifc_corridor.py` (35KB) - Look for `IfcCourse` creation

---

## Issue 3: SPS002 - Wrong Spatial Parent for IfcRoadPart

**Severity:** 🔴 ERROR  
**Entity ID:** #16148 (IfcRoadPart)

### Problem
`IfcRoadPart` is being aggregated/decomposed by `IfcAlignment` (#36), but according to the IFC Spatial Composition rules, `IfcRoadPart` must be aggregated by one of:
- `IfcFacility`
- `IfcFacilityPartCommon`
- `IfcRoad`
- `IfcRoadPart`
- `IfcSpace`

**NOT** by `IfcAlignment`!

### Rule Reference
> "Spatial elements are aggregated as per the Spatial Composition Table."

https://buildingsmart.github.io/ifc-gherkin-rules/branches/main/features/SPS002_Correct-spatial-breakdown.html

### Correct Spatial Hierarchy
```
IfcProject
└── IfcSite
    └── IfcRoad                    ← Facility
        ├── IfcAlignment           ← Contained in Road (not a parent!)
        └── IfcRoadPart            ← Aggregated BY Road ✅
            └── IfcCourse          ← Contained in RoadPart
```

### Current (Wrong) Structure
```
IfcAlignment
└── IfcRoadPart  ❌ Wrong! RoadPart can't be child of Alignment
```

### Fix Required

```python
# WRONG - RoadPart aggregated to Alignment
ifc_file.create_entity(
    "IfcRelAggregates",
    GlobalId=ifcopenshell.guid.new(),
    RelatingObject=alignment,  # ❌ Alignment can't aggregate RoadPart
    RelatedObjects=[road_part]
)

# CORRECT - RoadPart aggregated to Road
ifc_file.create_entity(
    "IfcRelAggregates",
    GlobalId=ifcopenshell.guid.new(),
    Name="Road to RoadParts",
    RelatingObject=road,  # ✅ Road aggregates RoadPart
    RelatedObjects=[road_part]
)

# Alignment is CONTAINED in Road, not aggregating it
ifc_file.create_entity(
    "IfcRelContainedInSpatialStructure",
    GlobalId=ifcopenshell.guid.new(),
    RelatingStructure=road,
    RelatedElements=[alignment]  # Alignment contained in Road
)
```

### Complete Correct Pattern

```python
def setup_road_spatial_structure(ifc_file, site, road_name, alignment, road_parts):
    """
    Set up correct spatial hierarchy for road corridor.
    
    Hierarchy:
    - Site aggregates Road
    - Road aggregates RoadPart(s)
    - Road contains Alignment
    - RoadPart contains Course(s)
    """
    
    # 1. Create Road (facility)
    road = ifc_file.create_entity(
        "IfcRoad",
        GlobalId=ifcopenshell.guid.new(),
        Name=road_name,
        PredefinedType="USERDEFINED",
        ObjectType="Highway"
    )
    
    # 2. Site aggregates Road
    ifc_file.create_entity(
        "IfcRelAggregates",
        GlobalId=ifcopenshell.guid.new(),
        Name="Site to Road",
        RelatingObject=site,
        RelatedObjects=[road]
    )
    
    # 3. Road aggregates RoadPart(s) - THIS IS THE KEY FIX
    if road_parts:
        ifc_file.create_entity(
            "IfcRelAggregates",
            GlobalId=ifcopenshell.guid.new(),
            Name="Road to RoadParts",
            RelatingObject=road,  # ✅ Road is parent
            RelatedObjects=road_parts
        )
    
    # 4. Road CONTAINS Alignment (not aggregates)
    ifc_file.create_entity(
        "IfcRelContainedInSpatialStructure",
        GlobalId=ifcopenshell.guid.new(),
        Name="Road contains Alignment",
        RelatingStructure=road,
        RelatedElements=[alignment]
    )
    
    return road
```

### Files to Modify
- `core/native_ifc_corridor.py` (35KB) - Look for IfcRoadPart spatial setup
- `core/ifc_manager/manager.py` (52KB) - May have spatial hierarchy helpers

---

## Summary

| Issue | Entity | Fix | File |
|-------|--------|-----|------|
| IFC105 | IfcCartesianPoint | Remove orphaned point or don't create | Various geometry files |
| OJT001 | IfcCourse | Use `PredefinedType="PAVEMENT"` or set `ObjectType` | `core/native_ifc_corridor.py` |
| SPS002 | IfcRoadPart | Aggregate to `IfcRoad`, not `IfcAlignment` | `core/native_ifc_corridor.py` |

---

## Key Insight: Spatial Hierarchy

The SPS002 error reveals an important IFC concept:

**Alignments don't own spatial elements - Roads do!**

```
CORRECT:
IfcRoad (facility/spatial element)
├── contains: IfcAlignment (defines geometry)
└── aggregates: IfcRoadPart (spatial breakdown)
                └── contains: IfcCourse, IfcPavement, etc.

WRONG:
IfcAlignment
└── aggregates: IfcRoadPart  ❌
```

The alignment defines the *geometry* of the road, but the *spatial structure* (RoadPart, Course, etc.) belongs to the Road facility.

---

*Document generated for Claude Code implementation*  
*Date: 2025-12-15*
*Progress: 600+ schema errors → 0 → 12 normative → 3 normative*
