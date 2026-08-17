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


def test_get_centroid_nonexistent_object():
    """Tests get_centroid with non-existent city object ID"""
    cm = {
        "CityObjects": {
            "id1": {"geometry": [{"boundaries": [[0, 1, 2]], "type": "Solid"}]}
        },
        "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
    }
    result = utils.get_centroid(cm, "nonexistent")
    assert result is None


def test_get_centroid_object_without_geometry():
    """Tests get_centroid with city object that has no geometry"""
    cm = {
        "CityObjects": {"id1": {"type": "Building"}},
        "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
    }
    result = utils.get_centroid(cm, "id1")
    assert result is None


def test_get_centroid_empty_geometry():
    """Tests get_centroid with city object that has empty geometry array"""
    cm = {
        "CityObjects": {"id1": {"geometry": []}},
        "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
    }
    result = utils.get_centroid(cm, "id1")
    assert result is None


def test_get_centroid_complex_nested_boundaries():
    """Tests get_centroid with complex nested boundary structure"""
    cm = {
        "CityObjects": {
            "id1": {
                "geometry": [
                    {
                        "boundaries": [
                            [[[0, 1, 2]], [[1, 2, 3]]],  # Nested structure
                            [[[3, 4, 5]]],
                        ],
                        "type": "MultiSurface",
                    }
                ]
            }
        },
        "vertices": [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],  # 0, 1, 2
            [1, 1, 0],
            [2, 0, 0],
            [2, 1, 0],  # 3, 4, 5
        ],
    }
    centroid = utils.get_centroid(cm, "id1")
    # Should collect all vertex indices: 0,1,2,1,2,3,3,4,5
    # Unique vertices used: 0,1,2,1,2,3,3,4,5 -> coords: [0,0,0],[1,0,0],[0,1,0],[1,0,0],[0,1,0],[1,1,0],[1,1,0],[2,0,0],[2,1,0]
    # Sum: [0+1+0+1+0+1+1+2+2, 0+0+1+0+1+1+1+0+1, 0] = [8, 5, 0]
    # Count: 9, Centroid: [8/9, 5/9, 0]
    assert pytest.approx(centroid) == [8 / 9, 5 / 9, 0]


def test_get_centroid_with_transform_and_complex_geometry():
    """Tests get_centroid with both transform and complex geometry"""
    cm = {
        "CityObjects": {
            "id1": {"geometry": [{"boundaries": [[[0, 1, 2, 0]]], "type": "Solid"}]}
        },
        "vertices": [[0, 0, 0], [10, 0, 0], [5, 10, 0]],
        "transform": {"scale": [0.1, 0.1, 0.1], "translate": [100, 200, 300]},
    }
    centroid = utils.get_centroid(cm, "id1")
    # Original vertices used: [0, 1, 2, 0] -> coords: [0,0,0], [10,0,0], [5,10,0], [0,0,0]
    # Sum: [15, 10, 0], Count: 4, Raw centroid: [3.75, 2.5, 0]
    # After transform: [100 + 3.75*0.1, 200 + 2.5*0.1, 300 + 0*0.1] = [100.375, 200.25, 300]
    assert pytest.approx(centroid) == [100.375, 200.25, 300]


def test_get_subset_cotype_with_multitype_objects(monkeypatch):
    """Tests get_subset_cotype with various CityObject types"""
    cm = {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
        "CityObjects": {
            "building1": {"type": "Building"},
            "part1": {"type": "BuildingPart", "parents": ["building1"]},
            "bridge1": {"type": "Bridge"},
            "road1": {"type": "Road"},
            "other1": {"type": "GenericCityObject"},
        },
        "vertices": [],
    }

    # Patch subset functions
    monkeypatch.setattr(utils.subset, "process_geometry", lambda cm, cm2: None)
    monkeypatch.setattr(utils.subset, "process_templates", lambda cm, cm2: None)
    monkeypatch.setattr(utils.subset, "process_appearance", lambda cm, cm2: None)

    # Test filtering by BuildingPart
    result = utils.get_subset_cotype(cm, "BuildingPart")
    assert "part1" in result["CityObjects"]
    assert "building1" not in result["CityObjects"]
    assert "bridge1" not in result["CityObjects"]

    # Test filtering by Road
    result = utils.get_subset_cotype(cm, "Road")
    assert "road1" in result["CityObjects"]
    assert len(result["CityObjects"]) == 1


def test_get_subset_bbox_edge_cases(monkeypatch):
    """Tests get_subset_bbox with edge case scenarios"""
    # Patch subset functions
    monkeypatch.setattr(utils.subset, "process_geometry", lambda cm, cm2: None)
    monkeypatch.setattr(utils.subset, "process_templates", lambda cm, cm2: None)
    monkeypatch.setattr(utils.subset, "process_appearance", lambda cm, cm2: None)

    # Test with objects without geometry
    cm = {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
        "CityObjects": {
            "id1": {"type": "Building"},  # No geometry
        },
        "vertices": [],
    }
    bbox = [0, 0, 10, 10]
    result = utils.get_subset_bbox(cm, bbox)
    # Objects without geometry have no centroid, so they are excluded from bbox filtering
    assert "id1" not in result["CityObjects"]
    assert len(result["CityObjects"]) == 0

    # Test with exactly on bbox boundary
    cm = {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
        "CityObjects": {
            "boundary": {"geometry": [{"boundaries": [[0, 1, 2]], "type": "Solid"}]},
        },
        "vertices": [[4, 4, 0], [4, 4, 0], [4, 4, 0]],  # Inside boundary
    }
    bbox = [0, 0, 5, 5]  # bbox boundary at x=5, y=5, point at (4,4) is inside
    result = utils.get_subset_bbox(cm, bbox)
    # Point inside boundary should be included (4 >= 0, 4 >= 0, 4 < 5, 4 < 5)
    assert "boundary" in result["CityObjects"]
