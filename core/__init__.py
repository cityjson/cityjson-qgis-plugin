"""A module that provide classes in order to manage data from CityJSON
to QGIS layers and features
"""

from __future__ import annotations

import logging


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger instance for the core module"""
    logger_name = "cityjson_loader"
    if name:
        logger_name = f"cityjson_loader.{name}"

    logger = logging.getLogger(logger_name)

    # Configure logger if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger
