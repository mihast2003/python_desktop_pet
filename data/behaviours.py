# behaviours.py
# choose a target destination
# choose a movement type from MovementType enum in enums.py
#

BEHAVIOURS = {
    "STATIONARY": {
        "movement": "STATIONARY"
    },

    "DRAGGING": {
        "target": {
            "x": {"type": "random", "min": "screen.left", "max": "screen.right"},
            "y": {"type": "current"}
        },
        "movement": "DRAG",
    },

    "MOVE_RANDOM_X": {
        "target": {
            "x": {"type": "random", "min": "screen.left", "max": "screen.right"},
            "y": {"type": "current"}
        },
        "movement": "LERP",
        "collide_with_surfaces": "all",
        "parent_to_surfaces": {"RIGHT"},
    },

    "FALLING": {
        "target": {
            "x": {"type": "current"},
            "y": {"type": "fixed", "to": "screen.bottom"}
        },
        "movement": "ACCELERATE",
        "settings": {
            "gravity": 700,
        },
        "collide_with_surfaces": {"TOP"},
        "parent_to_surfaces": {"TOP"},
    },

}
