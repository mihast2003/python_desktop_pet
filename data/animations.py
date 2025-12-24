# animation data config, holds the animation folder path, default fps and loop(can be overriden in states.py)
# "holds" specifies how long should certain frames last

ANIMATIONS = {
    "idle": {
        "folder": "animations/idle",
        "fps": 8,
        "loop": True,
    },

    "blink": {
        "folder": "animations/blink",
        "fps": 8,
        "loop": True,
        "holds": {
            2: 2,
        }
    },

    "roll": {
        "folder": "animations/roll",
        "fps": 12,
        "loop": True,
    },

    "look_around": {
        "folder": "animations/look_around",
        "fps": 8,
        "loop": True,
        "holds": {
            3: 10,
            8: 10,
        }
    },

    "held_by_the_nose": {
        "folder": "animations/held_by_the_nose",
        "fps": 12,
        "loop": True,

    },

}