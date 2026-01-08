# Saikei Civil Compliance Assessment vs buildingSMART IFC Infra Overall Architecture Guidelines

**Assessment Date:** January 2026
**Reference Document:** 08_bSI_OverallArchitecure_Guidelines_final.pdf (buildingSMART Infra Room, March 2017)
**Assessed Project:** Saikei Civil - Native IFC for Horizontal Construction

---

## Executive Summary

**Overall Compliance: EXCELLENT**

Saikei Civil demonstrates strong adherence to the buildingSMART IFC Infra Overall Architecture Guidelines. The project follows the "native IFC" philosophy exactly as the guidelines envision - working *in* IFC format rather than converting *to* IFC. Below is a detailed assessment by guideline area.

---

## 1. General Principles (Section 4 of Whitepaper)

| Principle | Guideline | Saikei Implementation | Compliance |
|-----------|-----------|----------------------|------------|
| Minimal Intervention | Ensure backwards compatibility | Uses IFC4X3 schema, uses existing IFC entities where possible | **COMPLIANT** |
| Minimal Extension | Use existing data structures | Uses standard IFC entities (IfcRoad, IfcAlignment, etc.) rather than inventing new ones | **COMPLIANT** |
| International Scope | Only global elements in model | Uses standard IFC entities and property sets; custom Psets prefixed with "SaikeiCivil_" not "Pset_" | **COMPLIANT** |

---

## 2. Spatial Structure (Section 2)

| Requirement | Guideline | Saikei Implementation | Compliance |
|-------------|-----------|----------------------|------------|
| Hierarchy | IfcProject → IfcSite → IfcBuiltFacility | Implements IfcProject → IfcSite → IfcRoad hierarchy correctly | **COMPLIANT** |
| Relationships | Use IfcRelAggregates | Uses `ifcopenshell.api.aggregate.assign_object()` for all aggregation | **COMPLIANT** |
| Single IfcSite | Recommend only one IfcSite | Creates single IfcSite per project | **COMPLIANT** |
| Road Parts | Use IfcRoadPart for decomposition | Implements IfcRoadPart with correct PredefinedType (TRAFFICLANE, SHOULDER, etc.) | **COMPLIANT** |
| ObjectType | Required per BSI OJT001 | Extensive enforcement via cleanup functions | **COMPLIANT** |

**Notable Strength:** Saikei includes comprehensive BSI compliance validation (SPS002, SPS007, OJT001, ALB004, etc.) to ensure spatial structure correctness.

---

## 3. Geodetic Reference Systems (Section 3.1)

| Requirement | Guideline | Saikei Implementation | Compliance |
|-------------|-----------|----------------------|------------|
| IfcProjectedCRS | Define coordinate reference system | Implements with EPSG codes, geodetic datum, map unit | **COMPLIANT** |
| IfcMapConversion | Local to global transformation | Implements with Eastings, Northings, OrthogonalHeight, rotation | **COMPLIANT** |
| Single GRS | Don't define multiple GRS | Single GRS per file | **COMPLIANT** |
| Optional but recommended | GRS definition encouraged for infrastructure | Provides full georeferencing module | **COMPLIANT** |

**Notable Strength:** When Bonsai is available, Saikei **defers to Bonsai's georeferencing** implementation, following the CLAUDE.md principle of "detect and defer" to leverage the more mature Bonsai features.

---

## 4. Alignment & Positioning (Section 3.3)

| Requirement | Guideline | Saikei Implementation | Compliance |
|-------------|-----------|----------------------|------------|
| IfcAlignment | Primary positioning entity | Implements as core functionality | **COMPLIANT** |
| IfcAlignment2DHorizontal | Horizontal layout | Correctly nested via IfcRelNests | **COMPLIANT** |
| IfcAlignment2DVertical | Vertical layout | Correctly nested via IfcRelNests | **COMPLIANT** |
| IfcAlignmentSegment | Segment wrapper | Implements with DesignParameters and ObjectType | **COMPLIANT** |
| Segment Types | LINE, CIRCULARARC, CLOTHOID, etc. | Implements LINE and CIRCULARARC; clothoid support noted as future work | **PARTIAL** |
| IfcReferent | Known positions on alignment | Implements for stationing with Pset_Stationing | **COMPLIANT** |
| IfcLinearPlacement | Position elements along alignment | Architecture supports it | **COMPLIANT** |
| IfcDistanceExpression | Distance and offsets | Used for cross-section positioning | **COMPLIANT** |

