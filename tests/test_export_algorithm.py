# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

import pytest

from processing.cityjson_export_algorithm import CityJsonExportAlgorithm
from unittest.mock import MagicMock, patch
from qgis.core import (
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProject,
)

from core.exporting import save_cityjson_model
from core.loading import CityJSONLoader, load_cityjson_model
from tests.test_export import _delete_feature, _two_cubes_citymodel


@pytest.fixture
def algorithm():
    return CityJsonExportAlgorithm()


def test_algorithm_metadata(algorithm):
    """Test algorithm basic metadata."""
    assert algorithm.name() == "exportcityjson"
    assert algorithm.displayName() == "Export CityJSON"
    assert algorithm.group() == "Export"
    assert algorithm.groupId() == "export"
    assert "CityJSON" in algorithm.shortHelpString()


def test_algorithm_creation():
    """Test algorithm can be instantiated."""
    algorithm = CityJsonExportAlgorithm()
    instance = algorithm.createInstance()
    assert isinstance(instance, CityJsonExportAlgorithm)


def test_init_algorithm(algorithm):
    """Test parameter initialization."""
    algorithm.initAlgorithm()
    param_names = [p.name() for p in algorithm.parameterDefinitions()]
    for name in [
        "LAYERS",
        "INPUT",
        "LOD_SELECTION",
        "KEEP_UNLOADED",
        "SEMANTIC_SURFACES",
        "OUTPUT",
    ]:
        assert name in param_names


def test_process_algorithm_invalid_file(algorithm):
    """Missing source file raises."""
    context = MagicMock(spec=QgsProcessingContext)
    feedback = MagicMock(spec=QgsProcessingFeedback)
    with (
        patch.object(algorithm, "parameterAsFile", return_value=""),
        patch.object(algorithm, "invalidSourceError", return_value="Invalid source"),
    ):
        with pytest.raises(QgsProcessingException):
            algorithm.processAlgorithm({"INPUT": None}, context, feedback)


def _patched(algorithm, lod=[], keep=True, semantic=False):
    """Patch every parameterAs... so processAlgorithm runs without real QGIS inputs."""

    def as_bool(params, key, ctx):
        return keep if key == "KEEP_UNLOADED" else semantic

    return (
        patch.object(algorithm, "parameterAsFile", return_value="/in.json"),
        patch.object(algorithm, "parameterAsLayerList", return_value=["layer"]),
        patch.object(algorithm, "parameterAsEnums", return_value=lod),
        patch.object(algorithm, "parameterAsBoolean", side_effect=as_bool),
        patch.object(algorithm, "parameterAsFileOutput", return_value="/out.json"),
    )


@patch("processing.cityjson_export_algorithm.save_cityjson_model")
@patch("processing.cityjson_export_algorithm.CityJSONExporter")
@patch("processing.cityjson_export_algorithm.load_cityjson_model")
def test_process_algorithm_passes_kwargs(
    mock_load, mock_exporter, mock_save, algorithm
):
    """Inputs reach CityJSONExporter and the result is saved."""
    mock_load.return_value = {"CityObjects": {"a": {}, "b": {}}}
    mock_exporter.return_value.export.return_value = {"CityObjects": {"a": {}}}
    context = MagicMock(spec=QgsProcessingContext)
    feedback = MagicMock(spec=QgsProcessingFeedback)

    p = _patched(algorithm, lod=[4], keep=False, semantic=True)
    with p[0], p[1], p[2], p[3], p[4]:
        result = algorithm.processAlgorithm({}, context, feedback)

    args, kwargs = mock_exporter.call_args
    assert args == (["layer"], mock_load.return_value)
    assert kwargs == {
        "loaded_lod": "2.0",
        "keep_unloaded": False,
        "semantic_surfaces": True,
    }
    mock_save.assert_called_once_with({"CityObjects": {"a": {}}}, "/out.json")
    assert result == {"OUTPUT": "/out.json"}


@patch("processing.cityjson_export_algorithm.save_cityjson_model")
@patch("processing.cityjson_export_algorithm.CityJSONExporter")
@patch("processing.cityjson_export_algorithm.load_cityjson_model")
def test_process_algorithm_export_error(mock_load, mock_exporter, mock_save, algorithm):
    """A ValueError from the exporter becomes a QgsProcessingException, nothing saved."""
    mock_load.return_value = {"CityObjects": {}}
    mock_exporter.return_value.export.side_effect = ValueError("Geometry edited")
    context = MagicMock(spec=QgsProcessingContext)
    feedback = MagicMock(spec=QgsProcessingFeedback)

    p = _patched(algorithm)
    with p[0], p[1], p[2], p[3], p[4]:
        with pytest.raises(QgsProcessingException):
            algorithm.processAlgorithm({}, context, feedback)

    mock_save.assert_not_called()


def test_export_algorithm_end_to_end(qgis_app, tmp_path, algorithm):
    """Load, delete a building, run the real algorithm, reload the output."""
    # 1. Write the fixture to a real file
    src = tmp_path / "input.city.json"
    out = tmp_path / "output.city.json"
    save_cityjson_model(_two_cubes_citymodel(), str(src))

    # 2. Load it like the plugin does (adds the layers to QgsProject)
    citymodel = load_cityjson_model(str(src))
    loader = CityJSONLoader(filepath=str(src), citymodel=citymodel)
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    # 3. The user's edit: delete building2
    _delete_feature(layers, "building2")

    # 4. Run the algorithm for real: real context, real feedback, no mocks
    context = QgsProcessingContext()
    context.setProject(QgsProject.instance())
    algorithm.initAlgorithm()
    result = algorithm.processAlgorithm(
        {
            "LAYERS": [layer.id() for layer in layers],
            "INPUT": str(src),
            "LOD_SELECTION": [],
            "KEEP_UNLOADED": True,
            "SEMANTIC_SURFACES": False,
            "OUTPUT": str(out),
        },
        context,
        QgsProcessingFeedback(),
    )

    # 5. Check the written file
    assert result == {"OUTPUT": str(out)}
    exported = load_cityjson_model(str(out))
    assert set(exported["CityObjects"]) == {"building1"}
    assert len(exported["vertices"]) == 8

    QgsProject.instance().removeAllMapLayers()  # don't leak layers into other tests


def test_process_algorithm_refuses_overwriting_source(algorithm):
    """Output path equal to the source path raises before anything is read or written."""
    context = MagicMock(spec=QgsProcessingContext)
    feedback = MagicMock(spec=QgsProcessingFeedback)
    p = _patched(algorithm)
    with (
        p[0],
        p[1],
        p[2],
        p[3],
        patch.object(algorithm, "parameterAsFileOutput", return_value="/in.json"),
        patch("processing.cityjson_export_algorithm.load_cityjson_model") as mock_load,
    ):
        with pytest.raises(QgsProcessingException):
            algorithm.processAlgorithm({}, context, feedback)
    mock_load.assert_not_called()
