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
Logging Configuration Module
=============================

Centralized logging setup for Saikei Civil extension.

Usage:
    from saikei.core.logging_config import get_logger

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
LOGGER_PREFIX = "saikei"

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
    """Initialize logging for Saikei Civil extension.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        detailed: If True, use detailed format with timestamps and line numbers
        stream: Output stream (defaults to sys.stdout for Blender console)

    Returns:
        Root logger for saikei
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

    # Convert full module path to saikei namespace
    # e.g., "saikei_civil.core.alignment" -> "saikei.core.alignment"
    if name.startswith("saikei_civil"):
        name = name.replace("saikei_civil", LOGGER_PREFIX, 1)
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
    """Log the Saikei Civil startup banner.

    Args:
        version: Extension version string
    """
    logger = get_logger("startup")
    logger.info("=" * 50)
    logger.info("Saikei Civil Extension v%s - Loading...", version)
    logger.info("=" * 50)


def log_startup_complete() -> None:
    """Log successful startup completion."""
    logger = get_logger("startup")
    logger.info("Saikei Civil Extension loaded successfully!")
    logger.info("Location: 3D Viewport > Sidebar (N) > Saikei Civil tab")
    logger.info("=" * 50)


def log_shutdown() -> None:
    """Log extension shutdown."""
    logger = get_logger("startup")
    logger.info("Saikei Civil Extension unregistered")


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
