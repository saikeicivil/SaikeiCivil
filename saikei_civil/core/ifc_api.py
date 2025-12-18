# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under the GNU General Public License v3
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
IFC API Wrappers
=================

Wrapper functions that use ifcopenshell.api for IFC operations.
This module provides a cleaner interface to the ifcopenshell API and
ensures consistent patterns across the codebase.

The ifcopenshell.api handles:
- Schema version differences automatically
- Relationship management
- Ownership tracking
- Entity lifecycle

Usage:
    from saikei_civil.core import ifc_api

    # Create a new project
    project = ifc_api.create_project(ifc_file, "My Project")

    # Create an alignment using PI method
    alignment = ifc_api.create_alignment_by_pi(
        ifc_file,
        name="Main Road",
        pis=[(0, 0), (100, 0), (100, 100)],
        radii=[0, 50.0, 0]
    )

    # Add georeferencing
    ifc_api.add_georeferencing(ifc_file, epsg=6339)

References:
    - https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/alignment/index.html
    - https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/georeference/index.html
    - https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/project/index.html
"""
from typing import TYPE_CHECKING, Optional, List, Tuple, Dict, Any

# Use the project's logging config for consistent output
from .logging_config import get_logger

if TYPE_CHECKING:
    import ifcopenshell

try:
    import ifcopenshell
    import ifcopenshell.api
    import ifcopenshell.api.project
    import ifcopenshell.api.spatial
    import ifcopenshell.api.root
    import ifcopenshell.api.context
    import ifcopenshell.api.unit
    import ifcopenshell.api.georeference
    # Alignment API may not be available in all versions
    try:
        import ifcopenshell.api.alignment
        HAS_ALIGNMENT_API = True
    except ImportError:
        HAS_ALIGNMENT_API = False
    HAS_IFCOPENSHELL = True
except ImportError:
    HAS_IFCOPENSHELL = False
    HAS_ALIGNMENT_API = False

logger = get_logger(__name__)


# =============================================================================
# Project & Spatial Hierarchy
# =============================================================================

def create_project(
    ifc_file: "ifcopenshell.file",
    name: str = "Saikei Civil Project",
    description: str = "Civil engineering project"
) -> "ifcopenshell.entity_instance":
    """
    Create or get the IfcProject entity.

    Uses ifcopenshell.api.project if available, falls back to manual creation.

    Args:
        ifc_file: The IFC file
        name: Project name
        description: Project description

    Returns:
        The IfcProject entity
    """
    # Check if project already exists
    projects = ifc_file.by_type("IfcProject")
    if projects:
        return projects[0]

    # Try using the API
    try:
        project = ifcopenshell.api.project.create_file(schema=ifc_file.schema)
        # This creates a new file, so we need a different approach
        # Fall through to manual creation
    except Exception:
        pass

    # Manual creation (compatible approach)
    project = ifc_file.create_entity(
        "IfcProject",
        GlobalId=ifcopenshell.guid.new(),
        Name=name,
        Description=description,
    )

    return project


def create_site(
    ifc_file: "ifcopenshell.file",
    project: "ifcopenshell.entity_instance",
    name: str = "Site",
    description: str = "Project site"
) -> "ifcopenshell.entity_instance":
    """
    Create an IfcSite and aggregate it to the project.

    Args:
        ifc_file: The IFC file
        project: The parent IfcProject
        name: Site name
        description: Site description

    Returns:
        The IfcSite entity
    """
    # Check if site already exists
    sites = ifc_file.by_type("IfcSite")
    if sites:
        return sites[0]

    # Create placement
    placement = _create_local_placement(ifc_file)

    # OJT001 FIX: ObjectType must be set for spatial elements
    site = ifc_file.create_entity(
        "IfcSite",
        GlobalId=ifcopenshell.guid.new(),
        Name=name,
        Description=description,
        ObjectType="SITE",  # Required by OJT001
        ObjectPlacement=placement
    )

    # Aggregate site to project using API
    try:
        ifcopenshell.api.aggregate.assign_object(
            ifc_file,
            relating_object=project,
            products=[site]
        )
    except Exception:
        # Fall back to manual aggregation
        _aggregate_manual(ifc_file, project, site)

    return site


def create_road(
    ifc_file: "ifcopenshell.file",
    site: "ifcopenshell.entity_instance",
    name: str = "Road",
    description: str = "Road facility"
) -> "ifcopenshell.entity_instance":
    """
    Create an IfcRoad and aggregate it to the site.

    Args:
        ifc_file: The IFC file
        site: The parent IfcSite
        name: Road name
        description: Road description

    Returns:
        The IfcRoad entity
    """
    # Check if road already exists
    roads = ifc_file.by_type("IfcRoad")
    if roads:
        return roads[0]

    # Create placement relative to site
    site_placement = site.ObjectPlacement if hasattr(site, 'ObjectPlacement') else None
    placement = _create_local_placement(ifc_file, relative_to=site_placement)

    # OJT001 FIX: ObjectType must be set for spatial elements
    road = ifc_file.create_entity(
        "IfcRoad",
        GlobalId=ifcopenshell.guid.new(),
        Name=name,
        Description=description,
        ObjectType="ROAD",  # Required by OJT001
        ObjectPlacement=placement
    )

    # Aggregate road to site
    try:
        ifcopenshell.api.aggregate.assign_object(
            ifc_file,
            relating_object=site,
            products=[road]
        )
    except Exception:
        _aggregate_manual(ifc_file, site, road)

    return road


# =============================================================================
# Alignment Creation
# =============================================================================

def create_alignment(
    ifc_file: "ifcopenshell.file",
    name: str,
    container: Optional["ifcopenshell.entity_instance"] = None
) -> "ifcopenshell.entity_instance":
    """
    Create a new IfcAlignment entity.

    Args:
        ifc_file: The IFC file
        name: Alignment name
        container: Spatial container (IfcRoad, IfcSite, etc.)

    Returns:
        The IfcAlignment entity
    """
    if HAS_ALIGNMENT_API:
        try:
            alignment = ifcopenshell.api.alignment.create(
                ifc_file,
                name=name
            )
            if container:
                contain_in_spatial(ifc_file, alignment, container)
            return alignment
        except Exception as e:
            logger.debug(f"API alignment creation failed: {e}, using manual")

    # Manual creation fallback
    placement = _create_local_placement(ifc_file)

    alignment = ifc_file.create_entity(
        "IfcAlignment",
        GlobalId=ifcopenshell.guid.new(),
        Name=name,
        ObjectPlacement=placement,
        PredefinedType="USERDEFINED"
    )

    if container:
        contain_in_spatial(ifc_file, alignment, container)

    return alignment


def create_alignment_by_pi(
    ifc_file: "ifcopenshell.file",
    name: str,
    pis: List[Tuple[float, float]],
    radii: Optional[List[float]] = None,
    starting_station: float = 10000.0,
    container: Optional["ifcopenshell.entity_instance"] = None
) -> "ifcopenshell.entity_instance":
    """
    Create alignment using PI (Point of Intersection) method.

    This is the recommended method for creating alignments as it uses
    the ifcopenshell.api.alignment module which handles all the
    complex geometry and relationship management.

    Args:
        ifc_file: The IFC file
        name: Alignment name
        pis: List of (x, y) coordinate tuples for PIs
        radii: List of curve radii (0 for no curve at that PI)
        starting_station: Starting station value
        container: Spatial container (IfcRoad)

    Returns:
        The IfcAlignment entity

    Example:
        alignment = create_alignment_by_pi(
            ifc,
            "Main Street",
            pis=[(0, 0), (100, 0), (100, 100), (200, 100)],
            radii=[0, 50.0, 30.0, 0],
            starting_station=10000.0
        )
    """
    if not pis or len(pis) < 2:
        raise ValueError("At least 2 PIs required for alignment")

    # Default radii to 0 (no curves)
    if radii is None:
        radii = [0.0] * len(pis)
    elif len(radii) != len(pis):
        raise ValueError(f"radii length ({len(radii)}) must match pis length ({len(pis)})")

    if HAS_ALIGNMENT_API:
        try:
            # Format data for API
            pi_data = [
                {"Coordinates": (x, y), "Radius": r}
                for (x, y), r in zip(pis, radii)
            ]

            alignment = ifcopenshell.api.alignment.create_by_pi_method(
                ifc_file,
                name=name,
                horizontal=pi_data,
                starting_station=starting_station
            )

            if container:
                contain_in_spatial(ifc_file, alignment, container)

            logger.info(f"Created alignment '{name}' with {len(pis)} PIs using API")
            return alignment

        except Exception as e:
            logger.warning(f"API alignment creation failed: {e}, using legacy method")

    # Fall back to legacy NativeIfcAlignment
    from .horizontal_alignment import NativeIfcAlignment

    native = NativeIfcAlignment(ifc_file, name)
    for x, y in pis:
        native.add_pi(x, y)

    for i, radius in enumerate(radii):
        if radius > 0 and 0 < i < len(pis) - 1:
            native.insert_curve_at_pi(i, radius)

    if starting_station != 10000.0:
        native.set_starting_station(starting_station)

    if container:
        contain_in_spatial(ifc_file, native.alignment, container)

    logger.info(f"Created alignment '{name}' with {len(pis)} PIs using legacy method")
    return native.alignment


def add_horizontal_layout(
    ifc_file: "ifcopenshell.file",
    alignment: "ifcopenshell.entity_instance"
) -> "ifcopenshell.entity_instance":
    """
    Add IfcAlignmentHorizontal to an alignment.

    Args:
        ifc_file: The IFC file
        alignment: The parent IfcAlignment

    Returns:
        The IfcAlignmentHorizontal entity
    """
    if HAS_ALIGNMENT_API:
        try:
            return ifcopenshell.api.alignment.get_horizontal_layout(
                ifc_file, alignment=alignment
            )
        except Exception:
            pass

    # Manual creation
    horizontal = ifc_file.create_entity(
        "IfcAlignmentHorizontal",
        GlobalId=ifcopenshell.guid.new()
    )

    # Nest in alignment
    ifc_file.create_entity(
        "IfcRelNests",
        GlobalId=ifcopenshell.guid.new(),
        Name="AlignmentToHorizontal",
        RelatingObject=alignment,
        RelatedObjects=[horizontal]
    )

    return horizontal


def add_vertical_layout(
    ifc_file: "ifcopenshell.file",
    alignment: "ifcopenshell.entity_instance"
) -> "ifcopenshell.entity_instance":
    """
    Add IfcAlignmentVertical to an alignment.

    Args:
        ifc_file: The IFC file
        alignment: The parent IfcAlignment

    Returns:
        The IfcAlignmentVertical entity
    """
    if HAS_ALIGNMENT_API:
        try:
            return ifcopenshell.api.alignment.get_vertical_layout(
                ifc_file, alignment=alignment
            )
        except Exception:
            pass

    # Manual creation
    vertical = ifc_file.create_entity(
        "IfcAlignmentVertical",
        GlobalId=ifcopenshell.guid.new()
    )

    # Nest in alignment
    ifc_file.create_entity(
        "IfcRelNests",
        GlobalId=ifcopenshell.guid.new(),
        Name="AlignmentToVertical",
        RelatingObject=alignment,
        RelatedObjects=[vertical]
    )

    return vertical


# =============================================================================
# Georeferencing
# =============================================================================

def add_georeferencing(
    ifc_file: "ifcopenshell.file",
    epsg: int = 3857,
    eastings: float = 0.0,
    northings: float = 0.0,
    orthogonal_height: float = 0.0,
    x_axis_abscissa: float = 1.0,
    x_axis_ordinate: float = 0.0,
    scale: float = 1.0
) -> Tuple["ifcopenshell.entity_instance", "ifcopenshell.entity_instance"]:
    """
    Add georeferencing to an IFC file.

    Args:
        ifc_file: The IFC file
        epsg: EPSG code for the coordinate reference system
        eastings: X offset to map coordinates
        northings: Y offset to map coordinates
        orthogonal_height: Z offset
        x_axis_abscissa: X component of X axis direction
        x_axis_ordinate: Y component of X axis direction
        scale: Scale factor

    Returns:
        Tuple of (IfcMapConversion, IfcProjectedCRS)
    """
    try:
        # Use API to add georeferencing
        ifcopenshell.api.georeference.add_georeferencing(
            ifc_file,
            ifc_class="IfcMapConversion",
            name=f"EPSG:{epsg}"
        )

        # Edit the parameters
        ifcopenshell.api.georeference.edit_georeferencing(
            ifc_file,
            coordinate_operation={
                "Eastings": eastings,
                "Northings": northings,
                "OrthogonalHeight": orthogonal_height,
                "XAxisAbscissa": x_axis_abscissa,
                "XAxisOrdinate": x_axis_ordinate,
                "Scale": scale
            },
            projected_crs={
                "Name": f"EPSG:{epsg}"
            }
        )

        # Get the created entities
        map_conversion = ifc_file.by_type("IfcMapConversion")
        projected_crs = ifc_file.by_type("IfcProjectedCRS")

        return (
            map_conversion[0] if map_conversion else None,
            projected_crs[0] if projected_crs else None
        )

    except Exception as e:
        logger.warning(f"API georeferencing failed: {e}, using manual")

        # Manual fallback
        return _add_georeferencing_manual(
            ifc_file, epsg, eastings, northings, orthogonal_height,
            x_axis_abscissa, x_axis_ordinate, scale
        )


def edit_georeferencing(
    ifc_file: "ifcopenshell.file",
    eastings: Optional[float] = None,
    northings: Optional[float] = None,
    orthogonal_height: Optional[float] = None,
    scale: Optional[float] = None
) -> None:
    """
    Edit existing georeferencing parameters.

    Args:
        ifc_file: The IFC file
        eastings: New X offset (None to keep current)
        northings: New Y offset (None to keep current)
        orthogonal_height: New Z offset (None to keep current)
        scale: New scale factor (None to keep current)
    """
    coord_op = {}
    if eastings is not None:
        coord_op["Eastings"] = eastings
    if northings is not None:
        coord_op["Northings"] = northings
    if orthogonal_height is not None:
        coord_op["OrthogonalHeight"] = orthogonal_height
    if scale is not None:
        coord_op["Scale"] = scale

    if coord_op:
        ifcopenshell.api.georeference.edit_georeferencing(
            ifc_file,
            coordinate_operation=coord_op
        )


# =============================================================================
# Spatial Containment & Relationships
# =============================================================================

def contain_in_spatial(
    ifc_file: "ifcopenshell.file",
    element: "ifcopenshell.entity_instance",
    container: "ifcopenshell.entity_instance"
) -> Optional["ifcopenshell.entity_instance"]:
    """
    Contain an element in a spatial structure.

    Args:
        ifc_file: The IFC file
        element: The element to contain
        container: The spatial container (IfcRoad, IfcSite, etc.)

    Returns:
        The IfcRelContainedInSpatialStructure relationship, or None if element
        should not be in spatial containment

    Note:
        Per BSI SPS007, IfcAlignmentSegment should NOT be in spatial containment.
        They should only be nested via IfcRelNests.
    """
    # BSI SPS007: IfcAlignmentSegment must NOT be in spatial containment
    # They should only be nested via IfcRelNests
    if element.is_a("IfcAlignmentSegment"):
        logger.warning(
            f"IfcAlignmentSegment '{element.Name or element.id()}' should not be "
            "in spatial containment (BSI SPS007). Use IfcRelNests instead."
        )
        return None

    try:
        return ifcopenshell.api.spatial.assign_container(
            ifc_file,
            relating_structure=container,
            products=[element]
        )
    except Exception:
        # Manual fallback
        return ifc_file.create_entity(
            "IfcRelContainedInSpatialStructure",
            GlobalId=ifcopenshell.guid.new(),
            Name="ContainsElement",
            RelatingStructure=container,
            RelatedElements=[element]
        )


def cleanup_misplaced_alignment_segments(ifc_file: "ifcopenshell.file") -> int:
    """
    Remove IfcAlignmentSegment entities from spatial containment relationships.

    Per BSI SPS007, IfcAlignmentSegment should only be nested via IfcRelNests,
    never contained via IfcRelContainedInSpatialStructure.

    Args:
        ifc_file: The IFC file to clean up

    Returns:
        Number of segments removed from spatial containment
    """
    removed_count = 0

    for rel in ifc_file.by_type("IfcRelContainedInSpatialStructure"):
        if not rel.RelatedElements:
            continue

        elements = list(rel.RelatedElements)
        segments_to_remove = [e for e in elements if e.is_a("IfcAlignmentSegment")]

        if segments_to_remove:
            # Remove segments from this relationship
            remaining = [e for e in elements if not e.is_a("IfcAlignmentSegment")]

            if remaining:
                rel.RelatedElements = remaining
            else:
                # No elements left, remove the relationship
                ifc_file.remove(rel)

            removed_count += len(segments_to_remove)
            for seg in segments_to_remove:
                logger.info(
                    f"Removed IfcAlignmentSegment '{seg.Name or seg.id()}' "
                    "from spatial containment (BSI SPS007)"
                )

    if removed_count > 0:
        logger.info(
            f"Cleaned up {removed_count} IfcAlignmentSegment(s) from spatial containment"
        )

    return removed_count


def cleanup_misplaced_alignments(ifc_file: "ifcopenshell.file") -> int:
    """
    Fix IfcAlignment entities aggregated to incorrect parents.

    Per BSI SPS002: IfcAlignment should be aggregated to IfcRoad (or IfcFacility),
    NOT to IfcSite directly. This fixes the error:
    "IfcSite should be decomposed by one of [IfcFacility, IfcRoad, IfcRoadPart, IfcSpace]"

    Args:
        ifc_file: The IFC file to clean up

    Returns:
        Number of alignments moved
    """
    moved_count = 0

    # Valid parent types for IfcAlignment
    valid_parent_types = ("IfcRoad", "IfcFacility", "IfcFacilityPart")

    # Invalid parent types that should not contain IfcAlignment
    invalid_parent_types = ("IfcSite", "IfcBuilding", "IfcSpace")

    # Find all IfcAlignments that are incorrectly aggregated
    for rel in list(ifc_file.by_type("IfcRelAggregates")):
        if not rel.RelatingObject:
            continue

        parent_is_invalid = rel.RelatingObject.is_a() in invalid_parent_types

        if parent_is_invalid and rel.RelatedObjects:
            alignments_in_rel = [
                obj for obj in rel.RelatedObjects
                if obj.is_a("IfcAlignment")
            ]

            if not alignments_in_rel:
                continue

            # Find IfcRoad to move alignments to
            roads = ifc_file.by_type("IfcRoad")
            if not roads:
                logger.warning(
                    f"Cannot fix misplaced alignments - no IfcRoad found in file"
                )
                continue

            road = roads[0]

            # Remove alignments from invalid parent
            other_objects = [
                obj for obj in rel.RelatedObjects
                if not obj.is_a("IfcAlignment")
            ]

            if other_objects:
                rel.RelatedObjects = other_objects
            else:
                # BUG FIX (SPS002): When all objects in the relationship are
                # alignments to be moved, we must update the relationship to remove them.
                # Previous code did 'pass' which left alignments aggregated to IfcSite!
                rel.RelatedObjects = []
                logger.debug(f"Cleared all alignments from IfcRelAggregates #{rel.id()}")

            # Add alignments to IfcRoad
            for alignment in alignments_in_rel:
                # Check if already properly aggregated to road
                already_in_road = False
                for existing_rel in ifc_file.by_type("IfcRelAggregates"):
                    if existing_rel.RelatingObject == road:
                        if alignment in (existing_rel.RelatedObjects or []):
                            already_in_road = True
                            break

                if not already_in_road:
                    # Find existing aggregation from road or create new one
                    road_agg = None
                    for existing_rel in ifc_file.by_type("IfcRelAggregates"):
                        if existing_rel.RelatingObject == road:
                            road_agg = existing_rel
                            break

                    if road_agg:
                        # Add to existing relationship
                        current_objects = list(road_agg.RelatedObjects or [])
                        if alignment not in current_objects:
                            current_objects.append(alignment)
                            road_agg.RelatedObjects = current_objects
                    else:
                        # Create new aggregation
                        ifc_file.create_entity(
                            "IfcRelAggregates",
                            GlobalId=ifcopenshell.guid.new(),
                            Name="RoadToAlignment",
                            RelatingObject=road,
                            RelatedObjects=[alignment]
                        )

                moved_count += 1
                logger.info(
                    f"Moved IfcAlignment '{alignment.Name}' from "
                    f"{rel.RelatingObject.is_a()} to IfcRoad (BSI SPS002)"
                )

    if moved_count > 0:
        logger.info(
            f"Fixed {moved_count} misplaced IfcAlignment(s) (BSI SPS002)"
        )

    return moved_count


def cleanup_road_part_issues(ifc_file: "ifcopenshell.file") -> int:
    """
    Fix IfcRoadPart entities with incorrect parent or missing ObjectType.

    Per BSI SPS002: IfcRoadPart must be aggregated to IfcRoad (or IfcFacility),
    NOT to IfcAlignment.

    Per BSI OJT001: When PredefinedType is USERDEFINED, ObjectType must be set.

    Args:
        ifc_file: The IFC file to clean up

    Returns:
        Number of issues fixed
    """
    fixed_count = 0

    # Find IfcRoad for re-parenting
    roads = ifc_file.by_type("IfcRoad")
    road = roads[0] if roads else None

    # Log what we're working with
    road_parts = ifc_file.by_type("IfcRoadPart")
    logger.info(f"cleanup_road_part_issues: Found {len(road_parts)} IfcRoadPart(s), road={road is not None}")

    # Debug: Show details of each road part
    for rp in road_parts:
        pt = getattr(rp, 'PredefinedType', 'N/A')
        ot = getattr(rp, 'ObjectType', 'N/A')
        logger.info(f"  IfcRoadPart '{rp.Name}': PredefinedType={pt}, ObjectType={ot}")

    # Valid parent types for IfcRoadPart per BSI SPS002
    valid_parent_types = ("IfcFacility", "IfcFacilityPartCommon", "IfcRoad", "IfcRoadPart", "IfcSpace")

    # Debug: Show ALL aggregation relationships in file (comprehensive diagnostic)
    logger.info("  === ALL IfcRelAggregates in file ===")
    for rel in ifc_file.by_type("IfcRelAggregates"):
        parent_type = rel.RelatingObject.is_a() if rel.RelatingObject else "None"
        parent_name = getattr(rel.RelatingObject, 'Name', 'unnamed') if rel.RelatingObject else "None"
        parent_id = rel.RelatingObject.id() if rel.RelatingObject else 0
        for obj in (rel.RelatedObjects or []):
            child_type = obj.is_a()
            child_name = getattr(obj, 'Name', 'unnamed')
            child_id = obj.id()
            # Flag suspicious parent-child combinations
            flag = ""
            if child_type == "IfcRoadPart" and parent_type == "IfcAlignment":
                flag = " [INVALID - SPS002!]"
            logger.info(f"    #{parent_id} {parent_type} '{parent_name}' -> #{child_id} {child_type} '{child_name}'{flag}")
    logger.info("  === End of IfcRelAggregates ===")

    # Debug: Show IfcRelContainedInSpatialStructure (IfcRoadPart shouldn't appear here)
    logger.info("  === IfcRelContainedInSpatialStructure (checking for IfcRoadPart) ===")
    for rel in ifc_file.by_type("IfcRelContainedInSpatialStructure"):
        structure_type = rel.RelatingStructure.is_a() if rel.RelatingStructure else "None"
        structure_name = getattr(rel.RelatingStructure, 'Name', 'unnamed') if rel.RelatingStructure else "None"
        structure_id = rel.RelatingStructure.id() if rel.RelatingStructure else 0
        for elem in (rel.RelatedElements or []):
            elem_type = elem.is_a()
            elem_name = getattr(elem, 'Name', 'unnamed')
            elem_id = elem.id()
            if elem_type == "IfcRoadPart":
                logger.info(f"    [WARNING] #{elem_id} IfcRoadPart '{elem_name}' CONTAINED IN #{structure_id} {structure_type} '{structure_name}'")
    logger.info("  === End of IfcRelContainedInSpatialStructure ===")

    # Debug: Show aggregation relationships involving IfcRoadPart specifically
    logger.info("  IfcRoadPart aggregation summary:")
    for rel in ifc_file.by_type("IfcRelAggregates"):
        if rel.RelatedObjects:
            for obj in rel.RelatedObjects:
                if obj.is_a("IfcRoadPart"):
                    parent_type = rel.RelatingObject.is_a() if rel.RelatingObject else "None"
                    parent_name = getattr(rel.RelatingObject, 'Name', 'None') if rel.RelatingObject else "None"
                    is_valid = any(rel.RelatingObject.is_a(t) for t in valid_parent_types) if rel.RelatingObject else False
                    status = "OK" if is_valid else "INVALID"
                    logger.info(f"    '{obj.Name}' aggregated to {parent_type} '{parent_name}' [{status}]")

    # Fix IfcRoadParts with INVALID parent (SPS002)
    # Per BSI: IfcRoadPart must be aggregated to IfcFacility, IfcFacilityPartCommon,
    # IfcRoad, IfcRoadPart, or IfcSpace - NOT IfcAlignment or other types
    for rel in list(ifc_file.by_type("IfcRelAggregates")):
        if not rel.RelatingObject:
            continue

        # Check if parent is NOT a valid type for IfcRoadPart
        parent_is_valid = any(rel.RelatingObject.is_a(t) for t in valid_parent_types)

        if not parent_is_valid:
            road_parts_to_move = []
            other_objects = []

            for obj in (rel.RelatedObjects or []):
                if obj.is_a("IfcRoadPart"):
                    road_parts_to_move.append(obj)
                else:
                    other_objects.append(obj)

            if road_parts_to_move:
                old_parent_type = rel.RelatingObject.is_a()
                old_parent_name = getattr(rel.RelatingObject, 'Name', 'unknown')

                # Update relationship to remove road parts
                if other_objects:
                    rel.RelatedObjects = other_objects
                else:
                    ifc_file.remove(rel)

                # Only add to IfcRoad if we have one and not already there
                if road:
                    # Check if already correctly aggregated to road
                    already_in_road = False
                    for existing_rel in ifc_file.by_type("IfcRelAggregates"):
                        if existing_rel.RelatingObject == road:
                            for rp in road_parts_to_move:
                                if rp in (existing_rel.RelatedObjects or []):
                                    already_in_road = True
                                    break

                    if not already_in_road:
                        ifc_file.create_entity(
                            "IfcRelAggregates",
                            GlobalId=ifcopenshell.guid.new(),
                            Name="RoadToRoadPart_Fixed",
                            Description=f"Re-parented from {old_parent_type} to IfcRoad (SPS002)",
                            RelatingObject=road,
                            RelatedObjects=road_parts_to_move
                        )

                for rp in road_parts_to_move:
                    logger.info(
                        f"Removed IfcRoadPart '{rp.Name}' from invalid parent {old_parent_type} '{old_parent_name}' (SPS002)"
                    )
                fixed_count += len(road_parts_to_move)

    # Fix IfcRoadParts with empty ObjectType (OJT001)
    # BSI validator requires ObjectType for ALL IfcRoadParts, not just USERDEFINED
    for road_part in ifc_file.by_type("IfcRoadPart"):
        object_type = getattr(road_part, 'ObjectType', None)

        # If ObjectType is empty, set it based on PredefinedType or Name
        if not object_type:
            predefined_type = getattr(road_part, 'PredefinedType', None)
            name = road_part.Name or "RoadPart"
            # Use PredefinedType as ObjectType if it's a standard type
            if predefined_type and predefined_type not in ('USERDEFINED', 'NOTDEFINED'):
                road_part.ObjectType = predefined_type
            else:
                road_part.ObjectType = f"ROADPART_{name.upper().replace(' ', '_')}"
            logger.info(
                f"Set ObjectType='{road_part.ObjectType}' for IfcRoadPart '{road_part.Name}' (OJT001)"
            )
            fixed_count += 1

    if fixed_count > 0:
        logger.info(f"Fixed {fixed_count} IfcRoadPart issue(s) (SPS002/OJT001)")

    return fixed_count


def cleanup_orphaned_resources(ifc_file: "ifcopenshell.file") -> int:
    """
    Remove resource entities that are not referenced by any rooted entity.

    Per BSI IFC105, resource entities must be directly or indirectly related
    to at least one rooted entity (IfcRoot subclass) instance.

    This function removes orphaned:
    - IfcCartesianPoint
    - IfcDirection
    - IfcVector
    - IfcAxis2Placement2D/3D
    - Other geometric primitives

    Args:
        ifc_file: The IFC file to clean up

    Returns:
        Number of orphaned entities removed
    """
    # CRITICAL FIX (IFC105): Only collect references starting from ROOTED entities
    # Previous implementation collected from ALL entities, missing cascading orphans
    # (e.g., if A -> B -> C and A is orphaned, B and C still appeared "referenced")

    def collect_references_recursive(entity, visited):
        """Recursively collect all entity IDs referenced by this entity."""
        entity_id = entity.id()
        if entity_id in visited:
            return
        visited.add(entity_id)

        for attr in entity:
            # Handle direct entity references
            if hasattr(attr, 'id'):
                collect_references_recursive(attr, visited)
            # Handle lists/tuples of entities
            elif isinstance(attr, (list, tuple)):
                for item in attr:
                    if hasattr(item, 'id'):
                        collect_references_recursive(item, visited)

    # Start from rooted entities only (IfcRoot subclasses)
    reachable_ids = set()
    for entity in ifc_file.by_type("IfcRoot"):
        collect_references_recursive(entity, reachable_ids)

    # Resource types that might be orphaned
    resource_types = [
        "IfcCartesianPoint",
        "IfcDirection",
        "IfcVector",
        "IfcAxis2Placement2D",
        "IfcAxis2Placement3D",
        "IfcLine",
        "IfcCircle",
        "IfcCurveSegment",
        "IfcPolynomialCurve",
        "IfcGradientCurve",
        "IfcCompositeCurve",
        # Profile definitions that might be orphaned
        "IfcArbitraryClosedProfileDef",
        "IfcArbitraryOpenProfileDef",
        "IfcOpenCrossProfileDef",
        "IfcCartesianPointList2D",
        "IfcIndexedPolyCurve",
        "IfcPolyline",
    ]

    removed_count = 0
    for resource_type in resource_types:
        for entity in list(ifc_file.by_type(resource_type)):
            entity_id = entity.id()  # Capture ID before removal
            if entity_id not in reachable_ids:
                try:
                    ifc_file.remove(entity)
                    removed_count += 1
                    logger.debug(
                        f"Removed orphaned {resource_type} #{entity_id}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not remove orphaned {resource_type} #{entity_id}: {e}"
                    )

    if removed_count > 0:
        logger.info(
            f"Cleaned up {removed_count} orphaned resource entities (BSI IFC105)"
        )

    return removed_count


def cleanup_orphaned_gradient_curves(ifc_file: "ifcopenshell.file") -> int:
    """
    Remove IfcGradientCurve and IfcCurveSegment entities not properly linked.

    This is critical for fixing ALS017 errors - orphaned gradient curves from
    previous exports can cause geometric continuity validation failures.

    Args:
        ifc_file: The IFC file to clean up

    Returns:
        Number of orphaned entities removed
    """
    removed_count = 0

    # Find all IfcGradientCurves that are properly linked to ShapeRepresentations
    linked_gradient_curves = set()
    for shape_rep in ifc_file.by_type("IfcShapeRepresentation"):
        for item in shape_rep.Items or []:
            if item.is_a("IfcGradientCurve"):
                linked_gradient_curves.add(item.id())

    # Remove orphaned IfcGradientCurves and their segments
    for gradient_curve in list(ifc_file.by_type("IfcGradientCurve")):
        if gradient_curve.id() not in linked_gradient_curves:
            # Remove all curve segments in this gradient curve
            if hasattr(gradient_curve, 'Segments') and gradient_curve.Segments:
                for curve_seg in list(gradient_curve.Segments):
                    if curve_seg.is_a("IfcCurveSegment"):
                        _remove_curve_segment_deep(ifc_file, curve_seg)
                        removed_count += 1

            # Remove the gradient curve itself
            try:
                ifc_file.remove(gradient_curve)
                removed_count += 1
                logger.debug(f"Removed orphaned IfcGradientCurve #{gradient_curve.id()}")
            except Exception as e:
                logger.warning(f"Failed to remove orphaned IfcGradientCurve: {e}")

    if removed_count > 0:
        logger.info(f"Cleaned up {removed_count} orphaned gradient curve entities (ALS017)")

    return removed_count


def _remove_curve_segment_deep(ifc_file: "ifcopenshell.file", curve_segment) -> None:
    """Remove IfcCurveSegment and all its nested geometry entities."""
    try:
        # Remove Placement
        if hasattr(curve_segment, 'Placement') and curve_segment.Placement:
            placement = curve_segment.Placement
            if hasattr(placement, 'Location') and placement.Location:
                try:
                    ifc_file.remove(placement.Location)
                except Exception:
                    pass
            if hasattr(placement, 'RefDirection') and placement.RefDirection:
                try:
                    ifc_file.remove(placement.RefDirection)
                except Exception:
                    pass
            try:
                ifc_file.remove(placement)
            except Exception:
                pass

        # Remove ParentCurve and its nested geometry
        if hasattr(curve_segment, 'ParentCurve') and curve_segment.ParentCurve:
            parent_curve = curve_segment.ParentCurve
            try:
                # Handle IfcLine
                if parent_curve.is_a("IfcLine"):
                    if hasattr(parent_curve, 'Pnt') and parent_curve.Pnt:
                        ifc_file.remove(parent_curve.Pnt)
                    if hasattr(parent_curve, 'Dir') and parent_curve.Dir:
                        vector = parent_curve.Dir
                        if hasattr(vector, 'Orientation') and vector.Orientation:
                            ifc_file.remove(vector.Orientation)
                        ifc_file.remove(vector)
                # Handle IfcPolynomialCurve
                elif parent_curve.is_a("IfcPolynomialCurve"):
                    if hasattr(parent_curve, 'Position') and parent_curve.Position:
                        pos = parent_curve.Position
                        if hasattr(pos, 'Location') and pos.Location:
                            ifc_file.remove(pos.Location)
                        if hasattr(pos, 'RefDirection') and pos.RefDirection:
                            ifc_file.remove(pos.RefDirection)
                        ifc_file.remove(pos)
                ifc_file.remove(parent_curve)
            except Exception:
                pass

        # Remove the curve segment itself
        ifc_file.remove(curve_segment)
    except Exception as e:
        logger.debug(f"Error in deep curve segment removal: {e}")


def cleanup_alignment_segment_issues(ifc_file: "ifcopenshell.file") -> int:
    """
    Fix IfcAlignmentSegment entities with missing ObjectType.

    Per BSI OJT001: ObjectType must be set for alignment segments.
    This cleans up old segments that were created before we added ObjectType.

    Args:
        ifc_file: The IFC file to clean up

    Returns:
        Number of issues fixed
    """
    fixed_count = 0

    for segment in ifc_file.by_type("IfcAlignmentSegment"):
        object_type = getattr(segment, 'ObjectType', None)

        if not object_type:
            # Determine ObjectType from DesignParameters.PredefinedType
            design_params = getattr(segment, 'DesignParameters', None)
            if design_params:
                predefined_type = getattr(design_params, 'PredefinedType', None)
                if predefined_type:
                    segment.ObjectType = predefined_type
                else:
                    # Fallback based on segment name
                    name = segment.Name or "SEGMENT"
                    if "tangent" in name.lower() or "line" in name.lower():
                        segment.ObjectType = "LINE"
                    elif "curve" in name.lower() or "arc" in name.lower():
                        segment.ObjectType = "CIRCULARARC"
                    elif "endpoint" in name.lower():
                        segment.ObjectType = "ENDPOINT"
                    else:
                        segment.ObjectType = "SEGMENT"
            else:
                segment.ObjectType = "SEGMENT"

            logger.info(
                f"Set ObjectType='{segment.ObjectType}' for IfcAlignmentSegment "
                f"'{segment.Name or segment.id()}' (OJT001)"
            )
            fixed_count += 1

    if fixed_count > 0:
        logger.info(f"Fixed {fixed_count} IfcAlignmentSegment ObjectType issue(s) (OJT001)")

    return fixed_count


def cleanup_course_issues(ifc_file: "ifcopenshell.file") -> int:
    """
    Fix IfcCourse entities with missing ObjectType.

    Per BSI OJT001: ObjectType should be set for IfcCourse entities.
    We set ObjectType for ALL IfcCourse without one (safer than just USERDEFINED).

    Args:
        ifc_file: The IFC file to clean up

    Returns:
        Number of issues fixed
    """
    fixed_count = 0

    courses = ifc_file.by_type("IfcCourse")
    logger.info(f"cleanup_course_issues: Found {len(courses)} IfcCourse(s)")

    for course in courses:
        predefined_type = getattr(course, 'PredefinedType', None)
        object_type = getattr(course, 'ObjectType', None)
        course_id = course.id()

        logger.info(f"  #{course_id} IfcCourse '{course.Name}': PredefinedType={predefined_type}, ObjectType={object_type}")

        # Set ObjectType for ANY IfcCourse without one (BSI may require it broadly)
        if not object_type:
            name = course.Name or "Course"
            # Use PredefinedType if available, otherwise generate descriptive name
            if predefined_type and predefined_type not in ('USERDEFINED', 'NOTDEFINED', None):
                course.ObjectType = predefined_type
            else:
                course.ObjectType = f"PAVEMENT_{name.upper().replace(' ', '_')}"
            logger.info(f"  -> Set ObjectType for #{course_id} IfcCourse '{course.Name}' to '{course.ObjectType}' (OJT001)")
            fixed_count += 1

    if fixed_count > 0:
        logger.info(f"Fixed {fixed_count} IfcCourse ObjectType issue(s) (OJT001)")

    return fixed_count


def nest_objects(
    ifc_file: "ifcopenshell.file",
    parent: "ifcopenshell.entity_instance",
    children: List["ifcopenshell.entity_instance"],
    name: str = "Nesting"
) -> "ifcopenshell.entity_instance":
    """
    Create nesting relationship between objects.

    Args:
        ifc_file: The IFC file
        parent: The parent object
        children: List of child objects
        name: Relationship name

    Returns:
        The IfcRelNests relationship
    """
    try:
        return ifcopenshell.api.nest.assign_object(
            ifc_file,
            relating_object=parent,
            related_objects=children
        )
    except Exception:
        return ifc_file.create_entity(
            "IfcRelNests",
            GlobalId=ifcopenshell.guid.new(),
            Name=name,
            RelatingObject=parent,
            RelatedObjects=children
        )


def aggregate_objects(
    ifc_file: "ifcopenshell.file",
    parent: "ifcopenshell.entity_instance",
    children: List["ifcopenshell.entity_instance"],
    name: str = "Aggregates"
) -> "ifcopenshell.entity_instance":
    """
    Create aggregation relationship between objects.

    Used for spatial hierarchy (e.g., Road contains RoadParts).

    Args:
        ifc_file: The IFC file
        parent: The parent object
        children: List of child objects
        name: Relationship name

    Returns:
        The IfcRelAggregates relationship
    """
    try:
        return ifcopenshell.api.aggregate.assign_object(
            ifc_file,
            relating_object=parent,
            products=children
        )
    except Exception:
        # Manual fallback
        return ifc_file.create_entity(
            "IfcRelAggregates",
            GlobalId=ifcopenshell.guid.new(),
            Name=name,
            RelatingObject=parent,
            RelatedObjects=children
        )


# =============================================================================
# Helper Functions
# =============================================================================

def _create_local_placement(
    ifc_file: "ifcopenshell.file",
    relative_to: Optional["ifcopenshell.entity_instance"] = None,
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0)
) -> "ifcopenshell.entity_instance":
    """Create IfcLocalPlacement with optional relative placement."""
    origin = ifc_file.create_entity(
        "IfcCartesianPoint",
        Coordinates=list(location)
    )

    axis2placement = ifc_file.create_entity(
        "IfcAxis2Placement3D",
        Location=origin
    )

    return ifc_file.create_entity(
        "IfcLocalPlacement",
        PlacementRelTo=relative_to,
        RelativePlacement=axis2placement
    )


def _aggregate_manual(
    ifc_file: "ifcopenshell.file",
    parent: "ifcopenshell.entity_instance",
    child: "ifcopenshell.entity_instance"
) -> "ifcopenshell.entity_instance":
    """Manual aggregation when API is not available."""
    return ifc_file.create_entity(
        "IfcRelAggregates",
        GlobalId=ifcopenshell.guid.new(),
        Name="Aggregates",
        RelatingObject=parent,
        RelatedObjects=[child]
    )


def _add_georeferencing_manual(
    ifc_file: "ifcopenshell.file",
    epsg: int,
    eastings: float,
    northings: float,
    orthogonal_height: float,
    x_axis_abscissa: float,
    x_axis_ordinate: float,
    scale: float
) -> Tuple["ifcopenshell.entity_instance", "ifcopenshell.entity_instance"]:
    """Manual georeferencing creation."""
    # Find geometric context
    contexts = ifc_file.by_type("IfcGeometricRepresentationContext")
    context = contexts[0] if contexts else None

    if not context:
        logger.warning("No geometric context found for georeferencing")
        return None, None

    projected_crs = ifc_file.create_entity(
        "IfcProjectedCRS",
        Name=f"EPSG:{epsg}"
    )

    map_conversion = ifc_file.create_entity(
        "IfcMapConversion",
        SourceCRS=context,
        TargetCRS=projected_crs,
        Eastings=eastings,
        Northings=northings,
        OrthogonalHeight=orthogonal_height,
        XAxisAbscissa=x_axis_abscissa,
        XAxisOrdinate=x_axis_ordinate,
        Scale=scale
    )

    return map_conversion, projected_crs


# =============================================================================
# Utility Functions
# =============================================================================

def get_or_create_road(ifc_file: "ifcopenshell.file") -> "ifcopenshell.entity_instance":
    """
    Get existing IfcRoad or create the full hierarchy.

    Creates IfcProject → IfcSite → IfcRoad if needed.

    Args:
        ifc_file: The IFC file

    Returns:
        The IfcRoad entity
    """
    roads = ifc_file.by_type("IfcRoad")
    if roads:
        return roads[0]

    # Create hierarchy
    project = create_project(ifc_file)
    site = create_site(ifc_file, project)
    road = create_road(ifc_file, site)

    return road


def is_api_available() -> bool:
    """Check if ifcopenshell.api is available."""
    return HAS_IFCOPENSHELL


def is_alignment_api_available() -> bool:
    """Check if ifcopenshell.api.alignment is available."""
    return HAS_ALIGNMENT_API


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Project & Spatial
    "create_project",
    "create_site",
    "create_road",
    "get_or_create_road",
    # Alignment
    "create_alignment",
    "create_alignment_by_pi",
    "add_horizontal_layout",
    "add_vertical_layout",
    # Georeferencing
    "add_georeferencing",
    "edit_georeferencing",
    # Relationships
    "contain_in_spatial",
    "nest_objects",
    "aggregate_objects",
    # Cleanup & Validation
    "cleanup_misplaced_alignment_segments",
    "cleanup_misplaced_alignments",
    "cleanup_road_part_issues",
    "cleanup_orphaned_resources",
    "cleanup_orphaned_gradient_curves",
    "cleanup_alignment_segment_issues",
    "cleanup_course_issues",
    # Utilities
    "is_api_available",
    "is_alignment_api_available",
]
