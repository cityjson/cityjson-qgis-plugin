# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

"""Tests for the top-level CityJsonLoader plugin class."""

import importlib
import json
import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle

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

        assert loader.load_file_crs("/does/not/exist.json") is None

    def test_add_cityjson_file_without_crs(
        self, plugin_module, mock_iface, qgis_app, tmp_path
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)
        model = {
            "type": "CityJSON",
            "version": "2.0",
            "CityObjects": {"b1": {"type": "Building", "geometry": []}},
            "vertices": [[0, 0, 0]],
        }
        path = tmp_path / "no_crs.json"
        path.write_text(json.dumps(model), encoding="utf-8")

        loader.add_cityjson_files([str(path)])

        assert loader.file_epsg_map[str(path)] is None
        assert loader.dlg.crsLineEdit.text() == ""

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

    def test_request_cancel(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)

        loader.request_cancel()

        assert loader._cancel_requested is True

    def test_clear_file_information(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)
        loader.dlg.cityjsonVersionLineEdit.setText("2.0")
        loader.dlg.compressedLineEdit.setText("Yes")
        loader.dlg.crsLineEdit.setText("4326")

        loader.clear_file_information()

        assert loader.dlg.cityjsonVersionLineEdit.text() == ""
        assert loader.dlg.compressedLineEdit.text() == ""
        assert loader.dlg.crsLineEdit.text() == ""
        assert loader.dlg.metadataTreeView.model() is None

    def test_reset_progress_format_on_ui_change(
        self, plugin_module, mock_iface, qgis_app
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)
        loader.dlg.progressBar.setFormat("Complete")

        loader.reset_progress_format_on_ui_change()

        assert loader.dlg.progressBar.format() == "%p%"

    def test_semantics_loading_changed_enables_styling(
        self, plugin_module, mock_iface, qgis_app
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)

        with patch(
            f"{PACKAGE_NAME}.cityjson_loader.is_rule_based_3d_styling_available",
            return_value=True,
        ):
            loader.dlg.semanticsLoadingCheckBox.setChecked(True)
            loader.semantics_loading_changed()

        assert loader.dlg.semanticSurfacesStylingCheckBox.isEnabled()

    def test_semantics_loading_changed_disables_styling(
        self, plugin_module, mock_iface, qgis_app
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)

        with patch(
            f"{PACKAGE_NAME}.cityjson_loader.is_rule_based_3d_styling_available",
            return_value=True,
        ):
            loader.dlg.semanticsLoadingCheckBox.setChecked(False)
            loader.semantics_loading_changed()

        assert not loader.dlg.semanticSurfacesStylingCheckBox.isChecked()
        assert not loader.dlg.semanticSurfacesStylingCheckBox.isEnabled()

    def test_select_cityjson_files(
        self, plugin_module, mock_iface, sample_cityjson_file, qgis_app
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)

        with patch(
            f"{PACKAGE_NAME}.cityjson_loader.QFileDialog.getOpenFileNames",
            return_value=([sample_cityjson_file], ""),
        ):
            loader.select_cityjson_files()

        assert loader.dlg.listWidget.count() == 1
        assert loader.dlg.listWidget.item(0).text() == sample_cityjson_file

    def test_select_cityjson_files_directory(
        self, plugin_module, mock_iface, qgis_app, tmp_path
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)
        model = {
            "type": "CityJSON",
            "version": "2.0",
            "metadata": {"crs": {"epsg": 4326}},
            "CityObjects": {},
            "vertices": [],
        }
        (tmp_path / "a.json").write_text(json.dumps(model), encoding="utf-8")
        (tmp_path / "b.city.json").write_text(json.dumps(model), encoding="utf-8")
        (tmp_path / "c.txt").write_text("x", encoding="utf-8")

        with patch(
            f"{PACKAGE_NAME}.cityjson_loader.QFileDialog.getExistingDirectory",
            return_value=str(tmp_path),
        ):
            loader.select_cityjson_files_directory()

        assert loader.dlg.listWidget.count() == 2

    def test_update_file_information(
        self, plugin_module, mock_iface, qgis_app, tmp_path
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)
        model = {
            "type": "CityJSON",
            "version": "2.0",
            "transform": {"scale": [1, 1, 1], "translate": [0, 0, 0]},
            "metadata": {"datasetTitle": "Test"},
            "+metadata-extended": {"custom": "value"},
            "CityObjects": {
                "b1": {
                    "type": "Building",
                    "geometry": [
                        {"lod": "2.2", "type": "Solid", "boundaries": [[[0, 1, 2]]]}
                    ],
                }
            },
            "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
        }
        path = tmp_path / "extended.json"
        path.write_text(json.dumps(model), encoding="utf-8")
        loader.file_epsg_map[str(path)] = "4326"

        loader.update_file_information(str(path))

        assert loader.dlg.cityjsonVersionLineEdit.text() == "2.0"
        assert loader.dlg.compressedLineEdit.text() == "Yes"
        assert loader.dlg.crsLineEdit.text() == "4326"
        items = [
            loader.dlg.loDSelectionComboBox.itemText(i)
            for i in range(loader.dlg.loDSelectionComboBox.count())
        ]
        assert items == ["All", "2.2"]
        assert loader.dlg.metadataTreeView.model() is not None

    def test_select_crs(
        self, plugin_module, mock_iface, sample_cityjson_file, qgis_app
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)
        loader.add_cityjson_files([sample_cityjson_file])

        mock_crs_dialog = MagicMock()
        mock_crs = MagicMock()
        mock_crs.postgisSrid.return_value = 28992
        mock_crs_dialog.crs.return_value = mock_crs
        mock_crs_dialog.exec.return_value = 0

        with patch(
            f"{PACKAGE_NAME}.cityjson_loader.QgsProjectionSelectionDialog",
            return_value=mock_crs_dialog,
        ):
            loader.select_crs()

        assert loader.dlg.crsLineEdit.text() == "28992"
        assert loader.file_epsg_map[sample_cityjson_file] == "28992"

    def test_select_crs_no_projection(
        self, plugin_module, mock_iface, sample_cityjson_file, qgis_app
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)
        loader.add_cityjson_files([sample_cityjson_file])

        mock_crs_dialog = MagicMock()
        mock_crs = MagicMock()
        mock_crs.postgisSrid.return_value = 0
        mock_crs_dialog.crs.return_value = mock_crs
        mock_crs_dialog.exec.return_value = 0

        with patch(
            f"{PACKAGE_NAME}.cityjson_loader.QgsProjectionSelectionDialog",
            return_value=mock_crs_dialog,
        ):
            loader.select_crs()

        assert loader.dlg.crsLineEdit.text() == "None"
        assert loader.file_epsg_map[sample_cityjson_file] is None

    def test_load_cityjson_passes_options(
        self, plugin_module, mock_iface, sample_cityjson_file, qgis_app
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)
        loader.file_epsg_map[sample_cityjson_file] = "28992"
        loader.dlg.loDLoadingComboBox.setCurrentIndex(2)  # LAYERS
        loader.dlg.loDSelectionComboBox.addItem("2.2")
        loader.dlg.loDSelectionComboBox.setCurrentIndex(1)
        loader.dlg.inheritParentAttributesCheckBox.setChecked(True)
        loader.dlg.splitByTypeCheckBox.setChecked(True)
        loader.dlg.semanticsLoadingCheckBox.setChecked(True)
        loader.dlg.semanticSurfacesStylingCheckBox.setChecked(True)

        mock_loader_instance = MagicMock()
        mock_loader_instance.load.return_value = 3

        with patch(f"{PACKAGE_NAME}.cityjson_loader.CityJSONLoader") as mock_loader_cls:
            mock_loader_cls.return_value = mock_loader_instance
            result = loader.load_cityjson(sample_cityjson_file)

        assert result == 3
        args, kwargs = mock_loader_cls.call_args
        assert args[0] == sample_cityjson_file
        assert kwargs["epsg"] == "28992"
        assert kwargs["lod_as"] == "LAYERS"
        assert kwargs["lod"] == "2.2"
        assert kwargs["keep_parent_attributes"] is True
        assert kwargs["divide_by_object"] is True
        assert kwargs["load_semantic_surfaces"] is True
        assert kwargs["style_semantic_surfaces"] is True

    def test_process_files_starts_timer(
        self, plugin_module, mock_iface, sample_cityjson_file, qgis_app
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)
        loader.add_cityjson_files([sample_cityjson_file])

        mock_timer = MagicMock()
        with patch(f"{PACKAGE_NAME}.cityjson_loader.QTimer", return_value=mock_timer):
            loader.process_files()

        assert loader.file_queue == [sample_cityjson_file]
        assert loader.current_file_index == 0
        assert loader._cancel_requested is False
        assert loader.dlg.cancelButton.isEnabled()
        assert not loader.dlg.loadButton.isEnabled()
        mock_timer.timeout.connect.assert_called_once_with(loader.process_next_file)
        mock_timer.start.assert_called_once_with(50)

    def test_process_next_file_loads_and_increments(
        self, plugin_module, mock_iface, sample_cityjson_file, qgis_app
    ):
        loader = plugin_module.CityJsonLoader(mock_iface)
        loader.file_queue = [sample_cityjson_file]
        loader.current_file_index = 0

        mock_loader_instance = MagicMock()
        mock_loader_instance.load.return_value = 0

        with patch(f"{PACKAGE_NAME}.cityjson_loader.CityJSONLoader") as mock_loader_cls:
            mock_loader_cls.return_value = mock_loader_instance
            loader.process_next_file()

        assert loader.current_file_index == 1
        assert loader.dlg.progressBar.value() == 100

    def test_process_next_file_complete(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)
        loader.file_queue = []
        loader.current_file_index = 0
        mock_timer = MagicMock()
        loader.process_timer = mock_timer

        with patch(f"{PACKAGE_NAME}.cityjson_loader.QTimer.singleShot"):
            loader.process_next_file()

        mock_timer.stop.assert_called_once()
        assert loader.process_timer is None
        assert loader.dlg.progressBar.value() == 100

    def test_process_next_file_cancelled(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)
        loader._cancel_requested = True
        mock_timer = MagicMock()
        loader.process_timer = mock_timer

        with patch(f"{PACKAGE_NAME}.cityjson_loader.QTimer.singleShot"):
            loader.process_next_file()

        mock_timer.stop.assert_called_once()
        assert loader.process_timer is None
        assert loader.dlg.progressBar.format() == "Cancelled"

    def test_add_action(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)
        callback = MagicMock()

        action = loader.add_action(":/icon.svg", "My Action", callback)

        assert action in loader.actions
        loader.toolbar.addAction.assert_called_once_with(action)
        mock_iface.addPluginToVectorMenu.assert_called_once_with(loader.menu, action)

    def test_initGui(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)
        mock_iface.mainWindow.return_value = None

        with patch.object(loader, "initProcessing") as mock_init_processing:
            loader.initGui()

        assert len(loader.actions) == 2
        mock_init_processing.assert_called_once()
        mock_iface.addPluginToVectorMenu.assert_called()

    def test_run(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)

        with (
            patch.object(loader.dlg, "show") as mock_show,
            patch.object(loader.dlg, "reset_fields") as mock_reset,
        ):
            loader.run()

        mock_reset.assert_called_once()
        mock_show.assert_called_once()
        assert loader.dlg.progressBar.value() == 0

    def test_run_when_visible(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)

        with (
            patch.object(loader.dlg, "isVisible", return_value=True),
            patch.object(loader.dlg, "raise_") as mock_raise,
            patch.object(loader.dlg, "activateWindow") as mock_activate,
        ):
            loader.run()

        mock_raise.assert_called_once()
        mock_activate.assert_called_once()


