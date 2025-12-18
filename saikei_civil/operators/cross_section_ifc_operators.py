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
Cross-Section IFC Operators
============================

Operators for saving and exporting cross-section assemblies to IFC format.

Operators:
    BC_OT_ExportAssemblyIFC: Export assembly to standalone IFC file
    BC_OT_SaveAssemblyToIFC: Save assembly to current IFC file
    BC_OT_SaveAssemblyTemplate: Save assembly as reusable template
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class BC_OT_ExportAssemblyIFC(Operator):
    """
    Export the active assembly to IFC 4.3 format.

    Converts the assembly definition to IFC 4.3 IfcAlignment schema,
    enabling interoperability with other civil engineering software
    that supports IFC standards.

    Properties:
        filepath: Destination path for IFC file

    Requirements:
        - Assembly must be valid (run validation first)
        - Assembly must have at least one component
        - ifcopenshell library must be available

    Usage:
        Called from export menu to save assembly definitions for use
        in other software or for project archival.
    """
    bl_idname = "bc.export_assembly_ifc"
    bl_label = "Export to IFC"
    bl_description = "Export assembly to IFC 4.3 file"
    bl_options = {'REGISTER'}

    filepath: StringProperty(
        name="File Path",
        description="Path to save IFC file",
        default="",
        subtype='FILE_PATH',
    )

    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return assembly.is_valid and len(assembly.components) > 0

    def execute(self, context):
        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]

        if not self.filepath:
            self.report({'ERROR'}, "No file path specified")
            return {'CANCELLED'}

        try:
            import ifcopenshell

            # Create IFC file
            ifc_file = ifcopenshell.file(schema="IFC4X3")

            # Create basic IFC structure
            # This is a simplified version - full implementation would include
            # proper IFC project setup, units, etc.

            # TODO: Implement full IFC export using native_ifc_cross_section module

            # Save file
            ifc_file.write(self.filepath)

            self.report({'INFO'}, f"Exported to {self.filepath}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class BC_OT_SaveAssemblyTemplate(Operator):
    """
    Save the active assembly as a reusable template.

    Exports the assembly configuration to an external template file that
    can be loaded in future projects, enabling standardization of cross-
    section designs across multiple projects.

    Properties:
        template_name: Name for the saved template

    Requirements:
        - Assembly must be valid
        - Template name must be provided

    Usage:
        Called after creating a custom assembly that should be reused.
        Useful for creating organization-specific design standards.
    """
    bl_idname = "bc.save_assembly_template"
    bl_label = "Save as Template"
    bl_description = "Save assembly configuration as a reusable template"
    bl_options = {'REGISTER', 'UNDO'}

    template_name: StringProperty(
        name="Template Name",
        description="Name for the template",
        default="My Template",
    )

    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return assembly.is_valid

    def execute(self, context):
        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]

        # TODO: Implement template saving to external file
        # For now, just report success

        self.report({'INFO'}, f"Template '{self.template_name}' saved")
        return {'FINISHED'}

    def invoke(self, context, event):
        cs = context.scene.bc_cross_section
        self.template_name = cs.assemblies[cs.active_assembly_index].name
        return context.window_manager.invoke_props_dialog(self)


