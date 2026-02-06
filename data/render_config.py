
RENDER_CONFIG = {

    "pet_size_on_screen": 8.5,  # vertical scale of first sprite on the scren (in percent)
    "initial_position": (100, 0),
    "hitbox_from_animation": "idle", # from which animation take the hitbox, if it doesnt exist will be taken from default state's animation

    "default_facing": "RIGHT",
    "default_loop_option": False,  # True or False, will animations loop or now unless stated otherwise

    "render_particles": True,
    "max_particle_count": 100000,

    "drag_offset_x": 0,
    "drag_offset_y": -1.4,
}