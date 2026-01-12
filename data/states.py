# data/states
# config, main data structure, dictates states, their animation, transitions between states
# after "animation" can write overrides for "fps" or "loop"

# tansitions is a list of dictionaries of lists.
# "transitions": [
#             {
#                 "when": [ 
#                       {"flag":"THIS_FLAG"}, 
#                       {"var":"sitting_still_timer", "op":">", "value":10},
#                 ],  
#                 "to": "DRAGGING",
#                 "chance": 1,
#             },
# BUT
# "when": ["THIS_FLAG", "THAT_PULSE" ],  
# ALSO WORKS
# 
#
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
                "when": [  "DRAGGING_STARTED" ],  
                "to": "DRAGGING",
                "chance": 1,
            },
            {
                "when": ["ANIMATION_END", ],
                "to": "BLINK",
                "chance": 0.06,
            },
            {
                "when": [ {"pulse":"ANIMATION_END"}, ],
                "to": "LOOKING_AROUND",
                "chance": 0.1,
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
                "when": [ {"pulse":"ANIMATION_END"}, ],
                "to": "IDLE"
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
        ],
        "exit_when": ["ANIMATION_END"],
        "exit_to": "IDLE"
    },

    "ROLL": {
        "animation": "roll",
        "behaviour": "MOVING_RANDOM",

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
        
        "exit_when": ["DRAGGING_ENDED"],
        "exit_to": "FALLING"
    },

    "FALLING": {
        "animation": "roll",
        "behaviour": "FALLING",
        
        "transitions": [
            {
                "when": ["MOVEMENT_FINISHED",],
                "to": "IDLE",
                "transition_anim": "standing_up",
                "transition_anim_cfg": {
                    "fps": 12
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
                "transition_anim": "trollface",
                "transition_anim_cfg": {
                    "fps": 10,
                }
            }
        ],
    }, 
    
}
