# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.
from core import subset


# ============================================================================
# SELECT_CO_IDS TESTS
# ============================================================================


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


def test_select_co_ids_empty_input():
    cm = {"CityObjects": {}}
    result = subset.select_co_ids(cm, [])
    assert len(result) == 0


def test_select_co_ids_nonexistent_ids(capsys):
    cm = {
        "CityObjects": {
            "id1": {"type": "Building"},
            "id2": {"type": "Bridge"},
        }
    }
    result = subset.select_co_ids(cm, ["id1", "nonexistent", "id2"])
    captured = capsys.readouterr()

    assert "id1" in result
    assert "id2" in result
    assert "nonexistent" not in result
    assert "WARNING: ID nonexistent not found" in captured.out


def test_select_co_ids_with_city_object_group():
    cm = {
        "CityObjects": {
            "group1": {
                "type": "CityObjectGroup",
                "children": ["building1", "building2"],
            },
            "building1": {"type": "Building", "parents": ["group1"]},
            "building2": {"type": "Building", "parents": ["group1"]},
            "building3": {"type": "Building"},
        }
    }
    result = subset.select_co_ids(cm, ["group1"])

    assert "group1" in result
    assert "building1" in result  # member of group
    assert "building2" in result  # member of group
    assert "building3" not in result  # not a member


def test_select_co_ids_with_city_object_group_no_members():
    cm = {
        "CityObjects": {
            "group1": {"type": "CityObjectGroup"},  # No members key
            "building1": {"type": "Building"},
        }
    }
    result = subset.select_co_ids(cm, ["group1"])

    assert "group1" in result
    assert "building1" not in result


def test_select_co_ids_with_children():
    cm = {
        "CityObjects": {
            "parent1": {"type": "Building", "children": ["part1", "part2"]},
            "part1": {"type": "BuildingPart", "parents": ["parent1"]},
            "part2": {"type": "BuildingPart", "parents": ["parent1"]},
            "unrelated": {"type": "Building"},
        }
    }
    result = subset.select_co_ids(cm, ["parent1"])

    assert "parent1" in result
    assert "part1" in result  # child of parent1
    assert "part2" in result  # child of parent1
    assert "unrelated" not in result


def test_select_co_ids_with_parent():
    cm = {
        "CityObjects": {
            "parent1": {"type": "Building", "children": ["part1", "part2"]},
            "part1": {"type": "BuildingPart", "parents": ["parent1"]},
            "part2": {"type": "BuildingPart", "parents": ["parent1"]},
        }
    }
    result = subset.select_co_ids(cm, ["part1"])

    assert "part1" in result
    assert "parent1" in result  # parent of part1


# ============================================================================
# PROCESS_GEOMETRY TESTS
# ============================================================================


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
    assert cm2["vertices"][0] == [0, 0, 0]
    assert cm2["vertices"][1] == [1, 0, 0]
    assert cm2["vertices"][2] == [0, 1, 0]


def test_process_geometry_complex_boundaries():
    cm = {
        "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1]],
        "CityObjects": {
            "building": {
                "geometry": [
                    {
                        "boundaries": [
                            [[0, 1, 2]],  # face 1
                            [[1, 3, 4], [0, 2, 4]],  # face 2 with nested arrays
                        ],
                        "type": "MultiSurface",
                    }
                ]
            }
        },
    }
    cm2 = {
        "CityObjects": {
            "building": {
                "geometry": [
                    {
                        "boundaries": [[[0, 1, 2]], [[1, 3, 4], [0, 2, 4]]],
                        "type": "MultiSurface",
                    }
                ]
            }
        }
    }

    subset.process_geometry(cm, cm2)
    assert len(cm2["vertices"]) == 5
    # Verify all original vertices are preserved
    assert [0, 0, 0] in cm2["vertices"]
    assert [1, 1, 1] in cm2["vertices"]


def test_process_geometry_multiple_objects():
    cm = {
        "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "CityObjects": {
            "obj1": {"geometry": [{"boundaries": [[0, 1, 2]], "type": "Solid"}]},
            "obj2": {"geometry": [{"boundaries": [[1, 2, 3]], "type": "Solid"}]},
        },
    }
    cm2 = {
        "CityObjects": {
            "obj1": {"geometry": [{"boundaries": [[0, 1, 2]], "type": "Solid"}]},
            "obj2": {"geometry": [{"boundaries": [[1, 2, 3]], "type": "Solid"}]},
        }
    }

    subset.process_geometry(cm, cm2)
    assert len(cm2["vertices"]) == 4


def test_process_geometry_no_geometry():
    cm = {
        "vertices": [[0, 0, 0]],
        "CityObjects": {"obj1": {"type": "Building"}},  # No geometry
    }
    cm2 = {"CityObjects": {"obj1": {"type": "Building"}}}

    # Should not raise error and should create empty vertices array
    subset.process_geometry(cm, cm2)
    assert "vertices" in cm2
    assert len(cm2["vertices"]) == 0


