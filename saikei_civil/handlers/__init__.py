# ==============================================================================
# Saikei Civil - Civil Engineering Tools for Blender
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
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
Handlers Package
================

Contains Blender persistent handlers for:
- Undo/redo synchronization
- Edit tracking
- File load/save events
"""

from .undo_handler import (
    register_handlers,
    unregister_handlers,
)


def register():
    """Register all handlers."""
    register_handlers()


def unregister():
    """Unregister all handlers."""
    unregister_handlers()


__all__ = [
    "register",
    "unregister",
    "register_handlers",
    "unregister_handlers",
]