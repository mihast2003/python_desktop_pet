# engine/state_runtime.py
# handles Events

import random
from engine.enums import Flag, Pulse

class StateRuntime:
    def __init__(self, current_state_name, config, all_configs, variables):
        self.current_state_name = current_state_name
        self.config = config
        self.all_configs = all_configs
        self.variables = variables

        self.all_forced_transitions = {}

        # getting all force transitions in a dictionary for ease of use
        for state in self.all_configs:
            force_transition = self.all_configs[state].get("force_transition")
            if not force_transition: continue

            for t in force_transition:
                conditions = t.get("when")
                exception_states = t.get("except_states")
                to = state
                chance = t.get("chance", 1)
                trans_anim = t.get("transition_animationation")
                trans_anim_cfg = t.get("transition_animationation_cfg")

                # print(conditions)
                # print(to)
                # print(chance)

                self.all_forced_transitions[to] = {"conditions": conditions, "except_states": exception_states, "chance": chance, "transition_animationation": trans_anim, "transition_animationation_cfg": trans_anim_cfg}

        # print(self.all_forced_transitions)

        self.flags = set()
        self.pulses = set()

    # flags
    def raise_flag(self, flag: Flag):
        if flag == Flag.DRAGGING and not flag in self.flags:  # special check for sending a pulse dragging started when dragging flag is raised
            self.pulse(Pulse.DRAGGING_STARTED)

        self.flags.add(flag)

    def remove_flag(self, flag: Flag):
        self.flags.discard(flag)

    def has_flag(self, flag: Flag):
        return flag in self.flags

    # pulses
    def pulse(self, pulse: Pulse):
        self.pulses.add(pulse)

    def has_pulse(self, pulse: Pulse):
        return pulse in self.pulses

    def clear_pulses(self):
        self.pulses.clear()
        
    
    def _apply_on_enter(self):  # called from state machine on enter
        for cmd in self.config.get("on_enter", []):
            self._execute_command(cmd)

    def _apply_on_transition(self, cmds): # called when a transition occured successfully
        for cmd in cmds:
            self._execute_command(cmd)

    def _apply_on_exit(self): # called from state machine on exit
        for cmd in self.config.get("on_exit", []):
            self._execute_command(cmd)

    def _execute_command(self, cmd):
        if "var" in cmd:
            name = cmd["var"]
            op = cmd["op"]
            value = cmd["value"]

            if op == "+=":
                self.variables.add(name, value)
            elif op == "-=":
                self.variables.add(name, -value)
            elif op == "=":
                self.variables.set(name, value)

        elif "set_flag" in cmd:
            self.flags.add(cmd["set_flag"])

        elif "clear_flag" in cmd:
            self.flags.discard(cmd["clear_flag"])


    #unified check
    def _check_condition(self, cond):
        if "flag" in cond:
            return Flag.__members__.get(cond["flag"]) in self.flags

        if "pulse" in cond:
            return Pulse.__members__.get(cond["pulse"]) in self.pulses

        if "var" in cond:
            val = self.variables.get(cond["var"])
            match cond["op"]:
                case "<": return val < cond["value"]
                case ">": return val > cond["value"]
                case "==": return val == cond["value"]
                case "<=": return val <= cond["value"]
                case ">=": return val >= cond["value"]

        return Flag.__members__.get(cond) in self.flags or Pulse.__members__.get(cond) in self.pulses   # THIS makes it so instead of Flag.FLAG_NAME you can just FLAG_NAME


    def handle_events(self):
        # print(f"state_runtime: handling events, {self.flags}, {self.pulses}")

        # --- Checking for forced transitions ---
        for state in self.all_forced_transitions:
            force_trans = self.all_forced_transitions[state]

            # print(self.current_state_name)
            if self.current_state_name in force_trans.get("except_states"):
                # print("this state is an exception")
                break

            conditions = force_trans.get("conditions")
            chance = force_trans.get("chance", 1)

            if all(self._check_condition(c) for c in conditions) and random.random() <= chance:  # all() returns true if all iterable conditions inside are true
                print("-- Forced transition --")

                return (
                    state,  # return the destination state
                    force_trans.get("transition_animation", None),  # may be None
                    force_trans.get("transition_animation_cfg", {})
                )        


        # --- Normal transitions now ---
        transitions = self.config.get("transitions", [])
        # print("handling events: Flags: ", self.flags, " Pulses: ", self.pulses)

        for t in transitions:  # handling all "transitions" in configs
            conditions = t["when"]
            chance = t.get("chance", 1)

            if all(self._check_condition(c) for c in conditions) and random.random() <= chance:  # all() returns true if all iterable conditions inside are true
                # print("chance of this was: ", chance)
                # print("state_runtime detected transition to:", t["to"])
                commands_on_transition = t.get("on_transition", []) # getting commands with variables executed on specific transitions
                self._apply_on_transition(commands_on_transition)
                print("cmds:", commands_on_transition)

                return (
                    t["to"],  # return the destination state
                    t.get("transition_animation", None),  # may be None
                    t.get("transition_animation_cfg", {})
                )
            
        exit_conditions = self.config.get("exit_when")
        if exit_conditions and all(self._check_condition(c) for c in exit_conditions):
            # print("exiting state")
            return(self.config["exit_to"], self.config.get("exit_animation", None), self.config.get("exit_animation_cfg", None))

        return None
