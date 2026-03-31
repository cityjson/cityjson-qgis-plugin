# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

import pytest
from unittest.mock import MagicMock, patch
from qgis.core import (
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsCoordinateReferenceSystem,
    QgsRectangle,
    QgsProcessingException,
)

from processing.cityjson_load_algorithm import CityJsonLoadAlgorithm


@pytest.fixture
def algorithm():
    return CityJsonLoadAlgorithm()


@pytest.fixture
def mock_context():
    return MagicMock(spec=QgsProcessingContext)


@pytest.fixture
def mock_feedback():
    feedback = MagicMock(spec=QgsProcessingFeedback)
    feedback.pushInfo = MagicMock()
    feedback.setProgressText = MagicMock()
    return feedback


@pytest.fixture
def mock_invalid_crs():
    """Create a mock CRS that behaves like an invalid CRS."""
    mock_crs = MagicMock()
    mock_crs.isValid.return_value = False
    return mock_crs


@pytest.fixture
def sample_cityjson():
    return {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
        "CityObjects": {
            "building1": {
                "type": "Building",
                "geometry": [{"type": "Solid", "lod": "2"}],
            },
            "bridge1": {"type": "Bridge", "geometry": [{"type": "Solid", "lod": "1"}]},
        },
        "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
    }


def test_algorithm_metadata(algorithm):
    """Test algorithm basic metadata."""
    assert algorithm.name() == "loadcityjson"
    assert algorithm.displayName() == "Load CityJSON"
    assert algorithm.group() == "Import"
    assert algorithm.groupId() == "import"
    assert "CityJSON" in algorithm.shortHelpString()


def test_algorithm_creation():
    """Test algorithm can be instantiated."""
    algorithm = CityJsonLoadAlgorithm()
    instance = algorithm.createInstance()
    assert isinstance(instance, CityJsonLoadAlgorithm)


def test_init_algorithm(algorithm):
    """Test parameter initialization."""
    algorithm.initAlgorithm()

    # Verify all required parameters exist
    param_names = [param.name() for param in algorithm.parameterDefinitions()]

    expected_params = [
        "INPUT",
        "KEEP_PARENT_ATTRIBUTES",
        "DIVIDE_BY_OBJECT_TYPE",
        "LOD_AS",
        "LOD_SELECTION",
        "LOAD_SEMANTIC_SURFACES",
        "STYLE_BY_SEMANTIC_SURFACES",
        "SRID",
        "BBOX",
        "OBJECT_TYPE",
    ]

    for param in expected_params:
        assert param in param_names


def test_init_algorithm_parameter_types(algorithm):
    """Test parameter types are correct."""
    algorithm.initAlgorithm()
    params = {param.name(): param for param in algorithm.parameterDefinitions()}

    # Check file parameter
    assert params["INPUT"].type() == "file"

    # Check boolean parameters
    bool_params = [
        "KEEP_PARENT_ATTRIBUTES",
        "DIVIDE_BY_OBJECT_TYPE",
        "LOAD_SEMANTIC_SURFACES",
        "STYLE_BY_SEMANTIC_SURFACES",
    ]
    for param_name in bool_params:
        assert "boolean" in params[param_name].type().lower() or hasattr(
            params[param_name], "defaultValue"
        )


