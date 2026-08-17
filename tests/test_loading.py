# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

import json
import os
import shutil
import tempfile

import pytest
from qgis.core import QgsFeedback, QgsVectorLayer

from core.loading import CityJSONLoader, get_model_epsg, load_cityjson_model


class TestLoadCityJsonModel:
    """Test the load_cityjson_model function"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Create temporary test files and clean up after"""
        self.temp_dir = tempfile.mkdtemp()

        # Valid CityJSON content
        self.valid_cityjson = {
            "type": "CityJSON",
            "version": "2.0",
            "CityObjects": {"building1": {"type": "Building", "geometry": []}},
            "vertices": [[0, 0, 0], [1, 1, 1]],
            "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
        }

        # Create valid test file
        self.valid_file_path = os.path.join(self.temp_dir, "valid.json")
        with open(self.valid_file_path, "w", encoding="utf-8") as f:
            json.dump(self.valid_cityjson, f)

        # Create invalid JSON file
        self.invalid_file_path = os.path.join(self.temp_dir, "invalid.json")
        with open(self.invalid_file_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json content")

        yield  # This is where the test runs

        # Cleanup
        shutil.rmtree(self.temp_dir)

    def test_load_valid_cityjson_file(self):
        """Test loading a valid CityJSON file"""
        result = load_cityjson_model(self.valid_file_path)

        assert isinstance(result, dict)
        assert result["type"] == "CityJSON"
        assert result["version"] == "2.0"
        assert "CityObjects" in result
        assert "vertices" in result

    def test_load_nonexistent_file(self):
        """Test loading a non-existent file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            load_cityjson_model("/path/that/does/not/exist.json")

    def test_load_invalid_json_file(self):
        """Test loading an invalid JSON file raises JSONDecodeError"""
        with pytest.raises(json.JSONDecodeError):
            load_cityjson_model(self.invalid_file_path)

    def test_load_utf8_with_bom(self):
        """Test loading file with UTF-8 BOM encoding"""
        # Create file with BOM
        bom_file_path = os.path.join(self.temp_dir, "bom.json")
        with open(bom_file_path, "w", encoding="utf-8-sig") as f:
            json.dump(self.valid_cityjson, f)

        result = load_cityjson_model(bom_file_path)
        assert result["type"] == "CityJSON"


class TestGetModelEpsg:
    """Test the get_model_epsg function"""

    def test_no_metadata(self):
        """Test citymodel without metadata returns None"""
        citymodel = {"type": "CityJSON"}
        result = get_model_epsg(citymodel)
        assert result is None

    def test_metadata_without_crs_or_reference_system(self):
        """Test metadata without CRS or referenceSystem returns None"""
        citymodel = {"metadata": {"title": "Test model"}}
        result = get_model_epsg(citymodel)
        assert result is None

    def test_crs_with_epsg_number(self):
        """Test CRS with numeric EPSG code"""
        citymodel = {"metadata": {"crs": {"epsg": 4326}}}
        result = get_model_epsg(citymodel)
        assert result == "4326"

    def test_crs_with_epsg_string(self):
        """Test CRS with string EPSG code"""
        citymodel = {"metadata": {"crs": {"epsg": "28992"}}}
        result = get_model_epsg(citymodel)
        assert result == "28992"

    def test_crs_without_epsg_key(self):
        """Test CRS without EPSG key falls back to referenceSystem"""
        citymodel = {
            "metadata": {"crs": {"authority": "EPSG"}, "referenceSystem": "EPSG::4326"}
        }
        result = get_model_epsg(citymodel)
        assert result == "4326"

    def test_reference_system_with_double_colon(self):
        """Test referenceSystem with :: separator"""
        citymodel = {"metadata": {"referenceSystem": "EPSG::28992"}}
        result = get_model_epsg(citymodel)
        assert result == "28992"

    def test_reference_system_with_url_pattern(self):
        """Test referenceSystem with URL pattern"""
        citymodel = {
            "metadata": {
                "referenceSystem": "https://www.opengis.net/def/crs/EPSG/0/4326"
            }
        }
        result = get_model_epsg(citymodel)
        assert result == "4326"

    def test_reference_system_with_http_url_pattern(self):
        """Test referenceSystem with http:// URL pattern"""
        citymodel = {
            "metadata": {
                "referenceSystem": "http://www.opengis.net/def/crs/EPSG/0/4326"
            }
        }
        result = get_model_epsg(citymodel)
        assert result == "4326"

    def test_reference_system_with_complex_url(self):
        """Test referenceSystem with more complex URL"""
        citymodel = {
            "metadata": {
                "referenceSystem": "https://www.opengis.net/def/crs/EPSG/9.9.1/28992"
            }
        }
        result = get_model_epsg(citymodel)
        assert result == "28992"

    def test_reference_system_invalid_url_pattern(self):
        """Test referenceSystem with invalid URL pattern returns None"""
        citymodel = {"metadata": {"referenceSystem": "https://example.com/crs/4326"}}
        result = get_model_epsg(citymodel)
        assert result is None

    def test_reference_system_without_double_colon_or_url(self):
        """Test referenceSystem with neither :: nor valid URL returns None"""
        citymodel = {"metadata": {"referenceSystem": "WGS84"}}
        result = get_model_epsg(citymodel)
        assert result is None

    def test_crs_with_invalid_epsg_type(self):
        """Test CRS with invalid EPSG type falls back to referenceSystem"""
        citymodel = {
            "metadata": {"crs": {"epsg": None}, "referenceSystem": "EPSG::4326"}
        }
        result = get_model_epsg(citymodel)
        assert result == "4326"

    def test_crs_with_nested_structure_missing_epsg(self):
        """Test CRS with nested structure but missing EPSG key"""
        citymodel = {
            "metadata": {
                "crs": {"properties": {"name": "EPSG:4326"}},
                "referenceSystem": "EPSG::28992",
            }
        }
        result = get_model_epsg(citymodel)
        assert result == "28992"

    def test_both_crs_and_reference_system_prefer_crs(self):
        """Test that CRS is preferred over referenceSystem when both exist"""
        citymodel = {
            "metadata": {"crs": {"epsg": 4326}, "referenceSystem": "EPSG::28992"}
        }
        result = get_model_epsg(citymodel)
        assert result == "4326"

    def test_reference_system_with_type_error(self):
        """Test handling of TypeError when processing referenceSystem"""
        citymodel = {"metadata": {"referenceSystem": None}}
        result = get_model_epsg(citymodel)
        assert result is None

    @pytest.mark.parametrize(
        "epsg_value,expected",
        [
            (4326, "4326"),
            ("28992", "28992"),
            (0, "0"),
            ("0", "0"),
        ],
    )
    def test_various_epsg_formats(self, epsg_value, expected):
        """Test various EPSG value formats"""
        citymodel = {"metadata": {"crs": {"epsg": epsg_value}}}
        result = get_model_epsg(citymodel)
        assert result == expected

    @pytest.mark.parametrize(
        "ref_system,expected",
        [
            ("EPSG::4326", "4326"),
            ("EPSG::28992", "28992"),
            ("https://www.opengis.net/def/crs/EPSG/0/4326", "4326"),
            ("https://www.opengis.net/def/crs/EPSG/9.9.1/28992", "28992"),
            ("WGS84", None),
            ("invalid", None),
        ],
    )
    def test_various_reference_system_formats(self, ref_system, expected):
        """Test various referenceSystem formats"""
        citymodel = {"metadata": {"referenceSystem": ref_system}}
        result = get_model_epsg(citymodel)
        assert result == expected


class TestCityJSONLoader:
    """Test the CityJSONLoader class"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test data"""
        self.test_filepath = "/test/path/test_file.json"
        self.basic_citymodel = {
            "type": "CityJSON",
            "version": "1.0",
            "vertices": [[0, 0, 0], [1, 1, 1], [2, 2, 2]],
            "CityObjects": {
                "building1": {
                    "type": "Building",
                    "geometry": [
                        {"type": "Solid", "lod": "2.2", "boundaries": [[[0, 1, 2]]]}
                    ],
                }
            },
        }

    def test_loader_initialization_basic(self):
        """Test basic CityJSONLoader initialization"""
        loader = CityJSONLoader(
            filepath=self.test_filepath, citymodel=self.basic_citymodel
        )

        assert loader.filepath == self.test_filepath
        assert loader.filename == "test_file"
        assert loader.citymodel == self.basic_citymodel
        assert loader.lod == "All"
        assert loader.srid is None

    def test_loader_initialization_with_epsg(self):
        """Test CityJSONLoader initialization with EPSG"""
        loader = CityJSONLoader(
            filepath=self.test_filepath, citymodel=self.basic_citymodel, epsg="4326"
        )

        assert loader.srid == "4326"

    def test_loader_initialization_with_transform(self):
        """Test CityJSONLoader with transform in citymodel"""
        citymodel_with_transform = self.basic_citymodel.copy()
        citymodel_with_transform["transform"] = {
            "scale": [1.0, 1.0, 1.0],
            "translate": [0.0, 0.0, 0.0],
        }

        loader = CityJSONLoader(
            filepath=self.test_filepath, citymodel=citymodel_with_transform
        )

        # Verify that vertices_cache was initialized with transform
        assert loader.vertices_cache is not None

    def test_loader_initialization_with_geometry_templates(self):
        """Test CityJSONLoader with geometry templates"""
        citymodel_with_templates = self.basic_citymodel.copy()
        citymodel_with_templates["geometry-templates"] = {
            "template1": {"type": "MultiSurface", "boundaries": [[[0, 1, 2]]]},
            "vertices-templates": [[0, 0, 0], [1, 1, 1], [2, 2, 2]],
        }

        loader = CityJSONLoader(
            filepath=self.test_filepath, citymodel=citymodel_with_templates
        )

        assert loader.geometry_reader is not None
        assert loader.geometry_reader._geometry_templates is not None
        assert loader.geometry_reader._templates_vertices_cache is not None

    def test_loader_with_all_options(self):
        """Test CityJSONLoader with all configuration options"""
        loader = CityJSONLoader(
            filepath=self.test_filepath,
            citymodel=self.basic_citymodel,
            epsg="28992",
            keep_parent_attributes=True,
            divide_by_object=True,
            lod_as="ATTRIBUTES",
            lod="2.2",
            load_semantic_surfaces=True,
            style_semantic_surfaces=True,
        )

        assert loader.srid == "28992"
        assert loader.lod == "2.2"

    def test_init_vertices_basic(self):
        """Test vertices initialization without transform"""
        loader = CityJSONLoader(
            filepath=self.test_filepath, citymodel=self.basic_citymodel
        )

        # Test that vertices were added to cache
        assert len(loader.vertices_cache._vertices) == 3

    def test_init_vertices_with_transform(self):
        """Test vertices initialization with transform"""
        citymodel_with_transform = self.basic_citymodel.copy()
        citymodel_with_transform["transform"] = {
            "scale": [2.0, 2.0, 2.0],
            "translate": [10.0, 10.0, 10.0],
        }

        loader = CityJSONLoader(
            filepath=self.test_filepath, citymodel=citymodel_with_transform
        )

        # Verify transform was applied
        assert loader.vertices_cache is not None

    def test_load_method_basic(self):
        """Test the load method"""

        loader = CityJSONLoader(
            filepath=self.test_filepath, citymodel=self.basic_citymodel
        )

        # Create a real vector layer
        layer = QgsVectorLayer("Point?crs=EPSG:4326", "test", "memory")
        assert layer.isValid()

        loader.layer_manager.get_all_layers = lambda: [layer]

        result = loader.load()

        # Verify the load method completed and returned skipped geometries count
        assert isinstance(result, int)
        assert result == 0

    def test_load_with_feedback(self):
        """Test the load method with feedback"""

        feedback = QgsFeedback()

        loader = CityJSONLoader(
            filepath=self.test_filepath, citymodel=self.basic_citymodel
        )
        # Create a real vector layer
        layer = QgsVectorLayer("Point?crs=EPSG:4326", "test", "memory")
        assert layer.isValid()
        loader.layer_manager.get_all_layers = lambda: [layer]

        assert feedback.progress() == 0.0
        _ = loader.load(feedback=feedback)
        assert feedback.progress() == 100.0

    @pytest.mark.parametrize(
        "lod,expected",
        [
            ("All", "All"),
            ("1.0", "1.0"),
            ("2.2", "2.2"),
            (None, None),
        ],
    )
    def test_lod_configuration(self, lod, expected):
        """Test various LOD configurations"""
        loader = CityJSONLoader(
            filepath=self.test_filepath, citymodel=self.basic_citymodel, lod=lod
        )
        assert loader.lod == expected
