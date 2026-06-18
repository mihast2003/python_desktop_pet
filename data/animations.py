# animation data config, holds the animation folder path, default fps and loop(can be overriden in states.py)
# "holds" specifies how long should certain frames last

# When adding animations dont forget to add them to repository <----

ANIMATIONS = {
    "idle": {
        "folder": "assets/animations/idle",
        "fps": 8,
        "loop": True,
    },

    "blink": {
        "folder": "assets/animations/blink",
        "fps": 8,
        "loop": False,
        "holds": {
            2: 2,
        }
    },

    "roll": {
        "folder": "assets/animations/roll",
        "fps": 12,
        "loop": True,
    },

    "look_around": {
        "folder": "assets/animations/look_around",
        "fps": 8,
        "loop": True,
        "holds": {
            3: 10,
            8: 10,
        }
    },

    "held_by_the_nose": {
        "folder": "assets/animations/held_by_the_nose",
        "fps": 12,
        "loop": True,
    },

    "grow": {
        "folder": "assets/animations/grow",
        "fps": 12,
        "loop": False,
        "times_to_loop": 3,
    },

    "standing_up": {
        "folder": "assets/animations/standing_up",
        "fps": 12,
        "loop": False,
        "times_to_loop": 1,
    },

    "trollface": {
        "folder": "assets/animations/trollface",
        "fps": 60,
        "loop": False,
        "holds": {
            1: 10,
        }
    },

    "dozing_off": {
        "folder": "assets/animations/dozing_off",
        "fps": 3,
        "loop": False,
        "holds": {
            3: 2,
            4: 2,
        }
    },

    "dozed_off": {
        "folder": "assets/animations/dozed_off",
        "fps": 6,
        "loop": True,
    },

    "waking_up": {
        "folder": "assets/animations/TRANSITIONS/waking_up",
        "fps": 8,
        "loop": False,
    },

    "falling_asleep": {
        "folder": "assets/animations/TRANSITIONS/falling_asleep",
        "fps": 16,
        "loop": False,
        "holds": {
            1: 4,
            2: 4,
        }
    },

    "sleeping": {
        "folder": "assets/animations/sleeping",
        "fps": 6,
        "loop": True,
    },

    "waking_up_after_sleep": {
        "folder": "assets/animations/TRANSITIONS/waking_up_after_sleep",
        "fps": 8,
        "loop": False,
    },
}