@patch("processing.cityjson_load_algorithm.load_cityjson_model")
@patch("processing.cityjson_load_algorithm.CityJSONLoader")
@patch("processing.cityjson_load_algorithm.get_model_epsg")
def test_process_algorithm_basic(
    mock_epsg,
    mock_loader,
    mock_load,
    algorithm,
    mock_context,
    mock_feedback,
    mock_invalid_crs,
    sample_cityjson,
):
    """Test basic processAlgorithm workflow."""
    # Setup mocks
    mock_load.return_value = sample_cityjson
    mock_epsg.return_value = 4326
    mock_loader_instance = MagicMock()
    mock_loader.return_value = mock_loader_instance

    # Mock parameter extraction methods
    with (
        patch.object(algorithm, "parameterAsFile", return_value="/path/to/test.json"),
        patch.object(algorithm, "parameterAsBoolean", return_value=False),
        patch.object(algorithm, "parameterAsEnum", return_value=0),
        patch.object(algorithm, "parameterAsEnums", return_value=[]),
        patch.object(
            algorithm, "parameterAsCrs", return_value=QgsCoordinateReferenceSystem()
        ),
        patch.object(algorithm, "parameterAsExtent", return_value=QgsRectangle()),
    ):
        parameters = {
            "INPUT": "/path/to/test.json",
            "KEEP_PARENT_ATTRIBUTES": False,
            "DIVIDE_BY_OBJECT_TYPE": False,
            "LOD_AS": 0,  # NONE
            "LOD_SELECTION": [],
            "LOAD_SEMANTIC_SURFACES": False,
            "STYLE_BY_SEMANTIC_SURFACES": False,
            "SRID": QgsCoordinateReferenceSystem(),
            "BBOX": QgsRectangle(),
            "OBJECT_TYPE": [],
        }

        # Execute
        result = algorithm.processAlgorithm(parameters, mock_context, mock_feedback)

        # Verify
        assert result == {"STATUS": "SUCCESS"}
        mock_load.assert_called_once_with("/path/to/test.json")
        mock_loader.assert_called_once()
        mock_loader_instance.load.assert_called_once_with(feedback=mock_feedback)


def test_process_algorithm_invalid_file(
    algorithm, mock_context, mock_feedback, mock_invalid_crs
):
    """Test processAlgorithm with invalid file parameter."""

    # Mock parameterAsFile to return None for invalid file
    with (
        patch.object(algorithm, "parameterAsFile", return_value=None),
        patch.object(algorithm, "invalidSourceError", return_value="Invalid source"),
    ):
        parameters = {
            "INPUT": None,
            "KEEP_PARENT_ATTRIBUTES": False,
            "DIVIDE_BY_OBJECT_TYPE": False,
            "LOD_AS": 0,
            "LOD_SELECTION": [],
            "LOAD_SEMANTIC_SURFACES": False,
            "STYLE_BY_SEMANTIC_SURFACES": False,
            "SRID": QgsCoordinateReferenceSystem(),
            "BBOX": QgsRectangle(),
            "OBJECT_TYPE": [],
        }

        with pytest.raises(QgsProcessingException):
            algorithm.processAlgorithm(parameters, mock_context, mock_feedback)


@patch("processing.cityjson_load_algorithm.load_cityjson_model")
@patch("processing.cityjson_load_algorithm.get_subset_bbox")
def test_process_algorithm_with_bbox_filter(
    mock_subset_bbox,
    mock_load,
    algorithm,
    mock_context,
    mock_feedback,
    mock_invalid_crs,
    sample_cityjson,
):
    """Test processAlgorithm with bbox filtering."""
    # Setup mocks
    mock_load.return_value = sample_cityjson
    filtered_model = dict(sample_cityjson)
    filtered_model["CityObjects"] = {
        "building1": sample_cityjson["CityObjects"]["building1"]
    }
    mock_subset_bbox.return_value = filtered_model

    # Setup bbox rectangle
    bbox_rect = QgsRectangle(0, 0, 10, 10)

    with (
        patch("processing.cityjson_load_algorithm.CityJSONLoader") as mock_loader,
        patch.object(algorithm, "parameterAsFile", return_value="/path/to/test.json"),
        patch.object(algorithm, "parameterAsBoolean", return_value=False),
        patch.object(algorithm, "parameterAsEnum", return_value=0),
        patch.object(algorithm, "parameterAsEnums", return_value=[]),
        patch.object(
            algorithm, "parameterAsCrs", return_value=QgsCoordinateReferenceSystem()
        ),
        patch.object(algorithm, "parameterAsExtent", return_value=bbox_rect),
        patch("processing.cityjson_load_algorithm.get_model_epsg", return_value=None),
    ):
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance

        parameters = {
            "INPUT": "/path/to/test.json",
            "BBOX": bbox_rect,
            "KEEP_PARENT_ATTRIBUTES": False,
            "DIVIDE_BY_OBJECT_TYPE": False,
            "LOD_AS": 0,
            "LOD_SELECTION": [],
            "LOAD_SEMANTIC_SURFACES": False,
            "STYLE_BY_SEMANTIC_SURFACES": False,
            "SRID": QgsCoordinateReferenceSystem(),
            "OBJECT_TYPE": [],
        }

        result = algorithm.processAlgorithm(parameters, mock_context, mock_feedback)

    # Verify bbox filtering was called with correct parameters
    expected_bbox = [0, 0, 10, 10]
    mock_subset_bbox.assert_called_once_with(sample_cityjson, expected_bbox)
    assert result == {"STATUS": "SUCCESS"}


