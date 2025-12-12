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
Cross-Section Assembly Operators
=================================

Core operators for creating, editing, and managing cross-section assemblies.

This module contains the primary CRUD operators for assemblies and components.
Additional operators are split into focused modules:

- cross_section_preview_operators: 2D preview mesh generation
- cross_section_overlay_operators: OpenRoads-style overlay viewer
- cross_section_ifc_operators: IFC save/export operations

Operators:
    BC_OT_CreateAssembly: Create new cross-section assembly
    BC_OT_DeleteAssembly: Remove assembly from scene
    BC_OT_AddComponent: Add component to assembly
    BC_OT_RemoveComponent: Remove component from assembly
    BC_OT_MoveComponentUp: Reorder component up
    BC_OT_MoveComponentDown: Reorder component down
    BC_OT_AddConstraint: Add parametric constraint
    BC_OT_RemoveConstraint: Remove constraint
    BC_OT_ValidateAssembly: Validate assembly configuration
    BC_OT_CalculateSection: Calculate section geometry at station
"""

import bpy
from bpy.types import Operator
from bpy.props import FloatProperty, StringProperty, EnumProperty
from ..core.logging_config import get_logger

logger = get_logger(__name__)


def update_assembly_total_width(assembly):
    """
    Calculate and update the total width of an assembly.

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
    populated with predefined templates or created empty for custom config.
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
        """Populate assembly with two-lane rural template."""
        _add_component_with_ifc(
            assembly, "Right Travel Lane", 'LANE', 'RIGHT',
            width=3.6, cross_slope=0.02, offset=0.0, lane_type='TRAVEL'
        )
        _add_component_with_ifc(
            assembly, "Right Shoulder", 'SHOULDER', 'RIGHT',
            width=2.4, cross_slope=0.04, offset=3.6, shoulder_type='PAVED'
        )
        _add_component_with_ifc(
            assembly, "Right Ditch", 'DITCH', 'RIGHT',
            width=6.0, offset=6.0,
            foreslope=4.0, backslope=3.0, bottom_width=1.2, depth=0.45
        )
        _add_component_with_ifc(
            assembly, "Left Travel Lane", 'LANE', 'LEFT',
            width=3.6, cross_slope=0.02, offset=0.0, lane_type='TRAVEL'
        )
        _add_component_with_ifc(
            assembly, "Left Shoulder", 'SHOULDER', 'LEFT',
            width=1.8, cross_slope=0.04, offset=-3.6, shoulder_type='PAVED'
        )
        _add_component_with_ifc(
            assembly, "Left Ditch", 'DITCH', 'LEFT',
            width=6.0, offset=-5.4,
            foreslope=4.0, backslope=3.0, bottom_width=1.2, depth=0.45
        )

        assembly.is_valid = True
        assembly.validation_message = "Template created successfully"
        update_assembly_total_width(assembly)

    def _create_four_lane_divided(self, assembly):
        """Populate assembly with four-lane divided template."""
        _add_component_with_ifc(
            assembly, "Inside Shoulder", 'SHOULDER', 'LEFT',
            width=1.2, cross_slope=0.04, offset=0.0, shoulder_type='PAVED'
        )
        _add_component_with_ifc(
            assembly, "Lane 1", 'LANE', 'RIGHT',
            width=3.6, cross_slope=0.02, offset=1.2, lane_type='TRAVEL'
        )
        _add_component_with_ifc(
            assembly, "Lane 2", 'LANE', 'RIGHT',
            width=3.6, cross_slope=0.02, offset=4.8, lane_type='TRAVEL'
        )
        _add_component_with_ifc(
            assembly, "Outside Shoulder", 'SHOULDER', 'RIGHT',
            width=3.0, cross_slope=0.04, offset=8.4, shoulder_type='PAVED'
        )
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
    """Delete the currently active assembly."""
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
    """Add a new component to the active assembly."""
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
    """Remove the selected component from the active assembly."""
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
    """Move the selected component up in the list."""
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
    """Move the selected component down in the list."""
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
    """Add a parametric constraint for component variation along alignment."""
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
    """Remove the selected parametric constraint."""
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
    """Validate the active assembly for errors and warnings."""
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
    """Calculate cross-section geometry at a specified station."""
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


# Import operators from split modules for re-export
from .cross_section_preview_operators import (
    BC_OT_GenerateCrossSectionPreview,
    BC_OT_ClearCrossSectionPreview,
)
from .cross_section_overlay_operators import (
    BC_OT_ToggleCrossSectionView,
    BC_OT_LoadAssemblyToView,
    BC_OT_RefreshCrossSectionView,
    BC_OT_FitCrossSectionView,
    BC_OT_SetCrossSectionViewPosition,
    BC_OT_CrossSectionViewInteraction,
)
from .cross_section_ifc_operators import (
    BC_OT_ExportAssemblyIFC,
    BC_OT_SaveAssemblyTemplate,
    BC_OT_SaveAssemblyToIFC,
)


# Registration - core operators only (submodules register themselves)
_core_classes = (
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
)


def register():
    """Register operator classes"""
    # Register core operators
    for cls in _core_classes:
        bpy.utils.register_class(cls)

    # Register submodule operators
    from . import cross_section_preview_operators
    from . import cross_section_overlay_operators
    from . import cross_section_ifc_operators

    cross_section_preview_operators.register()
    cross_section_overlay_operators.register()
    cross_section_ifc_operators.register()

    logger.info("Cross-section operators registered")


def unregister():
    """Unregister operator classes"""
    # Unregister submodule operators first
    from . import cross_section_preview_operators
    from . import cross_section_overlay_operators
    from . import cross_section_ifc_operators

    cross_section_ifc_operators.unregister()
    cross_section_overlay_operators.unregister()
    cross_section_preview_operators.unregister()

    # Unregister core operators
    for cls in reversed(_core_classes):
        bpy.utils.unregister_class(cls)

    logger.info("Cross-section operators unregistered")


if __name__ == "__main__":
    register()
