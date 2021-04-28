"""This module contains functions that originate from cjio"""

import copy

from .subset import *

def createCityJSON():
    """Returns an empty CityJSON file"""
    cm = {}
    cm["type"] = "CityJSON"
    cm["version"] = "1.0"
    cm["CityObjects"] = {}
    cm["vertices"] = []

    return cm

def get_centroid(cm, coid):
    def recusionvisit(a, vs):
        for each in a:
            if isinstance(each, list):
                recusionvisit(each, vs)
            else:
                vs.append(each)
    #-- find the 3D centroid
    centroid = [0, 0, 0]
    total = 0
    for g in cm['CityObjects'][coid]['geometry']:
        vs = []
        recusionvisit(g["boundaries"], vs)
        for each in vs:
            v = cm["vertices"][each]
            total += 1
            centroid[0] += v[0]
            centroid[1] += v[1]
            centroid[2] += v[2]
    if (total != 0):
        centroid[0] /= total
        centroid[1] /= total
        centroid[2] /= total
        if "transform" in cm:
            centroid[0] = (centroid[0] * cm["transform"]["scale"][0]) + cm["transform"]["translate"][0]
            centroid[1] = (centroid[1] * cm["transform"]["scale"][1]) + cm["transform"]["translate"][1]
            centroid[2] = (centroid[2] * cm["transform"]["scale"][2]) + cm["transform"]["translate"][2]
        return centroid
    else:
        return None

def get_subset_cotype(cm, cotype, invert=False):
    # print ('get_subset_cotype')
    if isinstance(cotype, list):
        lsCOtypes = cotype
    else:
        lsCOtypes = [cotype]

    for t in lsCOtypes:
        if t == 'Building':
            lsCOtypes.append('BuildingInstallation')
            lsCOtypes.append('BuildingPart')
        if t == 'Bridge':
            lsCOtypes.append('BridgePart')
            lsCOtypes.append('BridgeInstallation')
            lsCOtypes.append('BridgeConstructionElement')
        if t == 'Tunnel':
            lsCOtypes.append('TunnelInstallation')
            lsCOtypes.append('TunnelPart')
    #-- new sliced CityJSON object
    cm2 = createCityJSON()
    cm2["version"] = cm["version"]
    if "transform" in cm:
        cm2["transform"] = cm["transform"]
    #-- copy selected CO to the j2
    for theid in cm["CityObjects"]:
        if invert is False:
            if cm["CityObjects"][theid]["type"] in lsCOtypes:
                cm2["CityObjects"][theid] = cm["CityObjects"][theid]
        else:
            if cm["CityObjects"][theid]["type"] not in lsCOtypes:
                cm2["CityObjects"][theid] = cm["CityObjects"][theid]
    #-- geometry
    process_geometry(cm, cm2)
    #-- templates
    process_templates(cm, cm2)
    #-- appearance
    if ("appearance" in cm):
        cm2["appearance"] = {}
        process_appearance(cm, cm2)
    #-- metadata
    if ("metadata" in cm):
        cm2["metadata"] = cm["metadata"]

    return cm2

def get_subset_bbox(cm, bbox, invert=False):
    # print ('get_subset_bbox')
    #-- new sliced CityJSON object
    cm2 = createCityJSON()
    cm2["version"] = cm["version"]
    if "transform" in cm:
        cm2["transform"] = cm["transform"]
    re = set()            
    for coid in cm["CityObjects"]:
        centroid = get_centroid(cm, coid)
        if ((centroid is not None) and
            (centroid[0] >= bbox[0]) and
            (centroid[1] >= bbox[1]) and
            (centroid[0] <  bbox[2]) and
            (centroid[1] <  bbox[3]) ):
            re.add(coid)
    re2 = copy.deepcopy(re)
    if invert == True:
        allkeys = set(cm["CityObjects"].keys())
        re = allkeys ^ re
    #-- also add the parent-children
    for theid in re2:
        if "children" in cm['CityObjects'][theid]:
            for child in cm['CityObjects'][theid]['children']:
                re.add(child)
        if "parent" in cm['CityObjects'][theid]:
            re.add(cm['CityObjects'][theid]['parent'])

    for each in re:
        cm2["CityObjects"][each] = cm["CityObjects"][each]
    #-- geometry
    process_geometry(cm, cm2)
    #-- templates
    process_templates(cm, cm2)
    #-- appearance
    if ("appearance" in cm):
        cm2["appearance"] = {}
        process_appearance(cm, cm2)
    #-- metadata
    if ("metadata" in cm):
        cm2["metadata"] = cm["metadata"]

    return cm2