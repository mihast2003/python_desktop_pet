#engine/state_machine.py

from engine.state_runtime import StateRuntime
from engine.enums import Flag, Pulse

class StateMachine:
    def __init__(self, pet, configs, initial):
        self.pet = pet
        self.configs = configs
        self.state = StateRuntime(state_name=initial, config=configs[initial], variables=self.pet.variables)   # created instance of runtime and then changed
        self.change(initial)
        self.in_transition = False

        # for pending states
        self.pending_state = None
        self.pending_transition_anim = None
        self.pending_transition_cfg = None
        self.freeze_simulation = False

    def raise_flag(self, flag: Flag):
        self.state.raise_flag(flag)

    def remove_flag(self, flag: Flag):
        self.state.remove_flag(flag)

    def pulse(self, pulse: Pulse):
        self.state.pulse(pulse)

        if self.in_transition and pulse == Pulse.ANIMATION_END:  # logic for ending transition animation
            self.on_transition_animation_end()
            

    def on_transition_animation_end(self):
        # self.state.clear_pulses()
        # print("changing after animation finished")
        self.apply_pending_changes()
        self.in_transition = False
        

    def update(self, dt):    # state logic runs here
        if self.freeze_simulation: return

        # HANDLING EVENTS
        if not self.in_transition:
            result = self.state.handle_events()  # sends event to state_runtime.py expecting two strings (next state and animation name)
        else: result = None

        # MOVEMENT AND ANIMATION UPDATE
        arrived = self.pet.mover.update(dt)
        self.pet.animator.update(dt)

        if arrived:
            self.pet.click_detector.release()
            self.raise_flag(Flag.MOVEMENT_FINISHED)


        # TRANSITION LOGIC
        if result:
            next_state, transition_anim, anim_cfg = result

            if transition_anim:
                self.queue_transition(next_state, transition_anim, anim_cfg) # queueing transition until transition anim is finished
            else:
                self.queue_transition(next_state, None, None)
                self.apply_pending_changes()    # immediately executing transition

        # print("state machine. result:", result)
        # print("state_machine next state is: ", next_state)

        self.state.clear_pulses()  # IMPORTANT

        
    def queue_transition(self, next_state, anim, cfg):
        self.pending_state = next_state
        self.pending_transition_anim = anim
        self.pending_transition_cfg = cfg
        self.in_transition = True

    def apply_pending_changes(self):
        if not self.pending_state:
            return

        self.freeze_simulation = True

        # 1. Play transition animation first (if any)
        if self.pending_transition_anim:
            self.pet.play_animation(
                self.pending_transition_anim,
                cfg=self.pending_transition_cfg,
                isTransitionAnimation=True
            )

        # 2. Change state
        self.change(self.pending_state)

        # 3. Cleanup
        self.pending_state = None
        self.pending_transition_anim = None
        self.pending_transition_cfg = None
        self.in_transition = False
        self.freeze_simulation = False
  
    def change(self, next_state): #changes the state, updates state_runtime, calls on_state_enter in pet.py
        if self.state.name != next_state:
            self.pet.on_state_exit(self.state)
        
        self.remove_flag(Flag.ANIMATION_FINISHED)
        self.remove_flag(Flag.MOVEMENT_FINISHED)
        self.state.config = self.configs[next_state]
        self.pet.on_state_enter(next_state)