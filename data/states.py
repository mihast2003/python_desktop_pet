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
"""



INITIAL_STATE = {"default": "IDLE"} #MUST HAVE

STATES = {
    "IDLE": {
        "animation": "idle",
        "fps": 6,

        "behaviour": "STATIONARY",

        "on_enter": [
            {"var": "times_clicked", "op": "=", "value": 0},
        ],

        "transitions": [
            {
                "when": [ "ANIMATION_END", {"var":"sleepiness", "op":">", "value":30}],
                "to": "BLINK",
                "chance": 0.3
            },
            {
                "when": ["ANIMATION_END", ],
                "to": "BLINK",
                "chance": 0.1,
            },
            {
                "when": [ {"pulse":"ANIMATION_END"}, ],
                "to": "LOOKING_AROUND",
                "chance": 0.03,
            },
            {
                "when": [ 
                    {"pulse":"ANIMATION_END"}, 
                    {"var":"sitting_still_timer", "op":">", "value":100},
                ],
                "to": "ROLL",
                "chance": 0.05,
            },
            {
                "when": [ 
                    {"pulse":"ANIMATION_END"},
                    {"var":"sitting_still_timer", "op":">", "value":100},
                ],
                "to": "TROLLING",
                "chance": 0.005,
            },
            {
                "when": [ 
                    {"pulse":"CLICK"}, 
                    {"var":"worrying_meter", "op":">", "value":50}    
                    ],
                "to": "VERY_WORRIED",
            },
            {
                "when": [ {"pulse":"CLICK"}, ],
                "to": "ROLL",
            },
        ],
    },

    "BLINK": {
        "animation": "blink",

        "transitions": [
            {
                "when": ["DRAGGING_STARTED"],  
                "to": "DRAGGING",
            },
            {
                "when": [ {"pulse":"ANIMATION_END"}, {"var":"sleepiness", "op":">", "value":60}],
                "to": "DOZING_OFF",
                "chance": 0.6
            },
            {
                "when": [ {"pulse":"ANIMATION_END"}, ],
                "to": "IDLE"
            },
        ],

    },

    "DOZING_OFF": {
        "animation": "dozing_off",

        "transitions": [
            {
                "when": [ "ANIMATION_END", {"var":"sleepiness", "op":">", "value":100}],
                "to": "SLEEPING",
                "transition_animation": "falling_asleep",
                "transition_animation_cfg": {
                    "fps": 8, 
                },
                "chance": 0.5,
            },
            {
                "when": [ {"pulse":"ANIMATION_END"}, {"var":"sleepiness", "op":">", "value":60}],
                "to": "DOZED_OFF",
                "chance": 1,
            },
            {
                "when": [ {"pulse":"ANIMATION_END"}, ],
                "to": "IDLE",
                "transition_animation": "waking_up",
                "transition_animation_cfg": {
                    "fps": 7, 
                }
            },
        ],

    },

    "DOZED_OFF": {
        "animation": "dozed_off",

        "transitions": [
            {
                "when": [{"pulse":"CLICK"},],
                "to": "IDLE",
                "chance": 0.7,
                "transition_animation": "waking_up",
                "transition_animation_cfg": {
                    "fps": 9, 
                },
                "on_transition": [
                    {"var": "sleepiness", "op": "-=", "value": 5},
                ]
            },
            {
                "when": [ "ANIMATION_END", {"var":"sleepiness", "op":">", "value":80}],
                "to": "SLEEPING",
                "transition_animation": "falling_asleep",
                "transition_animation_cfg": {
                    "fps": 8, 
                },
                "chance": 0.8,
            },
            {
                "when": [{"pulse":"ANIMATION_END"}, {"var":"time_spent_in_this_state", "op":">", "value":30} ],
                "to": "IDLE",
                "chance": 0.2,
                "transition_animation": "waking_up",
                "transition_animation_cfg": {
                    "fps": 6, 
                },
                "on_transition": [
                    {"var": "sleepiness", "op": "=", "value": 0},
                ],
            },
        ],

    },

    "SLEEPING": {
        "animation": "sleeping",

        "transitions": [
            {
                "when": [ {"pulse":"ANIMATION_END"}, {"var":"time_spent_in_this_state", "op":">", "value":10}],
                "to": "IDLE",
                "chance": 1,
                "transition_animation": "waking_up_after_sleep",
                "on_transition": [
                    {"var": "sleepiness", "op": "=", "value": -300},
                ],
            },
        ],

    },

    "LOOKING_AROUND": {
        "animation": "look_around",
        "loop": False,
        "transitions": [
            {
                "when": [ {"pulse":"CLICK"}, ],
                "to": "ROLL",
            },
            {
                "when": ["DRAGGING_STARTED"],  
                "to": "DRAGGING",
            },
        ],
        "exit_when": ["ANIMATION_END"],
        "exit_to": "IDLE"
    },

    "ROLL": {
        "animation": "roll",
        "behaviour": "MOVE_RANDOM_X_ON_SURFACE",
        # "settings": {
        #     "gravity": 700,
        # },

        "on_enter": [
            {"var": "sitting_still_timer", "op": "=", "value": 0},
        ],
        
        "transitions": [
            {
                "when": [{"flag":"MOVEMENT_FINISHED"},],
                "to": "BLINK",
                "chance": 0.1,
            },
        ],
        "exit_when": ["MOVEMENT_FINISHED"],
        "exit_to": "IDLE"
    }, 

    "JUMP": {
        "animation": "roll",
        "behaviour": "JUMP",

        "on_enter": [
            {"var": "sitting_still_timer", "op": "=", "value": 0},
        ],
        
        "transitions": [
            {
                "when": [{"flag":"MOVEMENT_FINISHED"},],
                "to": "BLINK",
                "chance": 0.1,
            },
        ],
        "exit_when": ["MOVEMENT_FINISHED"],
        "exit_to": "IDLE"
    },

    "DRAGGING": {
        "animation": "held_by_the_nose",
        "fps": 5,
        "behaviour": "DRAGGING",
        "settings": {
            "gravity": 5000,
        },

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
        
        "exit_when": ["DRAGGING_ENDED"],
        "exit_to": "FALLING"
    },

    "FALLING": {
        "animation": "roll",
        "behaviour": "FALL",

        "force_transition": [
            {
                "when": ["LOST_PARENT"],
                "except_states": ["DRAGGING"],
                # "transition_animation": "standing_up",
                # "transition_animation_cfg": {
                #     "fps": 4,
                # },
            }
        ],
        
        "transitions": [
            {
                "when": ["MOVEMENT_FINISHED",],
                "to": "IDLE",
                "transition_animation": "standing_up",
                "transition_animation_cfg": {
                    "fps": 12,
                },
            }
        ],
        "exit_when": ["MOVEMENT_FINISHED"],
        "exit_to": "IDLE"
    },    

    "VERY_WORRIED": {
        "animation": "grow",
        "times_to_loop": 5,
        "behaviour": "STATIONARY",
        "on_enter": [
            {"var": "worrying_meter", "op": "=", "value": 0},
        ],
        "transitions":[
            {
                "when": ["ANIMATION_FINISHED",],
                "to": "IDLE",
            }
        ],
    }, 

    "TROLLING": {
        "animation": "idle",
        "fps": 0,
        "behaviour": "STATIONARY",

        "transitions":[
            {
                "when": [ 
                    "CLICK", 
                    {"var": "times_clicked_this_state", "op": ">=", "value": 3}
                    ],
                "to": "IDLE",
                "transition_animation": "trollface",
                "transition_animation_cfg": {
                    "fps": 10,
                }
            }
        ],
    }, 
    
}
