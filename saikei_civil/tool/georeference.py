# ============================================================================
# Saikei Civil - Native IFC for Horizontal Construction
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# Licensed under Apache License 2.0
# https://github.com/saikeicivil/SaikeiCivil
# ============================================================================
"""
Georeference tool implementation - Blender-specific georeferencing operations.

This tool wraps the core NativeIfcGeoreferencing class and provides the standard
interface for georeferencing operations. It also integrates with Blender's scene
properties for UI-driven configuration.

Usage:
    from saikei_civil.tool import Georeference

    # Check if georeferencing is set up
    if Georeference.has_georeferencing():
        crs_info = Georeference.get_crs()
        print(f"Using EPSG:{crs_info['epsg_code']}")

    # Set up georeferencing
    Georeference.set_crs(26910)  # NAD83 / UTM zone 10N
    Georeference.set_map_conversion(
        eastings=551000.0,
        northings=4182000.0,
        height=50.0
    )

    # Transform coordinates
    global_coords = Georeference.transform_to_global((100, 200, 0))
"""
from typing import TYPE_CHECKING, Optional, Dict, Tuple

if TYPE_CHECKING:
    import ifcopenshell

# Import will fail if ifcopenshell not installed - that's expected
try:
    import ifcopenshell
    HAS_IFCOPENSHELL = True
except ImportError:
    HAS_IFCOPENSHELL = False

from ..core import tool as core_tool


