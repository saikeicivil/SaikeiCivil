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
Tests for Logging Configuration Module
=======================================

Tests for the centralized logging setup.
"""

import logging

import pytest

from core.logging_config import (
    setup_logging,
    get_logger,
    set_log_level,
    enable_debug,
    disable_debug,
    LOGGER_PREFIX,
)


class TestSetupLogging:
    """Tests for setup_logging function."""

    @pytest.mark.unit
    def test_setup_returns_logger(self):
        """Test that setup_logging returns a logger."""
        logger = setup_logging()
        assert logger is not None
        assert isinstance(logger, logging.Logger)

    @pytest.mark.unit
    def test_setup_with_debug_level(self):
        """Test setup with DEBUG level."""
        logger = setup_logging(level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    @pytest.mark.unit
    def test_setup_with_info_level(self):
        """Test setup with INFO level (default)."""
        logger = setup_logging(level=logging.INFO)
        assert logger.level == logging.INFO


class TestGetLogger:
    """Tests for get_logger function."""

    @pytest.mark.unit
    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger(__name__)
        assert logger is not None
        assert isinstance(logger, logging.Logger)

    @pytest.mark.unit
    def test_get_logger_uses_prefix(self):
        """Test that logger name uses saikei prefix."""
        logger = get_logger("test_module")
        assert LOGGER_PREFIX in logger.name

    @pytest.mark.unit
    def test_get_logger_same_name_same_logger(self):
        """Test that same name returns same logger instance."""
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")
        assert logger1 is logger2


class TestSetLogLevel:
    """Tests for set_log_level function."""

    @pytest.mark.unit
    def test_set_debug_level(self):
        """Test setting DEBUG level."""
        setup_logging()
        set_log_level(logging.DEBUG)

        root = logging.getLogger(LOGGER_PREFIX)
        assert root.level == logging.DEBUG

    @pytest.mark.unit
    def test_set_warning_level(self):
        """Test setting WARNING level."""
        setup_logging()
        set_log_level(logging.WARNING)

        root = logging.getLogger(LOGGER_PREFIX)
        assert root.level == logging.WARNING


class TestDebugHelpers:
    """Tests for enable_debug and disable_debug functions."""

    @pytest.mark.unit
    def test_enable_debug(self):
        """Test enable_debug sets DEBUG level."""
        setup_logging()
        enable_debug()

        root = logging.getLogger(LOGGER_PREFIX)
        assert root.level == logging.DEBUG

    @pytest.mark.unit
    def test_disable_debug(self):
        """Test disable_debug sets INFO level."""
        setup_logging()
        enable_debug()
        disable_debug()

        root = logging.getLogger(LOGGER_PREFIX)
        assert root.level == logging.INFO


class TestLoggerOutput:
    """Tests for logger output functionality."""

    @pytest.mark.unit
    def test_logger_can_log_info(self, caplog):
        """Test that logger can log INFO messages."""
        setup_logging(level=logging.INFO)
        logger = get_logger("test_output")

        with caplog.at_level(logging.INFO, logger=LOGGER_PREFIX):
            logger.info("Test info message")

        assert "Test info message" in caplog.text

    @pytest.mark.unit
    def test_logger_can_log_warning(self, caplog):
        """Test that logger can log WARNING messages."""
        setup_logging(level=logging.WARNING)
        logger = get_logger("test_output")

        with caplog.at_level(logging.WARNING, logger=LOGGER_PREFIX):
            logger.warning("Test warning message")

        assert "Test warning message" in caplog.text

    @pytest.mark.unit
    def test_logger_can_log_error(self, caplog):
        """Test that logger can log ERROR messages."""
        setup_logging(level=logging.ERROR)
        logger = get_logger("test_output")

        with caplog.at_level(logging.ERROR, logger=LOGGER_PREFIX):
            logger.error("Test error message")

        assert "Test error message" in caplog.text

    @pytest.mark.unit
    def test_debug_filtered_at_info_level(self, caplog):
        """Test that DEBUG messages are filtered at INFO level."""
        setup_logging(level=logging.INFO)
        logger = get_logger("test_filter")

        with caplog.at_level(logging.INFO, logger=LOGGER_PREFIX):
            logger.debug("This should not appear")
            logger.info("This should appear")

        assert "This should not appear" not in caplog.text
        assert "This should appear" in caplog.text
