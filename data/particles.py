"""
a bit of syntax:

"emitter_shape": "DOT" requires:   "emitter_offset": (1, 1),
"emitter_shape": "LINE" requires:  "point1": (-1, 1), "point2": (1, 1),
"emitter_shape": "CIRCLE" requires:  "emitter_offset": (1, 1), "radius": 5, "hollow": True,
"emitter_shape": "HITBOX" requires:  "emitter_offset": (0, 0), "modify_border": (1, 1), "hollow": True,
"emit_top": True, "emit_bottom": True, "emit_left": True, "emit_right": True,

"emitter_shape": "RECTANGLE" requires:  "emitter_offset": (0, 0), "size": (1, 1), "hollow": True,
"emit_top": True, "emit_bottom": True, "emit_left": True, "emit_right": True,

"""

PARTICLES = {
    "dirt": {
        "folder": "particles/dirt",
        "fps": 2,
        "loop": False,
        "holds": {
            2: 1,
        },

        "emitter_shape": "RECTANGLE",
        "point1": (-1, 1), "point2": (1, 1),
        "round_square": 0,    # from 0 (rectangle) to 1 (ellipse)
        "modify_border": (0.0, 0.0),
        "emitter_offset": (0, 0), 
        "hollow": False,
        "emit_bottom": True,

        "duration": 1, #duration of emission
        "rate_over_time": 10,
        "random_timing": 1, # preferrably from 0 to 1, random offset to emition intervals
        "total_count": 100000,

        "lifetime": 10, #lifetime of each particle
        "start_vel": (100, 350),
        "start_acceleration": (0, -20),
        "start_size": 1,
    },

    "sleep_zzz": {
        "folder": "particles/sleep_zzz",
        "fps": 6,
        "loop": True,

        "emitter_shape": "DOT",
        "emitter_offset": (1, 1),
        "duration": 0.5,
        "rate_over_time": 1,
        "start_vel": 1,
        "start_size": 1,
    },
}