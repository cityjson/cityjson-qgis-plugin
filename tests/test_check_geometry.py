import pytest

from scripts import check_geometry

# --- newell_normal ---


def test_flat_square_points_up():
    square = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    assert check_geometry.newell_normal(square) == pytest.approx((0, 0, 2))


def test_rd_square_points_up():
    ring = [
        (85000, 446000, 0),
        (85001, 446000, 0),
        (85001, 446001, 0),
        (85000, 446001, 0),
    ]
    assert check_geometry.newell_normal(ring) == pytest.approx((0, 0, 2))


def test_wall_points_sideways():
    ring = [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]
    assert check_geometry.newell_normal(ring) == pytest.approx((0, -2, 0))


def test_concave_l_shape():
    ring = [(0, 0, 0), (2, 0, 0), (2, 1, 0), (1, 1, 0), (1, 2, 0), (0, 2, 0)]
    assert check_geometry.newell_normal(ring) == pytest.approx((0, 0, 6))


# --- planarity_deviation ---


def test_flat_square_is_planar():
    face = [[(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]]
    assert check_geometry.planarity_deviation(face) == pytest.approx(0, abs=1e-9)


def test_lifted_corner_is_not_planar():
    face = [[(0, 0, 0), (1, 0, 0), (1, 1, 0.05), (0, 1, 0)]]
    assert check_geometry.planarity_deviation(face) == pytest.approx(0.0125, abs=1e-4)


def test_wall_is_planar():
    face = [[(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]]
    assert check_geometry.planarity_deviation(face) == pytest.approx(0, abs=1e-9)


def test_rd_square_is_planar():
    face = [
        [(85000, 446000, 0), (85001, 446000, 0), (85001, 446001, 0), (85000, 446001, 0)]
    ]
    assert check_geometry.planarity_deviation(face) == pytest.approx(0, abs=1e-9)


def test_hole_off_plane_is_not_planar():
    outer = [(0, 0, 0), (4, 0, 0), (4, 4, 0), (0, 4, 0)]
    hole = [(1, 1, 0.05), (1, 3, 0.05), (3, 3, 0.05), (3, 1, 0.05)]
    assert check_geometry.planarity_deviation([outer, hole]) == pytest.approx(
        0.05, abs=1e-4
    )


def test_collinear_face_returns_none():
    face = [[(0, 0, 0), (1, 0, 0), (2, 0, 0)]]
    assert check_geometry.planarity_deviation(face) is None


# --- is_degenerate ---


def test_square_is_not_degenerate():
    face = [[(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]]
    assert check_geometry.is_degenerate(face) is False


def test_repeated_corner_is_degenerate():
    face = [[(0, 0, 0), (1, 0, 0), (1, 0, 0)]]
    assert check_geometry.is_degenerate(face) is True


def test_collinear_is_degenerate():
    face = [[(0, 0, 0), (1, 0, 0), (2, 0, 0)]]
    assert check_geometry.is_degenerate(face) is True


def test_degenerate_hole_is_caught():
    outer = [(0, 0, 0), (4, 0, 0), (4, 4, 0), (0, 4, 0)]
    hole = [(1, 1, 0), (2, 2, 0), (3, 3, 0)]
    assert check_geometry.is_degenerate([outer, hole]) is True


# --- is_self_intersecting ---


def test_square_does_not_self_intersect():
    face = [[(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]]
    assert check_geometry.is_self_intersecting(face) is False


def test_concave_l_shape_does_not_self_intersect():
    face = [[(0, 0, 0), (2, 0, 0), (2, 1, 0), (1, 1, 0), (1, 2, 0), (0, 2, 0)]]
    assert check_geometry.is_self_intersecting(face) is False


def test_bowtie_self_intersects():
    face = [[(0, 0, 0), (2, 2, 0), (2, 0, 0), (0, 1, 0)]]
    assert check_geometry.is_self_intersecting(face) is True


def test_symmetric_bowtie_self_intersects():
    # both halves cancel out, so the normal is (0, 0, 0): uses the fallback
    face = [[(0, 0, 0), (1, 1, 0), (1, 0, 0), (0, 1, 0)]]
    assert check_geometry.is_self_intersecting(face) is True


def test_bowtie_wall_self_intersects():
    face = [[(0, 0, 0), (2, 0, 2), (2, 0, 0), (0, 0, 1)]]
    assert check_geometry.is_self_intersecting(face) is True


def test_hole_poking_out_self_intersects():
    outer = [(0, 0, 0), (4, 0, 0), (4, 4, 0), (0, 4, 0)]
    hole = [(1, 1, 0), (5, 1, 0), (5, 3, 0), (1, 3, 0)]
    assert check_geometry.is_self_intersecting([outer, hole]) is True


# --- check_face ---


def test_check_face_lifted_corner():
    face = [[(0, 0, 0), (1, 0, 0), (1, 1, 0.05), (0, 1, 0)]]
    result = check_geometry.check_face(face)
    assert result["non_planar"] is True
    assert result["degenerate"] is False
    assert result["self_intersecting"] is False


def test_check_face_tolerance_is_used():
    face = [[(0, 0, 0), (1, 0, 0), (1, 1, 0.05), (0, 1, 0)]]
    assert check_geometry.check_face(face, tol=0.02)["non_planar"] is False


# --- faces_from_cityjson ---


def _tiny_citymodel():
    """One MultiSurface with 1 face, one Solid with 2 faces, one line (skipped)."""
    return {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {"scale": [0.001, 0.001, 0.001], "translate": [85000, 446000, 0]},
        "vertices": [
            [0, 0, 0],
            [1000, 0, 0],
            [1000, 1000, 0],
            [0, 1000, 0],
            [0, 0, 1000],
        ],
        "CityObjects": {
            "flat": {
                "type": "Building",
                "geometry": [
                    {"type": "MultiSurface", "lod": "1", "boundaries": [[[0, 1, 2, 3]]]}
                ],
            },
            "box": {
                "type": "Building",
                "geometry": [
                    {
                        "type": "Solid",
                        "lod": "2",
                        "boundaries": [[[[0, 1, 2, 3]], [[0, 1, 4]]]],
                    }
                ],
            },
            "line": {
                "type": "Road",
                "geometry": [
                    {"type": "MultiLineString", "lod": "1", "boundaries": [[0, 1]]}
                ],
            },
        },
    }


def test_faces_from_cityjson_finds_every_face():
    tagged = check_geometry.faces_from_cityjson(_tiny_citymodel())
    assert [(t["id"], t["face"]) for t, _ in tagged] == [
        ("flat", 0),
        ("box", 0),
        ("box", 1),
    ]


def test_faces_from_cityjson_decodes_coordinates():
    tags, face = check_geometry.faces_from_cityjson(_tiny_citymodel())[0]
    assert face[0][1] == pytest.approx((85001, 446000, 0))
    assert tags["lod"] == "1"


def test_main_prints_summary(tmp_path, capsys):
    path = tmp_path / "tiny.city.json"
    path.write_text(__import__("json").dumps(_tiny_citymodel()), encoding="utf-8")
    check_geometry.main([str(path)])
    out = capsys.readouterr().out
    assert "Checked 3 faces" in out
    assert "non-planar > 1 cm: 0" in out


# --- fixes after the 3D BAG baseline ---


def test_repeated_corner_in_bigger_ring_is_degenerate():
    # 5 corners, 4 different: (1,0,0) twice in a row (val3dity 102)
    face = [[(0, 0, 0), (1, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]]
    assert check_geometry.is_degenerate(face) is True


def test_repeated_last_and_first_corner_is_degenerate():
    face = [[(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 0)]]
    assert check_geometry.is_degenerate(face) is True


def test_corner_touching_own_edge_self_intersects():
    # corner (1, 0) of the notch lands on the bottom edge (val3dity 104)
    face = [[(0, 0, 0), (2, 0, 0), (2, 2, 0), (1, 2, 0), (1, 0, 0), (0, 2, 0)]]
    assert check_geometry.is_self_intersecting(face) is True


def test_pinched_ring_self_intersects():
    # figure-8: corner (1, 1) is used twice, not next to itself
    face = [[(0, 0, 0), (1, 1, 0), (2, 0, 0), (2, 2, 0), (1, 1, 0), (0, 2, 0)]]
    assert check_geometry.is_self_intersecting(face) is True


def test_hole_touching_outer_ring_is_allowed():
    outer = [(0, 0, 0), (4, 0, 0), (4, 4, 0), (0, 4, 0)]
    hole = [(0, 2, 0), (2, 1, 0), (2, 3, 0)]  # corner (0, 2) sits on the outer edge
    assert check_geometry.is_self_intersecting([outer, hole]) is False