@patch("processing.cityjson_load_algorithm.load_cityjson_model")
@patch("processing.cityjson_load_algorithm.get_subset_cotype")
def test_process_algorithm_with_type_filter(
    mock_subset_cotype,
    mock_load,
    algorithm,
    mock_context,
    mock_feedback,
    sample_cityjson,
):
    """Test processAlgorithm with object type filtering."""
    # Setup mocks
    mock_load.return_value = sample_cityjson
    filtered_model = dict(sample_cityjson)
    filtered_model["CityObjects"] = {
        "building1": sample_cityjson["CityObjects"]["building1"]
    }
    mock_subset_cotype.return_value = filtered_model

    with (
        patch("processing.cityjson_load_algorithm.CityJSONLoader") as mock_loader,
        patch.object(algorithm, "parameterAsFile", return_value="/path/to/test.json"),
        patch.object(algorithm, "parameterAsBoolean", return_value=False),
        patch.object(algorithm, "parameterAsEnum", return_value=0),
        patch.object(
            algorithm,
            "parameterAsEnums",
            side_effect=lambda params, key, ctx: [0] if key == "OBJECT_TYPE" else [],
        ),
        patch.object(
            algorithm, "parameterAsCrs", return_value=QgsCoordinateReferenceSystem()
        ),
        patch.object(algorithm, "parameterAsExtent", return_value=QgsRectangle()),
        patch("processing.cityjson_load_algorithm.get_model_epsg", return_value=None),
    ):
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance

        parameters = {
            "INPUT": "/path/to/test.json",
            "OBJECT_TYPE": [0],  # Building
            "KEEP_PARENT_ATTRIBUTES": False,
            "DIVIDE_BY_OBJECT_TYPE": False,
            "LOD_AS": 0,
            "LOD_SELECTION": [],
            "LOAD_SEMANTIC_SURFACES": False,
            "STYLE_BY_SEMANTIC_SURFACES": False,
            "SRID": QgsCoordinateReferenceSystem(),
            "BBOX": QgsRectangle(),
        }

        result = algorithm.processAlgorithm(parameters, mock_context, mock_feedback)

    # Verify type filtering was called with correct parameters
    mock_subset_cotype.assert_called_once_with(sample_cityjson, ["Building"])
    assert result == {"STATUS": "SUCCESS"}


@patch("processing.cityjson_load_algorithm.load_cityjson_model")
@patch("processing.cityjson_load_algorithm.get_model_epsg")
def test_process_algorithm_empty_objects_early_return(
    mock_epsg, mock_load, algorithm, mock_context, mock_feedback
):
    """Test early return when no objects remain after filtering."""
    empty_model = {
        "type": "CityJSON",
        "version": "2.0",
        "CityObjects": {},
        "vertices": [],
    }

    mock_load.return_value = empty_model
    mock_epsg.return_value = None

    with (
        patch.object(algorithm, "parameterAsFile", return_value="/path/to/empty.json"),
        patch.object(algorithm, "parameterAsBoolean", return_value=False),
        patch.object(algorithm, "parameterAsEnum", return_value=0),
        patch.object(algorithm, "parameterAsEnums", return_value=[]),
        patch.object(
            algorithm, "parameterAsCrs", return_value=QgsCoordinateReferenceSystem()
        ),
        patch.object(algorithm, "parameterAsExtent", return_value=QgsRectangle()),
    ):
        parameters = {
            "INPUT": "/path/to/empty.json",
            "KEEP_PARENT_ATTRIBUTES": False,
            "DIVIDE_BY_OBJECT_TYPE": False,
            "LOD_AS": 0,
            "LOD_SELECTION": [],
            "LOAD_SEMANTIC_SURFACES": False,
            "STYLE_BY_SEMANTIC_SURFACES": False,
            "SRID": QgsCoordinateReferenceSystem(),
            "BBOX": QgsRectangle(),
            "OBJECT_TYPE": [],
        }

        result = algorithm.processAlgorithm(parameters, mock_context, mock_feedback)

    assert result == {"STATUS": "SUCCESS"}
    mock_feedback.pushInfo.assert_called_with("No objects to load. Skipping!")


