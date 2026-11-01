import json
import os
import shutil
import tempfile
import pytest
import copy

from core.loading import CityJSONLoader, load_cityjson_model
from core.exporting import CityJSONExporter, read_provenance, save_cityjson_model


def _cube_vertices(dx):
    """Eight cube corners, shifted dx along x"""
    return [
        [0 + dx, 0, 0],
        [1000 + dx, 0, 0],
        [1000 + dx, 1000, 0],
        [0 + dx, 1000, 0],
        [0 + dx, 0, 1000],
        [1000 + dx, 0, 1000],
        [1000 + dx, 1000, 1000],
        [0 + dx, 1000, 1000],
    ]


def _cube_geometry(first_vertex):
    """A Multisurface cube whose eight corners start at first_vertex"""
    o = first_vertex
    return {
        "type": "MultiSurface",
        "lod": "1",
        "boundaries": [
            [[o + 0, o + 3, o + 2, o + 1]],  # ground
            [[o + 4, o + 5, o + 6, o + 7]],  # roof
            [[o + 0, o + 1, o + 5, o + 4]],  # wall
            [[o + 1, o + 2, o + 6, o + 5]],  # wall
            [[o + 2, o + 3, o + 7, o + 6]],  # wall
            [[o + 3, o + 0, o + 4, o + 7]],  # wall
        ],
    }


def _two_cubes_citymodel():
    """A CityJSON model with two cubes, one shifted along x"""
    return {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {"scale": [0.001, 0.001, 0.001], "translate": [0.0, 0.0, 0.0]},
        "vertices": _cube_vertices(0)
        + _cube_vertices(1000),  # two cubes, one shifted along x
        "CityObjects": {
            "building1": {
                "type": "Building",
                "attributes": {"function": "residential"},
                "geometry": [_cube_geometry(0)],
            },
            "building2": {
                "type": "Building",
                "attributes": {"function": "commercial"},
                "geometry": [_cube_geometry(8)],  # because vuilding 1 already uses 0-7
            },
        },
    }


def _hierarchy_citymodel():
    """A CityJSON model with a hierarchy of two buildings, one parent and one child"""
    return {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {"scale": [0.001, 0.001, 0.001], "translate": [0.0, 0.0, 0.0]},
        "vertices": _cube_vertices(0)
        + _cube_vertices(1000)
        + _cube_vertices(2000),  # two cubes, one shifted along x
        "CityObjects": {
            "building1": {
                "type": "Building",
                "attributes": {"function": "residential"},
                "geometry": [_cube_geometry(0)],
                "children": ["building2", "building3"],
            },
            "building2": {
                "type": "BuildingPart",
                "attributes": {"function": "commercial"},
                "geometry": [_cube_geometry(8)],  # because building 1 already uses 0-7
                "parents": ["building1"],
            },
            "building3": {
                "type": "BuildingPart",
                "attributes": {"function": "commercial"},
                "geometry": [
                    _cube_geometry(16)
                ],  # because building 1 already uses 0-7, building2 uses 8-15
                "parents": ["building1"],
            },
        },
    }


def _unloaded_lod_citymodel():
    """house_a and house_b have LoD1 + LoD2; tree has only LoD2"""
    return {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {"scale": [0.001, 0.001, 0.001], "translate": [0.0, 0.0, 0.0]},
        "vertices": _cube_vertices(0)
        + _cube_vertices(2000)
        + _cube_vertices(4000),  # three cubes, shifted along x
        "CityObjects": {
            "house_a": {
                "type": "Building",
                "attributes": {"function": "residential"},
                "geometry": [
                    _cube_geometry(0),
                    {**_cube_geometry(0), "lod": "2"},
                ],  # ** copies every key from _cube_geometry(0), then lod 2 overwrites LoD
            },
            "house_b": {
                "type": "Building",
                "attributes": {"function": "commercial"},
                "geometry": [
                    _cube_geometry(8),
                    {**_cube_geometry(8), "lod": "2"},
                ],  # because house_a, already uses 0-7
            },
            "tree": {
                "type": "SolitaryVegetationObject",
                "geometry": [{**_cube_geometry(16), "lod": "2"}],
            },
        },
    }


