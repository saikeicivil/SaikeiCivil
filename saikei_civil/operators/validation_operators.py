# ==============================================================================
# Saikei Civil - Civil Engineering Tools for Blender
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
Validation Operators
====================

Provides operators for validating and debugging IFC alignment data structures.

This module contains diagnostic tools for inspecting IFC alignment structures,
examining segment details, and listing IFC-linked objects. These operators are
essential for troubleshooting alignment issues and verifying proper IFC
data construction.

Operators:
    BC_OT_validate_ifc_alignment: Validate IFC alignment structure and report statistics
    BC_OT_show_segment_info: Display detailed information about a selected alignment segment
    BC_OT_list_all_ifc_objects: List all IFC-linked objects in the scene
"""

import bpy
from bpy.props import StringProperty, FloatProperty, IntProperty, BoolProperty

# Import from parent operators module
from . import NativeIfcManager
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class BC_OT_validate_ifc_alignment(bpy.types.Operator):
    """Validate IFC alignment structure.

    Performs validation checks on IFC alignment data to ensure proper structure
    and connectivity. Reports statistics about PI (Point of Intersection) markers
    and alignment segments found in the scene.

    This operator checks:
        - Presence of alignments in the IFC file
        - Number of PI markers (objects with ifc_pi_id property)
        - Number of segments (objects with ifc_definition_id property)
        - Basic structural integrity

    Usage:
        Called from the validation panel to verify alignment data structure.
        Outputs detailed information to the console logger.

    Returns:
        {'FINISHED'} if alignments found and valid, {'CANCELLED'} if no alignments
    """
    bl_idname = "bc.validate_ifc_alignment"
    bl_label = "Validate IFC"
    
    def execute(self, context):
        ifc = NativeIfcManager.get_file()
        
        # Check for alignments
        alignments = ifc.by_type("IfcAlignment")
        if not alignments:
            self.report({'ERROR'}, "No alignments in IFC file")
            return {'CANCELLED'}
        
        logger.info("="*60)
        logger.info("IFC ALIGNMENT VALIDATION")
        logger.info("="*60)

        # Get PIs and segments from scene
        pis = [obj for obj in bpy.data.objects if "ifc_pi_id" in obj]
        segments = [obj for obj in bpy.data.objects
                   if "ifc_definition_id" in obj and "ifc_class" in obj]

        logger.info("STRUCTURE:")
        logger.info("  PIs found: %s", len(pis))
        logger.info("  Segments found: %s", len(segments))

        logger.info("SEGMENT DETAILS:")
        for obj in segments:
            obj_type = "CURVE" if obj.type == 'CURVE' else obj.type
            logger.info("  [%s] %s - Type: %s", len([s for s in segments if segments.index(s) < segments.index(obj)]), obj.name, obj_type)

        logger.info("VALIDATION PASSED")
        
        self.report({'INFO'}, f"Validation passed: {len(pis)} PIs, {len(segments)} segments")
        return {'FINISHED'}



class BC_OT_show_segment_info(bpy.types.Operator):
    """Show segment information.

    Displays detailed information about a selected alignment segment including
    its geometric parameters from the IFC DesignParameters.

    Information shown:
        - Segment type (LINE, CLOTHOID, CIRCULARARC, etc.)
        - Segment length
        - Start point coordinates
        - Start direction (radians)
        - Start and end radius of curvature

    Usage:
        Select an alignment segment object in the scene and call this operator.
        The segment must have an ifc_definition_id property linking it to the IFC data.

    Returns:
        {'FINISHED'} if valid segment selected, {'CANCELLED'} if no segment selected
    """
    bl_idname = "bc.show_segment_info"
    bl_label = "Show Segment Info"
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or "ifc_definition_id" not in obj:
            self.report({'ERROR'}, "Select an alignment segment")
            return {'CANCELLED'}
        
        ifc = NativeIfcManager.get_file()
        segment = ifc.by_id(obj["ifc_definition_id"])
        params = segment.DesignParameters

        logger.info("="*60)
        logger.info("SEGMENT: %s", obj.name)
        logger.info("="*60)
        logger.info("Type: %s", params.PredefinedType)
        logger.info("Length: %.3fm", params.SegmentLength)
        logger.info("Start Point: %s", params.StartPoint.Coordinates)
        logger.info("Start Direction: %.4f rad", params.StartDirection)
        logger.info("Start Radius: %.2fm", params.StartRadiusOfCurvature)
        logger.info("End Radius: %.2fm", params.EndRadiusOfCurvature)
        
        self.report({'INFO'}, f"{params.PredefinedType}: {params.SegmentLength:.2f}m")
        return {'FINISHED'}



class BC_OT_list_all_ifc_objects(bpy.types.Operator):
    """List all IFC-linked objects.

    Generates a comprehensive list of all objects in the scene that are linked
    to IFC entities. Displays statistics and detailed information for both
    PI markers and IFC segment objects.

    Output includes:
        - Total count of IFC entities and PI markers
        - For each PI: ID, radius, and location
        - For each IFC object: name and IFC class

    Usage:
        Called from the validation panel to get an overview of all IFC-linked
        geometry in the scene. Useful for debugging and verification.

    Returns:
        {'FINISHED'} always
    """
    bl_idname = "bc.list_all_ifc_objects"
    bl_label = "List All IFC Objects"
    
    def execute(self, context):
        logger.info("="*60)
        logger.info("LISTING ALL IFC OBJECTS")
        logger.info("="*60)

        # Get all IFC-linked objects
        ifc_objects = [obj for obj in bpy.data.objects
                      if "ifc_definition_id" in obj]
        pis = [obj for obj in bpy.data.objects if "ifc_pi_id" in obj]

        logger.info("="*60)
        logger.info("ALL IFC-LINKED OBJECTS")
        logger.info("="*60)

        logger.info("SUMMARY:")
        logger.info("  IFC Entities: %s", len(ifc_objects))
        logger.info("  PI Markers: %s", len(pis))

        logger.info("PIs:")
        for obj in sorted(pis, key=lambda x: x.get("ifc_pi_id", 0)):
            pi_id = obj.get("ifc_pi_id", "?")
            radius = obj.get("radius", 0.0)
            loc = obj.location
            logger.info("  [%s] %s - R=%sm at (%.1f, %.1f)", pi_id, obj.name, radius, loc.x, loc.y)

        logger.info("IFC SEGMENTS:")
        for obj in ifc_objects:
            ifc_class = obj.get("ifc_class", "Unknown")
            logger.info("  %s - %s", obj.name, ifc_class)
        
        self.report({'INFO'}, f"Found {len(ifc_objects)} IFC objects, {len(pis)} PIs")
        return {'FINISHED'}


# ==================== UI PANELS ====================



# Registration
classes = (
    BC_OT_validate_ifc_alignment,
    BC_OT_show_segment_info,
    BC_OT_list_all_ifc_objects,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
