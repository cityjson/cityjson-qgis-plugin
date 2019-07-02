"""A module that contains sample geometries for tests"""

example_multisurface_with_semantics = [{
    "type": "MultiSurface",
    "boundaries": [
        [[0, 3, 2, 1]], [[4, 5, 6, 7]], [[0, 1, 5, 4]], [[0, 2, 3, 8]], [[10, 12, 23, 48]]
    ],
    "semantics": {
        "surfaces" : [
            {
                "type": "WallSurface",
                "slope": 33.4,
                "children": [2]
            }, 
            {
                "type": "RoofSurface",
                "slope": 66.6
            },
            {
                "type": "Door",
                "parent": 0,
                "colour": "blue"
            }
        ],
        "values": [0, 0, None, 1, 2]
    }
}]

example_solid_with_semantics = [
    {
        "type": "CompositeSolid",
        "lod": 2,
        "boundaries": [
            [
            [ [[0, 3, 2, 1, 22]], [[4, 5, 6, 7]], [[0, 1, 5, 4]], [[1, 2, 6, 5]] ]
            ],
            [
            [ [[666, 667, 668]], [[74, 75, 76]], [[880, 881, 885]], [[111, 122, 226]] ] 
            ]    
        ],
        "semantics": {
            "surfaces" : [
            {      
                "type": "RoofSurface",
            }, 
            {
                "type": "WallSurface",
            }
            ],
            "values": [
            [
                [0, 1, 1, None]
            ],
            [
                None
            ]
            ]
        }
    }  
]

example_composite_solid = [{
    "type": "CompositeSolid",
    "lod": 3,
    "boundaries": [
        [
        [ [[0, 3, 2, 1, 22]], [[4, 5, 6, 7]], [[0, 1, 5, 4]], [[1, 2, 6, 5]] ],
        [ [[240, 243, 124]], [[244, 246, 724]], [[34, 414, 45]], [[111, 246, 5]] ]
        ],
        [
        [ [[666, 667, 668]], [[74, 75, 76]], [[880, 881, 885]], [[111, 122, 226]] ] 
        ]    
    ]
}]