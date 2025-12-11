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
import logging

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

logger = logging.getLogger(__name__)


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

    site = ifc_file.create_entity(
        "IfcSite",
        GlobalId=ifcopenshell.guid.new(),
        Name=name,
        Description=description,
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

    road = ifc_file.create_entity(
        "IfcRoad",
        GlobalId=ifcopenshell.guid.new(),
        Name=name,
        Description=description,
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
) -> "ifcopenshell.entity_instance":
    """
    Contain an element in a spatial structure.

    Args:
        ifc_file: The IFC file
        element: The element to contain
        container: The spatial container (IfcRoad, IfcSite, etc.)

    Returns:
        The IfcRelContainedInSpatialStructure relationship
    """
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
    # Utilities
    "is_api_available",
    "is_alignment_api_available",
]