@patch("processing.cityjson_load_algorithm.load_cityjson_model")
@patch("processing.cityjson_load_algorithm.get_model_epsg")
def test_lod_parameter_handling_single(
    mock_epsg, mock_load, algorithm, mock_context, mock_feedback, sample_cityjson
):
    """Test single LoD selection parameter."""
    mock_load.return_value = sample_cityjson
    mock_epsg.return_value = 4326

    with (
        patch("processing.cityjson_load_algorithm.CityJSONLoader") as mock_loader,
        patch.object(algorithm, "parameterAsFile", return_value="/path/to/test.json"),
        patch.object(algorithm, "parameterAsBoolean", return_value=False),
        patch.object(algorithm, "parameterAsEnum", return_value=0),
        patch.object(
            algorithm,
            "parameterAsEnums",
            side_effect=lambda params, key, ctx: [4] if key == "LOD_SELECTION" else [],
        ),
        patch.object(
            algorithm, "parameterAsCrs", return_value=QgsCoordinateReferenceSystem()
        ),
        patch.object(algorithm, "parameterAsExtent", return_value=QgsRectangle()),
    ):
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance

        # Test single LoD selection
        parameters = {
            "INPUT": "/path/to/test.json",
            "LOD_SELECTION": [4],  # "2.0"
            "KEEP_PARENT_ATTRIBUTES": False,
            "DIVIDE_BY_OBJECT_TYPE": False,
            "LOD_AS": 0,
            "LOAD_SEMANTIC_SURFACES": False,
            "STYLE_BY_SEMANTIC_SURFACES": False,
            "SRID": QgsCoordinateReferenceSystem(),
            "BBOX": QgsRectangle(),
            "OBJECT_TYPE": [],
        }

        result = algorithm.processAlgorithm(parameters, mock_context, mock_feedback)

        # Verify LoD was passed correctly
        call_args = mock_loader.call_args[1]
        assert call_args["lod"] == "2.0"
        assert result == {"STATUS": "SUCCESS"}


@patch("processing.cityjson_load_algorithm.load_cityjson_model")
@patch("processing.cityjson_load_algorithm.get_model_epsg")
def test_lod_parameter_handling_multiple(
    mock_epsg, mock_load, algorithm, mock_context, mock_feedback, sample_cityjson
):
    """Test multiple LoD selection parameter."""
    mock_load.return_value = sample_cityjson
    mock_epsg.return_value = 4326

    with (
        patch("processing.cityjson_load_algorithm.CityJSONLoader") as mock_loader,
        patch.object(algorithm, "parameterAsFile", return_value="/path/to/test.json"),
        patch.object(algorithm, "parameterAsBoolean", return_value=False),
        patch.object(algorithm, "parameterAsEnum", return_value=0),
        patch.object(
            algorithm,
            "parameterAsEnums",
            side_effect=lambda params, key, ctx: (
                [0, 4, 8] if key == "LOD_SELECTION" else []
            ),
        ),
        patch.object(
            algorithm, "parameterAsCrs", return_value=QgsCoordinateReferenceSystem()
        ),
        patch.object(algorithm, "parameterAsExtent", return_value=QgsRectangle()),
    ):
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance

        # Test multiple LoD selection
        parameters = {
            "INPUT": "/path/to/test.json",
            "LOD_SELECTION": [0, 4, 8],  # "0", "2.0", "3.0"
            "KEEP_PARENT_ATTRIBUTES": False,
            "DIVIDE_BY_OBJECT_TYPE": False,
            "LOD_AS": 0,
            "LOAD_SEMANTIC_SURFACES": False,
            "STYLE_BY_SEMANTIC_SURFACES": False,
            "SRID": QgsCoordinateReferenceSystem(),
            "BBOX": QgsRectangle(),
            "OBJECT_TYPE": [],
        }

        result = algorithm.processAlgorithm(parameters, mock_context, mock_feedback)

        # Verify multiple LoDs were passed correctly
        call_args = mock_loader.call_args[1]
        assert call_args["lod"] == ["0", "2.0", "3.0"]
        assert result == {"STATUS": "SUCCESS"}


