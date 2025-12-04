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
Validation Panel
UI panel for validation and debugging tools

NOTE: The Validation panel UI has been moved to Edit > Preferences > Extensions
This file is kept for potential future operator definitions.
"""

import bpy


# NOTE: The Validation panel UI has been moved to Edit > Preferences > Extensions
# Operators (bc.validate_ifc_alignment, bc.list_all_ifc_objects) are defined in
# operators/validation_operators.py


# Registration - No classes to register (panel moved to preferences)
classes = ()

def register():
    pass

def unregister():
    pass
