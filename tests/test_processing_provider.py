# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.
from processing.provider import Provider
from processing.cityjson_load_algorithm import CityJsonLoadAlgorithm


def test_provider_metadata():
    """Test provider basic metadata."""
    provider = Provider()

    assert provider.id() == "cityjsonloader"
    assert "CityJSON" in provider.name() or "cityjson" in provider.name().lower()


def test_provider_loads_algorithms():
    """Test that provider correctly loads algorithms."""
    provider = Provider()

    # Call loadAlgorithms to populate algorithms
    provider.loadAlgorithms()

    # Check that algorithms were added
    algorithms = provider.algorithms()
    assert len(algorithms) > 0

    # Check that our algorithm is present
    algorithm_names = [alg.name() for alg in algorithms]
    assert "loadcityjson" in algorithm_names

    # Check algorithm type
    cityjson_alg = next(alg for alg in algorithms if alg.name() == "loadcityjson")
    assert isinstance(cityjson_alg, CityJsonLoadAlgorithm)


def test_provider_algorithm_count():
    """Test that provider loads expected number of algorithms."""
    provider = Provider()
    provider.loadAlgorithms()

    # Currently we only have one algorithm
    algorithms = provider.algorithms()
    assert len(algorithms) == 1


def test_provider_algorithm_properties():
    """Test properties of loaded algorithms."""
    provider = Provider()
    provider.loadAlgorithms()

    algorithms = provider.algorithms()
    cityjson_alg = algorithms[0]

    # Test algorithm has required methods
    assert hasattr(cityjson_alg, "name")
    assert hasattr(cityjson_alg, "displayName")
    assert hasattr(cityjson_alg, "group")
    assert hasattr(cityjson_alg, "groupId")
    assert hasattr(cityjson_alg, "processAlgorithm")

    # Test algorithm metadata
    assert cityjson_alg.name() == "loadcityjson"
    assert cityjson_alg.displayName() == "Load CityJSON"
    assert cityjson_alg.group() == "Import"
    assert cityjson_alg.groupId() == "import"


def test_provider_can_be_instantiated():
    """Test that provider can be created without errors."""
    provider = Provider()
    assert provider is not None
    assert hasattr(provider, "loadAlgorithms")
    assert hasattr(provider, "algorithms")
    assert hasattr(provider, "id")
    assert hasattr(provider, "name")


def test_provider_id_format():
    """Test provider ID follows expected format."""
    provider = Provider()
    provider_id = provider.id()

    # ID should be lowercase, no spaces
    assert provider_id.islower()
    assert " " not in provider_id
    assert provider_id == "cityjsonloader"


def test_provider_multiple_instantiation():
    """Test that multiple provider instances work correctly."""
    provider1 = Provider()
    provider2 = Provider()

    provider1.loadAlgorithms()
    provider2.loadAlgorithms()

    # Both should have the same algorithms
    assert len(provider1.algorithms()) == len(provider2.algorithms())
    assert provider1.algorithms()[0].name() == provider2.algorithms()[0].name()


def test_provider_algorithm_initialization():
    """Test that algorithms are properly initialized after loading."""
    provider = Provider()
    provider.loadAlgorithms()

    algorithm = provider.algorithms()[0]

    # Algorithm should be able to initialize parameters
    algorithm.initAlgorithm()

    # Should have parameter definitions
    params = algorithm.parameterDefinitions()
    assert len(params) > 0

    # Check for required parameters
    param_names = [param.name() for param in params]
    assert "INPUT" in param_names
