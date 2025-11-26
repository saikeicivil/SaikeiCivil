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
BlenderCivil Test Suite
========================

Test organization:
- tests/core/       - Core module tests (geometry, IFC, alignments)
- tests/operators/  - Blender operator tests
- tests/ui/         - UI panel and property tests

Running tests:
    pytest                      # Run all tests
    pytest -m unit              # Run only unit tests
    pytest -m "not blender"     # Skip Blender-dependent tests
    pytest tests/core/          # Run only core tests
    pytest -k "alignment"       # Run tests matching "alignment"
"""