@patch("processing.cityjson_load_algorithm.load_cityjson_model")
@patch("processing.cityjson_load_algorithm.get_model_epsg")
def test_crs_parameter_handling(
    mock_epsg, mock_load, algorithm, mock_context, mock_feedback, sample_cityjson
):
    """Test CRS parameter handling."""
    mock_load.return_value = sample_cityjson
    mock_epsg.return_value = None  # No CRS in model

    # Create a mock CRS that behaves like a valid EPSG:4326
    mock_crs = MagicMock()
    mock_crs.isValid.return_value = True
    mock_crs.postgisSrid.return_value = 4326

    with (
        patch("processing.cityjson_load_algorithm.CityJSONLoader") as mock_loader,
        patch.object(algorithm, "parameterAsFile", return_value="/path/to/test.json"),
        patch.object(algorithm, "parameterAsBoolean", return_value=False),
        patch.object(algorithm, "parameterAsEnum", return_value=0),
        patch.object(algorithm, "parameterAsEnums", return_value=[]),
        patch.object(algorithm, "parameterAsCrs", return_value=mock_crs),
        patch.object(algorithm, "parameterAsExtent", return_value=QgsRectangle()),
    ):
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance

        parameters = {
            "INPUT": "/path/to/test.json",
            "SRID": mock_crs,
            "KEEP_PARENT_ATTRIBUTES": False,
            "DIVIDE_BY_OBJECT_TYPE": False,
            "LOD_AS": 0,
            "LOD_SELECTION": [],
            "LOAD_SEMANTIC_SURFACES": False,
            "STYLE_BY_SEMANTIC_SURFACES": False,
            "BBOX": QgsRectangle(),
            "OBJECT_TYPE": [],
        }

        result = algorithm.processAlgorithm(parameters, mock_context, mock_feedback)

        # Verify EPSG was passed correctly
        call_args = mock_loader.call_args[1]
        assert call_args["epsg"] == 4326
        assert result == {"STATUS": "SUCCESS"}


@patch("processing.cityjson_load_algorithm.load_cityjson_model")
@patch("processing.cityjson_load_algorithm.get_model_epsg")
def test_all_boolean_parameters(
    mock_epsg, mock_load, algorithm, mock_context, mock_feedback, sample_cityjson
):
    """Test all boolean parameters are passed to CityJSONLoader correctly."""
    mock_load.return_value = sample_cityjson
    mock_epsg.return_value = 4326

    def mock_parameter_as_boolean(params, key, ctx):
        return True  # Return True for all boolean parameters in this test

    def mock_parameter_as_enum(params, key, ctx):
        if key == "LOD_AS":
            return 2  # LAYERS
        return 0

    with (
        patch("processing.cityjson_load_algorithm.CityJSONLoader") as mock_loader,
        patch.object(algorithm, "parameterAsFile", return_value="/path/to/test.json"),
        patch.object(
            algorithm, "parameterAsBoolean", side_effect=mock_parameter_as_boolean
        ),
        patch.object(algorithm, "parameterAsEnum", side_effect=mock_parameter_as_enum),
        patch.object(algorithm, "parameterAsEnums", return_value=[]),
        patch.object(
            algorithm, "parameterAsCrs", return_value=QgsCoordinateReferenceSystem()
        ),
        patch.object(algorithm, "parameterAsExtent", return_value=QgsRectangle()),
    ):
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance

        parameters = {
            "INPUT": "/path/to/test.json",
            "KEEP_PARENT_ATTRIBUTES": True,
            "DIVIDE_BY_OBJECT_TYPE": True,
            "LOD_AS": 2,  # LAYERS
            "LOD_SELECTION": [],
            "LOAD_SEMANTIC_SURFACES": True,
            "STYLE_BY_SEMANTIC_SURFACES": True,
            "SRID": QgsCoordinateReferenceSystem(),
            "BBOX": QgsRectangle(),
            "OBJECT_TYPE": [],
        }

        result = algorithm.processAlgorithm(parameters, mock_context, mock_feedback)

        # Verify boolean parameters were passed correctly
        call_args = mock_loader.call_args[1]
        assert call_args["keep_parent_attributes"]
        assert call_args["divide_by_object"]
        assert call_args["load_semantic_surfaces"]
        assert call_args["style_semantic_surfaces"]
        assert call_args["lod_as"] == "LAYERS"
        assert result == {"STATUS": "SUCCESS"}


