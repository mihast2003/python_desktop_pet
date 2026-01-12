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

    def raise_flag(self, flag: Flag):
        self.state.raise_flag(flag)

    def remove_flag(self, flag: Flag):
        self.state.remove_flag(flag)

    def pulse(self, pulse: Pulse):
        self.state.pulse(pulse)

        if self.in_transition and pulse == Pulse.ANIMATION_END:  # logic for ending transition animation
            print("changing after animation finished")
            self.apply_pending_changes()
        

    def update(self, dt):    # state logic runs here
        # MOVEMENT AND ANIMATION UPDATE
        self.pet.animator.update(dt)
        arrived = self.pet.mover.update(dt)
        
        if arrived:
            self.pet.click_detector.release()
            self.raise_flag(Flag.MOVEMENT_FINISHED)


        # HANDLING EVENTS
        if not self.in_transition:
            result = self.state.handle_events()  # sends event to state_runtime.py expecting two strings (next state and animation name)
        else: result = None


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

        # if transition animation then play it
        if self.pending_transition_anim:
            # print("state_machine: animation queued")
            self.pet.play_animation(
                self.pending_transition_anim,
                cfg=self.pending_transition_cfg,
                isTransitionAnimation=True
            )
        
        

    def apply_pending_changes(self):
        if not self.pending_state:
            return
        
        self.state.clear_pulses() #just in case any pulses arent cleared too fast

        # Change state
        self.change(self.pending_state)
        # print("state_machine: pending changes applied")

        # Cleanup
        self.pending_state = None
        self.pending_transition_anim = None
        self.pending_transition_cfg = None
        self.in_transition = False
  
    def change(self, next_state): #changes the state, updates state_runtime, calls on_state_enter in pet.py
        if self.state.name != next_state:
            self.pet.on_state_exit(self.state)
        
        self.remove_flag(Flag.ANIMATION_FINISHED)
        self.remove_flag(Flag.MOVEMENT_FINISHED)
        self.state.config = self.configs[next_state]
        self.state._apply_on_enter()
        self.pet.on_state_enter(next_state)