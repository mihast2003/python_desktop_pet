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

ASSETS = { # continuing from asset/particles/
    "dirt": "dirt",
    "sleep_zzz": "sleep_zzz",
}

PARTICLES = {
    "dirt": {
        "asset": "dirt",
        "fps": 6,
        "loop": False,
        "holds": { # holds dont work
            3: 6,
        },

        "emitter_shape": "LINE",
        "point1": (-0.5, -0),
        "point2": (0.5, -0),
        "round_square": {"constant": 0},    # from 0 (rectangle) to 1 (ellipse)
        
        "modify_border": (
            {"constant": 0}, 
            {"constant": 0}
            ),

        "emitter_offset": (
            {"constant": 0}, 
            {"constant": 0},
            ), 

        "hollow": False,
        "emit_bottom": True,

        "duration": {"constant": 0.1}, #duration of emission
        "rate_over_time": {"constant": 100},
        "random_timing": {"constant": 1}, # preferrably from 0 to 1, random offset to emittion intervals
        "total_count": {"constant": 300},

        "lifetime": {"constant": 2}, #lifetime of each particle
        "start_vel": ({"constant": 0}, {"random_range": (300, 500)}),
        "start_acceleration": ({"constant": 0}, {"constant": -2500}),
        "start_size": {"constant": 0.4},
    },

    "single_z": {
        "asset": "sleep_zzz",
        "fps": 6,
        "loop": True,

        "emitter_shape": "CIRCLE",
        "radius": 2,
        "hollow": False,
        "duration": 1,
        "rate_over_time": 1,
        "start_vel": (0, 150),
        "start_size": 0.6, 
    },

    "sleep_z": {
        "asset": "sleep_zzz",
        "fps": 6,
        "loop": True,

        "emitter_shape": "CIRCLE",
        "radius": 0.5,
        "hollow": False,
        "duration": 1,
        "rate_over_time": 0.6,
        "random_timing": 1,
        "start_vel": (0, 150),
        "start_size": 0.5, 
    },

    "sleep_zzz": {
        "asset": "sleep_zzz",
        "fps": 6,
        "loop": True,

        "emitter_shape": "CIRCLE",
        "radius": 0.5,
        "duration": 1,
        "rate_over_time": 2,
        "random_timing": 1,
        "start_vel": (0, 150),
        "start_size": 0.5, 
    },
}