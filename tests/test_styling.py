"""A list of tests to check the styling classes functionality"""

import pytest

from core.styling import SemanticSurfacesStyling
from core.settings import semantic_colors
from qgis.core import QgsVectorLayer

class TestSemanticSurfacesStyling:
    """Tests the functionality of the SemanticSurfacesStyling class"""

    def test_creates_correct_number_of_rules(self):
        """Tests if the class creates the correct number of rules"""
        vectorlayer = QgsVectorLayer()

        styling = SemanticSurfacesStyling(semantic_colors)
        styling.apply(vectorlayer)

        renderer = vectorlayer.renderer3D()
        root_rule = renderer.rootRule()

        assert len(root_rule.children()) == len(semantic_colors) + 1
