"""A list of tests to check the styling classes functionality"""

import pytest

from core.styling import SemanticSurfacesStyling
from core.settings import semantic_colors
from qgis.core import QgsVectorLayer

@pytest.fixture()
def vectorlayer() -> QgsVectorLayer:
    return QgsVectorLayer("Polygon?crs=EPSG:4326&field=semantic_surface:string", 
            "test_layer", 
            "memory")

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