**Minor Gap:** Clothoid (spiral) transitions not yet implemented for horizontal alignments, though the architecture supports adding them.

---

## 5. Geometry Representations

### 5.1 Cross Sections (Section 3.5)

| Requirement | Guideline | Saikei Implementation | Compliance |
|-------------|-----------|----------------------|------------|
| IfcArbitraryClosedProfileDef | Closed areas | Implemented for pavement layers with depth | **COMPLIANT** |
| IfcArbitraryOpenProfileDef | Open curves | Implemented for surface-only profiles | **COMPLIANT** |
| IfcOpenCrossProfileDef | IFC4.3 specific | Implemented with Widths, Slopes, Tags | **COMPLIANT** |
| IfcCompositeProfileDef | Combined profiles | Implemented for road assemblies | **COMPLIANT** |
| Point labeling | Named vertices for interpolation | Uses comprehensive tag system (CL, ETW_L, ETW_R, etc.) | **EXCELLENT** |

### 5.2 Solid Geometry (Section 3.7)

| Requirement | Guideline | Saikei Implementation | Compliance |
|-------------|-----------|----------------------|------------|
| IfcSectionedSolidHorizontal | Cross-section sweep along alignment | **Fully implemented** in native_ifc_corridor.py | **COMPLIANT** |
| Variable cross-sections | Support for transitioning profiles | Implements with station-based interpolation | **COMPLIANT** |
| FixedAxisVertical | Keep vertical axis upright | Architecture supports this | **COMPLIANT** |

**Major Strength:** Full implementation of `IfcSectionedSolidHorizontal` as recommended in Section 3.7 for corridor modeling.

### 5.3 Surface/Terrain Representation (Sections 3.2, 3.6)

| Requirement | Guideline | Saikei Implementation | Compliance |
|-------------|-----------|----------------------|------------|
| IfcTriangulatedIrregularNetwork | Terrain surfaces | Not currently implemented | **NOT IMPLEMENTED** |
| IfcTriangulatedFaceSet | General surfaces | Not currently implemented | **NOT IMPLEMENTED** |

**Gap:** Terrain/TIN support is not yet implemented. This is noted as future work in the project roadmap.

---

## 6. Physical Element Description (Section 4)

| Requirement | Guideline | Saikei Implementation | Compliance |
|-------------|-----------|----------------------|------------|
| Classify by function | Elements classified by function, not domain | Uses IfcPavement for lanes/shoulders, IfcKerb for curbs, etc. | **COMPLIANT** |
| Use existing entities | Prefer existing IFC types | Uses IfcRoad, IfcRoadPart, IfcPavement, IfcKerb, IfcBuildingElementProxy | **COMPLIANT** |
| PredefinedType | Use before creating subtypes | Correctly uses enums (TRAFFICLANE, SHOULDER, etc.) | **COMPLIANT** |
| ObjectType | Required when PredefinedType is USERDEFINED | Enforced via cleanup and validation | **COMPLIANT** |
| IfcBuildingElementProxy | For elements without specific type | Used for DITCH, MEDIAN, CUSTOM components | **COMPLIANT** |

---

## 7. Classification, Property Sets & Linked Data (Section 5)

| Requirement | Guideline | Saikei Implementation | Compliance |
|-------------|-----------|----------------------|------------|
| Property Sets | Use for regional/project extensions | Custom Psets prefixed "SaikeiCivil_" (not standard prefix) | **COMPLIANT** |
| Standard Psets | Use standard names where applicable | Uses Pset_Stationing correctly | **COMPLIANT** |
| IfcRelDefinesByProperties | Attach property sets | Correctly implemented | **COMPLIANT** |
| Classification | Via IfcRelAssociatesClassification | Architecture supports but not extensively used | **PARTIAL** |
| bsDD linkage | Link to buildingSMART Data Dictionary | Not currently implemented | **NOT IMPLEMENTED** |

**Minor Gap:** External classification systems and bsDD linkage are not yet implemented, though the architecture supports adding them.