# ============================================================================
# PROCESS_TEMPLATES TESTS
# ============================================================================


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


def test_process_templates_with_geometry_instance():
    cm = {
        "geometry-templates": {
            "vertices-templates": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
            "templates": [{"type": "MultiSurface", "boundaries": [[[0, 1, 2]]]}],
        },
        "CityObjects": {
            "instance1": {
                "geometry": [
                    {
                        "type": "GeometryInstance",
                        "template": 0,
                        "transformationMatrix": [
                            1,
                            0,
                            0,
                            0,
                            0,
                            1,
                            0,
                            0,
                            0,
                            0,
                            1,
                            0,
                            0,
                            0,
                            0,
                            1,
                        ],
                    }
                ]
            }
        },
    }
    cm2 = {
        "CityObjects": {
            "instance1": {
                "geometry": [
                    {
                        "type": "GeometryInstance",
                        "template": 0,
                        "transformationMatrix": [
                            1,
                            0,
                            0,
                            0,
                            0,
                            1,
                            0,
                            0,
                            0,
                            0,
                            1,
                            0,
                            0,
                            0,
                            0,
                            1,
                        ],
                    }
                ]
            }
        }
    }

    subset.process_templates(cm, cm2)

    assert "geometry-templates" in cm2
    assert len(cm2["geometry-templates"]["templates"]) == 1
    assert cm2["geometry-templates"]["vertices-templates"] == [
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
    ]
    # Template index should remain 0 (first and only template)
    assert cm2["CityObjects"]["instance1"]["geometry"][0]["template"] == 0


def test_process_templates_multiple_instances_same_template():
    cm = {
        "geometry-templates": {
            "vertices-templates": [[0, 0, 0], [1, 0, 0]],
            "templates": [{"type": "MultiSurface", "boundaries": [[[0, 1]]]}],
        },
        "CityObjects": {
            "instance1": {"geometry": [{"type": "GeometryInstance", "template": 0}]},
            "instance2": {"geometry": [{"type": "GeometryInstance", "template": 0}]},
        },
    }
    cm2 = {
        "CityObjects": {
            "instance1": {"geometry": [{"type": "GeometryInstance", "template": 0}]},
            "instance2": {"geometry": [{"type": "GeometryInstance", "template": 0}]},
        }
    }

    subset.process_templates(cm, cm2)

    # Should only have one template (reused)
    assert len(cm2["geometry-templates"]["templates"]) == 1
    # Both instances should point to the same template (index 0)
    assert cm2["CityObjects"]["instance1"]["geometry"][0]["template"] == 0
    assert cm2["CityObjects"]["instance2"]["geometry"][0]["template"] == 0


def test_process_templates_no_geometry_instances():
    cm = {
        "geometry-templates": {
            "vertices-templates": [[0, 0, 0]],
            "templates": [{"type": "MultiSurface"}],
        },
        "CityObjects": {"regular": {"geometry": [{"type": "Solid", "boundaries": []}]}},
    }
    cm2 = {
        "CityObjects": {"regular": {"geometry": [{"type": "Solid", "boundaries": []}]}}
    }

    subset.process_templates(cm, cm2)

    # No geometry-templates should be added since no GeometryInstance was found
    assert "geometry-templates" not in cm2


# ============================================================================
# PROCESS_APPEARANCE TESTS
# ============================================================================


def test_process_appearance_handles_empty():
    cm = {
        "appearance": {"materials": [], "textures": [], "vertices-texture": []},
        "CityObjects": {},
    }
    cm2 = {"CityObjects": {}}
    subset.process_appearance(cm, cm2)
    assert "appearance" not in cm2 or "materials" in cm2.get("appearance", {})


def test_process_appearance_with_materials():
    cm = {
        "appearance": {
            "materials": [
                {"name": "roof", "diffuseColor": [0.8, 0.2, 0.2]},
                {"name": "wall", "diffuseColor": [0.2, 0.8, 0.2]},
            ],
            "textures": [],
            "vertices-texture": [],
        },
        "CityObjects": {
            "building": {
                "geometry": [
                    {
                        "type": "Solid",
                        "boundaries": [[[0, 1, 2]]],
                        "material": {
                            "exterior-wall": {"value": 1},
                            "roof": {"values": [0]},
                        },
                    }
                ]
            }
        },
    }
    cm2 = {
        "CityObjects": {
            "building": {
                "geometry": [
                    {
                        "type": "Solid",
                        "boundaries": [[[0, 1, 2]]],
                        "material": {
                            "exterior-wall": {"value": 1},
                            "roof": {"values": [0]},
                        },
                    }
                ]
            }
        }
    }

    subset.process_appearance(cm, cm2)

    assert "appearance" in cm2
    assert len(cm2["appearance"]["materials"]) == 2
    assert cm2["appearance"]["materials"][0]["name"] == "wall"
    assert cm2["appearance"]["materials"][1]["name"] == "roof"


