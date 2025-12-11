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