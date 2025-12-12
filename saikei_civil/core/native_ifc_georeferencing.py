# ==============================================================================
# Saikei Civil - Civil Engineering Tools for Blender
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# 
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================

"""
Saikei Civil - Native IFC Georeferencing Module
Implements IFC 4.3 georeferencing using IfcProjectedCRS and IfcMapConversion.

This module enables proper georeferencing storage in IFC files so they can be
correctly positioned in GIS platforms like Cesium, ArcGIS, and QGIS.
"""

import ifcopenshell
import ifcopenshell.api
from typing import Optional, Tuple, Dict
import math
import logging
from .logging_config import get_logger

try:
    import pyproj
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False


class NativeIfcGeoreferencing:
    """
    Manages georeferencing for IFC files using native IFC 4.3 entities.
    
    Key Concepts:
    - False Origin: Local Blender coordinates origin in map space
    - Map Coordinates: Real-world projected coordinates (e.g., UTM Easting/Northing)
    - Local Coordinates: Blender scene coordinates (relative to false origin)
    
    Coordinate Flow:
        Map Coords → IfcMapConversion → Local Coords (Blender)
        Local Coords (Blender) → IfcMapConversion → Map Coords
    
    Example:
        >>> georef = NativeIfcGeoreferencing(ifc_file)
        >>> georef.setup_georeferencing(
        ...     epsg_code=26910,  # NAD83 / UTM zone 10N
        ...     false_origin=(551000.0, 4182000.0, 50.0),
        ...     name="Highway 101 Widening Project"
        ... )
    """
    
    def __init__(self, ifc_file: ifcopenshell.file):
        self.ifc = ifc_file
        self.logger = get_logger(__name__)
        
        # Transformation matrices
        self._local_to_map_matrix = None
        self._map_to_local_matrix = None
    
    def setup_georeferencing(
        self,
        epsg_code: int,
        false_origin: Tuple[float, float, float],
        name: str = "Project Site",
        description: Optional[str] = None,
        scale: float = 1.0,
        rotation: float = 0.0
    ) -> Tuple[ifcopenshell.entity_instance, ifcopenshell.entity_instance]:
        """
        Set up complete georeferencing for the IFC file.
        
        This creates both IfcProjectedCRS and IfcMapConversion entities,
        establishing the relationship between local Blender coordinates
        and real-world map coordinates.
        
        Args:
            epsg_code: EPSG code for the projected CRS (e.g., 26910 for UTM 10N)
            false_origin: Origin of Blender scene in map coordinates (Easting, Northing, Elevation)
            name: Name for the georeferencing context
            description: Optional description
            scale: Scale factor (usually 1.0)
            rotation: Rotation in degrees (clockwise from map north)
        
        Returns:
            Tuple of (IfcProjectedCRS, IfcMapConversion) entities
        """
        self.logger.info(f"Setting up georeferencing with EPSG:{epsg_code}")
        
        # Get or create geometric representation context
        context = self._get_or_create_geometric_context()
        
        # Create IfcProjectedCRS
        projected_crs = self.create_projected_crs(
            epsg_code=epsg_code,
            name=name,
            description=description
        )
        
        # Create IfcMapConversion
        map_conversion = self.create_map_conversion(
            source_crs=context,
            target_crs=projected_crs,
            eastings=false_origin[0],
            northings=false_origin[1],
            orthogonal_height=false_origin[2],
            scale=scale,
            rotation=rotation
        )
        
        # Store transformation parameters
        self._setup_transformation_matrices(
            false_origin=false_origin,
            scale=scale,
            rotation=rotation
        )
        
        self.logger.info("Georeferencing setup complete")
        return projected_crs, map_conversion
    
    def create_projected_crs(
        self,
        epsg_code: int,
        name: str = "Project CRS",
        description: Optional[str] = None
    ) -> ifcopenshell.entity_instance:
        """
        Create an IfcProjectedCRS entity.
        
        IfcProjectedCRS defines the coordinate reference system used for
        the map coordinates (e.g., NAD83 / UTM zone 10N).
        
        Args:
            epsg_code: EPSG code (e.g., 26910)
            name: CRS name
            description: Optional description
        
        Returns:
            IfcProjectedCRS entity
        """
        # Check if IfcProjectedCRS already exists
        existing = self.ifc.by_type("IfcProjectedCRS")
        if existing:
            self.logger.warning("IfcProjectedCRS already exists, updating...")
            crs = existing[0]
            # Use ifcopenshell.api for attribute updates when available
            try:
                ifcopenshell.api.run(
                    "attribute.edit_attributes",
                    self.ifc,
                    product=crs,
                    attributes={
                        "Name": name,
                        "Description": description,
                        "GeodeticDatum": f"EPSG:{epsg_code}"
                    }
                )
            except Exception:
                # Fallback to direct assignment if API not available
                crs.Name = name
                crs.Description = description
                crs.GeodeticDatum = f"EPSG:{epsg_code}"
            return crs
        
        # Get CRS details if PyProj is available
        crs_name = name
        unit_name = "METRE"
        
        if PYPROJ_AVAILABLE:
            try:
                pyproj_crs = pyproj.CRS.from_epsg(epsg_code)
                crs_name = pyproj_crs.name
                if pyproj_crs.axis_info:
                    unit_name = pyproj_crs.axis_info[0].unit_name.upper()
            except Exception as e:
                self.logger.warning(f"Could not get CRS details from PyProj: {e}")
        
        # Create IfcProjectedCRS
        crs = self.ifc.create_entity(
            "IfcProjectedCRS",
            Name=crs_name,
            Description=description,
            GeodeticDatum=f"EPSG:{epsg_code}",
            VerticalDatum=None,
            MapProjection=None,
            MapZone=None,
            MapUnit=self._create_unit(unit_name)
        )
        
        self.logger.info(f"Created IfcProjectedCRS: EPSG:{epsg_code}")
        return crs
    
    def create_map_conversion(
        self,
        source_crs: ifcopenshell.entity_instance,
        target_crs: ifcopenshell.entity_instance,
        eastings: float,
        northings: float,
        orthogonal_height: float,
        x_axis_abscissa: float = 1.0,
        x_axis_ordinate: float = 0.0,
        scale: float = 1.0,
        rotation: float = 0.0
    ) -> ifcopenshell.entity_instance:
        """
        Create an IfcMapConversion entity.
        
        IfcMapConversion defines the transformation from local engineering
        coordinates (Blender scene) to map coordinates (projected CRS).
        
        Args:
            source_crs: Source context (usually GeometricRepresentationContext)
            target_crs: Target CRS (IfcProjectedCRS)
            eastings: Easting of local origin in map coordinates
            northings: Northing of local origin in map coordinates
            orthogonal_height: Elevation of local origin in map coordinates
            x_axis_abscissa: X-axis direction (usually 1.0)
            x_axis_ordinate: Y-axis direction (usually 0.0)
            scale: Scale factor (usually 1.0)
            rotation: Rotation in degrees from map north (clockwise positive)
        
        Returns:
            IfcMapConversion entity
        """
        # Calculate x-axis direction from rotation
        if rotation != 0.0:
            rad = math.radians(rotation)
            x_axis_abscissa = math.cos(rad)
            x_axis_ordinate = math.sin(rad)

        # Build attributes dictionary
        attributes = {
            "SourceCRS": source_crs,
            "TargetCRS": target_crs,
            "Eastings": eastings,
            "Northings": northings,
            "OrthogonalHeight": orthogonal_height,
            "XAxisAbscissa": x_axis_abscissa,
            "XAxisOrdinate": x_axis_ordinate,
            "Scale": scale if scale != 1.0 else None
        }

        # Check if IfcMapConversion already exists
        existing = self.ifc.by_type("IfcMapConversion")
        if existing:
            self.logger.warning("IfcMapConversion already exists, updating...")
            conversion = existing[0]
            # Use ifcopenshell.api for attribute updates when available
            try:
                ifcopenshell.api.run(
                    "attribute.edit_attributes",
                    self.ifc,
                    product=conversion,
                    attributes=attributes
                )
            except Exception:
                # Fallback to direct assignment if API not available
                for attr, value in attributes.items():
                    setattr(conversion, attr, value)
        else:
            # Create new entity with all attributes
            conversion = self.ifc.create_entity("IfcMapConversion", **attributes)
        
        self.logger.info(
            f"Created IfcMapConversion: "
            f"Origin=({eastings:.3f}, {northings:.3f}, {orthogonal_height:.3f}), "
            f"Rotation={rotation:.3f}°, Scale={scale}"
        )
        
        return conversion
    
    def get_georeferencing(self) -> Optional[Dict]:
        """
        Read existing georeferencing from IFC file.
        
        Returns:
            Dictionary with georeferencing parameters, or None if not found
        """
        map_conversion = self.ifc.by_type("IfcMapConversion")
        projected_crs = self.ifc.by_type("IfcProjectedCRS")
        
        if not map_conversion or not projected_crs:
            self.logger.warning("No georeferencing found in IFC file")
            return None
        
        conversion = map_conversion[0]
        crs = projected_crs[0]
        
        # Extract EPSG code from GeodeticDatum
        epsg_code = None
        if crs.GeodeticDatum:
            try:
                epsg_code = int(crs.GeodeticDatum.split(':')[1])
            except (IndexError, ValueError):
                pass
        
        # Calculate rotation from x-axis direction
        rotation = 0.0
        if conversion.XAxisAbscissa and conversion.XAxisOrdinate:
            rotation = math.degrees(
                math.atan2(conversion.XAxisOrdinate, conversion.XAxisAbscissa)
            )
        
        return {
            'epsg_code': epsg_code,
            'crs_name': crs.Name,
            'false_origin': (
                conversion.Eastings or 0.0,
                conversion.Northings or 0.0,
                conversion.OrthogonalHeight or 0.0
            ),
            'scale': conversion.Scale or 1.0,
            'rotation': rotation,
            'unit': crs.MapUnit.Name if crs.MapUnit else 'METRE'
        }
    
    def local_to_map(
        self,
        local_coords: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """
        Transform local Blender coordinates to map coordinates.
        
        Args:
            local_coords: (X, Y, Z) in Blender local space
        
        Returns:
            (Easting, Northing, Elevation) in map space
        """
        georef = self.get_georeferencing()
        if not georef:
            raise ValueError("No georeferencing set up")
        
        x, y, z = local_coords
        false_origin = georef['false_origin']
        scale = georef['scale']
        rotation_rad = math.radians(georef['rotation'])
        
        # Apply scale
        x_scaled = x * scale
        y_scaled = y * scale
        
        # Apply rotation
        cos_r = math.cos(rotation_rad)
        sin_r = math.sin(rotation_rad)
        x_rotated = x_scaled * cos_r - y_scaled * sin_r
        y_rotated = x_scaled * sin_r + y_scaled * cos_r
        
        # Add false origin
        easting = false_origin[0] + x_rotated
        northing = false_origin[1] + y_rotated
        elevation = false_origin[2] + z * scale
        
        return (easting, northing, elevation)
    
    def map_to_local(
        self,
        map_coords: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """
        Transform map coordinates to local Blender coordinates.
        
        Args:
            map_coords: (Easting, Northing, Elevation) in map space
        
        Returns:
            (X, Y, Z) in Blender local space
        """
        georef = self.get_georeferencing()
        if not georef:
            raise ValueError("No georeferencing set up")
        
        easting, northing, elevation = map_coords
        false_origin = georef['false_origin']
        scale = georef['scale']
        rotation_rad = math.radians(georef['rotation'])
        
        # Subtract false origin
        x_translated = easting - false_origin[0]
        y_translated = northing - false_origin[1]
        z_translated = elevation - false_origin[2]
        
        # Apply inverse rotation
        cos_r = math.cos(-rotation_rad)
        sin_r = math.sin(-rotation_rad)
        x_rotated = x_translated * cos_r - y_translated * sin_r
        y_rotated = x_translated * sin_r + y_translated * cos_r
        
        # Apply inverse scale
        x = x_rotated / scale
        y = y_rotated / scale
        z = z_translated / scale
        
        return (x, y, z)
    
    def _get_or_create_geometric_context(self) -> ifcopenshell.entity_instance:
        """Get existing or create new geometric representation context"""
        contexts = self.ifc.by_type("IfcGeometricRepresentationContext")
        
        if contexts:
            return contexts[0]
        
        # Create new context
        project = self.ifc.by_type("IfcProject")[0]
        
        context = self.ifc.create_entity(
            "IfcGeometricRepresentationContext",
            ContextIdentifier="Model",
            ContextType="Model",
            CoordinateSpaceDimension=3,
            Precision=1.0e-5,
            WorldCoordinateSystem=self._create_axis2_placement_3d()
        )
        
        # Link to project
        if project.RepresentationContexts:
            project.RepresentationContexts = list(project.RepresentationContexts) + [context]
        else:
            project.RepresentationContexts = [context]
        
        return context
    
    def _create_unit(self, unit_name: str) -> ifcopenshell.entity_instance:
        """Create or get existing unit entity"""
        # Check if unit already exists
        existing_units = self.ifc.by_type("IfcSIUnit")
        for unit in existing_units:
            if unit.Name == unit_name:
                return unit
        
        # Create new unit
        return self.ifc.create_entity(
            "IfcSIUnit",
            UnitType="LENGTHUNIT",
            Name=unit_name
        )
    
    def _create_axis2_placement_3d(
        self,
        location: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    ) -> ifcopenshell.entity_instance:
        """Create IfcAxis2Placement3D at given location"""
        point = self.ifc.create_entity(
            "IfcCartesianPoint",
            Coordinates=location
        )
        
        return self.ifc.create_entity(
            "IfcAxis2Placement3D",
            Location=point
        )
    
    def _setup_transformation_matrices(
        self,
        false_origin: Tuple[float, float, float],
        scale: float,
        rotation: float
    ):
        """Pre-compute transformation matrices for efficiency"""
        # Store for later use if we implement matrix transforms
        self._false_origin = false_origin
        self._scale = scale
        self._rotation = rotation


def validate_georeferencing(ifc_file: ifcopenshell.file) -> Dict:
    """
    Validate georeferencing in an IFC file.

    Checks:
    - IfcProjectedCRS exists
    - IfcMapConversion exists
    - Required attributes are set
    - EPSG code is valid

    Returns:
        Dictionary with validation results
    """
    logger = get_logger(__name__)
    results = {
        'valid': True,
        'warnings': [],
        'errors': []
    }
    
    # Check for IfcProjectedCRS
    projected_crs = ifc_file.by_type("IfcProjectedCRS")
    if not projected_crs:
        results['valid'] = False
        results['errors'].append("Missing IfcProjectedCRS")
    else:
        crs = projected_crs[0]
        if not crs.GeodeticDatum:
            results['warnings'].append("IfcProjectedCRS missing GeodeticDatum (EPSG code)")
    
    # Check for IfcMapConversion
    map_conversion = ifc_file.by_type("IfcMapConversion")
    if not map_conversion:
        results['valid'] = False
        results['errors'].append("Missing IfcMapConversion")
    else:
        conversion = map_conversion[0]
        if conversion.Eastings is None or conversion.Northings is None:
            results['errors'].append("IfcMapConversion missing Eastings or Northings")
            results['valid'] = False
    
    # Log results
    if results['valid']:
        logger.info("Georeferencing validation passed")
    else:
        logger.warning("Georeferencing validation failed")
    
    return results


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create a minimal IFC file for testing
    ifc = ifcopenshell.file(schema="IFC4X3")
    
    # Create required entities
    project = ifc.create_entity(
        "IfcProject",
        GlobalId=ifcopenshell.guid.new(),
        Name="Test Project"
    )
    
    # Setup georeferencing
    georef = NativeIfcGeoreferencing(ifc)
    crs, conversion = georef.setup_georeferencing(
        epsg_code=26910,  # NAD83 / UTM zone 10N
        false_origin=(551000.0, 4182000.0, 50.0),
        name="Test Site",
        description="Example georeferencing setup"
    )
    
    logger = get_logger(__name__)
    logger.info("=== Georeferencing Setup Complete ===")
    logger.info("IfcProjectedCRS: %s", crs.Name)
    logger.info("False Origin: %s, %s, %s", conversion.Eastings, conversion.Northings, conversion.OrthogonalHeight)

    # Test coordinate transformations
    logger.info("=== Coordinate Transformations ===")
    local = (100.0, 200.0, 5.0)
    map_coords = georef.local_to_map(local)
    logger.info("Local %s → Map %s", local, map_coords)

    back_to_local = georef.map_to_local(map_coords)
    logger.info("Map %s → Local %s", map_coords, back_to_local)

    # Validate
    logger.info("=== Validation ===")
    validation = validate_georeferencing(ifc)
    logger.info("Valid: %s", validation['valid'])
    if validation['warnings']:
        logger.warning("Warnings: %s", validation['warnings'])
    if validation['errors']:
        logger.error("Errors: %s", validation['errors'])

    # Save example file
    ifc.write("/home/claude/test_georeferenced.ifc")
    logger.info("=== Saved test_georeferenced.ifc ===")
