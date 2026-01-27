# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

from core import subset


def test_select_co_ids_basic():
    cm = {
        "CityObjects": {
            "id1": {"type": "Building"},
            "id2": {"type": "Bridge"},
            "id3": {"type": "Other"},
        }
    }
    result = subset.select_co_ids(cm, ["id1", "id3"])
    assert "id1" in result
    assert "id3" in result
    assert "id2" not in result


def test_process_geometry_updates_vertices():
    cm = {
        "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
        "CityObjects": {
            "id1": {"geometry": [{"boundaries": [[0, 1, 2]], "type": "Solid"}]}
        },
    }
    cm2 = {
        "CityObjects": {
            "id1": {"geometry": [{"boundaries": [[0, 1, 2]], "type": "Solid"}]}
        }
    }
    subset.process_geometry(cm, cm2)
    assert "vertices" in cm2
    assert len(cm2["vertices"]) == 3


def test_process_templates_handles_empty():
    cm = {
        "geometry-templates": {"vertices-templates": [], "templates": []},
        "CityObjects": {},
    }
    cm2 = {"CityObjects": {}}
    subset.process_templates(cm, cm2)
    assert "geometry-templates" not in cm2 or "vertices-templates" in cm2.get(
        "geometry-templates", {}
    )


def test_process_appearance_handles_empty():
    cm = {
        "appearance": {"materials": [], "textures": [], "vertices-texture": []},
        "CityObjects": {},
    }
    cm2 = {"CityObjects": {}}
    subset.process_appearance(cm, cm2)
    assert "appearance" not in cm2 or "materials" in cm2.get("appearance", {})


def test_update_array_indices_basic():
    arr = [0, 1, 2]
    dOldNewIDs = {}
    oldarray = [10, 20, 30]
    newarray = []
    subset.update_array_indices(arr, dOldNewIDs, oldarray, newarray, -1)
    assert newarray == [10, 20, 30]
    assert arr == [0, 1, 2]