def _cube_solid(first_vertex):
    """A Solid cube (one shell, six faces) whose corners start at first_vertex"""
    return {
        "type": "Solid",
        "lod": "2",
        "boundaries": [_cube_geometry(first_vertex)["boundaries"]],
    }


def _fidelity_citymodel():
    """building1 (kept): LoD2 Solid + semantics + material 1, and LoD1.
    building2 (deleted): LoD2 Solid + material 0."""
    return {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {"scale": [0.001, 0.001, 0.001], "translate": [0.0, 0.0, 0.0]},
        "metadata": {"title": "fidelity test"},
        "appearance": {"materials": [{"name": "red"}, {"name": "blue"}]},
        "vertices": _cube_vertices(0) + _cube_vertices(2000),
        "CityObjects": {
            "building1": {
                "type": "Building",
                "geometry": [
                    {
                        **_cube_solid(0),  # lod2
                        "semantics": {
                            "surfaces": [
                                {"type": "GroundSurface"},
                                {"type": "RoofSurface"},
                                {"type": "WallSurface"},
                            ],
                            "values": [[0, 1, 2, 2, 2, 2]],
                        },
                        "material": {"default": {"value": 1}},  # blue
                    },
                    _cube_geometry(0),  # lod 1
                ],
            },
            "building2": {
                "type": "Building",
                "geometry": [
                    {
                        **_cube_solid(8),
                        "semantics": {
                            "surfaces": [
                                {"type": "GroundSurface"},
                                {"type": "RoofSurface"},
                                {"type": "WallSurface"},
                            ],
                            "values": [[0, 1, 2, 2, 2, 2]],
                        },
                        "material": {"default": {"value": 0}},  # red
                    },
                    _cube_geometry(8),  # lod1
                ],
            },
        },
    }


def _delete_feature(layers, uid):
    for layer in layers:
        for f in layer.getFeatures():
            if f["uid"] == uid:
                layer.dataProvider().deleteFeatures([f.id()])
                return
    raise AssertionError(f"{uid} not found in any layer")


def _delete_lod_row(layers, uid, lod):
    for layer in layers:
        for f in layer.getFeatures():
            if f["uid"] == uid and f["lod"] == lod:
                layer.dataProvider().deleteFeatures([f.id()])
                return
    raise AssertionError(f"{uid} LoD {lod} not found in any layer")


def _set_attribute(layers, uid, field_name, value):
    """Simulate the user editing one cell in QGIS."""
    for layer in layers:
        for f in layer.getFeatures():
            if f["uid"] == uid:
                idx = layer.fields().indexOf(field_name)
                assert idx != -1, f"{field_name} is not a column"
                layer.dataProvider().changeAttributeValues({f.id(): {idx: value}})
                return
    raise AssertionError(f"{uid} not found in any layer")


def _delete_all_rows(layers, uid):
    """Simulate the user deleting every row of an object."""
    found = False
    for layer in layers:
        ids = [
            f.id() for f in layer.getFeatures() if f["uid"] == uid
        ]  # rows of this object
        if ids:
            layer.dataProvider().deleteFeatures(ids)
            found = True
    if not found:
        raise AssertionError(f"{uid} not found in any layer")


def _edit_geometry(layers, uid, edit):
    """Simulate a geometry edit in QGIS: apply edit(geom) to uid's first row."""
    for layer in layers:
        for f in layer.getFeatures():
            if f["uid"] == uid:
                geom = f.geometry()
                edit(geom)
                layer.dataProvider().changeGeometryValues({f.id(): geom})
                return
    raise AssertionError(f"{uid} not found in any layer")


