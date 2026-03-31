# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

import pytest
from core import utils


def test_create_cityjson():
    cj = utils.createCityJSON()
    assert cj["type"] == utils.CITYJSON_TYPE
    assert cj["version"] == utils.CITYJSON_VERSION
    assert cj["CityObjects"] == {}
    assert cj["vertices"] == []


def test_get_centroid_basic():
    cm = {
        "CityObjects": {
            "id1": {"geometry": [{"boundaries": [[0, 1, 2]], "type": "Solid"}]}
        },
        "vertices": [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
        ],
    }
    centroid = utils.get_centroid(cm, "id1")
    assert pytest.approx(centroid) == [1 / 3, 1 / 3, 0]


def test_get_centroid_with_transform():
    cm = {
        "CityObjects": {
            "id1": {"geometry": [{"boundaries": [[0, 1, 2]], "type": "Solid"}]}
        },
        "vertices": [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
        ],
        "transform": {"scale": [2, 2, 2], "translate": [10, 20, 30]},
    }
    centroid = utils.get_centroid(cm, "id1")
    assert pytest.approx(centroid) == [10 + 2 / 3, 20 + 2 / 3, 30]


def test_get_centroid_with_transform_simple():
    cm = {
        "CityObjects": {
            "id1": {"geometry": [{"boundaries": [[0, 1, 2]], "type": "Solid"}]}
        },
        "vertices": [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
        ],
        "transform": {"scale": [2, 2, 2], "translate": [5, 10, 20]},
    }
    centroid = utils.get_centroid(cm, "id1")
    # The centroid before transform is [1/3, 1/3, 0]
    # After transform: [5 + 2/3, 10 + 2/3, 20]
    assert pytest.approx(centroid) == [5 + 2 / 3, 10 + 2 / 3, 20]


def test_get_subset_cotype(monkeypatch):
    cm = {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
        "CityObjects": {
            "id1": {"type": "Building"},
            "id2": {"type": "Bridge"},
            "id3": {"type": "Other"},
        },
        "vertices": [],
    }

    # Patch subset.process_geometry, process_templates, process_appearance
    monkeypatch.setattr(utils.subset, "process_geometry", lambda cm, cm2: None)
    monkeypatch.setattr(utils.subset, "process_templates", lambda cm, cm2: None)
    monkeypatch.setattr(utils.subset, "process_appearance", lambda cm, cm2: None)
    result = utils.get_subset_cotype(cm, "Building")
    assert "id1" in result["CityObjects"]
    assert "id2" not in result["CityObjects"]
    assert "id3" not in result["CityObjects"]


def test_get_subset_bbox(monkeypatch):
    cm = {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
        "CityObjects": {
            "id1": {"geometry": [{"boundaries": [[0, 1, 2]], "type": "Solid"}]},
            "id2": {"geometry": [{"boundaries": [[3, 4, 5]], "type": "Solid"}]},
        },
        "vertices": [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [10, 10, 0],
            [11, 10, 0],
            [10, 11, 0],
        ],
    }
    monkeypatch.setattr(utils.subset, "process_geometry", lambda cm, cm2: None)
    monkeypatch.setattr(utils.subset, "process_templates", lambda cm, cm2: None)
    monkeypatch.setattr(utils.subset, "process_appearance", lambda cm, cm2: None)
    bbox = [0, 0, 2, 2]
    result = utils.get_subset_bbox(cm, bbox)
    assert "id1" in result["CityObjects"]
    assert "id2" not in result["CityObjects"]
