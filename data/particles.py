

PARTICLES = {
    "dirt": {
        "folder": "particles/dirt",
        "fps": 3,
        "loop": False,
        "holds": {
            2: 1,
        },

        "lifetime": 2, #lifetime of each particle

        "emitter_shape": "DOT",
        "duration": 0.5 , #duration of emission
        "rate_over_time": 4,
        "total_count": 20,
        "start_vel": (0, -100),
        "start_size": 1 ,
    },

    "sleep_zzz": {
        "folder": "particles/sleep_zzz",
        "fps": 6,
        "loop": True,

        "emitter_shape": "DOT",
        "duration": 0.5,
        "rate_over_time": 1,
        "start_vel": 1,
        "start_size": 1,
    },
}