def _lift_vertex(geom, dz):
    """Move vertex 1 up by dz metres (X9 edit 2)."""
    p = geom.vertexAt(1)
    p.setZ(p.z() + dz)
    geom.moveVertex(p, 1)


def test_fixture_writes_and_reads_back():
    temp_dir = (
        tempfile.mkdtemp()
    )  # a throwaway directory somewhere in the container's /tmp

    file_path = os.path.join(temp_dir, "input.city.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(_two_cubes_citymodel(), f)  # dict → real .json file on disk

    original = load_cityjson_model(file_path)  # file on disk -> dict

    loader = CityJSONLoader(
        filepath=file_path, citymodel=original
    )  # build the converter
    for key, obj in original["CityObjects"].items():
        loader.layer_manager.add_object(key, obj)  # each CityObject -> one QGIS row

    layers = loader.layer_manager.get_all_layers()  # collect the finished layer

    assert len(layers) == 1

    features = list(layers[0].getFeatures())  # read the rows back out
    assert len(features) == 2  # two buildings in, two rows out

    shutil.rmtree(temp_dir)  # delete the directory


def test_round_trip_after_deleting_one_building():
    temp_dir = (
        tempfile.mkdtemp()
    )  # a throwaway directory somewhere in the container's /tmp

    file_path = os.path.join(temp_dir, "input.city.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(_two_cubes_citymodel(), f)  # dict → real .json file on disk

    original = load_cityjson_model(file_path)  # file on disk -> dict

    loader = CityJSONLoader(
        filepath=file_path, citymodel=original
    )  # build the converter
    for key, obj in original["CityObjects"].items():
        loader.layer_manager.add_object(key, obj)  # each CityObject -> one QGIS row

    layers = loader.layer_manager.get_all_layers()  # collect the finished layer

    # module doesnt exist yet
    from core.exporting import CityJSONExporter, save_cityjson_model

    layer = layers[0]

    # find the row for building2
    fid = None
    for f in layer.getFeatures():
        if f["uid"] == "building2":
            fid = f.id()
            break

    assert fid is not None, "building2 not found in the layer"

    # delete that row -- this is the user's edit in QGIS
    layer.dataProvider().deleteFeatures([fid])

    # export what's left, write it out
    exported = CityJSONExporter(layers, citymodel=original).export()
    save_cityjson_model(
        exported, os.path.join(temp_dir, "output.city.json")
    )  # save the exported model in a temporary directory, that deletes after test

    # read it back and check
    output = load_cityjson_model(os.path.join(temp_dir, "output.city.json"))

    assert "building2" not in output["CityObjects"]  # building2 should be gone
    assert "building1" in output["CityObjects"]  # building1 should still be there

    assert len(output["vertices"]) == 8  # one cube's worth

    shutil.rmtree(temp_dir)  # delete the directory


def test_save_cityjson_model_round_trip():
    """dict → save_cityjson_model → file → load_cityjson_model → dict"""

    temp_dir = (
        tempfile.mkdtemp()
    )  # a throwaway directory somewhere in the container's /tmp
    file_path = os.path.join(temp_dir, "out.city.json")

    save_cityjson_model(_two_cubes_citymodel(), file_path)  # write out a CityJSON model
    loaded_back = load_cityjson_model(file_path)  # read the cityjson model back

    assert (
        loaded_back == _two_cubes_citymodel()
    )  # should be identical to what we wrote out
    shutil.rmtree(temp_dir)  # delete the directory


def test_get_surviving_ids_after_delete(qgis_app):
    cm = _two_cubes_citymodel()

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)  # build the converter
    loader.load()  # populate the layer manager
    layers = loader.layer_manager.get_all_layers()  # collect the finished layer

    # simulate deleting building2
    layer = layers[0]
    fid = None
    for f in layer.getFeatures():
        if f["uid"] == "building2":
            fid = f.id()
            break

    assert fid is not None, "building2 not found in the layer"

    # delete that row -- this is the user's edit in QGIS
    layer.dataProvider().deleteFeatures([fid])

    # get the surviving IDs
    surviving_ids = CityJSONExporter(layers, citymodel=cm).get_surviving_ids()

    assert "building2" not in surviving_ids  # building2 should be gone
    assert "building1" in surviving_ids  # building1 should still be there


def test_get_surviving_ids_after_delete_parent(qgis_app):
    cm = _hierarchy_citymodel()

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)  # build the converter
    loader.load()  # populate the layer manager
    layers = loader.layer_manager.get_all_layers()  # collect the finished layer

    # find building 1
    fid = None
    target_layer = None
    for layer in layers:  # iterating each layer to find the one that contains building1
        for f in layer.getFeatures():  # inner: each row in that layer (table)
            if f["uid"] == "building1":
                target_layer = layer
                fid = f.id()
                break
        if (
            fid is not None
        ):  # if we found the feature, we can break out of the outer loop as well
            break

    assert fid is not None, "building1 not found in the layer"
    assert target_layer is not None, "building1 not found in any layer"

    # delete building 1's feature from the layer -- this is the user's edit in QGIS
    target_layer.dataProvider().deleteFeatures([fid])

    surviving = CityJSONExporter(layers, citymodel=cm).get_surviving_ids()
    assert surviving == {"building1", "building2", "building3"}


