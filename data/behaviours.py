# behaviours.py
# choose a target destination
# choose a movement type from MovementType enum in enums.py

BEHAVIOURS = {
    "STATIONARY": {
        "movement": "STATIONARY"
    },

    "DRAGGING": {
        "target": {
            "x": {"type": "random", "min": "screen.left", "max": "screen.right"},
            "y": {"type": "current"}
        },
        "movement": "DRAG"
    },

    "MOVE_RANDOM_X": {
        "target": {
            "x": {"type": "random", "min": "screen.left", "max": "screen.right"},
            "y": {"type": "current"}
        },
        "movement": "LERP"
    },

    "MOVE_RANDOM_Y": {
        "target": {
            "x": {"type": "current"},
            "y": {"type": "random", "min": "screen.top", "max": "screen.bottom"}
        },
        "movement": "LERP"
    },

    "MOVE_RANDOM_XY": {
        "target": {
            "x": {"type": "random", "min": "screen.left", "max": "screen.right"},
            "y": {"type": "random", "min": "screen.top", "max": "screen.bottom"}
        },
        "movement": "LERP"
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
    },

    "JUMP": {
        "target": {
            "x": {"type": "random_range", "min": "screen.left", "max": "screen.right", "range": 200},
            "y": {"type": "fixed", "to": "screen.bottom"}
        },
        "movement": "JUMP"
    }
}
