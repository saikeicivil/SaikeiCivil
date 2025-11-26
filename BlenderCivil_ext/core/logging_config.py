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
Logging Configuration Module
=============================

Centralized logging setup for BlenderCivil extension.

Usage:
    from blendercivil.core.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("Operation completed")
    logger.debug("Detailed info: %s", data)
    logger.warning("Something unexpected")
    logger.error("Operation failed: %s", error)

Log Levels:
    DEBUG    - Detailed debugging information
    INFO     - General operational messages
    WARNING  - Something unexpected but recoverable
    ERROR    - Operation failed but extension continues
    CRITICAL - Extension cannot continue
"""

import logging
import sys
from typing import Optional

# Extension-wide logger name prefix
LOGGER_PREFIX = "blendercivil"

# Default format for log messages
DEFAULT_FORMAT = "[%(levelname)s] %(name)s: %(message)s"
DETAILED_FORMAT = "[%(levelname)s] %(asctime)s - %(name)s:%(lineno)d - %(message)s"

# Track if logging has been initialized
_initialized = False


def setup_logging(
    level: int = logging.INFO,
    detailed: bool = False,
    stream: Optional[object] = None
) -> logging.Logger:
    """Initialize logging for BlenderCivil extension.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        detailed: If True, use detailed format with timestamps and line numbers
        stream: Output stream (defaults to sys.stdout for Blender console)

    Returns:
        Root logger for blendercivil
    """
    global _initialized

    # Get the root logger for our extension
    root_logger = logging.getLogger(LOGGER_PREFIX)

    # Clear existing handlers if reinitializing
    if _initialized:
        root_logger.handlers.clear()

    # Set level
    root_logger.setLevel(level)

    # Create handler for Blender's console (stdout)
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setLevel(level)

    # Set format
    fmt = DETAILED_FORMAT if detailed else DEFAULT_FORMAT
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)

    # Add handler
    root_logger.addHandler(handler)

    # Prevent propagation to avoid duplicate messages
    root_logger.propagate = False

    _initialized = True

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the module

    Example:
        logger = get_logger(__name__)
        logger.info("Module loaded")
    """
    # Ensure logging is initialized
    if not _initialized:
        setup_logging()

    # Convert full module path to blendercivil namespace
    # e.g., "blendercivil_ext.core.alignment" -> "blendercivil.core.alignment"
    if name.startswith("blendercivil_ext"):
        name = name.replace("blendercivil_ext", LOGGER_PREFIX, 1)
    elif not name.startswith(LOGGER_PREFIX):
        name = f"{LOGGER_PREFIX}.{name}"

    return logging.getLogger(name)


def set_log_level(level: int) -> None:
    """Change the logging level at runtime.

    Args:
        level: New logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    root_logger = logging.getLogger(LOGGER_PREFIX)
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)


def enable_debug() -> None:
    """Enable DEBUG level logging."""
    set_log_level(logging.DEBUG)


def disable_debug() -> None:
    """Set logging back to INFO level."""
    set_log_level(logging.INFO)


# Convenience function for startup banner
def log_startup_banner(version: str = "0.5.0") -> None:
    """Log the BlenderCivil startup banner.

    Args:
        version: Extension version string
    """
    logger = get_logger("startup")
    logger.info("=" * 50)
    logger.info("BlenderCivil Extension v%s - Loading...", version)
    logger.info("=" * 50)


def log_startup_complete() -> None:
    """Log successful startup completion."""
    logger = get_logger("startup")
    logger.info("BlenderCivil Extension loaded successfully!")
    logger.info("Location: 3D Viewport > Sidebar (N) > BlenderCivil tab")
    logger.info("=" * 50)


def log_shutdown() -> None:
    """Log extension shutdown."""
    logger = get_logger("startup")
    logger.info("BlenderCivil Extension unregistered")


__all__ = [
    "setup_logging",
    "get_logger",
    "set_log_level",
    "enable_debug",
    "disable_debug",
    "log_startup_banner",
    "log_startup_complete",
    "log_shutdown",
    "LOGGER_PREFIX",
]
