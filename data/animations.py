"""
animation data config, holds the animation folder path, default fps and loop(can be overriden in states.py)
"holds" specifies how long should certain frames last

folder is has root in assets/animations

When adding animations dont forget to add them to repository <----
"""

ANIMATIONS = {
    "idle": {
        "folder": "idle",
        "fps": 8,
        "loop": True,
    },

    "blink": {
        "folder": "blink",
        "fps": 8,
        "loop": False,
        "holds": {
            2: 2,
        }
    },

    "roll": {
        "folder": "roll",
        "fps": 12,
        "loop": True,
    },

    "look_around": {
        "folder": "look_around",
        "fps": 8,
        "loop": True,
        "holds": {
            3: 10,
            8: 10,
        }
    },

    "held_by_the_nose": {
        "folder": "held_by_the_nose",
        "fps": 12,
        "loop": True,
    },

    "grow": {
        "folder": "grow",
        "fps": 12,
        "loop": False,
        "times_to_loop": 3,
    },

    "standing_up": {
        "folder": "standing_up",
        "fps": 12,
        "loop": False,
        "times_to_loop": 1,
    },

    "trollface": {
        "folder": "trollface",
        "fps": 60,
        "loop": False,
        "holds": {
            1: 10,
        }
    },

    "dozing_off": {
        "folder": "dozing_off",
        "fps": 3,
        "loop": False,
        "holds": {
            3: 2,
            4: 2,
        }
    },

    "dozed_off": {
        "folder": "dozed_off",
        "fps": 6,
        "loop": True,
    },

    "waking_up": {
        "folder": "TRANSITIONS/waking_up",
        "fps": 8,
        "loop": False,
    },

    "falling_asleep": {
        "folder": "TRANSITIONS/falling_asleep",
        "fps": 16,
        "loop": False,
        "holds": {
            1: 4,
            2: 4,
        }
    },

    "sleeping": {
        "folder": "sleeping",
        "fps": 6,
        "loop": True,
    },

    "waking_up_after_sleep": {
        "folder": "TRANSITIONS/waking_up_after_sleep",
        "fps": 6,
        "loop": False,
        "holds": {
            1: 3,
            2: 2,
            3: 3,
            5: 2,
            6: 2,
        }
    },

    "looking_for_something": {
        "folder": "TRANSITIONS/looking_for",
        "fps": 6,
        "times_to_loop": 3,
    },

    "magnifying_glass": {
        "folder": "magnifying_glass",
        "fps": 6,
        "loop": False,
    },
}