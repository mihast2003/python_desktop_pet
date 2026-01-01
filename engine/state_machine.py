#engine/state_machine.py

from engine.state_runtime import StateRuntime
from engine.enums import Flag, Pulse

class StateMachine:
    def __init__(self, pet, configs, initial):
        self.pet = pet
        self.configs = configs
        self.state = StateRuntime(state_name=initial, config=configs[initial], variables=self.pet.variables)   # ← created ONCE
        self.change(initial)
        self.in_transition = False

    def raise_flag(self, flag: Flag):
        self.state.raise_flag(flag)

    def remove_flag(self, flag: Flag):
        self.state.remove_flag(flag)

    def pulse(self, pulse: Pulse):
        self.state.pulse(pulse)

        if self.in_transition and pulse == Pulse.ANIMATION_END:  # logic for ending transition animation
            self.in_transition = False
            # print("changing after animation finished")
            self.change(self.pending_state)
            self.pending_state = None


    def update(self):    # state logic runs here
        if self.in_transition: return

        result = self.state.handle_events()  # sends event to state_runtime.py expecting two strings (next state and animation name)
        
        if not result: return # safe check

        next_state, transition_anim, anim_cfg = result

        # print("state machine. result:", result)

        # print("state_machine next state is: ", next_state)


        if transition_anim:
            self.start_transition(next_state, transition_anim, anim_cfg)
            # print("transition animation detected")
        else:
            self.state._apply_on_enter()  # signal to CurrentRuntime to apply changes in variables 
            self.remove_flag(Flag.ANIMATION_FINISHED)
            # print("changing right away")
            self.change(next_state)
        
        self.state.clear_pulses()  # IMPORTANT


    def change(self, next_state): #changes the state, updates state_runtime, calls on_state_enter in pet.py
        if self.state:
            self.pet.on_state_exit(self.state)

        self.state.config = self.configs[next_state]
        self.pet.on_state_enter(next_state)

    def start_transition(self, next_state, anim, cfg):
        self.in_transition = True
        self.pending_state = next_state

        self.pet.play_animation(anim, cfg=cfg, isTransitionAnimation=True)