def test_deleting_parent_resurrects_it(qgis_app):
    cm = _hierarchy_citymodel()

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    _delete_feature(layers, "building1")

    surviving = CityJSONExporter(layers, citymodel=cm).get_surviving_ids()
    assert surviving == {"building1", "building2", "building3"}

    exported = CityJSONExporter(layers, citymodel=cm).export()
    assert exported["CityObjects"]["building1"]["children"] == [
        "building2",
        "building3",
    ]


def test_prune_drops_deleted_children(qgis_app):
    cm = _hierarchy_citymodel()

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    _delete_feature(layers, "building2")

    exported = CityJSONExporter(layers, citymodel=cm).export()
    assert exported["CityObjects"]["building1"]["children"] == ["building3"]
    assert "building2" not in exported["CityObjects"]


# Test - changing an attribute in QGIS and exporting it back to CityJSON
def test_attribute_change_round_trip(qgis_app):
    cm = _two_cubes_citymodel()

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)  # build the converter
    loader.load()  # populate the layer manager
    layers = loader.layer_manager.get_all_layers()  # collect the finished layer

    # edit building1's function (the user does this in QGIS)
    _set_attribute(layers, "building1", "attribute.function", "mixed")

    # export and check
    out = CityJSONExporter(layers, citymodel=cm).export()
    assert out["CityObjects"]["building1"]["attributes"]["function"] == "mixed"
    assert (
        out["CityObjects"]["building2"]["attributes"]["function"] == "commercial"
    )  # unchanged


def test_untouched_int_keeps_its_type(qgis_app):
    cm = _two_cubes_citymodel()
    cm["CityObjects"]["building1"]["attributes"]["height"] = 12
    cm["CityObjects"]["building2"]["attributes"]["height"] = (
        12.5  # makes the column Double
    )

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    out = CityJSONExporter(layers, citymodel=cm).export()  # no edits

    height = out["CityObjects"]["building1"]["attributes"]["height"]
    assert height == 12
    assert isinstance(height, int)  # not 12.0


def test_missing_attribute_stays_missing(qgis_app):
    cm = _two_cubes_citymodel()
    cm["CityObjects"]["building1"]["attributes"]["height"] = 12  # only building1

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    out = CityJSONExporter(layers, citymodel=cm).export()  # no edits

    assert "height" not in out["CityObjects"]["building2"]["attributes"]