def _fake_layer(props):
    """A stand-in for a loaded layer: only custom properties and a CRS."""
    layer = MagicMock()
    layer.customProperty.side_effect = lambda key, default=None: props.get(key, default)
    layer.crs.return_value = QgsCoordinateReferenceSystem("EPSG:28992")
    return layer


@pytest.fixture
def export_env(plugin_module, mock_iface, tmp_path, qgis_app):
    """Plugin with one loaded file selected and a save path filled in.
    File reading, exporting, saving and reloading are all replaced by mocks."""
    mod = f"{PACKAGE_NAME}.cityjson_loader"
    source = str(tmp_path / "in.city.json")
    layer = _fake_layer({"cityjson/load_id": "load-1", "cityjson/source": source})
    group = {
        "source": source,
        "lod": "All",
        "semantic_surfaces": False,
        "keep_parent_attributes": False,
        "layers": [layer],
    }
    loader = plugin_module.CityJsonLoader(mock_iface)
    with (
        patch(f"{mod}.QgsProject") as project,
        patch(f"{mod}.read_provenance", return_value={"load-1": group}),
        patch(f"{mod}.load_cityjson_model"),
        patch(f"{mod}.CityJSONExporter") as exporter,
        patch(f"{mod}.save_cityjson_model") as save,
        patch(f"{mod}.CityJSONLoader") as reloader,
        patch(f"{mod}.get_model_epsg"),
    ):
        project.instance.return_value.mapLayers.return_value = {"l1": layer}
        exporter.return_value.export.return_value = {"CityObjects": {"b1": {}}}
        loader.dlg_wrt.layer_select.addItem("in.city.json", "load-1")
        output = str(tmp_path / "out.city.json")
        loader.dlg_wrt.save_file_name.setFilePath(output)
        yield SimpleNamespace(
            loader=loader,
            dlg=loader.dlg_wrt,
            bar=mock_iface.messageBar.return_value,
            group=group,
            output=output,
            exporter=exporter,
            save=save,
            reloader=reloader,
        )


