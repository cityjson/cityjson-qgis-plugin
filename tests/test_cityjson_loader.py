# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

"""Tests for the top-level CityJsonLoader plugin class."""

import importlib
import json
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_NAME = "cityjson_loader_plugin"


def _register_plugin_package() -> None:
    """Register the repository root as an importable package.

    The plugin uses relative imports (``from .core ...``), which only work
    when it is loaded as a package. The repository directory name contains a
    hyphen, so it cannot be imported by name directly; this helper registers it
    under a synthetic, valid package name.
    """
    if PACKAGE_NAME in sys.modules:
        return
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [REPO_ROOT]  # type: ignore[attr-defined]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package


def _load_plugin():
    _register_plugin_package()
    return importlib.import_module(f"{PACKAGE_NAME}.cityjson_loader")


@pytest.fixture(scope="module")
def plugin_module():
    """Import the plugin module once for all tests."""
    return _load_plugin()


@pytest.fixture
def mock_iface():
    """Return a minimal mock of the QGIS interface."""
    iface = MagicMock()
    toolbar = MagicMock()
    iface.addToolBar.return_value = toolbar
    return iface


@pytest.fixture
def sample_cityjson_file(tmp_path):
    """Create a temporary CityJSON file with a known CRS."""
    model = {
        "type": "CityJSON",
        "version": "2.0",
        "metadata": {"crs": {"epsg": 4326}},
        "CityObjects": {"b1": {"type": "Building", "geometry": []}},
        "vertices": [[0, 0, 0]],
    }
    path = tmp_path / "sample.json"
    path.write_text(json.dumps(model), encoding="utf-8")
    return str(path)


class TestCityJsonLoader:
    def test_init(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)

        assert loader.iface is mock_iface
        assert loader.dlg is not None
        assert loader.actions == []
        assert loader.menu == "&CityJSON Loader"
        mock_iface.addToolBar.assert_called_once_with("CityJsonLoader")
        assert loader.file_epsg_map == {}
        assert loader.citymodel_cache == {}

    def test_add_cityjson_files(
        self, plugin_module, mock_iface, sample_cityjson_file, qgis_app
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)

        loader.add_cityjson_files([sample_cityjson_file])

        assert loader.dlg.listWidget.count() == 1
        assert loader.dlg.listWidget.item(0).text() == sample_cityjson_file
        assert loader.file_epsg_map[sample_cityjson_file] == "4326"
        assert "1 file(s) selected" in loader.dlg.fileCountLabel.text()

    def test_add_cityjson_files_deduplicates(
        self, plugin_module, mock_iface, sample_cityjson_file, qgis_app
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)

        loader.add_cityjson_files([sample_cityjson_file])
        loader.add_cityjson_files([sample_cityjson_file])

        assert loader.dlg.listWidget.count() == 1

    def test_remove_cityjson_files(
        self, plugin_module, mock_iface, sample_cityjson_file, qgis_app
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)
        loader.add_cityjson_files([sample_cityjson_file])

        loader.dlg.listWidget.setCurrentRow(0)
        loader.remove_cityjson_files()

        assert loader.dlg.listWidget.count() == 0
        assert sample_cityjson_file not in loader.file_epsg_map

    def test_clear_all_files(
        self, plugin_module, mock_iface, sample_cityjson_file, qgis_app
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)
        loader.add_cityjson_files([sample_cityjson_file])

        loader.clear_all_files()

        assert loader.dlg.listWidget.count() == 0
        assert loader.file_epsg_map == {}
        assert loader.citymodel_cache == {}

    def test_update_file_count_label_empty(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)

        loader.update_file_count_label()

        assert "0 file(s) selected" in loader.dlg.fileCountLabel.text()
        assert not loader.dlg.removeFilesButton.isEnabled()
        assert not loader.dlg.clearAllButton.isEnabled()
        assert not loader.dlg.changeCrsButton.isEnabled()

    def test_manage_cache_size(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)
        for i in range(loader.max_cache_size + 5):
            loader.citymodel_cache[f"file{i}"] = {"version": "2.0"}

        loader._manage_cache_size()

        assert len(loader.citymodel_cache) == loader.max_cache_size

    def test_load_file_crs_missing_file(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)

        assert loader.load_file_crs("/does/not/exist.json") == "None"

    def test_process_files_without_files(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)

        with patch(
            f"{PACKAGE_NAME}.cityjson_loader.QMessageBox.warning"
        ) as mock_warning:
            loader.process_files()

        mock_warning.assert_called_once()

    def test_finish_processing(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)
        mock_timer = MagicMock()
        loader.process_timer = mock_timer

        loader.finish_processing("Complete")

        mock_timer.stop.assert_called_once()
        assert loader.process_timer is None
        assert not loader.dlg.cancelButton.isEnabled()
        assert loader.dlg.loadButton.isEnabled()

    def test_unload(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)
        loader.process_timer = None
        loader.actions = [MagicMock()]

        with patch(
            f"{PACKAGE_NAME}.cityjson_loader.QgsApplication.processingRegistry"
        ) as mock_registry:
            loader.unload()

        mock_iface.removePluginVectorMenu.assert_called_once()
        mock_iface.removeToolBarIcon.assert_called_once()
        mock_registry.return_value.removeProvider.assert_called_once_with(
            loader.provider
        )