def test_edited_list_comes_back_as_list(qgis_app):
    cm = _two_cubes_citymodel()
    cm["CityObjects"]["building1"]["attributes"]["tags"] = ["a", "b"]

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    _set_attribute(layers, "building1", "attribute.tags", '["a", "c"]')

    out = CityJSONExporter(layers, citymodel=cm).export()
    assert out["CityObjects"]["building1"]["attributes"]["tags"] == ["a", "c"]


def test_broken_json_list_raises_clear_error(qgis_app):
    cm = _two_cubes_citymodel()
    cm["CityObjects"]["building1"]["attributes"]["tags"] = ["a", "b"]

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    _set_attribute(layers, "building1", "attribute.tags", '["a", "c"')  # missing ]

    with pytest.raises(ValueError):
        CityJSONExporter(layers, citymodel=cm).export()


def test_export_does_not_mutate_original(qgis_app):
    cm = _two_cubes_citymodel()
    before = copy.deepcopy(cm)  # snapshot of the original, to compare against later

    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    # delete building1, so building2's vertex indices 8-15 get remapped to 0-7 on export
    _delete_feature(layers, "building1")

    out1 = CityJSONExporter(layers, citymodel=cm).export()
    out2 = CityJSONExporter(layers, citymodel=cm).export()

    assert out1 == out2  # exporting twice gives the same result
    assert cm == before  # the original model was not touched


# x7b


def test_unloaded_object_survives_export(qgis_app):
    """An object never loaded (no LoD1) must survive export, unlike a deleted one."""
    # 1. cm = the fixture
    cm = _unloaded_lod_citymodel()

    # 2. loader with lod="1", then loader.load()
    loader = CityJSONLoader(filepath="dummy", citymodel=cm, lod="1")
    loader.load()

    # 3. layers = ..., then delete house_b
    layers = loader.layer_manager.get_all_layers()
    _delete_feature(layers, "house_b")

    # 4. out = export
    out = CityJSONExporter(layers, citymodel=cm, loaded_lod="1").export()

    # 5. asserts:
    assert "house_b" not in out["CityObjects"]
    assert len(out["CityObjects"]["house_a"]["geometry"]) == 2
    assert "tree" in out["CityObjects"]


def test_unloaded_lods_dropped_when_not_kept(qgis_app):
    """With keep_unloaded=False, never-loaded objects and unloaded LoDs are dropped."""
    # 1. cm = the fixture
    cm = _unloaded_lod_citymodel()

    # 2. loader with lod="1", then loader.load()
    loader = CityJSONLoader(filepath="dummy", citymodel=cm, lod="1")
    loader.load()

    # 3. layers = ..., then delete house_b
    layers = loader.layer_manager.get_all_layers()
    _delete_feature(layers, "house_b")

    # 4. out = export
    out = CityJSONExporter(
        layers, citymodel=cm, loaded_lod="1", keep_unloaded=False
    ).export()

    # 5. asserts:
    assert "house_b" not in out["CityObjects"]
    assert len(out["CityObjects"]["house_a"]["geometry"]) == 1  # only lod 1 left
    assert "tree" not in out["CityObjects"]  # dropped