class TestExportDialog:
    """write() opens the export dialog; export_cityjson() runs when Convert is clicked."""

    def test_write_lists_one_entry_per_load(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)
        layers = {
            "a": _fake_layer(
                {"cityjson/load_id": "load-1", "cityjson/source": "/data/a.city.json"}
            ),
            "b": _fake_layer(
                {"cityjson/load_id": "load-1", "cityjson/source": "/data/a.city.json"}
            ),
            "plain": _fake_layer({}),
        }
        with (
            patch(f"{PACKAGE_NAME}.cityjson_loader.QgsProject") as project,
            patch.object(loader.dlg_wrt.extent, "setMapCanvas"),
            patch.object(loader.dlg_wrt, "show") as mock_show,
        ):
            project.instance.return_value.mapLayers.return_value = layers
            loader.write()

        combo = loader.dlg_wrt.layer_select
        assert combo.count() == 1
        assert combo.itemText(0) == "a.city.json"
        assert combo.itemData(0) == "load-1"
        mock_show.assert_called_once()

    def test_write_sets_map_canvas_once(self, plugin_module, mock_iface, qgis_app):
        loader = plugin_module.CityJsonLoader(mock_iface)
        with (
            patch(f"{PACKAGE_NAME}.cityjson_loader.QgsProject"),
            patch.object(loader.dlg_wrt.extent, "setMapCanvas") as set_canvas,
            patch.object(loader.dlg_wrt, "show"),
        ):
            loader.write()
            loader.write()

        set_canvas.assert_called_once_with(mock_iface.mapCanvas.return_value)

    @pytest.mark.parametrize("missing", ["file", "path"])
    def test_export_without_selection_warns(self, export_env, missing):
        if missing == "file":
            export_env.dlg.layer_select.clear()
        else:
            export_env.dlg.save_file_name.setFilePath("")

        export_env.loader.export_cityjson()

        export_env.bar.pushWarning.assert_called_once()
        export_env.exporter.assert_not_called()

    def test_export_refuses_overwriting_source(self, export_env):
        export_env.dlg.save_file_name.setFilePath(export_env.group["source"])

        export_env.loader.export_cityjson()

        message = export_env.bar.pushCritical.call_args.args[1]
        assert "overwrite the source" in message
        export_env.save.assert_not_called()

    def test_export_refuses_parent_attributes(self, export_env):
        export_env.group["keep_parent_attributes"] = True

        export_env.loader.export_cityjson()

        message = export_env.bar.pushCritical.call_args.args[1]
        assert "inherit parent attributes" in message
        export_env.save.assert_not_called()

    def test_export_error_shows_message(self, export_env):
        export_env.exporter.return_value.export.side_effect = ValueError(
            "Geometry was edited"
        )

        export_env.loader.export_cityjson()

        export_env.bar.pushCritical.assert_called_once_with(
            "CityJSON export", "Geometry was edited"
        )
        export_env.save.assert_not_called()

    def test_export_passes_options(self, export_env):
        export_env.group["lod"] = "2.2"
        export_env.group["semantic_surfaces"] = True
        export_env.dlg.keep_unloaded.setChecked(False)

        export_env.loader.export_cityjson()

        kwargs = export_env.exporter.call_args.kwargs
        assert kwargs["loaded_lod"] == "2.2"
        assert kwargs["semantic_surfaces"] is True
        assert kwargs["keep_unloaded"] is False
        assert kwargs["bbox"] is None  # "Whole file"
        exported = export_env.exporter.return_value.export.return_value
        export_env.save.assert_called_once_with(exported, export_env.output)

    def test_export_with_extent_passes_bbox_in_layer_crs(self, export_env):
        # Drawn in lon/lat around Delft; the layer is in EPSG:28992 (metres).
        export_env.dlg.extent.setOutputExtentFromUser(
            QgsRectangle(4.35, 52.00, 4.37, 52.01),
            QgsCoordinateReferenceSystem("EPSG:4326"),
        )

        export_env.loader.export_cityjson()

        xmin, ymin, xmax, ymax = export_env.exporter.call_args.kwargs["bbox"]
        assert 80000 < xmin < xmax < 90000
        assert 440000 < ymin < ymax < 455000

    @pytest.mark.parametrize(
        "reload, cityobjects, expected",
        [
            (True, {"b1": {}}, True),
            (False, {"b1": {}}, False),
            (True, {}, False),  # nothing exported, nothing to add
        ],
    )
    def test_export_reload_adds_file(self, export_env, reload, cityobjects, expected):
        export_env.dlg.reload.setChecked(reload)
        export_env.exporter.return_value.export.return_value = {
            "CityObjects": cityobjects
        }

        export_env.loader.export_cityjson()

        assert export_env.reloader.return_value.load.called is expected

    def test_export_success_closes_dialog(self, export_env):
        with patch.object(export_env.dlg, "close") as mock_close:
            export_env.loader.export_cityjson()

        export_env.bar.pushSuccess.assert_called_once()
        export_env.bar.pushCritical.assert_not_called()
        mock_close.assert_called_once()
