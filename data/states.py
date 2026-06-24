"""
data/states
config, main data structure, dictates states, their animation, transitions between states
after "animation" can write overrides for "fps" or "loop"

tansitions is a list of dictionaries of lists.
        "transitions": [
            {
                "when": [ 
                      {"flag":"THIS_FLAG"}, 
                      {"var":"sitting_still_timer", "op":">", "value":10},
                ],  
                "to": "DRAGGING",
                "chance": 1,
            },
BUT
"when": ["THIS_FLAG", "THAT_PULSE" ],  
ALSO WORKS

To force other states to transition to this when some flags/pulses are met:
        "force_transition": [
            {
                "when": ["DRAGGING_STARTED"],
                "except_states": ["DRAGGING"],
                # "transition_animation": "standing_up",
                # "transition_animation_cfg": {
                #     "fps": 4,
                # },
            }
        ],

Particles stuff:
In states can add conditional and constant particles, besides "particles_on_enter" and "particles_on_exit"
    "constant_particles": [
                {"emit": "dirt"}
            ],
    "conditional_particles": [
                {"when": ["CLICK"],
                "emit": "dirt",
                },
            ],

In transitions: [] can add particles now
    "particles_on_transition": [
                {"emit": "dirt"},
            ],
"""



INITIAL_STATE = {"default": "IDLE"} #MUST HAVE

STATES = {
    "IDLE": {
        "animation": "idle",
        "fps": 6,

        "behaviour": "STATIONARY",

        "transitions": [
            {
                "when": ["DRAGGING_STARTED"],
                "to": "DRAGGING",
                "chance": 1
            },
            
        ],
    },

    "DRAGGING": {
        "animation": "drag",
        "fps": 6,

        "behaviour": "DRAGGING",

        "transitions": [
            {
                "when": [ "ANIMATION_END", {"var":"sleepiness", "op":">", "value":300}],
                "to": "BLINK",
                "chance": 0.3
            },
            
        ],
    },


    
}
