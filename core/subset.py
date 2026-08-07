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
"""A module that provides functions to create subsets of CityJSON files"""

from . import get_logger

logger = get_logger("subset")


def select_co_ids(j, IDs):
    IDs = list(IDs)
    re = set()
    for theid in j["CityObjects"]:
        if theid in IDs:
            re.add(theid)
    not_found = [theid for theid in IDs if theid not in j["CityObjects"]]
    for theid in not_found:
        IDs.remove(theid)
        logger.warning(f"ID {theid} not found in input file; ignored.")
    # -- also add the children (covers CityObjectGroup which uses "children" per spec 2.0)
    for id in j["CityObjects"]:
        if id in IDs:
            if "children" in j["CityObjects"][id]:
                for child in j["CityObjects"][id]["children"]:
                    re.add(child)
            if "parents" in j["CityObjects"][id]:
                for parent_id in j["CityObjects"][id]["parents"]:
                    re.add(parent_id)
                    # -- add siblings
                    parent_obj = j["CityObjects"].get(parent_id, {})
                    if "children" in parent_obj:
                        for child in parent_obj["children"]:
                            re.add(child)
    return re


def process_geometry(j: dict, j2: dict) -> None:
    """Reindex vertex references in j2 to point into a compacted vertex list.

    Iterates over all geometries in j2, collects only the vertices that are
    actually referenced, and writes the compacted list back to j2["vertices"].
    Vertex indices inside each geometry's boundaries are updated in-place to
    reflect their new positions in the compacted list.

    Args:
        j (dict): The source CityJSON model containing the full vertex list.
        j2 (dict): The target CityJSON subset whose boundaries will be updated.
    """
    vertex_map = {}
    new_vertices = []
    for co in j2["CityObjects"].values():
        for geom in co.get("geometry", []):
            update_array_indices(
                geom["boundaries"], vertex_map, j["vertices"], new_vertices, -1
            )
    j2["vertices"] = new_vertices


def process_templates(j: dict, j2: dict) -> None:
    dOldNewIDs = {}
    newones = []
    for each in j2["CityObjects"]:
        for geom in j2["CityObjects"][each]["geometry"]:
            if geom["type"] == "GeometryInstance":
                t = geom["template"]
                if t in dOldNewIDs:
                    geom["template"] = dOldNewIDs[t]
                else:
                    geom["template"] = len(newones)
                    dOldNewIDs[t] = len(newones)
                    newones.append(j["geometry-templates"]["templates"][t])
    if len(newones) > 0:
        j2["geometry-templates"] = {}
        j2["geometry-templates"]["vertices-templates"] = j["geometry-templates"][
            "vertices-templates"
        ]
        j2["geometry-templates"]["templates"] = newones


def process_appearance(j: dict, j2: dict) -> None:
    # -- materials
    dOldNewIDs = {}
    newmats = []
    for each in j2["CityObjects"]:
        for geom in j2["CityObjects"][each]["geometry"]:
            if "material" in geom:
                for each in geom["material"]:
                    if "value" in geom["material"][each]:
                        v = geom["material"][each]["value"]
                        if v in dOldNewIDs:
                            geom["material"][each]["value"] = dOldNewIDs[v]
                        else:
                            geom["material"][each]["value"] = len(newmats)
                            dOldNewIDs[v] = len(newmats)
                            newmats.append(j["appearance"]["materials"][v])
                    if "values" in geom["material"][each]:
                        update_array_indices(
                            geom["material"][each]["values"],
                            dOldNewIDs,
                            j["appearance"]["materials"],
                            newmats,
                            -1,
                        )
    if len(newmats) > 0:
        j2.setdefault("appearance", {})["materials"] = newmats

    # -- textures references (first int in the arrays)
    dOldNewIDs = {}
    newtextures = []
    for each in j2["CityObjects"]:
        for geom in j2["CityObjects"][each]["geometry"]:
            if "texture" in geom:
                for each in geom["texture"]:
                    if "values" in geom["texture"][each]:
                        update_array_indices(
                            geom["texture"][each]["values"],
                            dOldNewIDs,
                            j["appearance"]["textures"],
                            newtextures,
                            0,
                        )
    if len(newtextures) > 0:
        j2.setdefault("appearance", {})["textures"] = newtextures
    # -- textures vertices references (1+ int in the arrays)
    dOldNewIDs = {}
    newtextures = []
    for each in j2["CityObjects"]:
        for geom in j2["CityObjects"][each]["geometry"]:
            if "texture" in geom:
                for each in geom["texture"]:
                    if "values" in geom["texture"][each]:
                        update_array_indices(
                            geom["texture"][each]["values"],
                            dOldNewIDs,
                            j["appearance"]["vertices-texture"],
                            newtextures,
                            1,
                        )
    if len(newtextures) > 0:
        j2.setdefault("appearance", {})["vertices-texture"] = newtextures


def update_array_indices(a, dOldNewIDs, oldarray, newarray, slicearray):
    # -- slicearray: -1=none ; 0=use-only-first (for textures) ; 1=use-1+ (for textures)
    # -- a must be an array
    # -- issue with passing integer is that it's non-mutable, thus can't update
    # -- (or I don't know how...)
    for i, each in enumerate(a):
        if isinstance(each, list):
            update_array_indices(each, dOldNewIDs, oldarray, newarray, slicearray)
        elif each is not None and (
            (slicearray == -1)
            or (slicearray == 0 and i == 0)
            or (slicearray == 1 and i > 0)
        ):
            if each in dOldNewIDs:
                a[i] = dOldNewIDs[each]
            else:
                a[i] = len(newarray)
                dOldNewIDs[each] = len(newarray)
                newarray.append(oldarray[each])