---

## 8. Additional Compliance Areas

### Transaction/Undo Support
The whitepaper emphasizes the need for proper data management. Saikei implements:
- **Three-level undo/redo** (IFC file, element maps, Blender objects)
- **Transaction system** with commit/rollback
- **IFC-as-source-of-truth** rebuilding after undo

### BSI Validation Rules
Saikei implements validation for multiple BSI rules:
- **SPS002:** Alignments aggregated to IfcRoad (not IfcSite)
- **SPS007:** Alignment segments not in spatial containment
- **ALB004:** Alignments aggregated to IfcProject (directly or via IfcRoad)
- **OJT001:** ObjectType required on all spatial elements
- **IFC105:** No orphaned resource entities
- **ALS016/ALS017:** RefDirection specified on placements

---

## Summary: Compliance by Area

| Area | Status | Notes |
|------|--------|-------|
| **General Principles** | **COMPLIANT** | Follows all three principles |
| **Spatial Structure** | **COMPLIANT** | Correct hierarchy with BSI validation |
| **Georeferencing** | **COMPLIANT** | Full implementation, defers to Bonsai when available |
| **Alignment & Positioning** | **MOSTLY COMPLIANT** | Missing clothoid transitions |
| **Cross Sections** | **COMPLIANT** | Full profile support with tagging |
| **Solid Geometry (Corridors)** | **COMPLIANT** | Full IfcSectionedSolidHorizontal support |
| **Terrain/TIN** | **NOT IMPLEMENTED** | Future work |
| **Physical Elements** | **COMPLIANT** | Correct entity usage and classification |
| **Property Sets** | **COMPLIANT** | Proper naming conventions |
| **External Classification** | **PARTIAL** | Architecture supports but not extensively used |

---

## Recommendations for Improvement

1. **Add Clothoid/Spiral Transitions** - Implement `IfcAlignmentHorizontalSegment` with `PredefinedType="CLOTHOID"` for horizontal transitions.

2. **Implement Terrain Support** - Add `IfcTriangulatedIrregularNetwork` for terrain surfaces and `IfcGeographicElement` with `PredefinedType="TERRAIN"`.

3. **External Classification Integration** - Consider implementing `IfcRelAssociatesClassification` for linking to classification systems like Uniclass or OmniClass.

4. **bsDD Integration** - Future consideration for linking to buildingSMART Data Dictionary for property definitions.

5. **Cant/Superelevation Events** - For railway support, consider implementing `IfcReferent` with `Pset_CantEvent` as described in Section 3.8.

---

## Conclusion

**Saikei Civil is highly compliant with the buildingSMART IFC Infra Overall Architecture Guidelines.** The project demonstrates:

- Deep understanding of IFC infrastructure concepts
- Proper use of IFC 4.3 entities for civil engineering
- Correct spatial structure and relationships
- Robust alignment and corridor implementation
- Strong BSI compliance validation

The "native IFC" philosophy aligns perfectly with the whitepaper's vision of tools that work *in* IFC format rather than converting to it. The identified gaps (terrain support, clothoid transitions, external classification) are relatively minor and represent future enhancement opportunities rather than fundamental compliance issues.

---

## Appendix: Key Saikei Civil Implementation Files

| Feature | Primary File(s) |
|---------|-----------------|
| Spatial Structure | `core/ifc_manager/manager.py`, `core/ifc_api.py` |
| Horizontal Alignments | `core/horizontal_alignment/manager.py`, `core/horizontal_alignment/segment_builder.py` |
| Vertical Alignments | `core/vertical_alignment/manager.py`, `core/native_ifc_vertical_alignment.py` |
| Georeferencing | `core/native_ifc_georeferencing.py` |
| Cross-Sections | `core/native_ifc_cross_section.py` |
| Corridors | `core/native_ifc_corridor.py` |
| BSI Validation | `core/ifc_api.py` (cleanup functions), `core/ifc_manager/validation.py` |
| Transaction System | `core/ifc_manager/transaction.py` |
| Bonsai Integration | `tool/ifc.py` |

---

*This assessment was generated by reviewing Saikei Civil source code against the buildingSMART IFC Infra Overall Architecture Project Documentation and Guidelines (FINAL, 01/03/2017).*