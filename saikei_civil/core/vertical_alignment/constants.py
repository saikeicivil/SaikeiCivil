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
Vertical Alignment Design Constants
====================================

AASHTO design standards for vertical curve K-values based on design speed.

K-value Definition:
    K = L / A
    where:
        L = curve length (m)
        A = |g2 - g1| × 100 (% grade change)

K-values control:
    - Stopping sight distance (crest curves)
    - Headlight sight distance (sag curves)
    - Driver comfort
"""

# AASHTO minimum K-values (m/% grade change)
MIN_K_CREST_80KPH = 29.0  # Design speed 80 km/h
MIN_K_SAG_80KPH = 17.0

# Common design speeds (km/h) and their K-values
# Source: AASHTO Green Book
DESIGN_STANDARDS = {
    40: {"k_crest": 7.0, "k_sag": 6.0},
    50: {"k_crest": 11.0, "k_sag": 9.0},
    60: {"k_crest": 17.0, "k_sag": 12.0},
    80: {"k_crest": 29.0, "k_sag": 17.0},
    100: {"k_crest": 51.0, "k_sag": 26.0},
    120: {"k_crest": 84.0, "k_sag": 37.0},
}

__all__ = [
    "MIN_K_CREST_80KPH",
    "MIN_K_SAG_80KPH",
    "DESIGN_STANDARDS",
]