class Georeference(core_tool.Georeference):
    """
    Blender-specific georeferencing operations.

    This class wraps the core NativeIfcGeoreferencing and provides the
    standard interface for all georeferencing operations in Saikei Civil.
    """

    @classmethod
    def _get_georef_manager(cls):
        """Get or create the georeferencing manager for the current IFC file."""
        from ..core.ifc_manager import NativeIfcManager
        from ..core.native_ifc_georeferencing import NativeIfcGeoreferencing

        ifc = NativeIfcManager.get_file()
        if ifc is None:
            return None

        return NativeIfcGeoreferencing(ifc)

    @classmethod
    def add_georeferencing(cls) -> None:
        """
        Add georeferencing entities to the IFC file.

        Creates IfcMapConversion and IfcProjectedCRS if they don't exist.
        Uses default values that can be configured later.
        """
        if not HAS_IFCOPENSHELL:
            raise RuntimeError("ifcopenshell not installed")

        from ..core.ifc_manager import NativeIfcManager
        from ..core import ifc_api

        ifc = NativeIfcManager.get_file()
        if ifc is None:
            raise RuntimeError("No IFC file loaded")

        # Use ifc_api wrapper which handles the georeferencing creation
        ifc_api.add_georeferencing(ifc, epsg=4326)  # Default to WGS84

    @classmethod
    def remove_georeferencing(cls) -> None:
        """Remove georeferencing from the IFC file."""
        if not HAS_IFCOPENSHELL:
            return

        from ..core.ifc_manager import NativeIfcManager

        ifc = NativeIfcManager.get_file()
        if ifc is None:
            return

        # Remove IfcMapConversion and IfcProjectedCRS
        for entity in ifc.by_type("IfcMapConversion"):
            ifc.remove(entity)

        for entity in ifc.by_type("IfcProjectedCRS"):
            ifc.remove(entity)

    @classmethod
    def has_georeferencing(cls) -> bool:
        """Check if the file has georeferencing set up."""
        if not HAS_IFCOPENSHELL:
            return False

        from ..core.ifc_manager import NativeIfcManager

        ifc = NativeIfcManager.get_file()
        if ifc is None:
            return False

        map_conversion = ifc.by_type("IfcMapConversion")
        projected_crs = ifc.by_type("IfcProjectedCRS")

        return bool(map_conversion and projected_crs)

    @classmethod
    def get_crs(cls) -> Optional[Dict]:
        """
        Get current CRS information.

        Returns:
            Dictionary with EPSG code, name, description, or None
        """
        if not HAS_IFCOPENSHELL:
            return None

        manager = cls._get_georef_manager()
        if manager is None:
            return None

        georef = manager.get_georeferencing()
        if georef is None:
            return None

        return {
            'epsg_code': georef.get('epsg_code'),
            'name': georef.get('crs_name'),
            'unit': georef.get('unit', 'METRE'),
        }

    @classmethod
    def set_crs(cls, epsg_code: int) -> None:
        """
        Set the coordinate reference system.

        Args:
            epsg_code: EPSG code (e.g., 32611 for UTM Zone 11N)
        """
        if not HAS_IFCOPENSHELL:
            raise RuntimeError("ifcopenshell not installed")

        manager = cls._get_georef_manager()
        if manager is None:
            raise RuntimeError("No IFC file loaded")

        # Get existing conversion parameters or defaults
        existing = manager.get_georeferencing()
        if existing:
            false_origin = existing.get('false_origin', (0.0, 0.0, 0.0))
            scale = existing.get('scale', 1.0)
            rotation = existing.get('rotation', 0.0)
        else:
            false_origin = (0.0, 0.0, 0.0)
            scale = 1.0
            rotation = 0.0

        # Set up with new EPSG code
        manager.setup_georeferencing(
            epsg_code=epsg_code,
            false_origin=false_origin,
            scale=scale,
            rotation=rotation
        )

    @classmethod
    def get_map_conversion(cls) -> Optional[Dict]:
        """
        Get map conversion parameters.

        Returns:
            Dictionary with eastings, northings, height, rotation, scale
        """
        if not HAS_IFCOPENSHELL:
            return None

        manager = cls._get_georef_manager()
        if manager is None:
            return None

        georef = manager.get_georeferencing()
        if georef is None:
            return None

        false_origin = georef.get('false_origin', (0.0, 0.0, 0.0))

        return {
            'eastings': false_origin[0],
            'northings': false_origin[1],
            'height': false_origin[2],
            'rotation': georef.get('rotation', 0.0),
            'scale': georef.get('scale', 1.0),
        }

    @classmethod
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
        if not HAS_IFCOPENSHELL:
            raise RuntimeError("ifcopenshell not installed")

        from ..core.ifc_manager import NativeIfcManager

        ifc = NativeIfcManager.get_file()
        if ifc is None:
            raise RuntimeError("No IFC file loaded")

        # Get existing map conversion or create new
        map_conversions = ifc.by_type("IfcMapConversion")
        if map_conversions:
            conversion = map_conversions[0]
            conversion.Eastings = eastings
            conversion.Northings = northings
            conversion.OrthogonalHeight = height
            conversion.XAxisAbscissa = x_axis_abscissa
            conversion.XAxisOrdinate = x_axis_ordinate
            conversion.Scale = scale if scale != 1.0 else None
        else:
            # Need to create full georeferencing first
            raise RuntimeError(
                "No georeferencing exists. Call add_georeferencing() first."
            )

    @classmethod
    def transform_to_global(
        cls,
        local_coords: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """
        Transform local coordinates to global (CRS) coordinates.

        Args:
            local_coords: (x, y, z) in local coordinates

        Returns:
            (easting, northing, height) in global coordinates
        """
        if not HAS_IFCOPENSHELL:
            return local_coords

        manager = cls._get_georef_manager()
        if manager is None:
            return local_coords

        try:
            return manager.local_to_map(local_coords)
        except ValueError:
            # No georeferencing set up, return as-is
            return local_coords

    @classmethod
    def transform_to_local(
        cls,
        global_coords: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """
        Transform global (CRS) coordinates to local.

        Args:
            global_coords: (easting, northing, height) in CRS

        Returns:
            (x, y, z) in local coordinates
        """
        if not HAS_IFCOPENSHELL:
            return global_coords

        manager = cls._get_georef_manager()
        if manager is None:
            return global_coords

        try:
            return manager.map_to_local(global_coords)
        except ValueError:
            # No georeferencing set up, return as-is
            return global_coords

    # =========================================================================
    # Extended Methods (not in core interface)
    # =========================================================================

    @classmethod
    def setup_georeferencing(
        cls,
        epsg_code: int,
        eastings: float,
        northings: float,
        height: float = 0.0,
        scale: float = 1.0,
        rotation: float = 0.0,
        name: str = "Project Site"
    ) -> None:
        """
        Set up complete georeferencing in one call.

        This is a convenience method that sets up both the CRS and
        map conversion in a single operation.

        Args:
            epsg_code: EPSG code for the CRS
            eastings: Easting of local origin
            northings: Northing of local origin
            height: Elevation of local origin
            scale: Scale factor (default 1.0)
            rotation: Rotation in degrees from map north
            name: Name for the georeferencing context
        """
        if not HAS_IFCOPENSHELL:
            raise RuntimeError("ifcopenshell not installed")

        manager = cls._get_georef_manager()
        if manager is None:
            raise RuntimeError("No IFC file loaded")

        manager.setup_georeferencing(
            epsg_code=epsg_code,
            false_origin=(eastings, northings, height),
            name=name,
            scale=scale,
            rotation=rotation
        )

    @classmethod
    def validate(cls) -> Dict:
        """
        Validate current georeferencing setup.

        Returns:
            Dictionary with 'valid', 'warnings', 'errors' keys
        """
        if not HAS_IFCOPENSHELL:
            return {
                'valid': False,
                'warnings': [],
                'errors': ['ifcopenshell not installed']
            }

        from ..core.ifc_manager import NativeIfcManager
        from ..core.native_ifc_georeferencing import validate_georeferencing

        ifc = NativeIfcManager.get_file()
        if ifc is None:
            return {
                'valid': False,
                'warnings': [],
                'errors': ['No IFC file loaded']
            }

        return validate_georeferencing(ifc)


__all__ = ["Georeference"]
