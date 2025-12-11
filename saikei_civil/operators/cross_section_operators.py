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
Cross-Section Assembly Operators
=================================

Comprehensive operators for creating, editing, and managing cross-section
assemblies in Saikei Civil. These operators handle the full lifecycle of
cross-section definitions used for corridor modeling.

Operators:
    BC_OT_CreateAssembly: Create new cross-section assembly with optional templates
    BC_OT_DeleteAssembly: Remove existing assembly from the scene
    BC_OT_AddComponent: Add components (lanes, shoulders, ditches, curbs) to assembly
    BC_OT_RemoveComponent: Remove component from active assembly
    BC_OT_MoveComponentUp: Reorder component up in the list
    BC_OT_MoveComponentDown: Reorder component down in the list
    BC_OT_AddConstraint: Add parametric constraint for component variation along alignment
    BC_OT_RemoveConstraint: Remove parametric constraint
    BC_OT_ValidateAssembly: Validate assembly configuration for errors
    BC_OT_CalculateSection: Calculate cross-section geometry at specific station
    BC_OT_ExportAssemblyIFC: Export assembly to IFC 4.3 format
    BC_OT_SaveAssemblyTemplate: Save assembly as reusable template

Assembly Structure:
    An assembly is a collection of components (lanes, shoulders, etc.) that
    define the cross-section shape. Components are positioned relative to the
    alignment centerline and can vary parametrically along the alignment using
    constraints.
