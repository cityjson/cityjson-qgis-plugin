"""
Pytest configuration and fixtures for QGIS plugin testing.
"""

import os
import pytest
from qgis.core import QgsApplication

# Set environment variables before any Qt imports
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("XDG_RUNTIME_DIR", "/tmp/runtime-root")
os.environ.setdefault("QGIS_DISABLE_MESSAGE_HOOKS", "1")
os.environ.setdefault("QGIS_NO_OVERRIDE_IMPORT", "1")

# Create runtime directory if it doesn't exist
os.makedirs("/tmp/runtime-root", exist_ok=True)


@pytest.fixture(scope="session")
def qgis_app():
    """
    Initialize QGIS application for entire test session.
    This ensures proper QGIS environment setup before any tests run.
    """
    # Initialize QGIS application
    qgs = QgsApplication([], False)
    qgs.initQgis()

    yield qgs

    # Clean up
    qgs.exitQgis()


@pytest.fixture(scope="function")
def clean_qgis(qgis_app):
    """
    Clean up QGIS state between individual tests.
    """
    yield
    # Any cleanup specific to individual tests can go here
