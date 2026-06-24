# animation data config, holds the animation folder path, default fps and loop(can be overriden in states.py)
# "holds" specifies how long should certain frames last

# When adding animations dont forget to add them to repository <----

ANIMATIONS = {
    "idle": {
        "folder": "assets/animations/idle",
        "fps": 8,
        "loop": True,
    },

    "drag": {
        "folder": "assets/animations/drag",
        "fps": 8,
        "loop": True,
    },

    "fall": {
        "folder": "assets/animations/fall",
        "fps": 8,
        "loop": True,
    },
}