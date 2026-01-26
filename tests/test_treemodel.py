from core.helpers import treemodel


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
    assert elem.subelements["max z"] == 6


def test_metadata_element_list_keywords():
    val = ["foo", "bar"]
    elem = treemodel.MetadataElement(("keywords", val))
    assert elem.key == "keywords"
    assert elem.value == ""
    assert elem.subelements == {"foo": "", "bar": ""}


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
