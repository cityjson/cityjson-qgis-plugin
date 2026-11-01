# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

import pytest

from processing.cityjson_export_algorithm import CityJsonExportAlgorithm


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