# x7
def test_export_preserves_fidelity(qgis_app):
    """Solid, semantics, material, unloaded LoD and metadata survive export."""
    # 1. cm = the fixture
    cm = _fidelity_citymodel()

    # 2. loader with lod="2", then loader.load()
    loader = CityJSONLoader(filepath="dummy", citymodel=cm, lod="2")
    loader.load()

    # 3. layers, then delete building2
    layers = loader.layer_manager.get_all_layers()
    _delete_feature(layers, "building2")

    # 4. out = export with loaded_lod="2"
    out = CityJSONExporter(
        layers, citymodel=cm, loaded_lod="2", keep_unloaded=True
    ).export()

    # 5. asserts
    b1 = out["CityObjects"]["building1"]
    lod2 = b1["geometry"][0]  # the Solid (first in the list)

    # building2 gone
    assert "building2" not in out["CityObjects"]
    # building1 still has 2 geometries (LoD1 survived without being loaded)
    assert len(b1["geometry"]) == 2
    # lod2["type"] is "Solid"
    assert lod2["type"] == "Solid"
    # len(lod2["boundaries"]) == 1        → one shell
    assert len(lod2["boundaries"]) == 1
    # len(lod2["boundaries"][0]) == 6     → six faces
    assert len(lod2["boundaries"][0]) == 6
    # lod2["semantics"] == the original building1 semantics in cm
    assert (
        lod2["semantics"] == cm["CityObjects"]["building1"]["geometry"][0]["semantics"]
    )
    # out["appearance"]["materials"] == [the original materials[1]]   → only blue left
    assert out["appearance"]["materials"] == [cm["appearance"]["materials"][1]]
    # lod2["material"]["default"]["value"] == 0                       → renumbered 1 → 0
    assert lod2["material"]["default"]["value"] == 0
    # out["metadata"] == cm["metadata"]
    assert out["metadata"] == cm["metadata"]


# x6
def test_deleting_lod_row_drops_only_that_geometry(qgis_app):
    """Deleting one LoD row drops only that geometry entry; the object survives."""
    # 1. cm = the fixture (_unloaded_lod_citymodel)
    cm = _unloaded_lod_citymodel()

    # 2. loader with lod_as="ATTRIBUTES", then loader.load()
    loader = CityJSONLoader(filepath="dummy", citymodel=cm, lod_as="ATTRIBUTES")
    loader.load()

    # 3. layers, then delete house_a's LoD "1" row
    layers = loader.layer_manager.get_all_layers()
    _delete_lod_row(layers, "house_a", "1")

    # 4. out = export (default loaded_lod)
    out = CityJSONExporter(layers, citymodel=cm).export()

    # 5. asserts:
    #    - house_a is in out
    assert "house_a" in out["CityObjects"]
    #    - house_a has 1 geometry
    assert len(out["CityObjects"]["house_a"]["geometry"]) == 1
    #    - that geometry's "lod" is "2"
    assert out["CityObjects"]["house_a"]["geometry"][0]["lod"] == "2"
    #    - house_b still has 2 geometries
    assert len(out["CityObjects"]["house_b"]["geometry"]) == 2


def test_deleting_one_surface_row_rasies(qgis_app):
    """Deleting one surface row of an object raises."""
    cm = _fidelity_citymodel()
    loader = CityJSONLoader(
        filepath="dummy", citymodel=cm, lod="2", load_semantic_surfaces=True
    )
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    _delete_feature(
        layers, "building1"
    )  # deletes the first row it finds which is exactly the first face

    with pytest.raises(ValueError, match="building1"):
        CityJSONExporter(
            layers, citymodel=cm, loaded_lod="2", semantic_surfaces=True
        ).export()


def test_deleting_all_surface_rows_drops_object(qgis_app):
    """Deleting all surface rows of an object drops it."""
    cm = _fidelity_citymodel()
    loader = CityJSONLoader(
        filepath="dummy", citymodel=cm, lod="2", load_semantic_surfaces=True
    )
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    _delete_all_rows(layers, "building2")

    out = CityJSONExporter(
        layers, citymodel=cm, loaded_lod="2", semantic_surfaces=True
    ).export()

    assert "building2" not in out["CityObjects"]
    assert "building1" in out["CityObjects"]


# x10
def _load_two_cubes():
    cm = _two_cubes_citymodel()
    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    return cm, loader.layer_manager.get_all_layers()


def test_untouched_geometry_exports(qgis_app):
    cm, layers = _load_two_cubes()
    out = CityJSONExporter(layers, citymodel=cm).export()
    assert set(out["CityObjects"]) == {"building1", "building2"}


