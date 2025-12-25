# data/states
# config, main data structure, dictates states, their animation, transitions between states
# after "animation" can write overrides for "fps" or "loop"
# tansitions is a list of dictionaries of lists. transitions[{"on": ["CLICK"]}, {"to": ["ROLL"]}]

STATES = {
    "IDLE": {
        "animation": "idle",
        "fps": 6,
        "behaviour": "STATIONARY",

        "transitions": [
            {
                "when": [ {"flag": "CLICK_HELD"}, ],  
                "to": "DRAGGING",
                "chance": 1,
            },
            {
                "when": [ {"pulse": "ANIMATION_END"}, ],
                "to": "BLINK",
                "chance": 0.08,
            },
            {
                "when": [ {"pulse": "ANIMATION_END"}, ],
                "to": "LOOKING_AROUND",
                "chance": 0.02,
            },
            {
                "when": [ {"pulse": "ANIMATION_END"}, ],
                "to": "ROLL",
                "chance": 0.01,
            },
            {
                "when": [ {"pulse": "CLICK"}, ],
                "to": "ROLL",
            },
        ],
    },

    "BLINK": {
        "animation": "blink",


        "transitions": [
            {
                "on": ["ANIMATION_END"],
                "to": "IDLE"
            },
        ],

    },

    "LOOKING_AROUND": {
        "animation": "look_around",
        "transitions": [
            {
                "on": ["CLICK"],
                "to": "ROLL",
            },
        ],
        "exit_when": ["ANIMATION_END"],
        "exit_to": "IDLE"
    },

    "ROLL": {
        "animation": "roll",
        "behaviour": "MOVING_RANDOM",
        
        "transitions": [
            {
                "on": ["MOVEMENT_FINISHED"],
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
        
        "exit_when": ["MOVEMENT_FINISHED"],
        "exit_to": "IDLE"
    },    
}
