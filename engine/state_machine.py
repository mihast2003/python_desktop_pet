#engine/state_machine.py

from engine.state_runtime import StateRuntime
from engine.enums import Flag, Pulse


class StateMachine:
    def __init__(self, pet, configs, initial):
        self.pet = pet
        self.configs = configs
        self.state = StateRuntime(pet = pet, current_state_name=initial, config=configs[initial], all_configs=configs, variables=self.pet.variables)   # created instance of runtime and then changed
        self.change(initial)
        self.in_transition = False

        # for pending states
        self.pending_state = None
        self.pending_transition_anim = None
        self.pending_transition_cfg = None

    def raise_flag(self, flag: Flag):
        self.state.raise_flag(flag)

        if self.in_transition and flag == Flag.ANIMATION_FINISHED:  # logic for ending transition animation
            # print("changing after animation finished")
            self.apply_pending_changes()

    def remove_flag(self, flag: Flag):
        self.state.remove_flag(flag)

    def pulse(self, pulse: Pulse):
        self.state.pulse(pulse)

        # if self.in_transition and pulse == Pulse.ANIMATION_END:  # logic for ending transition animation
        #     # print("changing after animation finished")
        #     self.apply_pending_changes()
        
    def update_apps(self, app_state):
        self.state.update_apps(app_state)

    def update(self, dt):    # state logic runs here
        # HANDLING EVENTS
        result = self.state.handle_global_events()
        # print("state_machine update", result)

        if not result and not self.in_transition:
            result = self.state.handle_events()  # sends event to state_runtime.py expecting two strings (next state and animation name)


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

        self.state.clear_pulses()

        
    def queue_transition(self, next_state, anim, cfg):      
        self.pet.on_state_exit(self.state.current_state_name)
        self.state._apply_on_exit()

        self.pending_state = next_state
        self.pending_transition_anim = anim
        self.pending_transition_cfg = cfg
        self.in_transition = True

        # if transition animation then play it
        if self.pending_transition_anim:
            # print("state_machine: animation queued")
            if type(self.pending_transition_cfg) != dict:
                raise RuntimeError(f"Excuse me, you messed up the config for transition animation: {self.pending_transition_anim}, should be a dict")

            self.pet.play_animation(
                self.pending_transition_anim,
                cfg=self.pending_transition_cfg,
                isTransitionAnimation=True
            )
        
        

    def apply_pending_changes(self):
        if not self.pending_state:
            return
        
        self.state.clear_pulses() #just in case any pulses arent cleared too fast

        self.in_transition = False

        # Change state
        self.change(self.pending_state)
        # print("state_machine: pending changes applied")

        # Cleanup
        self.pending_state = None
        self.pending_transition_anim = None
        self.pending_transition_cfg = None
  
    def change(self, next_state): #changes the state, updates state_runtime, calls on_state_enter in pet.py
        self.remove_flag(Flag.ANIMATION_FINISHED) # later will add some way to automatically clear these
        self.remove_flag(Flag.MOVEMENT_FINISHED)
        self.state.current_state_name = next_state
        self.state.config = self.configs[next_state]
        self.pet.on_state_enter(next_state)
        self.state._apply_on_enter()