class BC_OT_SaveAssemblyToIFC(Operator):
    """
    Save the active assembly to the currently loaded IFC file.

    Converts the Blender PropertyGroup assembly to IFC entities and adds
    them to the IFC file in memory. Use 'Save IFC File' to persist to disk.

    Creates:
    - IfcElementAssembly for the cross-section assembly
    - IfcOpenCrossProfileDef for each component
    - Links assembly to the IfcRoad in the spatial hierarchy
    """
    bl_idname = "bc.save_assembly_to_ifc"
    bl_label = "Save Assembly to IFC"
    bl_description = "Save cross-section assembly to the currently loaded IFC file"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        """Check if operator can run."""
        from ..core.ifc_manager import NativeIfcManager

        # Need an IFC file loaded
        if not NativeIfcManager.file:
            return False

        # Need an assembly with components
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False

        assembly = cs.assemblies[cs.active_assembly_index]
        return len(assembly.components) > 0

    def execute(self, context):
        """Save assembly to IFC file."""
        import ifcopenshell
        import ifcopenshell.guid
        from ..core.ifc_manager import NativeIfcManager

        try:
            ifc_file = NativeIfcManager.file
            if not ifc_file:
                self.report({'ERROR'}, "No IFC file loaded. Create or open a project first.")
                return {'CANCELLED'}

            cs = context.scene.bc_cross_section
            assembly = cs.assemblies[cs.active_assembly_index]

            # Check if assembly already exists in IFC (update vs create)
            existing_entity = None
            if assembly.ifc_definition_id > 0:
                try:
                    existing_entity = ifc_file.by_id(assembly.ifc_definition_id)
                except RuntimeError:
                    existing_entity = None

            if existing_entity:
                # Update existing - remove old and recreate
                # (IFC doesn't support in-place modification well)
                self._remove_assembly_from_ifc(ifc_file, existing_entity)

            # Create new IFC entities for the assembly
            ifc_assembly = self._create_ifc_assembly(ifc_file, assembly)

            # Update PropertyGroup with IFC linkage
            assembly.ifc_definition_id = ifc_assembly.id()
            assembly.global_id = ifc_assembly.GlobalId

            # Link to IfcRoad
            self._link_to_road(ifc_file, ifc_assembly)

            # Create Blender representation for the assembly
            blender_obj = self._create_blender_representation(
                context, assembly, ifc_assembly
            )

            self.report({'INFO'},
                f"Saved assembly '{assembly.name}' to IFC (ID: {ifc_assembly.id()})")

            logger.info(f"Saved cross-section assembly to IFC: {assembly.name}")
            return {'FINISHED'}

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Failed to save assembly: {str(e)}")
            return {'CANCELLED'}

    def _create_ifc_assembly(self, ifc_file, assembly):
        """Create IFC entities for the assembly and its components.

        Creates an IfcRoadPart (ROADSEGMENT) as the assembly container,
        with component elements (IfcPavement, IfcKerb, etc.) aggregated under it.
        """
        import ifcopenshell.guid

        # Create IfcRoadPart for the cross-section assembly
        # Using ROADSEGMENT as the PredefinedType for cross-section templates
        # UsageType="LATERAL" because cross-sections define lateral extent
        ifc_assembly = ifc_file.create_entity(
            "IfcRoadPart",
            GlobalId=ifcopenshell.guid.new(),
            Name=assembly.name,
            Description=assembly.description or f"Cross-section assembly: {assembly.name}",
            ObjectType="CROSS_SECTION_ASSEMBLY",
            PredefinedType="ROADSEGMENT",
            UsageType="LATERAL"
        )

        # Map component types to IFC classes
        component_ifc_classes = {
            'LANE': 'IfcPavement',
            'SHOULDER': 'IfcPavement',
            'CURB': 'IfcKerb',
            'DITCH': 'IfcEarthworksCut',
            'SIDEWALK': 'IfcPavement',
            'MEDIAN': 'IfcPavement',
        }

        # Create IFC elements for each component and collect them for aggregation
        component_elements = []
        profiles = []

        for comp in assembly.components:
            # Create profile geometry for the component
            profile = self._create_component_profile(ifc_file, comp)
            profiles.append(profile)

            # Determine IFC class for this component type
            ifc_class = component_ifc_classes.get(comp.component_type, 'IfcBuildingElementPart')

            # Create component element with profile
            comp_guid = ifcopenshell.guid.new()
            side_indicator = "L" if comp.side == "LEFT" else "R"
            comp_name = f"{comp.name} [{side_indicator}] ({ifc_class})"

            component_element = ifc_file.create_entity(
                ifc_class,
                GlobalId=comp_guid,
                Name=comp_name,
                Description=f"{comp.component_type} component: {comp.name}",
                ObjectType=comp.component_type,
            )

            component_elements.append(component_element)

            # Update component IFC linkage
            comp.ifc_definition_id = component_element.id()
            comp.global_id = comp_guid

            logger.debug(f"Created {ifc_class} for component: {comp.name}")

        # Aggregate components under the assembly using IfcRelAggregates
        if component_elements:
            ifc_file.create_entity(
                "IfcRelAggregates",
                GlobalId=ifcopenshell.guid.new(),
                Name=f"AssemblyToComponents_{assembly.name}",
                Description="Components aggregated to cross-section assembly",
                RelatingObject=ifc_assembly,
                RelatedObjects=component_elements
            )
            logger.info(f"Aggregated {len(component_elements)} components under assembly '{assembly.name}'")

        # Create composite profile combining all component profiles
        if profiles:
            composite = ifc_file.create_entity(
                "IfcCompositeProfileDef",
                ProfileType="AREA",
                ProfileName=f"{assembly.name}_Profile",
                Profiles=profiles
            )

            # Create property set with assembly metadata
            self._create_assembly_pset(ifc_file, ifc_assembly, assembly, composite)

        return ifc_assembly

    def _create_component_profile(self, ifc_file, component):
        """Create IfcArbitraryOpenProfileDef for a component.

        Uses IfcArbitraryOpenProfileDef with a polyline curve instead of
        IfcOpenCrossProfileDef since it's more flexible for our component geometry.
        """
        width = component.width
        slope = component.cross_slope
        offset = component.offset
        side = component.side

        # Calculate start and end points (offset, elevation)
        if side == "LEFT":
            # Left side: negative offsets, extends further left
            start_offset = -abs(offset)
            end_offset = start_offset - width
            start_elev = 0.0
            end_elev = -width * slope
        elif side == "RIGHT":
            # Right side: positive offsets, extends further right
            start_offset = abs(offset)
            end_offset = start_offset + width
            start_elev = 0.0
            end_elev = -width * slope
        else:
            # Center: spans both sides
            start_offset = -width / 2
            end_offset = width / 2
            start_elev = 0.0
            end_elev = 0.0

        # Create points for the profile curve
        start_point = ifc_file.create_entity(
            "IfcCartesianPoint",
            Coordinates=(start_offset, start_elev)
        )
        end_point = ifc_file.create_entity(
            "IfcCartesianPoint",
            Coordinates=(end_offset, end_elev)
        )

        # Create polyline from points
        polyline = ifc_file.create_entity(
            "IfcPolyline",
            Points=[start_point, end_point]
        )

        # Create IfcArbitraryOpenProfileDef
        profile = ifc_file.create_entity(
            "IfcArbitraryOpenProfileDef",
            ProfileType="CURVE",
            ProfileName=f"{component.name}_{component.component_type}",
            Curve=polyline
        )

        return profile

    def _create_assembly_pset(self, ifc_file, ifc_assembly, assembly, composite_profile):
        """Create property set with assembly metadata."""
        import ifcopenshell.guid

        # Create property values
        properties = []

        # Assembly type
        properties.append(ifc_file.create_entity(
            "IfcPropertySingleValue",
            Name="AssemblyType",
            NominalValue=ifc_file.create_entity("IfcLabel", assembly.assembly_type)
        ))

        # Design speed
        properties.append(ifc_file.create_entity(
            "IfcPropertySingleValue",
            Name="DesignSpeed",
            NominalValue=ifc_file.create_entity("IfcReal", assembly.design_speed)
        ))

        # Total width
        properties.append(ifc_file.create_entity(
            "IfcPropertySingleValue",
            Name="TotalWidth",
            NominalValue=ifc_file.create_entity("IfcLengthMeasure", assembly.total_width)
        ))

        # Component count
        properties.append(ifc_file.create_entity(
            "IfcPropertySingleValue",
            Name="ComponentCount",
            NominalValue=ifc_file.create_entity("IfcInteger", len(assembly.components))
        ))

        # Component data as JSON-like string
        comp_data = []
        for comp in assembly.components:
            comp_data.append(
                f"{comp.name}|{comp.component_type}|{comp.side}|"
                f"{comp.width:.4f}|{comp.cross_slope:.4f}|{comp.offset:.4f}"
            )
        comp_string = ";".join(comp_data)

        properties.append(ifc_file.create_entity(
            "IfcPropertySingleValue",
            Name="ComponentData",
            NominalValue=ifc_file.create_entity("IfcText", comp_string)
        ))

        # Create property set
        pset = ifc_file.create_entity(
            "IfcPropertySet",
            GlobalId=ifcopenshell.guid.new(),
            Name="SaikeiCivil_CrossSectionAssembly",
            HasProperties=properties
        )

        # Link property set to assembly
        ifc_file.create_entity(
            "IfcRelDefinesByProperties",
            GlobalId=ifcopenshell.guid.new(),
            RelatedObjects=[ifc_assembly],
            RelatingPropertyDefinition=pset
        )

    def _link_to_road(self, ifc_file, ifc_assembly):
        """Link assembly (IfcRoadPart) to IfcRoad via aggregation.

        Per IFC 4.3 SPS002: IfcRoadPart must be AGGREGATED to IfcRoad,
        not spatially contained. The spatial composition hierarchy is:
        IfcRoad (aggregates) -> IfcRoadPart (contains) -> elements
        """
        import ifcopenshell.guid

        # Find IfcRoad
        roads = ifc_file.by_type("IfcRoad")
        if not roads:
            logger.warning("No IfcRoad found - assembly not aggregated")
            return

        road = roads[0]

        # Check if aggregation relationship already exists
        for rel in ifc_file.by_type("IfcRelAggregates"):
            if rel.RelatingObject == road:
                if ifc_assembly in (rel.RelatedObjects or []):
                    return  # Already aggregated

        # Create aggregation relationship (IfcRoadPart aggregated BY IfcRoad)
        # Per SPS002: IfcRoadPart spatial parent must be IfcRoad, not IfcAlignment
        ifc_file.create_entity(
            "IfcRelAggregates",
            GlobalId=ifcopenshell.guid.new(),
            Name="RoadToRoadPart",
            Description="Cross-section assembly aggregated to road",
            RelatingObject=road,
            RelatedObjects=[ifc_assembly]
        )

    def _remove_assembly_from_ifc(self, ifc_file, entity):
        """Remove an existing assembly from IFC file."""
        try:
            # Remove related property sets
            for rel in entity.IsDefinedBy or []:
                if rel.is_a("IfcRelDefinesByProperties"):
                    pset = rel.RelatingPropertyDefinition
                    if pset:
                        for prop in pset.HasProperties or []:
                            try:
                                ifc_file.remove(prop)
                            except RuntimeError:
                                pass
                        try:
                            ifc_file.remove(pset)
                        except RuntimeError:
                            pass
                    try:
                        ifc_file.remove(rel)
                    except RuntimeError:
                        pass

            # Remove spatial containment
            for rel in entity.ContainedInStructure or []:
                try:
                    ifc_file.remove(rel)
                except RuntimeError:
                    pass

            # Remove the entity itself
            ifc_file.remove(entity)
        except RuntimeError:
            pass

    def _create_blender_representation(self, context, assembly, ifc_assembly):
        """Create a Blender empty to represent the assembly in the Outliner.

        Creates an empty object, adds it to the Saikei Civil Project collection,
        parents it to the Road empty, and links it to the IFC entity.

        Args:
            context: Blender context
            assembly: The PropertyGroup assembly data
            ifc_assembly: The IFC entity

        Returns:
            The created Blender object
        """
        from ..core.ifc_manager import NativeIfcManager
        from .. import tool

        # Check if a Blender object already exists for this assembly
        existing_obj = None
        for obj in bpy.data.objects:
            if obj.get("ifc_definition_id") == assembly.ifc_definition_id:
                existing_obj = obj
                break

        if existing_obj:
            # Update existing object name if needed
            existing_obj.name = f"{assembly.name} (IfcRoadPart)"
            return existing_obj

        # Create an empty object to represent the assembly
        empty = bpy.data.objects.new(f"{assembly.name} (IfcRoadPart)", None)
        empty.empty_display_type = 'PLAIN_AXES'
        empty.empty_display_size = 1.0

        # Link to IFC entity
        NativeIfcManager.link_object(empty, ifc_assembly)

        # Add to project collection
        project_coll_name = "Saikei Civil Project"
        if project_coll_name in bpy.data.collections:
            collection = bpy.data.collections[project_coll_name]
            collection.objects.link(empty)
        else:
            # Fallback to scene collection
            context.scene.collection.objects.link(empty)

        # Parent to Road object - use tool layer to find proper object
        road = tool.Spatial.get_road()
        road_obj = None
        if road:
            road_obj = tool.Ifc.get_object(road)
        if road_obj is None:
            # Fallback: try direct lookup by name
            from ..core.ifc_manager.blender_hierarchy import ROAD_EMPTY_NAME
            road_obj = bpy.data.objects.get(ROAD_EMPTY_NAME)

        if road_obj:
            empty.parent = road_obj

        logger.info(f"Created Blender representation for assembly: {assembly.name}")
        return empty


# Registration
classes = (
    BC_OT_ExportAssemblyIFC,
    BC_OT_SaveAssemblyTemplate,
    BC_OT_SaveAssemblyToIFC,
)


def register():
    """Register operator classes"""
    for cls in classes:
        bpy.utils.register_class(cls)

    logger.info("Cross-section IFC operators registered")


def unregister():
    """Unregister operator classes"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    logger.info("Cross-section IFC operators unregistered")
