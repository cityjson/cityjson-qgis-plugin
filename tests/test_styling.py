# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

"""A list of tests to check the styling classes functionality"""

from unittest.mock import MagicMock, patch

import pytest
from qgis.core import QgsVectorLayer
from qgis.PyQt.QtGui import QColor

from core.settings import semantic_colors
from core.styling import (
    Copy2dStyling,
    NullStyling,
    SemanticSurfacesStyling,
    create_material,
    is_3d_styling_available,
    is_rule_based_3d_styling_available,
)


@pytest.fixture()
def vectorlayer() -> QgsVectorLayer:
    return QgsVectorLayer(
        "Polygon?crs=EPSG:4326&field=semantic_surface:string", "test_layer", "memory"
    )


class TestSemanticSurfacesStyling:
    """Tests the functionality of the SemanticSurfacesStyling class"""

    def test_creates_correct_number_of_rules(self, vectorlayer: QgsVectorLayer):
        """Tests if the class creates the correct number of rules"""

        # Ensure the layer is valid
        assert vectorlayer.isValid(), "Vector layer should be valid"

        styling = SemanticSurfacesStyling(semantic_colors)
        styling.apply(vectorlayer)

        renderer = vectorlayer.renderer3D()
        root_rule = renderer.rootRule()

        assert len(root_rule.children()) == len(semantic_colors) + 1


class TestNullStyling:
    """Tests the functionality of the NullStyling class"""

    def test_apply_does_nothing(self, vectorlayer: QgsVectorLayer):
        """Tests that apply method does nothing and returns None"""
        styling = NullStyling()
        result = styling.apply(vectorlayer)
        assert result is None


class TestCopy2dStyling:
    """Tests the functionality of the Copy2dStyling class"""

    @patch("core.styling.has_3d", True)
    @patch("qgis.core.Qgis.versionInt")
    @patch("core.styling.QgsPolygon3DSymbol")
    @patch("core.styling.QgsVectorLayer3DRenderer")
    def test_apply_with_old_qgis_version(
        self,
        mock_renderer_class,
        mock_symbol_class,
        mock_version,
        vectorlayer: QgsVectorLayer,
    ):
        """Tests apply method with QGIS version < 33000 (uses setMaterial)"""
        # Mock QGIS version < 33000
        mock_version.return_value = 32000

        # Mock the symbol and renderer
        mock_symbol = MagicMock()
        mock_symbol_class.return_value = mock_symbol
        mock_renderer = MagicMock()
        mock_renderer_class.return_value = mock_renderer

        # Mock the layer renderer chain
        mock_layer_renderer = MagicMock()
        mock_layer_symbol = MagicMock()
        mock_color = QColor(255, 0, 0)
        mock_layer_symbol.color.return_value = mock_color
        mock_layer_renderer.symbol.return_value = mock_layer_symbol

        # Mock the vectorlayer methods
        with (
            patch.object(vectorlayer, "renderer", return_value=mock_layer_renderer),
            patch.object(vectorlayer, "setRenderer3D") as mock_set_renderer,
        ):
            styling = Copy2dStyling()
            styling.apply(vectorlayer)

            # Verify setMaterial was called (old API)
            mock_symbol.setMaterial.assert_called_once()
            mock_symbol.setMaterialSettings.assert_not_called()
            # Verify setRenderer3D was called
            mock_set_renderer.assert_called_once()

    @patch("core.styling.has_3d", True)
    @patch("qgis.core.Qgis.versionInt")
    @patch("core.styling.QgsPolygon3DSymbol")
    @patch("core.styling.QgsVectorLayer3DRenderer")
    def test_apply_with_new_qgis_version(
        self,
        mock_renderer_class,
        mock_symbol_class,
        mock_version,
        vectorlayer: QgsVectorLayer,
    ):
        """Tests apply method with QGIS version >= 33000 (uses setMaterialSettings)"""
        # Mock QGIS version >= 33000
        mock_version.return_value = 33000

        # Mock the symbol and renderer
        mock_symbol = MagicMock()
        mock_symbol_class.return_value = mock_symbol
        mock_renderer = MagicMock()
        mock_renderer_class.return_value = mock_renderer

        # Mock the layer renderer chain
        mock_layer_renderer = MagicMock()
        mock_layer_symbol = MagicMock()
        mock_color = QColor(0, 255, 0)
        mock_layer_symbol.color.return_value = mock_color
        mock_layer_renderer.symbol.return_value = mock_layer_symbol

        # Mock the vectorlayer methods
        with (
            patch.object(vectorlayer, "renderer", return_value=mock_layer_renderer),
            patch.object(vectorlayer, "setRenderer3D") as mock_set_renderer,
        ):
            styling = Copy2dStyling()
            styling.apply(vectorlayer)

            # Verify setMaterialSettings was called (new API)
            mock_symbol.setMaterialSettings.assert_called_once()
            mock_symbol.setMaterial.assert_not_called()
            # Verify setRenderer3D was called
            mock_set_renderer.assert_called_once()

    @patch("core.styling.has_3d", False)
    def test_constructor_raises_exception_when_3d_unavailable(self):
        """Tests that constructor raises exception when 3D is not available"""
        with pytest.raises(Exception, match="3D styling is not available"):
            Copy2dStyling()


