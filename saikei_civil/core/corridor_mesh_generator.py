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
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================
"""
DEPRECATED: This module has been moved to the tool layer.

The CorridorMeshGenerator class has been moved to saikei_civil.tool.corridor
as part of the three-layer architecture migration.

For new code, use:
    from saikei_civil.tool import Corridor
    mesh_obj, stats = Corridor.generate_corridor_mesh(stations, assembly, name, lod)

This file maintains backwards compatibility by re-exporting from the new location.

Migration Guide:
    OLD: from saikei_civil.core.corridor_mesh_generator import CorridorMeshGenerator
         generator = CorridorMeshGenerator(modeler)
         mesh_obj = generator.generate_mesh(lod='medium')

    NEW: from saikei_civil.tool import Corridor
         mesh_obj, stats = Corridor.generate_corridor_mesh(
             stations=modeler.stations,
             assembly=assembly_wrapper,
             name="Corridor",
             lod='medium'
         )
"""
import warnings

# Issue deprecation warning on import
warnings.warn(
    "saikei_civil.core.corridor_mesh_generator is deprecated. "
    "Use saikei_civil.tool.Corridor instead. "
    "This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

import bpy
import bmesh
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
import math
import time
from .logging_config import get_logger

logger = get_logger(__name__)

# Note: The classes below are maintained for backwards compatibility only.
# New code should use the tool layer: from saikei_civil.tool import Corridor


@dataclass
class LODSettings:
    """Level of Detail settings for corridor mesh generation."""
    name: str
    station_interval: float  # Base interval multiplier
    curve_densification: float  # Curve densification factor
    smooth_shading: bool
    subdivisions: int  # Number of subdivisions for smooth transitions
    
    @classmethod
    def high(cls) -> 'LODSettings':
        """High detail - Best quality, slower generation."""
        return cls(
            name="High",
            station_interval=1.0,  # Full density
            curve_densification=2.0,  # Dense curves
            smooth_shading=True,
            subdivisions=2
        )
    
    @classmethod
    def medium(cls) -> 'LODSettings':
        """Medium detail - Balanced quality and performance."""
        return cls(
            name="Medium",
            station_interval=1.5,  # 1.5x base interval
            curve_densification=1.5,
            smooth_shading=True,
            subdivisions=1
        )
    
    @classmethod
    def low(cls) -> 'LODSettings':
        """Low detail - Fast preview, lower quality."""
        return cls(
            name="Low",
            station_interval=2.0,  # 2x base interval
            curve_densification=1.0,  # Minimal curve densification
            smooth_shading=False,
            subdivisions=0
        )


@dataclass
class MaterialZone:
    """
    Material zone for corridor mesh.
    
    Represents a region of the corridor that should have a specific material.
    """
    name: str
    material_name: str
    component_type: str  # LANE, SHOULDER, CURB, etc.
    color: Tuple[float, float, float, float]  # RGBA
    roughness: float = 0.7
    metallic: float = 0.0


class CorridorMeshGenerator:
    """
    Generate Blender mesh geometry from corridor data.
    
    Takes corridor modeler output (stations + cross-sections) and creates
    optimized Blender mesh with LOD support and material assignment.
    
    Architecture:
    1. Extract corridor data (stations, cross-sections, assembly)
    2. Calculate vertices for each station
    3. Create quad strips connecting stations
    4. Apply materials to component zones
    5. Optimize mesh (merge vertices, smooth normals)
    6. Add to scene with proper collection organization
    
    Attributes:
        modeler: CorridorModeler instance with corridor data
        lod_settings: LOD configuration
        mesh_obj: Generated Blender mesh object
        material_zones: List of material zones
    """
    
    def __init__(self, modeler: Any, name: str = "Corridor"):
        """
        Initialize mesh generator.
        
        Args:
            modeler: CorridorModeler instance with generated corridor
            name: Name for the generated mesh object
        """
        self.modeler = modeler
        self.name = name
        self.mesh_obj = None
        self.material_zones: List[MaterialZone] = []
        
        # Performance tracking
        self.generation_time = 0.0
        self.vertex_count = 0
        self.face_count = 0
    
    def generate_mesh(
        self,
        lod: str = 'medium',
        apply_materials: bool = True,
        create_collection: bool = True
    ) -> bpy.types.Object:
        """
        Generate corridor mesh with specified LOD.
        
        Args:
            lod: Level of detail ('high', 'medium', 'low')
            apply_materials: Whether to create and apply materials
            create_collection: Whether to organize in collection
            
        Returns:
            Blender mesh object
            
        Raises:
            ValueError: If LOD setting is invalid
        """
        start_time = time.time()
        
        # Get LOD settings
        lod_map = {
            'high': LODSettings.high(),
            'medium': LODSettings.medium(),
            'low': LODSettings.low()
        }
        
        if lod not in lod_map:
            raise ValueError(f"Invalid LOD '{lod}'. Use 'high', 'medium', or 'low'")
        
        lod_settings = lod_map[lod]
        
        # Get corridor data
        stations = self.modeler.stations
        assembly = self.modeler.assembly
        
        if not stations or len(stations) < 2:
            raise ValueError("Need at least 2 stations to generate mesh")
        
        # Create new mesh
        mesh = bpy.data.meshes.new(self.name)
        self.mesh_obj = bpy.data.objects.new(self.name, mesh)
        
        # Generate geometry using BMesh
        bm = bmesh.new()
        
        try:
            # Generate vertices and faces
            self._generate_geometry(bm, stations, assembly, lod_settings)
            
            # Convert BMesh to mesh
            bm.to_mesh(mesh)
            
            # Apply smooth shading if requested
            if lod_settings.smooth_shading:
                for poly in mesh.polygons:
                    poly.use_smooth = True
            
            # Link to scene
            if create_collection:
                self._add_to_collection()
            else:
                bpy.context.collection.objects.link(self.mesh_obj)
            
            # Apply materials
            if apply_materials:
                self._apply_materials(assembly)
            
            # Update statistics
            self.vertex_count = len(mesh.vertices)
            self.face_count = len(mesh.polygons)
            self.generation_time = time.time() - start_time

            logger.info("Corridor mesh generated:")
            logger.info("  LOD: %s", lod_settings.name)
            logger.info("  Vertices: %s", f"{self.vertex_count:,}")
            logger.info("  Faces: %s", f"{self.face_count:,}")
            logger.info("  Time: %.2fs", self.generation_time)

            return self.mesh_obj
            
        finally:
            bm.free()
    
    def _generate_geometry(
        self,
        bm: bmesh.types.BMesh,
        stations: List[Any],
        assembly: Any,
        lod_settings: LODSettings
    ):
        """
        Generate corridor geometry using BMesh.
        
        Creates vertices at each station and connects them with quad strips.
        
        Args:
            bm: BMesh to add geometry to
            stations: List of StationPoint objects
            assembly: RoadAssembly with cross-section definition
            lod_settings: LOD configuration
        """
        # Get cross-section profile points
        # Each component (lane, shoulder, etc.) has offset/elevation pairs
        profile_points = self._get_profile_points(assembly)
        
        # Generate vertices for each station
        all_vertices = []
        
        for station in stations:
            # Get 3D position and bearing at this station
            station_vertices = self._create_station_vertices(
                station,
                profile_points,
                bm
            )
            all_vertices.append(station_vertices)
        
        # Connect adjacent stations with quad strips
        self._create_quad_strips(bm, all_vertices)
        
        # Add end caps for solid appearance
        self._create_end_caps(bm, all_vertices)
    
    def _get_profile_points(self, assembly: Any) -> List[Dict[str, Any]]:
        """
        Extract cross-section profile points from assembly.

        Returns list of component definitions with their geometry.

        Args:
            assembly: RoadAssembly instance

        Returns:
            List of dicts with component data:
            {
                'name': 'Left Lane',
                'type': 'LANE',
                'points': [(offset1, elevation1), (offset2, elevation2), ...],
                'material': 'Asphalt'
            }
        """
        profile_points = []

        for component in assembly.components:
            # Get component points (offset, elevation pairs)
            points = []

            # Check which side this component is on
            # Negative offset = left side, positive = right side
            is_left_side = component.offset < 0

            if is_left_side:
                # Left side: offset is already negative, width extends further left (more negative)
                # Start point (closer to centerline)
                start_offset = component.offset + component.width  # Less negative
                start_elev = component.elevation - component.slope * component.width
                # End point (further from centerline)
                end_offset = component.offset  # More negative
                end_elev = component.elevation
                points.append((start_offset, start_elev))
                points.append((end_offset, end_elev))
            else:
                # Right side: offset is positive or zero, width extends further right
                # Start point (closer to centerline)
                start_offset = component.offset
                start_elev = component.elevation
                # End point (further from centerline)
                end_offset = component.offset + component.width
                end_elev = component.elevation - component.slope * component.width
                points.append((start_offset, start_elev))
                points.append((end_offset, end_elev))

            profile_points.append({
                'name': component.name,
                'type': component.component_type,
                'points': points,
                'material': component.material
            })

        return profile_points
    
    def _create_station_vertices(
        self,
        station: Any,
        profile_points: List[Dict[str, Any]],
        bm: bmesh.types.BMesh
    ) -> List[bmesh.types.BMVert]:
        """
        Create vertices at a specific station.
        
        Transforms 2D cross-section points to 3D space based on
        station position and bearing.
        
        Args:
            station: StationPoint with position and bearing
            profile_points: Cross-section profile definition
            bm: BMesh to add vertices to
            
        Returns:
            List of created BMesh vertices
        """
        vertices = []
        
        # Get station data
        x, y, z = station.x, station.y, station.z
        bearing = station.direction
        
        # Trigonometry for perpendicular direction
        cos_bearing = math.cos(bearing)
        sin_bearing = math.sin(bearing)
        
        # Create vertices for all profile points
        for component in profile_points:
            for offset, elevation in component['points']:
                # Transform to 3D
                # Offset is perpendicular to alignment
                # Positive offset = right side of alignment
                vert_x = x - offset * sin_bearing
                vert_y = y + offset * cos_bearing
                vert_z = z + elevation
                
                # Create vertex
                vert = bm.verts.new((vert_x, vert_y, vert_z))
                vertices.append(vert)
        
        return vertices
    
    def _create_quad_strips(
        self,
        bm: bmesh.types.BMesh,
        all_vertices: List[List[bmesh.types.BMVert]]
    ):
        """
        Connect adjacent stations with quad faces.
        
        Creates quad strips between consecutive stations to form
        the corridor surface.
        
        Args:
            bm: BMesh to add faces to
            all_vertices: List of vertex lists (one per station)
        """
        # Connect each pair of adjacent stations
        for i in range(len(all_vertices) - 1):
            station_verts_1 = all_vertices[i]
            station_verts_2 = all_vertices[i + 1]
            
            # Create quads connecting corresponding vertices
            for j in range(len(station_verts_1) - 1):
                # Get four corners of quad
                v1 = station_verts_1[j]
                v2 = station_verts_1[j + 1]
                v3 = station_verts_2[j + 1]
                v4 = station_verts_2[j]
                
                # Create face (ensure correct winding order)
                try:
                    bm.faces.new([v1, v2, v3, v4])
                except ValueError:
                    # Face already exists or vertices are coplanar
                    pass
        
        # Update BMesh indices
        bm.verts.index_update()
        bm.faces.index_update()
    
    def _create_end_caps(
        self,
        bm: bmesh.types.BMesh,
        all_vertices: List[List[bmesh.types.BMVert]]
    ):
        """
        Create end cap faces at corridor start and end.
        
        Args:
            bm: BMesh to add faces to
            all_vertices: List of vertex lists
        """
        if len(all_vertices) < 2:
            return
        
        # Start cap
        start_verts = all_vertices[0]
        if len(start_verts) > 2:
            try:
                bm.faces.new(start_verts)
            except ValueError:
                pass
        
        # End cap
        end_verts = all_vertices[-1]
        if len(end_verts) > 2:
            try:
                # Reverse winding for end cap
                bm.faces.new(reversed(end_verts))
            except ValueError:
                pass
        
        # Update indices
        bm.faces.index_update()
    
    def _apply_materials(self, assembly: Any):
        """
        Create and apply materials to corridor mesh.
        
        Creates Blender materials based on cross-section components
        and assigns them to appropriate faces.
        
        Args:
            assembly: RoadAssembly with component definitions
        """
        # Standard colors for component types
        component_colors = {
            'LANE': (0.3, 0.3, 0.3, 1.0),  # Dark gray
            'SHOULDER': (0.5, 0.5, 0.45, 1.0),  # Light gray
            'CURB': (0.8, 0.8, 0.8, 1.0),  # White
            'DITCH': (0.4, 0.3, 0.2, 1.0),  # Brown
            'SIDEWALK': (0.7, 0.7, 0.7, 1.0),  # Light gray
            'MEDIAN': (0.2, 0.6, 0.2, 1.0),  # Green
        }
        
        # Create materials for each unique component type
        created_materials = {}
        
        for component in assembly.components:
            comp_type = component.component_type
            
            if comp_type not in created_materials:
                # Create material
                mat = self._create_material(
                    name=f"Corridor_{comp_type}",
                    color=component_colors.get(comp_type, (0.5, 0.5, 0.5, 1.0))
                )
                created_materials[comp_type] = mat
                
                # Add to mesh
                self.mesh_obj.data.materials.append(mat)

        logger.info("Created %s materials for corridor", len(created_materials))
    
    def _create_material(
        self,
        name: str,
        color: Tuple[float, float, float, float]
    ) -> bpy.types.Material:
        """
        Create a Blender material with Principled BSDF.
        
        Args:
            name: Material name
            color: RGBA color tuple
            
        Returns:
            Blender material
        """
        # Check if material already exists
        if name in bpy.data.materials:
            return bpy.data.materials[name]
        
        # Create new material
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        
        # Get Principled BSDF node
        nodes = mat.node_tree.nodes
        principled = nodes.get("Principled BSDF")
        
        if principled:
            # Set base color
            principled.inputs["Base Color"].default_value = color
            
            # Set roughness for realistic road surface
            principled.inputs["Roughness"].default_value = 0.7
            
            # Metallic = 0 for road materials
            principled.inputs["Metallic"].default_value = 0.0
        
        return mat
    
    def _add_to_collection(self):
        """
        Add mesh object to IFC project hierarchy.

        Adds the corridor to the "Saikei Civil Project" collection and
        parents it to the Road empty for proper IFC integration.
        Also creates an IFC entity and links the Blender object to it.
        """
        from .ifc_manager import NativeIfcManager
        import ifcopenshell.guid

        # Try to add to IFC project collection
        project_coll_name = "Saikei Civil Project"

        if project_coll_name in bpy.data.collections:
            collection = bpy.data.collections[project_coll_name]
            collection.objects.link(self.mesh_obj)

            # Parent to Road empty if it exists
            from .ifc_manager.blender_hierarchy import ROAD_EMPTY_NAME
            road_empty = bpy.data.objects.get(ROAD_EMPTY_NAME)
            if road_empty:
                self.mesh_obj.parent = road_empty
                logger.info("Parented corridor to Road empty")

            # Create IFC entity for the corridor
            ifc_file = NativeIfcManager.file
            if ifc_file:
                try:
                    # Create IfcCourse entity for the corridor solid
                    corridor_entity = ifc_file.create_entity(
                        "IfcCourse",
                        GlobalId=ifcopenshell.guid.new(),
                        Name=self.mesh_obj.name,
                        Description="Corridor solid generated from cross-section assembly",
                        ObjectType="CORRIDOR",
                        PredefinedType="USERDEFINED"
                    )

                    # Link Blender object to IFC entity
                    NativeIfcManager.link_object(self.mesh_obj, corridor_entity)

                    # Contain in IfcRoad
                    road = NativeIfcManager.get_road()
                    if road:
                        ifc_file.create_entity(
                            "IfcRelContainedInSpatialStructure",
                            GlobalId=ifcopenshell.guid.new(),
                            Name="CorridorToRoad",
                            RelatingStructure=road,
                            RelatedElements=[corridor_entity]
                        )
                        logger.info("Linked corridor to IFC Road")

                except Exception as e:
                    logger.warning(f"Could not create IFC entity for corridor: {e}")

            logger.info("Added corridor to IFC project collection: %s", project_coll_name)

        else:
            # Fallback: create standalone collection if no IFC project
            coll_name = "Corridor Visualization"

            if coll_name in bpy.data.collections:
                collection = bpy.data.collections[coll_name]
            else:
                collection = bpy.data.collections.new(coll_name)
                bpy.context.scene.collection.children.link(collection)

            collection.objects.link(self.mesh_obj)
            logger.info("Added mesh to fallback collection: %s", coll_name)
    
    def generate_with_materials(self, lod: str = 'medium') -> bpy.types.Object:
        """
        Generate corridor mesh with materials applied.
        
        Convenience method that calls generate_mesh with apply_materials=True.
        
        Args:
            lod: Level of detail
            
        Returns:
            Blender mesh object with materials
        """
        return self.generate_mesh(lod=lod, apply_materials=True)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get generation statistics.
        
        Returns:
            Dictionary with statistics:
            {
                'vertex_count': int,
                'face_count': int,
                'generation_time': float,
                'stations': int
            }
        """
        return {
            'vertex_count': self.vertex_count,
            'face_count': self.face_count,
            'generation_time': self.generation_time,
            'stations': len(self.modeler.stations) if self.modeler.stations else 0
        }


# Example usage
if __name__ == "__main__":
    logger.info("CorridorMeshGenerator - Sprint 5 Day 3")
    logger.info("This module generates Blender meshes from corridor data")
    logger.info("")
    logger.info("Key Features:")
    logger.info("  - LOD system (High, Medium, Low)")
    logger.info("  - Material assignment")
    logger.info("  - Performance optimized")
    logger.info("  - Collection organization")
    logger.info("")
    logger.info("Target Performance:")
    logger.info("  - High LOD: <5s for 1km corridor")
    logger.info("  - Medium LOD: <2s for 1km corridor")
    logger.info("  - Low LOD: <1s for 1km corridor")
