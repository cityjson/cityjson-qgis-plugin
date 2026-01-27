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


import copy
from typing import Any, Dict, List, Optional, Set, Union
from . import subset

CITYJSON_VERSION = "1.0"
CITYJSON_TYPE = "CityJSON"
COORDINATE_DIMENSIONS = 3


def createCityJSON() -> Dict[str, Any]:
    """Returns an empty CityJSON file"""
    return {
        "type": CITYJSON_TYPE,
        "version": CITYJSON_VERSION,
        "CityObjects": {},
        "vertices": [],
    }


def get_centroid(cm: Dict[str, Any], coid: str) -> Optional[List[float]]:
    """Calculate the 3D centroid of a city object"""

    def collect_vertices(boundaries: Any, vertex_list: List[int]) -> None:
        for item in boundaries:
            if isinstance(item, list):
                collect_vertices(item, vertex_list)
            else:
                vertex_list.append(item)

    # Calculate centroid
    centroid = [0, 0, 0]
    total = 0
    for g in cm["CityObjects"][coid]["geometry"]:
        vs = []
        collect_vertices(g["boundaries"], vs)
        for vertex_idx in vs:
            v = cm["vertices"][vertex_idx]
            total += 1
            centroid[0] += v[0]
            centroid[1] += v[1]
            centroid[2] += v[2]

    if total == 0:
        return None

    # Calculate average coordinates
    centroid = [coord / total for coord in centroid]

    # Apply transformation if present
    if "transform" in cm:
        transform = cm["transform"]
        for i in range(COORDINATE_DIMENSIONS):
            centroid[i] = (centroid[i] * transform["scale"][i]) + transform[
                "translate"
            ][i]

    return centroid


def get_subset_cotype(
    cm: Dict[str, Any],
    cotype: Union[str, List[str]],
    invert: bool = False
) -> Dict[str, Any]:
    if isinstance(cotype, list):
        lsCOtypes = cotype
    else:
        lsCOtypes = [cotype]

    for t in lsCOtypes:
        if t == "Building":
            lsCOtypes.append("BuildingInstallation")
            lsCOtypes.append("BuildingPart")
        if t == "Bridge":
            lsCOtypes.append("BridgePart")
            lsCOtypes.append("BridgeInstallation")
            lsCOtypes.append("BridgeConstructionElement")
        if t == "Tunnel":
            lsCOtypes.append("TunnelInstallation")
            lsCOtypes.append("TunnelPart")
    # -- new sliced CityJSON object
    cm2 = createCityJSON()
    cm2["version"] = cm["version"]
    if "transform" in cm:
        cm2["transform"] = cm["transform"]
    # -- copy selected CO to the j2
    for theid in cm["CityObjects"]:
        if invert is False:
            if cm["CityObjects"][theid]["type"] in lsCOtypes:
                cm2["CityObjects"][theid] = cm["CityObjects"][theid]
        else:
            if cm["CityObjects"][theid]["type"] not in lsCOtypes:
                cm2["CityObjects"][theid] = cm["CityObjects"][theid]
    # -- geometry
    subset.process_geometry(cm, cm2)
    # -- templates
    subset.process_templates(cm, cm2)
    # -- appearance
    if "appearance" in cm:
        cm2["appearance"] = {}
        subset.process_appearance(cm, cm2)
    # -- metadata
    if "metadata" in cm:
        cm2["metadata"] = cm["metadata"]

    return cm2


def get_subset_bbox(
    cm: Dict[str, Any],
    bbox: List[float],
    invert: bool = False
) -> Dict[str, Any]:
    # print ('get_subset_bbox')
    # -- new sliced CityJSON object
    cm2 = createCityJSON()
    cm2["version"] = cm['version']
    if "transform" in cm:
        cm2["transform"] = cm["transform"]
    re = set()
    for coid in cm["CityObjects"]:
        centroid = get_centroid(cm, coid)
        if (
            (centroid is not None) and (centroid[0] >= bbox[0]) and (centroid[1] >= bbox[1]) and (centroid[0] < bbox[2])
            and (centroid[1] < bbox[3])
        ):
            re.add(coid)
    re2 = copy.deepcopy(re)
    if invert:
        allkeys = set(cm["CityObjects"].keys())
        re = allkeys ^ re
    # -- also add the parent-children
    for theid in re2:
        if "children" in cm["CityObjects"][theid]:
            for child in cm["CityObjects"][theid]["children"]:
                re.add(child)
        if "parent" in cm["CityObjects"][theid]:
            re.add(cm["CityObjects"][theid]["parent"])

    for each in re:
        cm2["CityObjects"][each] = cm["CityObjects"][each]
    # -- geometry
    subset.process_geometry(cm, cm2)
    # -- templates
    subset.process_templates(cm, cm2)
    # -- appearance
    if "appearance" in cm:
        cm2["appearance"] = {}
        subset.process_appearance(cm, cm2)
    # -- metadata
    if "metadata" in cm:
        cm2["metadata"] = cm["metadata"]

    return cm2
