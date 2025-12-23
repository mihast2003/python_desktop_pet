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
                "on": ["CLICK"],
                "to": "BLINK",
                "chance": 0.5
            },
            {
                "on": ["CLICK"],
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
    }      
}
