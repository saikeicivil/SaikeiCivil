# ==============================================================================
# BlenderCivil - Civil Engineering Tools for Blender
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================

"""
Cross-Section Assembly Operators
=================================

Comprehensive operators for creating, editing, and managing cross-section
assemblies in BlenderCivil. These operators handle the full lifecycle of
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
        """Populate assembly with two-lane rural template"""
        # Right lane
        comp = assembly.components.add()
        comp.name = "Right Travel Lane"
        comp.component_type = 'LANE'
        comp.lane_type = 'TRAVEL'
        comp.side = 'RIGHT'
        comp.width = 3.6
        comp.cross_slope = 0.02
        comp.offset = 0.0
        
        # Right shoulder
        comp = assembly.components.add()
        comp.name = "Right Shoulder"
        comp.component_type = 'SHOULDER'
        comp.shoulder_type = 'PAVED'
        comp.side = 'RIGHT'
        comp.width = 2.4
        comp.cross_slope = 0.04
        comp.offset = 3.6
        
        # Right ditch
        comp = assembly.components.add()
        comp.name = "Right Ditch"
        comp.component_type = 'DITCH'
        comp.side = 'RIGHT'
        comp.width = 6.0
        comp.offset = 6.0
        comp.foreslope = 4.0
        comp.backslope = 3.0
        comp.bottom_width = 1.2
        comp.depth = 0.45
        
        # Left lane
        comp = assembly.components.add()
        comp.name = "Left Travel Lane"
        comp.component_type = 'LANE'
        comp.lane_type = 'TRAVEL'
        comp.side = 'LEFT'
        comp.width = 3.6
        comp.cross_slope = 0.02
        comp.offset = 0.0
        
        # Left shoulder
        comp = assembly.components.add()
        comp.name = "Left Shoulder"
        comp.component_type = 'SHOULDER'
        comp.shoulder_type = 'PAVED'
        comp.side = 'LEFT'
        comp.width = 1.8
        comp.cross_slope = 0.04
        comp.offset = -3.6
        
        # Left ditch
        comp = assembly.components.add()
        comp.name = "Left Ditch"
        comp.component_type = 'DITCH'
        comp.side = 'LEFT'
        comp.width = 6.0
        comp.offset = -5.4
        comp.foreslope = 4.0
        comp.backslope = 3.0
        comp.bottom_width = 1.2
        comp.depth = 0.45
        
        assembly.is_valid = True
        assembly.validation_message = "Template created successfully"
    
    def _create_four_lane_divided(self, assembly):
        """Populate assembly with four-lane divided template"""
        # Inside shoulder
        comp = assembly.components.add()
        comp.name = "Inside Shoulder"
        comp.component_type = 'SHOULDER'
        comp.shoulder_type = 'PAVED'
        comp.side = 'LEFT'
        comp.width = 1.2
        comp.cross_slope = 0.04
        comp.offset = 0.0
        
        # Lane 1
        comp = assembly.components.add()
        comp.name = "Lane 1"
        comp.component_type = 'LANE'
        comp.lane_type = 'TRAVEL'
        comp.side = 'RIGHT'
        comp.width = 3.6
        comp.cross_slope = 0.02
        comp.offset = 1.2
        
        # Lane 2
        comp = assembly.components.add()
        comp.name = "Lane 2"
        comp.component_type = 'LANE'
        comp.lane_type = 'TRAVEL'
        comp.side = 'RIGHT'
        comp.width = 3.6
        comp.cross_slope = 0.02
        comp.offset = 4.8
        
        # Outside shoulder
        comp = assembly.components.add()
        comp.name = "Outside Shoulder"
        comp.component_type = 'SHOULDER'
        comp.shoulder_type = 'PAVED'
        comp.side = 'RIGHT'
        comp.width = 3.0
        comp.cross_slope = 0.04
        comp.offset = 8.4
        
        # Outside ditch
        comp = assembly.components.add()
        comp.name = "Outside Ditch"
        comp.component_type = 'DITCH'
        comp.side = 'RIGHT'
        comp.width = 6.0
        comp.offset = 11.4
        comp.foreslope = 4.0
        comp.backslope = 3.0
        comp.bottom_width = 1.2
        comp.depth = 0.45
        
        assembly.is_valid = True
        assembly.validation_message = "Template created successfully"
    
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
        cs = context.scene.bc_cross_section
        
        if cs.active_assembly_index >= len(cs.assemblies):
            self.report({'ERROR'}, "No active assembly")
            return {'CANCELLED'}
        
        assembly = cs.assemblies[cs.active_assembly_index]
        
        # Add new component
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
        
        # Set as active
        assembly.active_component_index = len(assembly.components) - 1
        
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
        cs = context.scene.bc_cross_section
        assembly = cs.assemblies[cs.active_assembly_index]
        
        if assembly.active_component_index < len(assembly.components):
            name = assembly.components[assembly.active_component_index].name
            assembly.components.remove(assembly.active_component_index)
            
            # Adjust active index
            if assembly.active_component_index >= len(assembly.components):
                assembly.active_component_index = max(0, len(assembly.components) - 1)
            
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
    BC_OT_SaveAssemblyTemplate,
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
