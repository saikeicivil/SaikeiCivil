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
Template Operators Module
==========================

Blender UI operators for the cross-section template browser.
"""

import logging

import bpy

from .registry import get_all_templates, list_templates

logger = logging.getLogger(__name__)


class SAIKEI_OT_load_template(bpy.types.Operator):
    """Load a standard cross-section template."""

    bl_idname = "saikei.load_template"
    bl_label = "Load Template"
    bl_options = {'REGISTER', 'UNDO'}

    template_name: bpy.props.StringProperty(
        name="Template Name",
        description="Name of the template to load"
    )

    def execute(self, context):
        """Load the selected template."""
        try:
            templates = get_all_templates()

            if self.template_name not in templates:
                self.report({'ERROR'}, f"Template '{self.template_name}' not found")
                return {'CANCELLED'}

            # Create the assembly from template
            factory_func = templates[self.template_name]
            assembly = factory_func()

            # Add to scene (this would integrate with existing system)
            # manager = get_manager()
            # manager.add_assembly(assembly)

            self.report({'INFO'}, f"Loaded template: {self.template_name}")
            logger.info(f"Loaded cross-section template: {self.template_name}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to load template: {str(e)}")
            logger.exception(f"Failed to load template '{self.template_name}'")
            return {'CANCELLED'}


class SAIKEI_OT_template_browser(bpy.types.Operator):
    """Browse and select from template library."""

    bl_idname = "saikei.template_browser"
    bl_label = "Template Browser"
    bl_options = {'REGISTER', 'UNDO'}

    category_filter: bpy.props.EnumProperty(
        name="Category",
        description="Filter templates by category",
        items=[
            ('All', 'All Templates', 'Show all available templates'),
            ('AASHTO', 'AASHTO', 'American standards'),
            ('Austroads', 'Austroads', 'Australian/NZ standards'),
            ('UK DMRB', 'UK DMRB', 'UK Design Manual'),
        ],
        default='All'
    )

    def invoke(self, context, event):
        """Show template selection dialog."""
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        """Draw the template browser UI."""
        layout = self.layout

        # Category filter
        layout.prop(self, "category_filter")
        layout.separator()

        # List templates
        templates = list_templates()
        filtered_templates = [
            t for t in templates
            if self.category_filter == 'All' or self.category_filter in t[0]
        ]

        box = layout.box()
        box.label(
            text=f"Available Templates ({len(filtered_templates)}):",
            icon='PRESET'
        )

        for name, category, description in filtered_templates:
            row = box.row()
            row.operator(
                "saikei.load_template",
                text=name
            ).template_name = name
            row.label(text=f"[{category}]")

    def execute(self, context):
        """Execute is called when dialog is confirmed."""
        return {'FINISHED'}


# Registration
classes = [
    SAIKEI_OT_load_template,
    SAIKEI_OT_template_browser,
]


def register():
    """Register template operators."""
    for cls in classes:
        bpy.utils.register_class(cls)
    logger.debug("Template operators registered")


def unregister():
    """Unregister template operators."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    logger.debug("Template operators unregistered")


__all__ = [
    "SAIKEI_OT_load_template",
    "SAIKEI_OT_template_browser",
    "register",
    "unregister",
]
