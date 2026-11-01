# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

import pytest

from processing.cityjson_export_algorithm import CityJsonExportAlgorithm
from unittest.mock import MagicMock, patch
from qgis.core import QgsProcessingContext, QgsProcessingException, QgsProcessingFeedback

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
    for name in ["LAYERS", "INPUT", "LOD_SELECTION", "KEEP_UNLOADED",
                 "SEMANTIC_SURFACES", "OUTPUT"]:
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
def test_process_algorithm_passes_kwargs(mock_load, mock_exporter, mock_save, algorithm):
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
    assert kwargs == {"loaded_lod": "2.0", "keep_unloaded": False, "semantic_surfaces": True}
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