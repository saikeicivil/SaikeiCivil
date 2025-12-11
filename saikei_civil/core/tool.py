# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under the GNU General Public License v3
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
Interface definitions for Saikei Civil tools.

This module defines abstract interfaces that separate business logic from
Blender-specific implementations, following Bonsai's three-layer architecture:

    Layer 1: Core (this module) - Pure Python interfaces and business logic
    Layer 2: Tool (saikei_civil.tool) - Blender-specific implementations
    Layer 3: BIM Modules - UI, operators, and properties

Usage:
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        import saikei_civil.tool as tool

    def my_function(ifc: type[tool.Ifc], blender: type[tool.Blender]):
        file = ifc.get()
        ifc.run("alignment.create", name="My Alignment")
"""
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Tuple
import abc

if TYPE_CHECKING:
    import bpy
    import ifcopenshell


def interface(cls):
    """
    Decorator that converts all public methods to @classmethod @abstractmethod.

    This enables the dependency injection pattern where tool classes are passed
    as types (not instances) to core functions, and all methods are called as
    class methods.

    Example:
        @interface
        class Ifc:
            def get(cls): pass  # Becomes @classmethod @abstractmethod

        # In tool implementation:
        class Ifc(core.tool.Ifc):
            @classmethod
            def get(cls):
                return actual_implementation()

        # In core function:
        def do_something(ifc: type[tool.Ifc]):
            file = ifc.get()  # Called on the class, not an instance
    """
    for name, method in list(cls.__dict__.items()):
        if callable(method) and not name.startswith('_'):
            # Wrap with classmethod and abstractmethod
            setattr(cls, name, classmethod(abc.abstractmethod(method)))
    cls.__original_qualname__ = cls.__qualname__
    return cls


# =============================================================================
# Core Interfaces
# =============================================================================

@interface
class Ifc:
    """
    Interface for IFC file operations.

    This is the primary interface for interacting with the IFC file.
    All IFC modifications should go through this interface.
    """

    def get(cls) -> Optional["ifcopenshell.file"]:
        """
        Get the current IFC file.

        Returns:
            The active IFC file, or None if no file is loaded.
        """
        pass

    def set(cls, ifc_file: "ifcopenshell.file") -> None:
        """
        Set the current IFC file.

        Args:
            ifc_file: The IFC file to set as active.
        """
        pass

    def run(cls, command: str, **kwargs) -> Any:
        """
        Run an ifcopenshell.api command.

        This is the primary method for executing IFC operations. Commands
        are specified as "module.function" strings that map to
        ifcopenshell.api.module.function().

        Args:
            command: API command in format "module.function"
                     (e.g., "alignment.create", "georeference.add_georeferencing")
            **kwargs: Arguments to pass to the API function

        Returns:
            The result of the API call

        Raises:
            RuntimeError: If no IFC file is loaded
            ValueError: If the command format is invalid

        Example:
            ifc.run("alignment.create", name="Main Road")
            ifc.run("georeference.edit_georeferencing", projected_crs={...})
        """
        pass

    def get_entity(cls, obj: "bpy.types.Object") -> Optional["ifcopenshell.entity_instance"]:
        """
        Get the IFC entity linked to a Blender object.

        Args:
            obj: The Blender object

        Returns:
            The linked IFC entity, or None if not linked
        """
        pass

    def get_object(cls, entity: "ifcopenshell.entity_instance") -> Optional["bpy.types.Object"]:
        """
        Get the Blender object linked to an IFC entity.

        Args:
            entity: The IFC entity

        Returns:
            The linked Blender object, or None if not found
        """
        pass

    def link(cls, entity: "ifcopenshell.entity_instance", obj: "bpy.types.Object") -> None:
        """
        Link an IFC entity to a Blender object.

        This creates the bidirectional mapping that allows navigation
        between IFC data and Blender visualization.

        Args:
            entity: The IFC entity
            obj: The Blender object to link
        """
        pass

    def unlink(cls, obj: "bpy.types.Object") -> None:
        """
        Remove IFC linking from a Blender object.

        Args:
            obj: The Blender object to unlink
        """
        pass

    def get_schema(cls) -> str:
        """
        Get the IFC schema version of the current file.

        Returns:
            Schema identifier (e.g., "IFC4X3")
        """
        pass

    def by_type(cls, ifc_class: str) -> List["ifcopenshell.entity_instance"]:
        """
        Get all entities of a given IFC class.

        Args:
            ifc_class: The IFC class name (e.g., "IfcAlignment", "IfcRoad")

        Returns:
            List of matching entities
        """
        pass

    def by_id(cls, entity_id: int) -> Optional["ifcopenshell.entity_instance"]:
        """
        Get an entity by its ID.

        Args:
            entity_id: The entity's numeric ID

        Returns:
            The entity, or None if not found
        """
        pass


@interface
class Blender:
    """
    Interface for Blender-specific operations.

    Provides utilities for working with Blender objects, collections,
    and the viewport.
    """

    def create_object(cls, name: str, data: Any = None) -> "bpy.types.Object":
        """
        Create a new Blender object.

        Args:
            name: Object name
            data: Optional object data (mesh, curve, etc.)

        Returns:
            The created object (already linked to scene)
        """
        pass

    def get_active_object(cls) -> Optional["bpy.types.Object"]:
        """Get the active (selected) object."""
        pass

    def set_active_object(cls, obj: "bpy.types.Object") -> None:
        """Set the active object."""
        pass

    def get_selected_objects(cls) -> List["bpy.types.Object"]:
        """Get all selected objects."""
        pass

    def select_object(cls, obj: "bpy.types.Object", add: bool = False) -> None:
        """
        Select an object.

        Args:
            obj: Object to select
            add: If True, add to selection; if False, replace selection
        """
        pass

    def deselect_all(cls) -> None:
        """Deselect all objects."""
        pass

    def delete_object(cls, obj: "bpy.types.Object") -> None:
        """Delete a Blender object."""
        pass

    def update_viewport(cls) -> None:
        """Force a viewport update."""
        pass

    def get_collection(cls, name: str, create: bool = True) -> Optional["bpy.types.Collection"]:
        """
        Get or create a collection.

        Args:
            name: Collection name
            create: If True, create collection if it doesn't exist

        Returns:
            The collection, or None if not found and create=False
        """
        pass

    def link_to_collection(cls, obj: "bpy.types.Object", collection: "bpy.types.Collection") -> None:
        """Link an object to a collection."""
        pass

    def create_curve(cls, name: str) -> "bpy.types.Object":
        """
        Create a new curve object.

        Args:
            name: Curve name

        Returns:
            The created curve object
        """
        pass

    def create_empty(cls, name: str, empty_type: str = 'PLAIN_AXES') -> "bpy.types.Object":
        """
        Create a new empty object.

        Args:
            name: Empty name
            empty_type: Type of empty ('PLAIN_AXES', 'ARROWS', 'SPHERE', etc.)

        Returns:
            The created empty object
        """
        pass


@interface
class Alignment:
    """
    Interface for horizontal alignment operations.

    Handles creation, modification, and querying of horizontal alignments
    using the PI (Point of Intersection) method.
    """

    def create(cls, name: str, pis: List[Dict]) -> "ifcopenshell.entity_instance":
        """
        Create a new horizontal alignment.

        Args:
            name: Alignment name
            pis: List of PI dictionaries with keys:
                - x: X coordinate
                - y: Y coordinate
                - radius: Curve radius (0 for tangent points)
                - spiral_in: (optional) Spiral length into curve
                - spiral_out: (optional) Spiral length out of curve

        Returns:
            The created IfcAlignment entity
        """
        pass

    def get_pis(cls, alignment: "ifcopenshell.entity_instance") -> List[Dict]:
        """
        Get PI data from an alignment.

        Args:
            alignment: The IfcAlignment entity

        Returns:
            List of PI dictionaries
        """
        pass

    def set_pis(cls, alignment: "ifcopenshell.entity_instance", pis: List[Dict]) -> None:
        """
        Update alignment geometry from PI data.

        Args:
            alignment: The IfcAlignment entity
            pis: Updated PI data
        """
        pass

    def get_horizontal_segments(cls, alignment: "ifcopenshell.entity_instance") -> List[Dict]:
        """
        Get computed horizontal segments.

        Args:
            alignment: The IfcAlignment entity

        Returns:
            List of segment dictionaries with type, geometry, etc.
        """
        pass

    def get_length(cls, alignment: "ifcopenshell.entity_instance") -> float:
        """
        Get total alignment length.

        Args:
            alignment: The IfcAlignment entity

        Returns:
            Total length in model units
        """
        pass

    def get_point_at_station(
        cls,
        alignment: "ifcopenshell.entity_instance",
        station: float
    ) -> Optional[Dict]:
        """
        Get coordinates and direction at a station.

        Args:
            alignment: The IfcAlignment entity
            station: Station value

        Returns:
            Dictionary with x, y, z, direction (radians), or None if invalid
        """
        pass

    def get_station_at_point(
        cls,
        alignment: "ifcopenshell.entity_instance",
        point: Tuple[float, float]
    ) -> Optional[float]:
        """
        Get station value at the closest point on alignment.

        Args:
            alignment: The IfcAlignment entity
            point: (x, y) coordinates

        Returns:
            Station value, or None if point is too far from alignment
        """
        pass

    def update_visualization(cls, alignment: "ifcopenshell.entity_instance") -> None:
        """
        Update Blender visualization from IFC alignment data.

        This regenerates the curve geometry and PI markers from the
        current IFC data.

        Args:
            alignment: The IfcAlignment entity
        """
        pass


@interface
class VerticalAlignment:
    """
    Interface for vertical alignment operations.

    Handles creation, modification, and querying of vertical alignments
    using the PVI (Point of Vertical Intersection) method.
    """

    def create(
        cls,
        horizontal: "ifcopenshell.entity_instance",
        pvis: List[Dict]
    ) -> "ifcopenshell.entity_instance":
        """
        Create a vertical alignment for a horizontal alignment.

        Args:
            horizontal: The parent IfcAlignment entity
            pvis: List of PVI dictionaries with keys:
                - station: Station value
                - elevation: Elevation value
                - curve_length: Vertical curve length (0 for no curve)

        Returns:
            The IfcAlignmentVertical entity
        """
        pass

    def get_pvis(cls, alignment: "ifcopenshell.entity_instance") -> List[Dict]:
        """
        Get PVI data from alignment.

        Args:
            alignment: The IfcAlignment entity (parent of vertical)

        Returns:
            List of PVI dictionaries
        """
        pass

    def set_pvis(
        cls,
        alignment: "ifcopenshell.entity_instance",
        pvis: List[Dict]
    ) -> None:
        """
        Update vertical alignment geometry from PVI data.

        Args:
            alignment: The IfcAlignment entity
            pvis: Updated PVI data
        """
        pass

    def get_vertical_segments(cls, alignment: "ifcopenshell.entity_instance") -> List[Dict]:
        """
        Get computed vertical segments.

        Args:
            alignment: The IfcAlignment entity

        Returns:
            List of segment dictionaries
        """
        pass

    def get_elevation_at_station(
        cls,
        alignment: "ifcopenshell.entity_instance",
        station: float
    ) -> Optional[float]:
        """
        Get elevation at a station.

        Args:
            alignment: The IfcAlignment entity
            station: Station value

        Returns:
            Elevation, or None if station is out of range
        """
        pass

    def get_grade_at_station(
        cls,
        alignment: "ifcopenshell.entity_instance",
        station: float
    ) -> Optional[float]:
        """
        Get grade (slope) at a station.

        Args:
            alignment: The IfcAlignment entity
            station: Station value

        Returns:
            Grade as decimal (e.g., 0.02 for 2%), or None if out of range
        """
        pass

    def update_visualization(cls, alignment: "ifcopenshell.entity_instance") -> None:
        """Update Blender visualization for vertical alignment."""
        pass


@interface
class Georeference:
    """
    Interface for georeferencing operations.

    Handles coordinate reference system (CRS) setup and coordinate
    transformations between local and global coordinates.
    """

    def add_georeferencing(cls) -> None:
        """
        Add georeferencing entities to the IFC file.

        Creates IfcMapConversion and IfcProjectedCRS if they don't exist.
        """
        pass

    def remove_georeferencing(cls) -> None:
        """Remove georeferencing from the IFC file."""
        pass

    def has_georeferencing(cls) -> bool:
        """Check if the file has georeferencing set up."""
        pass

    def get_crs(cls) -> Optional[Dict]:
        """
        Get current CRS information.

        Returns:
            Dictionary with EPSG code, name, description, or None
        """
        pass

    def set_crs(cls, epsg_code: int) -> None:
        """
        Set the coordinate reference system.

        Args:
            epsg_code: EPSG code (e.g., 32611 for UTM Zone 11N)
        """
        pass

    def get_map_conversion(cls) -> Optional[Dict]:
        """
        Get map conversion parameters.

        Returns:
            Dictionary with eastings, northings, height, rotation, scale
        """
        pass

    def set_map_conversion(
        cls,
        eastings: float,
        northings: float,
        height: float = 0.0,
        x_axis_abscissa: float = 1.0,
        x_axis_ordinate: float = 0.0,
        scale: float = 1.0
    ) -> None:
        """
        Set map conversion parameters.

        Args:
            eastings: Easting of local origin in CRS
            northings: Northing of local origin in CRS
            height: Orthogonal height of local origin
            x_axis_abscissa: X component of local X axis direction
            x_axis_ordinate: Y component of local X axis direction
            scale: Scale factor
        """
        pass

    def transform_to_global(cls, local_coords: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Transform local coordinates to global (CRS) coordinates.

        Args:
            local_coords: (x, y, z) in local coordinates

        Returns:
            (easting, northing, height) in global coordinates
        """
        pass

    def transform_to_local(cls, global_coords: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Transform global (CRS) coordinates to local.

        Args:
            global_coords: (easting, northing, height) in CRS

        Returns:
            (x, y, z) in local coordinates
        """
        pass


@interface
class CrossSection:
    """
    Interface for cross-section operations.

    Handles road assembly creation and cross-section profile generation.
    """

    def create_assembly(cls, name: str) -> Any:
        """
        Create a new road assembly.

        Args:
            name: Assembly name

        Returns:
            The assembly object
        """
        pass

    def get_assembly(cls, name: str) -> Optional[Any]:
        """
        Get an existing assembly by name.

        Args:
            name: Assembly name

        Returns:
            The assembly, or None if not found
        """
        pass

    def add_component(
        cls,
        assembly: Any,
        component_type: str,
        side: str = "RIGHT",
        **params
    ) -> Any:
        """
        Add a component to an assembly.

        Args:
            assembly: The road assembly
            component_type: Type of component ("LANE", "SHOULDER", "CURB", etc.)
            side: "LEFT", "RIGHT", or "CENTER"
            **params: Component-specific parameters (width, slope, etc.)

        Returns:
            The created component
        """
        pass

    def remove_component(cls, assembly: Any, component: Any) -> None:
        """Remove a component from an assembly."""
        pass

    def get_components(cls, assembly: Any) -> List[Any]:
        """Get all components in an assembly."""
        pass

    def get_profile_at_station(
        cls,
        assembly: Any,
        station: float,
        alignment: "ifcopenshell.entity_instance" = None
    ) -> List[Tuple[float, float]]:
        """
        Get cross-section profile points at a station.

        Args:
            assembly: The road assembly
            station: Station value
            alignment: Optional alignment for superelevation, etc.

        Returns:
            List of (offset, elevation) tuples from centerline
        """
        pass

    def apply_template(cls, assembly: Any, template_name: str) -> None:
        """
        Apply a standard template to an assembly.

        Args:
            assembly: The road assembly
            template_name: Name of template (e.g., "AASHTO_2LANE_RURAL")
        """
        pass


@interface
class Corridor:
    """
    Interface for corridor operations.

    Handles 3D corridor generation from alignments and cross-sections.
    """

    def create(
        cls,
        name: str,
        alignment: "ifcopenshell.entity_instance",
        assembly: Any,
        start_station: float,
        end_station: float,
        interval: float = 10.0
    ) -> Any:
        """
        Create a corridor from alignment and assembly.

        Args:
            name: Corridor name
            alignment: The IfcAlignment entity
            assembly: The road assembly
            start_station: Starting station
            end_station: Ending station
            interval: Sampling interval for cross-sections

        Returns:
            The corridor object
        """
        pass

    def get_stations(cls, corridor: Any) -> List[float]:
        """Get list of stations where cross-sections are placed."""
        pass

    def add_station(cls, corridor: Any, station: float) -> None:
        """Add a cross-section at a specific station."""
        pass

    def remove_station(cls, corridor: Any, station: float) -> None:
        """Remove a cross-section at a specific station."""
        pass

    def generate_mesh(cls, corridor: Any) -> "bpy.types.Object":
        """
        Generate 3D mesh geometry for the corridor.

        Args:
            corridor: The corridor object

        Returns:
            Blender mesh object representing the corridor surface
        """
        pass

    def update_mesh(cls, corridor: Any) -> None:
        """
        Update existing mesh after corridor changes.

        Args:
            corridor: The corridor object
        """
        pass

    def export_to_ifc(cls, corridor: Any) -> "ifcopenshell.entity_instance":
        """
        Export corridor to IFC entities.

        Args:
            corridor: The corridor object

        Returns:
            The IfcSectionedSolidHorizontal or equivalent entity
        """
        pass


# =============================================================================
# Utility Interfaces
# =============================================================================

@interface
class Spatial:
    """
    Interface for IFC spatial structure operations.

    Handles the spatial hierarchy: Project > Site > Road > etc.
    """

    def get_project(cls) -> Optional["ifcopenshell.entity_instance"]:
        """Get the IfcProject entity."""
        pass

    def get_site(cls) -> Optional["ifcopenshell.entity_instance"]:
        """Get the IfcSite entity."""
        pass

    def get_road(cls) -> Optional["ifcopenshell.entity_instance"]:
        """Get the IfcRoad entity."""
        pass

    def ensure_spatial_structure(cls) -> Tuple[
        "ifcopenshell.entity_instance",
        "ifcopenshell.entity_instance",
        "ifcopenshell.entity_instance"
    ]:
        """
        Ensure the spatial structure exists (Project > Site > Road).

        Creates missing entities as needed.

        Returns:
            Tuple of (project, site, road) entities
        """
        pass

    def assign_to_road(cls, entity: "ifcopenshell.entity_instance") -> None:
        """
        Assign an entity to the road container.

        Args:
            entity: Entity to assign (e.g., IfcAlignment)
        """
        pass


@interface
class Visualizer:
    """
    Interface for visualization operations.

    Handles creating and updating Blender objects from IFC data.
    """

    def create_alignment_curve(
        cls,
        alignment: "ifcopenshell.entity_instance",
        resolution: int = 100
    ) -> "bpy.types.Object":
        """
        Create a Blender curve from alignment data.

        Args:
            alignment: The IfcAlignment entity
            resolution: Points per curve segment

        Returns:
            The curve object
        """
        pass

    def create_pi_markers(
        cls,
        alignment: "ifcopenshell.entity_instance"
    ) -> List["bpy.types.Object"]:
        """
        Create PI marker empties for an alignment.

        Args:
            alignment: The IfcAlignment entity

        Returns:
            List of empty objects representing PIs
        """
        pass

    def update_from_ifc(cls, entity: "ifcopenshell.entity_instance") -> None:
        """
        Update visualization from IFC entity data.

        Args:
            entity: The IFC entity to visualize
        """
        pass

    def highlight_entity(cls, entity: "ifcopenshell.entity_instance") -> None:
        """
        Highlight an entity in the viewport.

        Args:
            entity: The entity to highlight
        """
        pass