def test_process_appearance_with_textures():
    cm = {
        "appearance": {
            "materials": [],
            "textures": [
                {"type": "PNG", "image": "roof.png"},
                {"type": "JPG", "image": "wall.jpg"},
            ],
            "vertices-texture": [
                [0.0, 0.0],
                [1.0, 0.0],
                [0.0, 1.0],
                [0.5, 0.5],
                [1.0, 1.0],
            ],
        },
        "CityObjects": {
            "building": {
                "geometry": [
                    {
                        "type": "Solid",
                        "boundaries": [[[0, 1, 2]]],
                        "texture": {
                            "exterior-wall": {"values": [[0, 0, 1, 2], [1, 2, 3, 4]]}
                        },
                    }
                ]
            }
        },
    }
    cm2 = {
        "CityObjects": {
            "building": {
                "geometry": [
                    {
                        "type": "Solid",
                        "boundaries": [[[0, 1, 2]]],
                        "texture": {
                            "exterior-wall": {"values": [[0, 0, 1, 2], [1, 2, 3, 4]]}
                        },
                    }
                ]
            }
        }
    }

    subset.process_appearance(cm, cm2)

    assert "appearance" in cm2
    assert len(cm2["appearance"]["textures"]) == 2
    assert len(cm2["appearance"]["vertices-texture"]) == 5


def test_process_appearance_no_appearance_data():
    cm = {"CityObjects": {"obj": {"geometry": [{"type": "Solid"}]}}}
    cm2 = {"CityObjects": {"obj": {"geometry": [{"type": "Solid"}]}}}

    # Should not raise errors
    subset.process_appearance(cm, cm2)
    # No appearance key should be added
    assert "appearance" not in cm2


# ============================================================================
# UPDATE_ARRAY_INDICES TESTS
# ============================================================================


def test_update_array_indices_basic():
    arr = [0, 1, 2]
    dOldNewIDs = {}
    oldarray = [10, 20, 30]
    newarray = []
    subset.update_array_indices(arr, dOldNewIDs, oldarray, newarray, -1)
    assert newarray == [10, 20, 30]
    assert arr == [0, 1, 2]


def test_update_array_indices_nested_array():
    arr = [[0, 1], [1, 2]]
    dOldNewIDs = {}
    oldarray = ["a", "b", "c"]
    newarray = []
    subset.update_array_indices(arr, dOldNewIDs, oldarray, newarray, -1)

    assert newarray == ["a", "b", "c"]
    assert arr == [[0, 1], [1, 2]]  # indices should be updated


def test_update_array_indices_with_none_values():
    arr = [0, None, 1]
    dOldNewIDs = {}
    oldarray = ["a", "b"]
    newarray = []
    subset.update_array_indices(arr, dOldNewIDs, oldarray, newarray, -1)

    assert newarray == ["a", "b"]
    assert arr[0] == 0
    assert arr[1] is None  # None values should be preserved
    assert arr[2] == 1


def test_update_array_indices_slice_first_only():
    arr = [0, 1, 2]  # Only first element (index 0) should be processed
    dOldNewIDs = {}
    oldarray = ["texture1", "texture2", "vertex1"]
    newarray = []
    subset.update_array_indices(arr, dOldNewIDs, oldarray, newarray, 0)

    assert len(newarray) == 1  # Only first element processed
    assert newarray[0] == "texture1"
    assert arr[0] == 0  # First element updated
    assert arr[1] == 1  # Other elements unchanged
    assert arr[2] == 2


def test_update_array_indices_slice_skip_first():
    arr = [0, 1, 2]  # Skip first element (index 0), process rest
    dOldNewIDs = {}
    oldarray = ["skip", "vertex1", "vertex2"]
    newarray = []
    subset.update_array_indices(arr, dOldNewIDs, oldarray, newarray, 1)

    assert len(newarray) == 2  # Skip first, process 1,2
    assert newarray[0] == "vertex1"
    assert newarray[1] == "vertex2"
    assert arr[0] == 0  # First element unchanged
    assert arr[1] == 0  # Second element updated to new index
    assert arr[2] == 1  # Third element updated to new index


def test_update_array_indices_reuse_existing_mapping():
    arr = [0, 0, 1]  # Duplicate reference to index 0
    dOldNewIDs = {}
    oldarray = ["item1", "item2"]
    newarray = []
    subset.update_array_indices(arr, dOldNewIDs, oldarray, newarray, -1)

    assert len(newarray) == 2  # Should have both unique items
    assert arr == [0, 0, 1]  # First two should both point to same new index
    assert dOldNewIDs[0] == 0  # Mapping should be reused
    assert dOldNewIDs[1] == 1


def test_update_array_indices_deeply_nested():
    arr = [[[0, 1]], [[1, 2]]]
    dOldNewIDs = {}
    oldarray = ["a", "b", "c"]
    newarray = []
    subset.update_array_indices(arr, dOldNewIDs, oldarray, newarray, -1)

    assert newarray == ["a", "b", "c"]
    # Check that deeply nested indices are properly updated
    assert isinstance(arr[0][0], list)
    assert len(arr[0][0]) == 2
