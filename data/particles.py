"""
a bit of syntax:

"emitter_shape": "DOT" requires:   "emitter_offset": (1, 1),
"emitter_shape": "LINE" requires:  "point1": (-1, 1), "point2": (1, 1),
"emitter_shape": "CIRCLE" requires:  "emitter_offset": (1, 1), "radius": 5, "hollow": True,

"""

PARTICLES = {
    "dirt": {
        "folder": "particles/dirt",
        "fps": 3,
        "loop": False,
        "holds": {
            2: 1,
        },

        "lifetime": 5, #lifetime of each particle

        "emitter_shape": "CIRCLE",
        "emitter_offset": (0, 0.5), 
        "radius": 1, 
        "hollow": True,
        "duration": 2 , #duration of emission
        "rate_over_time": 50,
        "total_count": 200,
        "start_vel": (0, 10),
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