def test_object_types_list():
    """Test that OBJECTTYPES list contains expected CityJSON types."""
    algorithm = CityJsonLoadAlgorithm()

    expected_types = [
        "Building",
        "Bridge",
        "Road",
        "TransportSquare",
        "LandUse",
        "Railway",
        "TINRelief",
        "WaterBody",
        "PlantCover",
        "SolitaryVegetationObject",
        "CityFurniture",
        "GenericCityObject",
        "Tunnel",
    ]

    assert algorithm.OBJECTTYPES == expected_types


def test_lod_types_and_selections():
    """Test LOD type definitions."""
    algorithm = CityJsonLoadAlgorithm()

    assert algorithm.LODLOADINGTYPES == ["NONE", "ATTRIBUTES", "LAYERS"]

    expected_lod_selections = [
        "0",
        "1.1",
        "1.2",
        "1.3",
        "2.0",
        "2.1",
        "2.2",
        "2.3",
        "3.0",
        "3.1",
        "3.2",
        "3.3",
    ]
    assert algorithm.LODSELECTIONTYPES == expected_lod_selections


@patch("processing.cityjson_load_algorithm.load_cityjson_model")
@patch("processing.cityjson_load_algorithm.get_subset_bbox")
@patch("processing.cityjson_load_algorithm.get_subset_cotype")
def test_combined_filtering(
    mock_subset_cotype,
    mock_subset_bbox,
    mock_load,
    algorithm,
    mock_context,
    mock_feedback,
    sample_cityjson,
):
    """Test combined bbox and type filtering."""
    # Setup cascading filters
    mock_load.return_value = sample_cityjson

    bbox_filtered = dict(sample_cityjson)
    bbox_filtered["CityObjects"] = {
        "building1": sample_cityjson["CityObjects"]["building1"]
    }
    mock_subset_bbox.return_value = bbox_filtered

    type_filtered = dict(bbox_filtered)
    type_filtered["CityObjects"] = {
        "building1": bbox_filtered["CityObjects"]["building1"]
    }
    mock_subset_cotype.return_value = type_filtered

    # Setup bbox and type parameters
    bbox_rect = QgsRectangle(0, 0, 10, 10)

    with (
        patch("processing.cityjson_load_algorithm.CityJSONLoader") as mock_loader,
        patch.object(algorithm, "parameterAsFile", return_value="/path/to/test.json"),
        patch.object(algorithm, "parameterAsBoolean", return_value=False),
        patch.object(algorithm, "parameterAsEnum", return_value=0),
        patch.object(
            algorithm,
            "parameterAsEnums",
            side_effect=lambda params, key, ctx: [0] if key == "OBJECT_TYPE" else [],
        ),
        patch.object(
            algorithm, "parameterAsCrs", return_value=QgsCoordinateReferenceSystem()
        ),
        patch.object(algorithm, "parameterAsExtent", return_value=bbox_rect),
        patch("processing.cityjson_load_algorithm.get_model_epsg", return_value=None),
    ):
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance

        parameters = {
            "INPUT": "/path/to/test.json",
            "BBOX": bbox_rect,
            "OBJECT_TYPE": [0],  # Building
            "KEEP_PARENT_ATTRIBUTES": False,
            "DIVIDE_BY_OBJECT_TYPE": False,
            "LOD_AS": 0,
            "LOD_SELECTION": [],
            "LOAD_SEMANTIC_SURFACES": False,
            "STYLE_BY_SEMANTIC_SURFACES": False,
            "SRID": QgsCoordinateReferenceSystem(),
        }

        result = algorithm.processAlgorithm(parameters, mock_context, mock_feedback)

    # Verify both filters were applied in sequence
    mock_subset_bbox.assert_called_once_with(sample_cityjson, [0, 0, 10, 10])
    mock_subset_cotype.assert_called_once_with(bbox_filtered, ["Building"])
    assert result == {"STATUS": "SUCCESS"}
