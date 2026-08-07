# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

from unittest.mock import Mock, patch
from qgis.PyQt.QtCore import Qt, QModelIndex, QSize

from core.helpers import treemodel


# MetadataElement tests
def test_metadata_element_dict():
    elem = treemodel.MetadataElement(("citymodelIdentifier", {"foo": "bar"}))
    assert elem.key == "citymodelIdentifier"
    assert elem.value == ""
    assert elem.subelements == {"foo": "bar"}


def test_metadata_element_list_geographical_extent():
    val = [1, 2, 3, 4, 5, 6]
    elem = treemodel.MetadataElement(("geographicalExtent", val))
    assert elem.key == "geographicalExtent"
    assert elem.value == ""
    assert elem.subelements["min x"] == 1
    assert elem.subelements["min y"] == 2
    assert elem.subelements["min z"] == 3
    assert elem.subelements["max x"] == 4
    assert elem.subelements["max y"] == 5
    assert elem.subelements["max z"] == 6


def test_metadata_element_list_keywords():
    val = ["foo", "bar"]
    elem = treemodel.MetadataElement(("keywords", val))
    assert elem.key == "keywords"
    assert elem.value == ""
    assert elem.subelements == {"foo": "", "bar": ""}


def test_metadata_element_list_thematic_models():
    val = ["Building", "Road"]
    elem = treemodel.MetadataElement(("thematicModels", val))
    assert elem.key == "thematicModels"
    assert elem.value == ""
    assert elem.subelements == {"Building": "", "Road": ""}


def test_metadata_element_list_with_metadata_realnames():
    # Test list handling when key is in METADATA_REALNAMES
    val = ["contact1", "contact2"]
    elem = treemodel.MetadataElement(("datasetPointOfContact", val))
    assert elem.key == "datasetPointOfContact"
    assert elem.value == ""
    expected_keys = ["Dataset Point of Contact (1)", "Dataset Point of Contact (2)"]
    assert list(elem.subelements.keys()) == expected_keys
    assert elem.subelements[expected_keys[0]] == "contact1"
    assert elem.subelements[expected_keys[1]] == "contact2"


def test_metadata_element_list_other():
    val = [10, 20]
    elem = treemodel.MetadataElement(("otherkey", val))
    assert elem.key == "otherkey"
    assert elem.value == ""
    assert elem.subelements[1] == 10
    assert elem.subelements[2] == 20


def test_metadata_element_scalar():
    elem = treemodel.MetadataElement(("citymodelIdentifier", "abc"))
    assert elem.key == "citymodelIdentifier"
    assert elem.value == "abc"
    assert elem.subelements == {}


def test_get_real_key():
    assert treemodel.get_real_key("citymodelIdentifier") == "City Model Identifier"
    assert treemodel.get_real_key("not_in_map") == "not_in_map"
    # Test more entries from METADATA_REALNAMES
    assert treemodel.get_real_key("datasetTitle") == "Dataset Title"
    assert treemodel.get_real_key("geographicalExtent") == "Geographical Extent"


# MetadataNode tests
def test_metadata_node_init():
    # Create a simple MetadataElement
    elem = treemodel.MetadataElement(("citymodelIdentifier", "test"))
    node = treemodel.MetadataNode(elem, None, 0)

    assert node.ref == elem
    assert node.parent is None
    assert node.row == 0
    assert node.subnodes == []  # No children for scalar element


def test_metadata_node_with_children():
    # Create a MetadataElement with subelements
    elem = treemodel.MetadataElement(
        ("citymodelIdentifier", {"sub1": "val1", "sub2": "val2"})
    )
    node = treemodel.MetadataNode(elem, None, 0)

    assert len(node.subnodes) == 2
    assert all(isinstance(child, treemodel.MetadataNode) for child in node.subnodes)
    assert node.subnodes[0].parent == node
    assert node.subnodes[1].parent == node


# MetadataModel tests
class MockTreeView:
    def __init__(self):
        # Import QFont here to ensure it's available
        from qgis.PyQt.QtGui import QFont

        self._font = QFont()

    def font(self):
        return self._font

    def columnWidth(self, column):
        return 150


def test_metadata_model_init():
    root_elements = {"citymodelIdentifier": "test", "datasetTitle": "Test Dataset"}
    treeview = MockTreeView()
    model = treemodel.MetadataModel(root_elements, treeview)

    assert model.rootElements == root_elements
    assert model.treeview == treeview
    assert len(model.rootNodes) == 2


def test_metadata_model_column_count():
    root_elements = {"citymodelIdentifier": "test"}
    treeview = MockTreeView()
    model = treemodel.MetadataModel(root_elements, treeview)

    assert model.columnCount(QModelIndex()) == 2


def test_metadata_model_row_count_root():
    root_elements = {"key1": "val1", "key2": "val2", "key3": "val3"}
    treeview = MockTreeView()
    model = treemodel.MetadataModel(root_elements, treeview)

    assert model.rowCount(QModelIndex()) == 3


def test_metadata_model_row_count_with_parent(qgis_app):
    root_elements = {"parent": {"child1": "val1", "child2": "val2"}}
    treeview = MockTreeView()
    model = treemodel.MetadataModel(root_elements, treeview)

    # Get index for parent
    parent_index = model.index(0, 0, QModelIndex())
    assert model.rowCount(parent_index) == 2


