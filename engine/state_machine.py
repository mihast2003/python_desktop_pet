#engine/state_machine.py

from engine.state_runtime import StateRuntime
from engine.enums import Flag, Pulse

class StateMachine:
    def __init__(self, pet, configs, initial):
        self.pet = pet
        self.configs = configs
        self.state = StateRuntime(state_name=initial, config=configs[initial])   # ← created ONCE
        self.change(initial)

    def raise_flag(self, flag: Flag):
        self.state.raise_flag(flag)

    def remove_flag(self, flag: Flag):
        self.state.remove_flag(flag)

    def pulse(self, pulse: Pulse):
        self.state.pulse(pulse)

    def update(self):    # state logic runs here

        next_state = self.state.handle_events()  # sends event to state_runtime.py expecting a state in return
        
        # print("state_machine next state is: ", next_state)

        if next_state:
            self.change(next_state)

        self.state.clear_pulses()  # IMPORTANT


    def change(self, next_state): #changes the state, updates state_runtime, calls on_state_enter in pet.py
        if self.state:
            self.pet.on_state_exit(self.state)

        self.state.config = self.configs[next_state]
        self.pet.on_state_enter(next_state)
