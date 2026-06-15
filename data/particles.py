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
        "folder": "assets/particles/dirt",
        "fps": 2,
        "loop": False,
        "holds": { # holds dont work
            2: 1,
        },

        "emitter_shape": "LINE",
        "point1": (-0.5, 0), "point2": (0.5, 0),
        "round_square": 0,    # from 0 (rectangle) to 1 (ellipse)
        "modify_border": (0.0, 0.0),
        "emitter_offset": (0, 0), 
        "hollow": False,
        "emit_bottom": True,

        "duration": 0.1, #duration of emission
        "rate_over_time": 200,
        "random_timing": 1, # preferrably from 0 to 1, random offset to emition intervals
        "total_count": 300,

        "lifetime": 3, #lifetime of each particle
        "start_vel": (0, 500),
        "start_acceleration": (0, -2500),
        "start_size": 0.6,
    },

    "sleep_zzz": {
        "folder": "assets/particles/sleep_zzz",
        "fps": 6,
        "loop": True,

        "emitter_shape": "DOT",
        "emitter_offset": (1, 1),
        "duration": 0.5,
        "rate_over_time": 1,
        "start_vel": (0, 200),
        "start_size": 1, 
    },
}