def test_moved_building_raises(qgis_app):  # X9 edit 1
    cm, layers = _load_two_cubes()
    _edit_geometry(layers, "building1", lambda g: g.translate(1, 0, 0))
    with pytest.raises(ValueError, match="building1"):
        CityJSONExporter(layers, citymodel=cm).export()


def test_lifted_vertex_raises(qgis_app):  # X9 edit 2
    cm, layers = _load_two_cubes()
    _edit_geometry(layers, "building1", lambda g: _lift_vertex(g, 0.01))
    with pytest.raises(ValueError, match="building1"):
        CityJSONExporter(layers, citymodel=cm).export()


def test_deleted_vertex_raises(qgis_app):  # X9 edit 3
    cm, layers = _load_two_cubes()
    _edit_geometry(layers, "building1", lambda g: g.deleteVertex(1))
    with pytest.raises(ValueError, match="building1"):
        CityJSONExporter(layers, citymodel=cm).export()


def test_move_below_half_grid_step_exports(qgis_app):
    """0.1 mm < scale/2 (0.5 mm): rounds back to the same integer, so not an edit."""
    cm, layers = _load_two_cubes()
    _edit_geometry(layers, "building1", lambda g: _lift_vertex(g, 0.0001))
    out = CityJSONExporter(layers, citymodel=cm).export()
    assert "building1" in out["CityObjects"]


def test_lifted_vertex_raises_with_lod_rows(qgis_app):
    cm = _unloaded_lod_citymodel()
    loader = CityJSONLoader(filepath="dummy", citymodel=cm, lod_as="ATTRIBUTES")
    loader.load()
    layers = loader.layer_manager.get_all_layers()
    _edit_geometry(layers, "house_a", lambda g: _lift_vertex(g, 0.01))
    with pytest.raises(ValueError, match="house_a"):
        CityJSONExporter(layers, citymodel=cm).export()


def test_lifted_vertex_raises_with_surface_rows(qgis_app):
    cm = _fidelity_citymodel()
    loader = CityJSONLoader(
        filepath="dummy", citymodel=cm, lod="2", load_semantic_surfaces=True
    )
    loader.load()
    layers = loader.layer_manager.get_all_layers()
    _edit_geometry(layers, "building1", lambda g: _lift_vertex(g, 0.01))
    with pytest.raises(ValueError, match="building1"):
        CityJSONExporter(
            layers, citymodel=cm, loaded_lod="2", semantic_surfaces=True
        ).export()


def _unloaded_parent_layers():
    """Hierarchy where the parent only has LoD0, so loading LoD1 shows just the children."""
    cm = _hierarchy_citymodel()
    cm["CityObjects"]["building1"]["geometry"][0]["lod"] = "0"
    loader = CityJSONLoader(filepath="dummy", citymodel=cm, lod="1")
    loader.load()
    return cm, loader.layer_manager.get_all_layers()


def test_unloaded_parent_dropped_when_all_children_deleted(qgis_app):
    cm, layers = _unloaded_parent_layers()
    _delete_feature(layers, "building2")
    _delete_feature(layers, "building3")
    out = CityJSONExporter(layers, citymodel=cm, loaded_lod="1").export()
    assert out["CityObjects"] == {}


def test_unloaded_parent_kept_when_a_child_survives(qgis_app):
    cm, layers = _unloaded_parent_layers()
    _delete_feature(layers, "building2")
    out = CityJSONExporter(layers, citymodel=cm, loaded_lod="1").export()
    assert set(out["CityObjects"]) == {"building1", "building3"}
    assert out["CityObjects"]["building1"]["children"] == ["building3"]