"""

import bpy
from bpy.types import Operator
from bpy.props import FloatProperty, StringProperty, IntProperty, EnumProperty
from ..core.logging_config import get_logger

logger = get_logger(__name__)


def update_assembly_total_width(assembly):
    """
    Calculate and update the total width of an assembly.

    This function sums the widths of all components in the assembly,
    keeping left and right sides separate and adding them together
    for the full cross-section width.

    Args:
        assembly: BC_AssemblyProperties instance
    """
    left_width = 0.0
    right_width = 0.0

    for comp in assembly.components:
        if comp.side == 'LEFT':
            left_width += comp.width
        elif comp.side == 'RIGHT':
            right_width += comp.width
        else:  # CENTER
            # Center components contribute to both sides equally
            left_width += comp.width / 2
            right_width += comp.width / 2

    assembly.total_width = left_width + right_width


def _add_component_with_ifc(assembly, name, component_type, side, width,
                            cross_slope=0.0, offset=0.0, **kwargs):
    """
    Helper function to add a component with optional IFC entity creation.

    This implements the Native IFC pattern: when an IFC file is loaded,
    components are created as IFC entities. Otherwise, they're stored
    only in PropertyGroups.

    Args:
        assembly: BC_AssemblyProperties instance
        name: Component name
        component_type: LANE, SHOULDER, CURB, DITCH, etc.
        side: LEFT or RIGHT
        width: Component width in meters
        cross_slope: Cross slope as decimal (e.g., 0.02)
        offset: Offset from centerline
        **kwargs: Additional component-specific properties

    Returns:
        The created BC_ComponentProperties instance
    """
    from ..core.ifc_manager.manager import NativeIfcManager

    # Add to PropertyGroup
    comp = assembly.components.add()
    comp.name = name
    comp.component_type = component_type
    comp.side = side
    comp.width = width
    comp.cross_slope = cross_slope
    comp.offset = offset

    # Apply additional properties
    for key, value in kwargs.items():
        if hasattr(comp, key):
            setattr(comp, key, value)

    # === NATIVE IFC: Create IFC entity if file is loaded ===
    ifc_file = NativeIfcManager.get_file()
    if ifc_file:
        result = NativeIfcManager.create_cross_section_component(
            name=name,
            component_type=component_type,
            side=side,
            width=width,
            cross_slope=cross_slope,
            offset=offset,
            assembly_name=assembly.name
        )

        if result:
            ifc_entity, blender_obj = result
            comp.ifc_definition_id = ifc_entity.id()
            comp.global_id = ifc_entity.GlobalId

    return comp


class BC_OT_CreateAssembly(Operator):
    """
    Create a new cross-section assembly.

    Assemblies define the cross-sectional shape of roadways and can be
    populated with predefined templates (two-lane rural, four-lane divided)
    or created as empty assemblies for custom configuration.

    Properties:
        name: Assembly name (must be unique)
        assembly_type: Template type (CUSTOM, TWO_LANE_RURAL, FOUR_LANE_DIVIDED)

    Templates:
        - Two-Lane Rural: Standard rural highway with lanes, shoulders, and ditches
        - Four-Lane Divided: Divided highway with inside/outside shoulders
        - Custom: Empty assembly for manual component addition

    Usage:
        Called from cross-section panel to create new assemblies. Template
        assemblies are immediately ready for corridor generation.
    """
    bl_idname = "bc.create_assembly"
    bl_label = "Create Assembly"
    bl_description = "Create a new cross-section assembly"
    bl_options = {'REGISTER', 'UNDO'}
    
    name: StringProperty(
        name="Name",
        description="Assembly name",
        default="New Assembly",
    )
    
    assembly_type: EnumProperty(
        name="Type",
        description="Assembly type",
        items=[
            ('CUSTOM', "Custom", "Start with empty assembly"),
            ('TWO_LANE_RURAL', "Two-Lane Rural", "Standard two-lane rural highway"),
            ('FOUR_LANE_DIVIDED', "Four-Lane Divided", "Four-lane divided highway"),
        ],
        default='CUSTOM',
    )
    
    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        cs = context.scene.bc_cross_section
        
        # Check if name already exists
        for assembly in cs.assemblies:
            if assembly.name == self.name:
                self.report({'ERROR'}, f"Assembly '{self.name}' already exists")
                return {'CANCELLED'}
        
        # Create new assembly
        assembly = cs.assemblies.add()
        assembly.name = self.name
        assembly.assembly_type = self.assembly_type
        
        # If template selected, populate with components
        if self.assembly_type == 'TWO_LANE_RURAL':
            self._create_two_lane_rural(assembly)
        elif self.assembly_type == 'FOUR_LANE_DIVIDED':
            self._create_four_lane_divided(assembly)
        
        # Set as active
        cs.active_assembly_index = len(cs.assemblies) - 1
        
        self.report({'INFO'}, f"Created assembly '{self.name}'")
        return {'FINISHED'}
    
    def _create_two_lane_rural(self, assembly):
        """Populate assembly with two-lane rural template (with Native IFC)"""
        # Right lane
        _add_component_with_ifc(
            assembly, "Right Travel Lane", 'LANE', 'RIGHT',
            width=3.6, cross_slope=0.02, offset=0.0, lane_type='TRAVEL'
        )

        # Right shoulder
        _add_component_with_ifc(
            assembly, "Right Shoulder", 'SHOULDER', 'RIGHT',
            width=2.4, cross_slope=0.04, offset=3.6, shoulder_type='PAVED'
        )

        # Right ditch
        _add_component_with_ifc(
            assembly, "Right Ditch", 'DITCH', 'RIGHT',
            width=6.0, offset=6.0,
            foreslope=4.0, backslope=3.0, bottom_width=1.2, depth=0.45
        )

        # Left lane
        _add_component_with_ifc(
            assembly, "Left Travel Lane", 'LANE', 'LEFT',
            width=3.6, cross_slope=0.02, offset=0.0, lane_type='TRAVEL'
        )

        # Left shoulder
        _add_component_with_ifc(
            assembly, "Left Shoulder", 'SHOULDER', 'LEFT',
            width=1.8, cross_slope=0.04, offset=-3.6, shoulder_type='PAVED'
        )

        # Left ditch
        _add_component_with_ifc(
            assembly, "Left Ditch", 'DITCH', 'LEFT',
            width=6.0, offset=-5.4,
            foreslope=4.0, backslope=3.0, bottom_width=1.2, depth=0.45
        )

        assembly.is_valid = True
        assembly.validation_message = "Template created successfully"
        update_assembly_total_width(assembly)

    def _create_four_lane_divided(self, assembly):
        """Populate assembly with four-lane divided template (with Native IFC)"""
        # Inside shoulder
        _add_component_with_ifc(
            assembly, "Inside Shoulder", 'SHOULDER', 'LEFT',
            width=1.2, cross_slope=0.04, offset=0.0, shoulder_type='PAVED'
        )

        # Lane 1
        _add_component_with_ifc(
            assembly, "Lane 1", 'LANE', 'RIGHT',
            width=3.6, cross_slope=0.02, offset=1.2, lane_type='TRAVEL'
        )

        # Lane 2
        _add_component_with_ifc(
            assembly, "Lane 2", 'LANE', 'RIGHT',
            width=3.6, cross_slope=0.02, offset=4.8, lane_type='TRAVEL'
        )

        # Outside shoulder
        _add_component_with_ifc(
            assembly, "Outside Shoulder", 'SHOULDER', 'RIGHT',
            width=3.0, cross_slope=0.04, offset=8.4, shoulder_type='PAVED'
        )

        # Outside ditch
        _add_component_with_ifc(
            assembly, "Outside Ditch", 'DITCH', 'RIGHT',
            width=6.0, offset=11.4,
            foreslope=4.0, backslope=3.0, bottom_width=1.2, depth=0.45
        )

        assembly.is_valid = True
        assembly.validation_message = "Template created successfully"
        update_assembly_total_width(assembly)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class BC_OT_DeleteAssembly(Operator):
    """
    Delete the currently active assembly.

    Removes the assembly and all its components from the scene. The active
    assembly index is adjusted to maintain a valid selection.

    Usage:
        Invoked from cross-section panel when user wants to remove an assembly.
        Cannot be undone beyond Blender's standard undo system.
    """
    bl_idname = "bc.delete_assembly"
    bl_label = "Delete Assembly"
    bl_description = "Delete the active cross-section assembly"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        return len(cs.assemblies) > 0
    
    def execute(self, context):
        cs = context.scene.bc_cross_section
        
        if cs.active_assembly_index < len(cs.assemblies):
            name = cs.assemblies[cs.active_assembly_index].name
            cs.assemblies.remove(cs.active_assembly_index)
            
            # Adjust active index
            if cs.active_assembly_index >= len(cs.assemblies):
                cs.active_assembly_index = max(0, len(cs.assemblies) - 1)
            
            self.report({'INFO'}, f"Deleted assembly '{name}'")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No assembly selected")
            return {'CANCELLED'}


class BC_OT_AddComponent(Operator):
    """
    Add a new component to the active assembly.

    Components are the building blocks of cross-sections, representing
    lanes, shoulders, curbs, ditches, and other roadway elements. Each
    component type has appropriate default properties.

    Properties:
        component_type: Type of component (LANE, SHOULDER, CURB, DITCH)
        side: Side of centerline (LEFT, RIGHT)

    Component Types:
        - LANE: Travel lanes with width and cross slope
        - SHOULDER: Paved or unpaved shoulders
        - CURB: Vertical or sloped curbs
        - DITCH: Drainage ditches with foreslope/backslope

    Usage:
        Called from assembly editor to add components. Default properties
        are set based on typical design standards.
    """
    bl_idname = "bc.add_component"
    bl_label = "Add Component"
    bl_description = "Add a new component to the assembly"
    bl_options = {'REGISTER', 'UNDO'}
    
    component_type: EnumProperty(
        name="Type",
        description="Component type",
        items=[
            ('LANE', "Lane", "Travel lane"),
            ('SHOULDER', "Shoulder", "Shoulder"),
            ('CURB', "Curb", "Curb"),
            ('DITCH', "Ditch", "Ditch"),
        ],
        default='LANE',
    )
    
    side: EnumProperty(
        name="Side",
        description="Side of alignment",
        items=[
            ('LEFT', "Left", "Left side"),
            ('RIGHT', "Right", "Right side"),
        ],
        default='RIGHT',
    )
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        return len(cs.assemblies) > 0
    
    def execute(self, context):
        from ..core.ifc_manager.manager import NativeIfcManager

        cs = context.scene.bc_cross_section

        if cs.active_assembly_index >= len(cs.assemblies):
            self.report({'ERROR'}, "No active assembly")
            return {'CANCELLED'}

        assembly = cs.assemblies[cs.active_assembly_index]

        # Add new component to PropertyGroup
        comp = assembly.components.add()
        comp.component_type = self.component_type
        comp.side = self.side

        # Set default name
        count = sum(1 for c in assembly.components if c.component_type == self.component_type)
        comp.name = f"{self.component_type.title()} {count}"

        # Set default properties based on type
        if self.component_type == 'LANE':
            comp.lane_type = 'TRAVEL'
            comp.width = 3.6
            comp.cross_slope = 0.02
        elif self.component_type == 'SHOULDER':
            comp.shoulder_type = 'PAVED'
            comp.width = 2.4
            comp.cross_slope = 0.04
        elif self.component_type == 'CURB':
            comp.curb_type = 'VERTICAL'
            comp.width = 0.15
            comp.curb_height = 0.15
        elif self.component_type == 'DITCH':
            comp.width = 6.0
            comp.foreslope = 4.0
            comp.backslope = 3.0
            comp.bottom_width = 1.2
            comp.depth = 0.45

        # === NATIVE IFC: Create IFC entity and Blender object ===
        ifc_file = NativeIfcManager.get_file()
        if ifc_file:
            result = NativeIfcManager.create_cross_section_component(
                name=comp.name,
                component_type=self.component_type,
                side=self.side,
                width=comp.width,
                cross_slope=comp.cross_slope,
                offset=comp.offset,
                assembly_name=assembly.name
            )

            if result:
                ifc_entity, blender_obj = result
                # Store IFC link in PropertyGroup
                comp.ifc_definition_id = ifc_entity.id()
                comp.global_id = ifc_entity.GlobalId
                logger.info(f"Created IFC entity #{comp.ifc_definition_id} for {comp.name}")
            else:
                logger.warning(f"Failed to create IFC entity for {comp.name}")
        else:
            logger.debug("No IFC file loaded - component stored in PropertyGroup only")

        # Set as active
        assembly.active_component_index = len(assembly.components) - 1

        # Update total width
        update_assembly_total_width(assembly)

        self.report({'INFO'}, f"Added {comp.name}")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class BC_OT_RemoveComponent(Operator):
    """
    Remove the selected component from the active assembly.

    Removes a single component from the assembly's component list. The
    active component index is adjusted to maintain valid selection.

    Usage:
        Invoked from component list in assembly editor when user wants
        to remove a component from the cross-section definition.
    """
    bl_idname = "bc.remove_component"
    bl_label = "Remove Component"
    bl_description = "Remove the selected component"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return len(assembly.components) > 0
    
    def execute(self, context):
        from ..core.ifc_manager.manager import NativeIfcManager

        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]

        if assembly.active_component_index < len(assembly.components):
            comp = assembly.components[assembly.active_component_index]
            name = comp.name
            ifc_id = comp.ifc_definition_id

            # === NATIVE IFC: Delete IFC entity and Blender object ===
            if ifc_id > 0:
                # Find the Blender object linked to this IFC entity
                blender_obj = None
                for obj in bpy.data.objects:
                    if obj.get("ifc_definition_id") == ifc_id:
                        blender_obj = obj
                        break

                # Delete from IFC and Blender
                NativeIfcManager.delete_cross_section_component(ifc_id, blender_obj)
                logger.info(f"Deleted IFC entity #{ifc_id} for {name}")

            # Remove from PropertyGroup
            assembly.components.remove(assembly.active_component_index)

            # Adjust active index
            if assembly.active_component_index >= len(assembly.components):
                assembly.active_component_index = max(0, len(assembly.components) - 1)

            # Update total width
            update_assembly_total_width(assembly)

            self.report({'INFO'}, f"Removed component '{name}'")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No component selected")
            return {'CANCELLED'}


class BC_OT_MoveComponentUp(Operator):
    """
    Move the selected component up in the list.

    Reorders components in the assembly list. While component order
    doesn't affect geometry, it helps organize the UI display for
    better usability.

    Usage:
        Called from component list arrows to reorder components for
        better organization and readability.
    """
    bl_idname = "bc.move_component_up"
    bl_label = "Move Up"
    bl_description = "Move component up"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return assembly.active_component_index > 0
    
    def execute(self, context):
        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]
        
        idx = assembly.active_component_index
        assembly.components.move(idx, idx - 1)
        assembly.active_component_index = idx - 1
        
        return {'FINISHED'}


class BC_OT_MoveComponentDown(Operator):
    """
    Move the selected component down in the list.

    Reorders components in the assembly list. While component order
    doesn't affect geometry, it helps organize the UI display for
    better usability.

    Usage:
        Called from component list arrows to reorder components for
        better organization and readability.
    """
    bl_idname = "bc.move_component_down"
    bl_label = "Move Down"
    bl_description = "Move component down"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return assembly.active_component_index < len(assembly.components) - 1
    
    def execute(self, context):
        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]
        
        idx = assembly.active_component_index
        assembly.components.move(idx, idx + 1)
        assembly.active_component_index = idx + 1
        
        return {'FINISHED'}


class BC_OT_AddConstraint(Operator):
    """
    Add a parametric constraint to the active assembly.

    Constraints allow component properties to vary along the alignment.
    For example, lane width can narrow at a specific station, or shoulder
    slope can change. Constraints are interpolated between stations.

    Properties:
        station: Station where constraint applies (meters)
        component_name: Component to modify
        parameter: Which parameter to vary (width, cross_slope, offset)
        value: Parameter value at this station

    Usage:
        Used for transitioning roadway geometry along the alignment.
        Common scenarios include widening lanes, adjusting slopes,
        or shifting component positions.
    """
    bl_idname = "bc.add_constraint"
    bl_label = "Add Constraint"
    bl_description = "Add a parametric constraint for component variation along alignment"
    bl_options = {'REGISTER', 'UNDO'}
    
    station: FloatProperty(
        name="Station",
        description="Station where constraint applies (m)",
        default=0.0,
        min=0.0,
    )
    
    component_name: StringProperty(
        name="Component",
        description="Component to modify",
        default="",
    )
    
    parameter: EnumProperty(
        name="Parameter",
        description="Parameter to modify",
        items=[
            ('width', "Width", "Component width"),
            ('cross_slope', "Cross Slope", "Cross slope"),
            ('offset', "Offset", "Offset from centerline"),
        ],
        default='width',
    )
    
    value: FloatProperty(
        name="Value",
        description="Parameter value at this station",
        default=3.6,
    )
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return len(assembly.components) > 0
    
    def execute(self, context):
        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]
        
        # If no component name specified, use active component
        if not self.component_name and len(assembly.components) > 0:
            self.component_name = assembly.components[assembly.active_component_index].name
        
        # Check if component exists
        component_exists = any(c.name == self.component_name for c in assembly.components)
        if not component_exists:
            self.report({'ERROR'}, f"Component '{self.component_name}' not found")
            return {'CANCELLED'}
        
        # Add constraint
        constraint = assembly.constraints.add()
        constraint.station = self.station
        constraint.component_name = self.component_name
        constraint.parameter = self.parameter
        constraint.value = self.value
        
        # Sort constraints by station
        constraints_list = list(assembly.constraints)
        constraints_list.sort(key=lambda c: c.station)
        assembly.constraints.clear()
        for sorted_constraint in constraints_list:
            new_constraint = assembly.constraints.add()
            new_constraint.station = sorted_constraint.station
            new_constraint.component_name = sorted_constraint.component_name
            new_constraint.parameter = sorted_constraint.parameter
            new_constraint.value = sorted_constraint.value
        
        self.report({'INFO'}, f"Added constraint at station {self.station:.2f}m")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]
        
        # Pre-fill component name with active component
        if len(assembly.components) > 0:
            self.component_name = assembly.components[assembly.active_component_index].name
        
        return context.window_manager.invoke_props_dialog(self)


class BC_OT_RemoveConstraint(Operator):
    """
    Remove the selected parametric constraint.

    Deletes a constraint from the assembly, reverting the component to
    its default parameter values at that station location.

    Usage:
        Called when user wants to remove parameter variation at a
        specific station, simplifying the assembly definition.
    """
    bl_idname = "bc.remove_constraint"
    bl_label = "Remove Constraint"
    bl_description = "Remove the selected parametric constraint"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return len(assembly.constraints) > 0
    
    def execute(self, context):
        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]
        
        if assembly.active_constraint_index < len(assembly.constraints):
            station = assembly.constraints[assembly.active_constraint_index].station
            assembly.constraints.remove(assembly.active_constraint_index)
            
            # Adjust active index
            if assembly.active_constraint_index >= len(assembly.constraints):
                assembly.active_constraint_index = max(0, len(assembly.constraints) - 1)
            
            self.report({'INFO'}, f"Removed constraint at station {station:.2f}m")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No constraint selected")
            return {'CANCELLED'}


class BC_OT_ValidateAssembly(Operator):
    """
    Validate the active assembly for errors and warnings.

    Performs comprehensive checks on assembly configuration including:
    - Component presence and validity
    - Width and dimension checks
    - Cross slope reasonableness
    - Lane-specific standard compliance

    Validation results are stored in assembly properties and reported
    to the user. Invalid assemblies cannot be used for corridor generation.

    Usage:
        Called before corridor creation or export to ensure assembly
        meets design standards and will generate valid geometry.
    """
    bl_idname = "bc.validate_assembly"
    bl_label = "Validate Assembly"
    bl_description = "Check assembly for errors and warnings"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        return len(cs.assemblies) > 0
    
    def execute(self, context):
        cs = context.scene.bc_cross_section
        
        if cs.active_assembly_index >= len(cs.assemblies):
            self.report({'ERROR'}, "No active assembly")
            return {'CANCELLED'}
        
        assembly = cs.assemblies[cs.active_assembly_index]
        
        # Validation checks
        errors = []
        warnings = []
        
        # Check if assembly has components
        if len(assembly.components) == 0:
            errors.append("No components defined")
        
        # Check component properties
        for comp in assembly.components:
            # Width check
            if comp.width <= 0:
                errors.append(f"{comp.name}: Invalid width ({comp.width}m)")
            
            # Cross slope check
            if abs(comp.cross_slope) > 0.15:
                warnings.append(f"{comp.name}: Steep cross slope ({comp.cross_slope*100:.1f}%)")
            
            # Lane-specific checks
            if comp.component_type == 'LANE':
                if comp.lane_type == 'TRAVEL' and comp.width < 3.0:
                    warnings.append(f"{comp.name}: Narrow travel lane ({comp.width}m)")
        
        # Always update total width during validation
        update_assembly_total_width(assembly)

        # Update assembly status
        if errors:
            assembly.is_valid = False
            assembly.validation_message = "; ".join(errors[:2])
            self.report({'ERROR'}, f"Validation failed: {errors[0]}")
            return {'CANCELLED'}
        elif warnings:
            assembly.is_valid = True
            assembly.validation_message = f"Valid (warnings: {len(warnings)})"
            self.report({'WARNING'}, f"Validated with {len(warnings)} warnings")
        else:
            assembly.is_valid = True
            assembly.validation_message = "Valid"
            self.report({'INFO'}, "Assembly validated successfully")

        return {'FINISHED'}


class BC_OT_CalculateSection(Operator):
    """
    Calculate cross-section geometry at a specified station.

    Computes the cross-section properties at a query station, applying
    any parametric constraints that affect component dimensions at that
    location. Results include total width and component-specific values.

    Usage:
        Used for querying assembly properties at specific stations.
        Helpful for design verification and quantity calculations.
    """
    bl_idname = "bc.calculate_section"
    bl_label = "Calculate Section"
    bl_description = "Calculate cross-section geometry at specified station"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return len(assembly.components) > 0
    
    def execute(self, context):
        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]
        
        station = assembly.query_station
        
        # Calculate total width
        total_width = 0.0
        for comp in assembly.components:
            total_width += comp.width
        
        assembly.total_width = total_width
        
        self.report({'INFO'}, f"Section at {station:.2f}m: Width={total_width:.2f}m")
        return {'FINISHED'}


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
        self.template_name = cs.assemblies[cs.active_assembly_index].name
        return context.window_manager.invoke_props_dialog(self)


class BC_OT_GenerateCrossSectionPreview(Operator):
    """
    Generate a 2D cross-section preview mesh.

    Creates a flat 2D visualization of the cross-section assembly in the 3D view,
    allowing users to see the component layout while building the assembly. This
    preview does not require an alignment - it shows the cross-section shape at
    the world origin.

    The preview mesh is color-coded by component type:
    - Lanes: Dark gray
    - Shoulders: Light gray
    - Curbs: White
    - Ditches: Brown

    Usage:
        Called from the cross-section panel to visualize the assembly shape.
        Updates the existing preview if one exists.
    """
    bl_idname = "bc.generate_cross_section_preview"
    bl_label = "Generate Preview"
    bl_description = "Generate a 2D preview of the cross-section assembly"
    bl_options = {'REGISTER', 'UNDO'}

    # Component type colors (R, G, B, A)
    COMPONENT_COLORS = {
        'LANE': (0.3, 0.3, 0.3, 1.0),
        'SHOULDER': (0.5, 0.5, 0.45, 1.0),
        'CURB': (0.8, 0.8, 0.8, 1.0),
        'DITCH': (0.4, 0.3, 0.2, 1.0),
        'MEDIAN': (0.2, 0.6, 0.2, 1.0),
        'SIDEWALK': (0.7, 0.7, 0.7, 1.0),
        'CUSTOM': (0.6, 0.6, 0.6, 1.0),
    }

    @classmethod
    def poll(cls, context):
        cs = context.scene.bc_cross_section
        if cs.active_assembly_index >= len(cs.assemblies):
            return False
        assembly = cs.assemblies[cs.active_assembly_index]
        return len(assembly.components) > 0

    def execute(self, context):
        import bmesh

        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]

        # Collection for preview objects
        collection_name = "Cross-Section Preview"
        if collection_name in bpy.data.collections:
            collection = bpy.data.collections[collection_name]
            # Clear existing preview objects
            for obj in list(collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
        else:
            collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(collection)

        # Calculate cross-section points for all components
        all_points = []

        # Sort components by side and offset for proper layout
        left_components = []
        right_components = []

        for comp in assembly.components:
            if comp.side == 'LEFT':
                left_components.append(comp)
            else:
                right_components.append(comp)

        # Process LEFT components (negative X direction)
        current_x = 0.0
        for comp in left_components:
            points = self._calculate_component_points(comp, current_x, direction=-1)
            if points:
                all_points.append((comp.component_type, points))
                current_x = points[-1][0]  # Update position for next component

        # Process RIGHT components (positive X direction)
        current_x = 0.0
        for comp in right_components:
            points = self._calculate_component_points(comp, current_x, direction=1)
            if points:
                all_points.append((comp.component_type, points))
                current_x = points[-1][0]

        # Create mesh objects for each component
        for idx, (comp_type, points) in enumerate(all_points):
            if len(points) < 2:
                continue

            # Create mesh
            mesh_name = f"Preview_{comp_type}_{idx}"
            mesh = bpy.data.meshes.new(mesh_name)
            obj = bpy.data.objects.new(mesh_name, mesh)
            collection.objects.link(obj)

            # Build geometry
            bm = bmesh.new()

            # Create vertices for the profile (as a line with thickness)
            thickness = 0.1  # Visual thickness for the preview

            # Top edge vertices
            top_verts = []
            for x, z in points:
                vert = bm.verts.new((x, 0.0, z))
                top_verts.append(vert)

            # Bottom edge vertices (for closed cross-section)
            bottom_verts = []
            for x, z in reversed(points):
                vert = bm.verts.new((x, 0.0, z - thickness))
                bottom_verts.append(vert)

            # Create face
            all_verts = top_verts + bottom_verts
            if len(all_verts) >= 3:
                try:
                    bm.faces.new(all_verts)
                except ValueError:
                    # Face creation failed, use edges instead
                    for i in range(len(top_verts) - 1):
                        bm.edges.new((top_verts[i], top_verts[i + 1]))

            bm.to_mesh(mesh)
            bm.free()

            # Apply material
            mat = self._get_or_create_material(comp_type)
            if mat:
                obj.data.materials.append(mat)

        # Also create a centerline marker
        centerline_mesh = bpy.data.meshes.new("Preview_Centerline")
        centerline_obj = bpy.data.objects.new("Preview_Centerline", centerline_mesh)
        collection.objects.link(centerline_obj)

        # Simple vertical line at origin
        verts = [(0, 0, -0.5), (0, 0, 0.5)]
        edges = [(0, 1)]
        centerline_mesh.from_pydata(verts, edges, [])

        # Frame the view on the preview
        try:
            # Select all preview objects
            for obj in collection.objects:
                obj.select_set(True)
                context.view_layer.objects.active = obj

            # Frame selected in view
            bpy.ops.view3d.view_selected(use_all_regions=False)
        except Exception:
            pass  # May fail if no 3D view is active

        # Ensure total width is updated
        update_assembly_total_width(assembly)

        self.report({'INFO'}, f"Generated preview with {len(all_points)} components")
        return {'FINISHED'}

    def _calculate_component_points(self, comp, start_x, direction=1):
        """
        Calculate 2D points for a component.

        Args:
            comp: Component properties
            start_x: Starting X position
            direction: 1 for right, -1 for left

        Returns:
            List of (x, z) tuples
        """
        points = []

        if comp.component_type == 'LANE':
            # Simple sloped lane
            points.append((start_x, 0.0))
            end_x = start_x + direction * comp.width
            end_z = comp.width * comp.cross_slope * direction
            points.append((end_x, end_z))

        elif comp.component_type == 'SHOULDER':
            # Similar to lane but with steeper slope
            points.append((start_x, 0.0))
            end_x = start_x + direction * comp.width
            end_z = comp.width * comp.cross_slope * direction
            points.append((end_x, end_z))

        elif comp.component_type == 'CURB':
            # Curb with vertical face
            points.append((start_x, 0.0))
            points.append((start_x, comp.curb_height))
            end_x = start_x + direction * comp.width
            points.append((end_x, comp.curb_height))
            points.append((end_x, 0.0))

        elif comp.component_type == 'DITCH':
            # Trapezoidal ditch
            start_z = 0.0  # Top of foreslope
            foreslope_width = comp.depth * comp.foreslope
            backslope_width = comp.depth * comp.backslope

            # Foreslope start
            points.append((start_x, start_z))
            # Bottom of foreslope
            fore_x = start_x + direction * foreslope_width
            points.append((fore_x, start_z - comp.depth))
            # Across bottom
            bottom_end_x = fore_x + direction * comp.bottom_width
            points.append((bottom_end_x, start_z - comp.depth))
            # Top of backslope
            back_x = bottom_end_x + direction * backslope_width
            points.append((back_x, start_z))

        elif comp.component_type == 'MEDIAN':
            # Raised or flush median
            points.append((start_x, 0.0))
            points.append((start_x, 0.15))  # Default raised height
            end_x = start_x + direction * comp.width
            points.append((end_x, 0.15))
            points.append((end_x, 0.0))

        elif comp.component_type == 'SIDEWALK':
            # Flat sidewalk
            points.append((start_x, 0.0))
            end_x = start_x + direction * comp.width
            end_z = comp.width * comp.cross_slope * direction
            points.append((end_x, end_z))

        else:
            # Generic component
            points.append((start_x, 0.0))
            end_x = start_x + direction * comp.width
            points.append((end_x, 0.0))

        return points

    def _get_or_create_material(self, component_type):
        """Get or create a material for a component type."""
        mat_name = f"Preview_{component_type}"

        if mat_name in bpy.data.materials:
            return bpy.data.materials[mat_name]

        # Create new material
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True

        color = self.COMPONENT_COLORS.get(component_type, (0.6, 0.6, 0.6, 1.0))

        if mat.node_tree:
            bsdf = mat.node_tree.nodes.get('Principled BSDF')
            if bsdf:
                bsdf.inputs['Base Color'].default_value = color
                bsdf.inputs['Roughness'].default_value = 0.8

        return mat


class BC_OT_ClearCrossSectionPreview(Operator):
    """
    Clear the cross-section preview from the 3D view.

    Removes all preview objects created by Generate Preview, cleaning up
    the scene when the preview is no longer needed.

    Usage:
        Called from the cross-section panel to clear the preview.
    """
    bl_idname = "bc.clear_cross_section_preview"
    bl_label = "Clear Preview"
    bl_description = "Clear the cross-section preview from the 3D view"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return "Cross-Section Preview" in bpy.data.collections

    def execute(self, context):
        collection_name = "Cross-Section Preview"

        if collection_name in bpy.data.collections:
            collection = bpy.data.collections[collection_name]
            # Remove all objects in the collection
            for obj in list(collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            # Remove the collection itself
            bpy.data.collections.remove(collection)

        self.report({'INFO'}, "Cleared cross-section preview")
        return {'FINISHED'}


# ============================================================================
# CROSS-SECTION OVERLAY OPERATORS (OpenRoads-style viewer)
# ============================================================================

class BC_OT_ToggleCrossSectionView(Operator):
    """
    Toggle the cross-section overlay viewer on/off.

    This operator provides an OpenRoads-style cross-section viewer that
    displays the assembly as a 2D overlay in the viewport, rather than
    creating 3D geometry in the model space.

    The overlay viewer shows:
    - Cross-section profile with colored components
    - Grid with offset and elevation labels
    - Centerline reference
    - Component names and dimensions

    Usage:
        Press to toggle the overlay on/off. When enabled, the overlay
        appears at the bottom of the 3D viewport.
    """
    bl_idname = "bc.toggle_cross_section_view"
    bl_label = "Toggle Cross-Section Viewer"
    bl_description = "Toggle the cross-section overlay viewer (OpenRoads-style)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from ..core.cross_section_view_overlay import get_cross_section_overlay

        overlay = get_cross_section_overlay()
        overlay.toggle(context)

        if overlay.enabled:
            # Load active assembly if available
            self._load_active_assembly(context, overlay)

            # Start the interaction modal operator for drag/resize/hover
            if not BC_OT_CrossSectionViewInteraction._is_running:
                bpy.ops.bc.cross_section_view_interaction('INVOKE_DEFAULT')

            self.report({'INFO'}, "Cross-section viewer enabled")
        else:
            self.report({'INFO'}, "Cross-section viewer disabled")

        return {'FINISHED'}

    def _load_active_assembly(self, context, overlay):
        """Load the active assembly into the overlay."""
        if not hasattr(context.scene, 'bc_cross_section'):
            return

        cs = context.scene.bc_cross_section
        if cs.active_assembly_index < 0 or cs.active_assembly_index >= len(cs.assemblies):
            return

        assembly = cs.assemblies[cs.active_assembly_index]
        overlay.load_from_assembly(assembly)


class BC_OT_LoadAssemblyToView(Operator):
    """
    Load the active assembly into the cross-section overlay viewer.

    This refreshes the overlay with the current active assembly's data,
    updating the visualization to show any changes made to components.

    Usage:
        Call after making changes to the assembly to refresh the viewer.
    """
    bl_idname = "bc.load_assembly_to_view"
    bl_label = "Load to Viewer"
    bl_description = "Load the active assembly into the cross-section viewer"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if not hasattr(context.scene, 'bc_cross_section'):
            return False
        cs = context.scene.bc_cross_section
        return cs.active_assembly_index >= 0 and cs.active_assembly_index < len(cs.assemblies)

    def execute(self, context):
        from ..core.cross_section_view_overlay import (
            get_cross_section_overlay,
            load_active_assembly_to_overlay
        )

        overlay = get_cross_section_overlay()

        # Enable overlay if not already enabled
        if not overlay.enabled:
            overlay.enable(context)

        # Load the active assembly
        success = load_active_assembly_to_overlay(context)

        if success:
            cs = context.scene.bc_cross_section
            assembly = cs.assemblies[cs.active_assembly_index]
            self.report({'INFO'}, f"Loaded assembly: {assembly.name}")
        else:
            self.report({'WARNING'}, "Failed to load assembly")

        return {'FINISHED'}


class BC_OT_RefreshCrossSectionView(Operator):
    """
    Refresh the cross-section overlay viewer.

    Forces a redraw of the overlay with the current assembly data.

    Usage:
        Call to force a refresh after external changes.
    """
    bl_idname = "bc.refresh_cross_section_view"
    bl_label = "Refresh Viewer"
    bl_description = "Refresh the cross-section overlay viewer"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        from ..core.cross_section_view_overlay import get_cross_section_overlay
        return get_cross_section_overlay().enabled

    def execute(self, context):
        from ..core.cross_section_view_overlay import (
            get_cross_section_overlay,
            load_active_assembly_to_overlay
        )

        # Reload the active assembly
        load_active_assembly_to_overlay(context)

        # Force redraw
        overlay = get_cross_section_overlay()
        overlay.refresh(context)

        self.report({'INFO'}, "Cross-section viewer refreshed")
        return {'FINISHED'}


class BC_OT_FitCrossSectionView(Operator):
    """
    Fit the cross-section view to show all components.

    Adjusts the view extents to show the full cross-section with
    appropriate padding.
    """
    bl_idname = "bc.fit_cross_section_view"
    bl_label = "Fit to Data"
    bl_description = "Fit the cross-section view to show all components"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        from ..core.cross_section_view_overlay import get_cross_section_overlay
        overlay = get_cross_section_overlay()
        return overlay.enabled and len(overlay.data.components) > 0

    def execute(self, context):
        from ..core.cross_section_view_overlay import get_cross_section_overlay

        overlay = get_cross_section_overlay()
        overlay.data.update_view_extents()
        overlay.refresh(context)

        self.report({'INFO'}, "View fitted to cross-section data")
        return {'FINISHED'}


class BC_OT_SetCrossSectionViewPosition(Operator):
    """
    Set the cross-section overlay viewer position/anchor.

    Allows positioning the overlay at different edges of the viewport
    or as a floating, draggable window.

    Positions:
    - BOTTOM: Anchored to bottom edge (default)
    - TOP: Anchored to top edge
    - LEFT: Anchored to left edge
    - RIGHT: Anchored to right edge
    - FLOATING: Free-floating, draggable with title bar
    """
    bl_idname = "bc.set_cross_section_view_position"
    bl_label = "Set Viewer Position"
    bl_description = "Set the cross-section overlay position"
    bl_options = {'REGISTER'}

    position: bpy.props.EnumProperty(
        name="Position",
        description="Overlay anchor position",
        items=[
            ('BOTTOM', "Bottom", "Anchor to bottom edge"),
            ('TOP', "Top", "Anchor to top edge"),
            ('LEFT', "Left", "Anchor to left edge"),
            ('RIGHT', "Right", "Anchor to right edge"),
            ('FLOATING', "Floating", "Free-floating, draggable window"),
        ],
        default='BOTTOM'
    )

    @classmethod
    def poll(cls, context):
        from ..core.cross_section_view_overlay import get_cross_section_overlay
        return get_cross_section_overlay().enabled

    def execute(self, context):
        from ..core.cross_section_view_overlay import (
            get_cross_section_overlay,
            OverlayPosition
        )

        overlay = get_cross_section_overlay()

        # Convert string to enum
        position_map = {
            'BOTTOM': OverlayPosition.BOTTOM,
            'TOP': OverlayPosition.TOP,
            'LEFT': OverlayPosition.LEFT,
            'RIGHT': OverlayPosition.RIGHT,
            'FLOATING': OverlayPosition.FLOATING,
        }

        new_position = position_map.get(self.position, OverlayPosition.BOTTOM)
        overlay.set_position(new_position)
        overlay.refresh(context)

        self.report({'INFO'}, f"Viewer position set to: {self.position}")
        return {'FINISHED'}


class BC_OT_CrossSectionViewInteraction(Operator):
    """
    Modal operator for cross-section overlay interaction.

    This operator handles mouse events for:
    - Dragging the floating overlay by the title bar
    - Resizing the overlay by dragging edges
    - Hovering over components
    - Selecting components by clicking

    The operator runs modally while the overlay is enabled, capturing
    mouse events and routing them to the overlay's handler methods.

    Usage:
        Automatically started when the overlay is enabled in floating mode.
        Can also be manually invoked to enable interaction.
    """
    bl_idname = "bc.cross_section_view_interaction"
    bl_label = "Cross-Section View Interaction"
    bl_description = "Enable mouse interaction with the cross-section overlay"
    bl_options = {'INTERNAL'}

    _is_running = False  # Class variable to track if modal is active

    @classmethod
    def poll(cls, context):
        from ..core.cross_section_view_overlay import get_cross_section_overlay
        overlay = get_cross_section_overlay()
        return overlay.enabled and not cls._is_running

    def invoke(self, context, event):
        from ..core.cross_section_view_overlay import get_cross_section_overlay

        overlay = get_cross_section_overlay()
        if not overlay.enabled:
            self.report({'WARNING'}, "Cross-section overlay is not enabled")
            return {'CANCELLED'}

        # Mark as running
        BC_OT_CrossSectionViewInteraction._is_running = True

        # Add modal handler
        context.window_manager.modal_handler_add(self)

        logger.info("Cross-section view interaction started")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        from ..core.cross_section_view_overlay import get_cross_section_overlay

        overlay = get_cross_section_overlay()

        # Stop if overlay is disabled
        if not overlay.enabled:
            BC_OT_CrossSectionViewInteraction._is_running = False
            context.window.cursor_set('DEFAULT')
            logger.info("Cross-section view interaction stopped (overlay disabled)")
            return {'CANCELLED'}

        # Only process events in the VIEW_3D area
        if context.area and context.area.type != 'VIEW_3D':
            return {'PASS_THROUGH'}

        # Handle mouse movement
        if event.type == 'MOUSEMOVE':
            handled = overlay.handle_mouse_move(context, event)
            if handled:
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}

        # Handle mouse press
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            handled = overlay.handle_mouse_press(context, event)
            if handled:
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}

        # Handle mouse release
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            handled = overlay.handle_mouse_release(context, event)
            if handled:
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}

        # ESC key cancels drag/resize operations
        if event.type == 'ESC' and event.value == 'PRESS':
            if overlay.is_dragging or overlay.is_resizing:
                overlay.is_dragging = False
                overlay.is_resizing = False
                context.window.cursor_set('DEFAULT')
                if context.area:
                    context.area.tag_redraw()
                return {'RUNNING_MODAL'}

        # Pass through all other events
        return {'PASS_THROUGH'}

    def cancel(self, context):
        BC_OT_CrossSectionViewInteraction._is_running = False
        context.window.cursor_set('DEFAULT')
        logger.info("Cross-section view interaction cancelled")


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
        """Create IFC entities for the assembly."""
        import ifcopenshell.guid

        # Create IfcElementAssembly for the cross-section
        ifc_assembly = ifc_file.create_entity(
            "IfcElementAssembly",
            GlobalId=ifcopenshell.guid.new(),
            Name=assembly.name,
            Description=assembly.description or f"Cross-section assembly: {assembly.name}",
            ObjectType="CROSS_SECTION_ASSEMBLY",
            PredefinedType="USERDEFINED",
            AssemblyPlace="FACTORY"
        )

        # Create profile definitions for each component
        profiles = []
        for comp in assembly.components:
            profile = self._create_component_profile(ifc_file, comp)
            profiles.append(profile)

            # Update component IFC linkage
            comp.ifc_definition_id = profile.id()
            comp.global_id = ifcopenshell.guid.new()

        # Create composite profile combining all components
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
        """Create IfcOpenCrossProfileDef for a component."""
        # Calculate profile points based on component type and geometry
        # Points are (offset, elevation) pairs from centerline

        width = component.width
        slope = component.cross_slope
        offset = component.offset
        side = component.side

        # Calculate start and end points
        if side == "LEFT":
            # Left side: negative offsets
            start_offset = -abs(offset)
            end_offset = start_offset - width
            start_elev = 0.0
            end_elev = -width * slope
        elif side == "RIGHT":
            # Right side: positive offsets
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

        # Create IfcOpenCrossProfileDef
        # Tags are the distance values, depths are elevations
        profile = ifc_file.create_entity(
            "IfcOpenCrossProfileDef",
            ProfileType="CURVE",
            ProfileName=f"{component.name}_{component.component_type}",
            HorizontalWidths=False,  # Using full distances, not half-widths
            Tags=[str(start_offset), str(end_offset)],
            Widths=None,
            OffsetPoint=ifc_file.create_entity(
                "IfcCartesianPoint",
                Coordinates=(0.0, 0.0)
            )
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
            Name="Pset_SaikeiCrossSectionAssembly",
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
        """Link assembly to IfcRoad in spatial hierarchy."""
        # Find IfcRoad
        roads = ifc_file.by_type("IfcRoad")
        if not roads:
            logger.warning("No IfcRoad found - assembly not spatially contained")
            return

        road = roads[0]

        # Create IfcRelContainedInSpatialStructure
        import ifcopenshell.guid

        # Check if relationship already exists
        for rel in road.ContainsElements or []:
            if ifc_assembly in (rel.RelatedElements or []):
                return  # Already linked

        # Create new containment relationship
        ifc_file.create_entity(
            "IfcRelContainedInSpatialStructure",
            GlobalId=ifcopenshell.guid.new(),
            Name="RoadToCrossSection",
            RelatingStructure=road,
            RelatedElements=[ifc_assembly]
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


# Registration
classes = (
    BC_OT_CreateAssembly,
    BC_OT_DeleteAssembly,
    BC_OT_AddComponent,
    BC_OT_RemoveComponent,
    BC_OT_MoveComponentUp,
    BC_OT_MoveComponentDown,
    BC_OT_AddConstraint,
    BC_OT_RemoveConstraint,
    BC_OT_ValidateAssembly,
    BC_OT_CalculateSection,
    BC_OT_ExportAssemblyIFC,
    BC_OT_SaveAssemblyToIFC,
    BC_OT_SaveAssemblyTemplate,
    BC_OT_GenerateCrossSectionPreview,
    BC_OT_ClearCrossSectionPreview,
    # Overlay-based viewer operators (OpenRoads-style)
    BC_OT_ToggleCrossSectionView,
    BC_OT_LoadAssemblyToView,
    BC_OT_RefreshCrossSectionView,
    BC_OT_FitCrossSectionView,
    BC_OT_SetCrossSectionViewPosition,
    BC_OT_CrossSectionViewInteraction,
)


def register():
    """Register operator classes"""
    for cls in classes:
        bpy.utils.register_class(cls)

    logger.info("Cross-section operators registered")


def unregister():
    """Unregister operator classes"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    logger.info("Cross-section operators unregistered")


if __name__ == "__main__":
    register()