class TestSemanticSurfacesStylingExtended:
    """Extended tests for SemanticSurfacesStyling"""

    @patch("core.styling.has_rules", False)
    def test_constructor_raises_exception_when_rules_unavailable(self):
        """Tests that constructor raises exception when rule-based 3D is not available"""
        with pytest.raises(Exception, match="Rule-based 3D styling is not available"):
            SemanticSurfacesStyling()

    @patch("core.styling.has_rules", True)
    def test_constructor_with_custom_colors_and_else_color(
        self, vectorlayer: QgsVectorLayer
    ):
        """Tests constructor with custom colors and else_color parameters"""
        custom_colors = {
            "WallSurface": {
                "diffuse": QColor(255, 0, 0),
                "ambient": QColor(100, 0, 0),
                "specular": QColor(255, 255, 255),
            }
        }
        else_color = QColor(128, 128, 128)

        styling = SemanticSurfacesStyling(colors=custom_colors, else_color=else_color)
        assert styling._colors == custom_colors
        assert styling._else_color == else_color


class TestCreateMaterial:
    """Tests for the create_material function"""

    @patch("core.styling.QgsPhongMaterialSettings")
    def test_create_material_diffuse_only(self, mock_material_class):
        """Tests create_material with only diffuse color"""
        mock_material = MagicMock()
        mock_material_class.return_value = mock_material

        diffuse_color = QColor(255, 0, 0)
        result = create_material(diffuse_color)

        mock_material.setDiffuse.assert_called_once_with(diffuse_color)
        mock_material.setAmbient.assert_not_called()
        mock_material.setSpecular.assert_not_called()
        assert result == mock_material

    @patch("core.styling.QgsPhongMaterialSettings")
    def test_create_material_all_colors(self, mock_material_class):
        """Tests create_material with all color parameters"""
        mock_material = MagicMock()
        mock_material_class.return_value = mock_material

        diffuse_color = QColor(255, 0, 0)
        ambient_color = QColor(100, 0, 0)
        specular_color = QColor(255, 255, 255)

        result = create_material(diffuse_color, ambient_color, specular_color)

        mock_material.setDiffuse.assert_called_once_with(diffuse_color)
        mock_material.setAmbient.assert_called_once_with(ambient_color)
        mock_material.setSpecular.assert_called_once_with(specular_color)
        assert result == mock_material

    @patch("core.styling.QgsPhongMaterialSettings")
    def test_create_material_with_ambient_only(self, mock_material_class):
        """Tests create_material with diffuse and ambient colors"""
        mock_material = MagicMock()
        mock_material_class.return_value = mock_material

        diffuse_color = QColor(0, 255, 0)
        ambient_color = QColor(0, 100, 0)

        result = create_material(diffuse_color, ambient_color=ambient_color)

        mock_material.setDiffuse.assert_called_once_with(diffuse_color)
        mock_material.setAmbient.assert_called_once_with(ambient_color)
        mock_material.setSpecular.assert_not_called()
        assert result == mock_material


class TestUtilityFunctions:
    """Tests for utility functions"""

    @patch("core.styling.has_3d", True)
    def test_is_3d_styling_available_true(self):
        """Tests is_3d_styling_available when 3D is available"""
        result = is_3d_styling_available()
        assert result is True

    @patch("core.styling.has_3d", False)
    def test_is_3d_styling_available_false(self):
        """Tests is_3d_styling_available when 3D is not available"""
        result = is_3d_styling_available()
        assert result is False

    @patch("core.styling.has_rules", True)
    def test_is_rule_based_3d_styling_available_true(self):
        """Tests is_rule_based_3d_styling_available when rule-based 3D is available"""
        result = is_rule_based_3d_styling_available()
        assert result is True

    @patch("core.styling.has_rules", False)
    def test_is_rule_based_3d_styling_available_false(self):
        """Tests is_rule_based_3d_styling_available when rule-based 3D is not available"""
        result = is_rule_based_3d_styling_available()
        assert result is False