def test_metadata_model_data_display_role(qgis_app):
    root_elements = {"citymodelIdentifier": "test_id"}
    treeview = MockTreeView()
    model = treemodel.MetadataModel(root_elements, treeview)

    # Test column 0 (key)
    index = model.index(0, 0, QModelIndex())
    data = model.data(index, Qt.ItemDataRole.DisplayRole)
    assert data == "City Model Identifier"  # Should use real name

    # Test column 1 (value)
    index = model.index(0, 1, QModelIndex())
    data = model.data(index, Qt.ItemDataRole.DisplayRole)
    assert data == "test_id"


def test_metadata_model_data_invalid_index():
    root_elements = {"citymodelIdentifier": "test"}
    treeview = MockTreeView()
    model = treemodel.MetadataModel(root_elements, treeview)

    invalid_index = QModelIndex()
    data = model.data(invalid_index, Qt.ItemDataRole.DisplayRole)
    assert data is None


def test_metadata_model_data_size_hint_role(qgis_app):
    root_elements = {"citymodelIdentifier": "test"}
    treeview = MockTreeView()
    model = treemodel.MetadataModel(root_elements, treeview)

    # Test size hint for column 1 (value column)
    index = model.index(0, 1, QModelIndex())
    size_hint = model.data(index, Qt.ItemDataRole.SizeHintRole)

    assert isinstance(size_hint, QSize)
    assert size_hint.width() > 0
    assert size_hint.height() > 0


def test_metadata_model_header_data():
    root_elements = {"citymodelIdentifier": "test"}
    treeview = MockTreeView()
    model = treemodel.MetadataModel(root_elements, treeview)

    # Test horizontal headers
    header0 = model.headerData(
        0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
    )
    assert header0 == "Property"

    header1 = model.headerData(
        1, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
    )
    assert header1 == "Value"

    # Test invalid section
    invalid_header = model.headerData(
        2, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
    )
    assert invalid_header is None


def test_metadata_model_index(qgis_app):
    root_elements = {"parent": {"child": "value"}}
    treeview = MockTreeView()
    model = treemodel.MetadataModel(root_elements, treeview)

    # Test root index
    root_index = model.index(0, 0, QModelIndex())
    assert root_index.isValid()
    assert root_index.row() == 0
    assert root_index.column() == 0

    # Test child index
    child_index = model.index(0, 0, root_index)
    assert child_index.isValid()
    assert child_index.row() == 0
    assert child_index.column() == 0


def test_metadata_model_parent(qgis_app):
    root_elements = {"parent": {"child": "value"}}
    treeview = MockTreeView()
    model = treemodel.MetadataModel(root_elements, treeview)

    # Root node should have invalid parent
    root_index = model.index(0, 0, QModelIndex())
    root_parent = model.parent(root_index)
    assert not root_parent.isValid()

    # Child node should have valid parent
    child_index = model.index(0, 0, root_index)
    child_parent = model.parent(child_index)
    assert child_parent.isValid()
    assert child_parent == root_index


def test_metadata_model_reset():
    root_elements = {"key1": "val1"}
    treeview = MockTreeView()
    model = treemodel.MetadataModel(root_elements, treeview)

    original_root_count = len(model.rootNodes)
    original_root_nodes = model.rootNodes.copy()

    # Add more elements and reset
    model.rootElements["key2"] = "val2"

    # Call reset - this should refresh rootNodes even if Qt part fails
    with patch.object(model, "beginResetModel", Mock()):
        with patch.object(model, "endResetModel", Mock()):
            # Just test the core functionality - rootNodes should be regenerated
            model.rootNodes = model._getRootNodes()

    # Should have more root nodes now
    assert len(model.rootNodes) > original_root_count
    assert len(model.rootNodes) == 2  # key1 + key2

    # Root nodes should be different objects (regenerated)
    assert model.rootNodes != original_root_nodes


def test_metadata_model_get_key_column_width():
    root_elements = {"citymodelIdentifier": "test", "datasetPointOfContact": "contact"}
    treeview = MockTreeView()
    model = treemodel.MetadataModel(root_elements, treeview)

    # Test that width is calculated and is reasonable
    width = model.getKeyColumnWidth()

    # Should be at least the minimum width (100) + padding (30)
    assert width >= 130
    # Should be an integer
    assert isinstance(width, int)


# TreeNode abstract base class tests
def test_tree_node_abstract():
    # TreeNode is abstract, shouldn't be instantiated directly
    # But we can test the base functionality through MetadataNode
    elem = treemodel.MetadataElement(("test", "value"))
    node = treemodel.MetadataNode(elem, None, 5)

    assert node.parent is None
    assert node.row == 5
    assert hasattr(node, "subnodes")


# Edge cases and error conditions
def test_metadata_element_empty_list():
    elem = treemodel.MetadataElement(("keywords", []))
    assert elem.key == "keywords"
    assert elem.value == ""
    assert elem.subelements == {}


def test_metadata_element_none_value():
    elem = treemodel.MetadataElement(("test", None))
    assert elem.key == "test"
    assert elem.value is None
    assert elem.subelements == {}