def test_layers_are_stamped_with_provenance(qgis_app):
    cm = _two_cubes_citymodel()
    loader = CityJSONLoader(
        filepath="dummy.city.json",
        citymodel=cm,
        lod="1",
        load_semantic_surfaces=True,
    )
    for key, obj in cm["CityObjects"].items():
        loader.layer_manager.add_object(key, obj)

    layers = loader.layer_manager.get_all_layers()
    assert layers
    for layer in layers:
        assert layer.customProperty("cityjson/source") == os.path.abspath(
            "dummy.city.json"
        )
        assert json.loads(layer.customProperty("cityjson/lod")) == "1"
        assert json.loads(layer.customProperty("cityjson/semantic_surfaces")) is True
        assert (
            json.loads(layer.customProperty("cityjson/keep_parent_attributes")) is False
        )
        assert len(layer.customProperty("cityjson/load_id")) == 32


def test_read_provenance_groups_layers(qgis_app):
    cm = _two_cubes_citymodel()
    loader = CityJSONLoader(filepath="dummy.city.json", citymodel=cm, lod="1")
    loader.load()
    layers = loader.layer_manager.get_all_layers()

    groups = read_provenance(layers)

    assert len(groups) == 1
    group = next(iter(groups.values()))
    assert group["source"] == os.path.abspath("dummy.city.json")
    assert group["lod"] == "1"
    assert group["layers"] == layers


def test_read_provenance_refuses_empty_layers(qgis_app):
    cm = _two_cubes_citymodel()
    loader = CityJSONLoader(filepath="dummy.city.json", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()
    _delete_all_rows(layers, "building1")
    _delete_all_rows(layers, "building2")

    with pytest.raises(ValueError, match="empty"):
        read_provenance(layers)


def test_bbox_keeps_only_objects_inside(qgis_app):
    cm, layers = _load_two_cubes()  # cube1 x 0–1 m, cube2 x 1–2 m
    out = CityJSONExporter(layers, citymodel=cm, bbox=[0, 0, 1, 1]).export()
    assert set(out["CityObjects"]) == {"building1"}
    assert len(out["vertices"]) == 8


def test_bbox_brings_parent_and_prunes_children(qgis_app):
    cm = _hierarchy_citymodel()  # b1 (0–1 m) has children b2 (1–2 m), b3 (2–3 m)
    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()
    out = CityJSONExporter(layers, citymodel=cm, bbox=[1, 0, 2, 1]).export()
    assert set(out["CityObjects"]) == {"building1", "building2"}
    assert out["CityObjects"]["building1"]["children"] == ["building2"]


def test_bbox_with_nothing_inside_exports_empty(qgis_app):
    cm, layers = _load_two_cubes()
    out = CityJSONExporter(layers, citymodel=cm, bbox=[10, 10, 11, 11]).export()
    assert out["CityObjects"] == {}
    assert out["vertices"] == []


def test_parents_resurrected_at_every_level(qgis_app):
    cm = _hierarchy_citymodel()
    objs = cm["CityObjects"]  # make it a chain: building1 → building2 → building3
    objs["building1"]["children"] = ["building2"]
    objs["building2"]["children"] = ["building3"]
    objs["building3"]["parents"] = ["building2"]
    loader = CityJSONLoader(filepath="dummy", citymodel=cm)
    loader.load()
    layers = loader.layer_manager.get_all_layers()
    _delete_feature(layers, "building1")
    _delete_feature(layers, "building2")
    out = CityJSONExporter(layers, citymodel=cm).export()
    assert set(out["CityObjects"]) == {"building1", "building2", "building3"}


def test_object_without_geometry_survives_with_appearance(qgis_app):
    cm = _fidelity_citymodel()  # has appearance
    cm["CityObjects"]["group1"] = {"type": "CityObjectGroup"}  # no geometry key
    loader = CityJSONLoader(filepath="dummy", citymodel=cm, lod="2")
    loader.load()
    layers = loader.layer_manager.get_all_layers()
    out = CityJSONExporter(layers, citymodel=cm, loaded_lod="2").export()
    assert "group1" in out["CityObjects"]
    assert "geometry" not in out["CityObjects"]["group1"]
