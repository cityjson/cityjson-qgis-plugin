# ******************************************************************************
# Project: CityJsonLoader - A QGIS Plugin.
#
# Purpose: This plugin allows for CityJSON files to be loaded in QGIS.
#
# GitHub page: https://github.com/cityjson/cityjson-qgis-plugin
#
# Contact: G.Stavropoulou@tudelft.nl
# ******************************************************************************
#
# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ******************************************************************************
"""This module contains functions that originate from cjio"""

from __future__ import annotations

import copy
from typing import Any, Optional, Union

from . import subset

CITYJSON_VERSION = "2.0"
CITYJSON_TYPE = "CityJSON"
COORDINATE_DIMENSIONS = 3


def createCityJSON() -> dict[str, Any]:
    """Returns an empty CityJSON file"""
    return {
        "type": CITYJSON_TYPE,
        "version": CITYJSON_VERSION,
        "CityObjects": {},
        "vertices": [],
    }


def get_centroid(cm: dict[str, Any], coid: str) -> Optional[list[float]]:
    """Calculate the 3D centroid of a city object"""

    def collect_vertex_indices(boundaries: Any, vertex_indices: list[int]) -> None:
        for boundary in boundaries:
            if isinstance(boundary, list):
                collect_vertex_indices(boundary, vertex_indices)
            else:
                vertex_indices.append(boundary)

    # Check if city object exists
    if coid not in cm["CityObjects"]:
        return None

    city_object = cm["CityObjects"][coid]

    # Check if city object has geometry
    if "geometry" not in city_object:
        return None

    # Check if geometry is empty
    if not city_object["geometry"]:
        return None

    # Calculate centroid
    centroid: list[float] = [0, 0, 0]
    vertex_count = 0
    for geometry in city_object["geometry"]:
        vertex_indices: list[int] = []
        collect_vertex_indices(geometry["boundaries"], vertex_indices)
        for vertex_index in vertex_indices:
            vertex = cm["vertices"][vertex_index]
            vertex_count += 1
            centroid[0] += vertex[0]
            centroid[1] += vertex[1]
            centroid[2] += vertex[2]

    if vertex_count == 0:
        return None

    # Calculate average coordinates
    centroid = [coord / vertex_count for coord in centroid]

    # Apply transformation if present
    if "transform" in cm:
        transform = cm["transform"]
        for i in range(COORDINATE_DIMENSIONS):
            centroid[i] = (centroid[i] * transform["scale"][i]) + transform[
                "translate"
            ][i]

    return centroid


def get_subset_cotype(
    cm: dict[str, Any], cotype: Union[str, list[str]], invert: bool = False
) -> dict[str, Any]:
    if isinstance(cotype, list):
        cityobject_types = cotype
    else:
        cityobject_types = [cotype]

    # Expand types for related subtypes
    for cityobject_type in list(cityobject_types):
        if cityobject_type == "Building":
            cityobject_types.extend(["BuildingInstallation", "BuildingPart"])
        if cityobject_type == "Bridge":
            cityobject_types.extend(
                ["BridgePart", "BridgeInstallation", "BridgeConstructionElement"]
            )
        if cityobject_type == "Tunnel":
            cityobject_types.extend(["TunnelInstallation", "TunnelPart"])

    # -- new sliced CityJSON object
    subset_cm = createCityJSON()
    subset_cm["version"] = cm["version"]
    if "transform" in cm:
        subset_cm["transform"] = cm["transform"]
    # -- copy selected CityObjects
    for cityobject_id in cm["CityObjects"]:
        if not invert:
            if cm["CityObjects"][cityobject_id]["type"] in cityobject_types:
                subset_cm["CityObjects"][cityobject_id] = cm["CityObjects"][
                    cityobject_id
                ]
        else:
            if cm["CityObjects"][cityobject_id]["type"] not in cityobject_types:
                subset_cm["CityObjects"][cityobject_id] = cm["CityObjects"][
                    cityobject_id
                ]
    # -- geometry
    subset.process_geometry(cm, subset_cm)
    # -- templates
    subset.process_templates(cm, subset_cm)
    # -- appearance
    if "appearance" in cm:
        subset_cm["appearance"] = {}
        subset.process_appearance(cm, subset_cm)
    # -- metadata
    if "metadata" in cm:
        subset_cm["metadata"] = cm["metadata"]

    return subset_cm


def get_subset_bbox(
    cm: dict[str, Any], bbox: list[float], invert: bool = False
) -> dict[str, Any]:
    """Returns a subset of the CityJSON file within the given bbox."""
    # -- new sliced CityJSON object
    subset_cm = createCityJSON()
    subset_cm["version"] = cm["version"]
    if "transform" in cm:
        subset_cm["transform"] = cm["transform"]
    selected_ids = set()
    for cityobject_id in cm["CityObjects"]:
        centroid = get_centroid(cm, cityobject_id)
        if (
            (centroid is not None)
            and (centroid[0] >= bbox[0])
            and (centroid[1] >= bbox[1])
            and (centroid[0] < bbox[2])
            and (centroid[1] < bbox[3])
        ):
            selected_ids.add(cityobject_id)
    selected_ids_copy = copy.deepcopy(selected_ids)
    if invert:
        all_ids = set(cm["CityObjects"].keys())
        selected_ids = all_ids ^ selected_ids
    # -- also add the parent-children
    for cityobject_id in selected_ids_copy:
        if "children" in cm["CityObjects"][cityobject_id]:
            for child_id in cm["CityObjects"][cityobject_id]["children"]:
                selected_ids.add(child_id)
        if "parents" in cm["CityObjects"][cityobject_id]:
            for parent_id in cm["CityObjects"][cityobject_id]["parents"]:
                selected_ids.add(parent_id)

    for cityobject_id in selected_ids:
        subset_cm["CityObjects"][cityobject_id] = cm["CityObjects"][cityobject_id]
    # -- geometry
    subset.process_geometry(cm, subset_cm)
    # -- templates
    subset.process_templates(cm, subset_cm)
    # -- appearance
    if "appearance" in cm:
        subset_cm["appearance"] = {}
        subset.process_appearance(cm, subset_cm)
    # -- metadata
    if "metadata" in cm:
        subset_cm["metadata"] = cm["metadata"]

    return subset_cm
