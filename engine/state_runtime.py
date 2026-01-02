# engine/state_runtime.py
# handles Events

import random
from engine.enums import Flag, Pulse

class StateRuntime:
    def __init__(self, state_name, config, variables):
        self.name = state_name
        self.config = config
        self.variables = variables

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
        
    
    def _apply_on_enter(self):
        for cmd in self.config.get("on_enter", []):
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

        return Flag.__members__.get(cond) in self.flags or Pulse.__members__.get(cond) in self.pulses   # THIS IS WEIRD I WANNA TRY A BACKUP SYNTAX


    def handle_events(self):
        transitions = self.config.get("transitions", [])

        print("handling events: Flags: ", self.flags, " Pulses: ", self.pulses)

        for t in transitions:  # handling all "transitions" in configs
            conditions = t["when"]
            chance = t.get("chance", 1)

            
            if all(self._check_condition(c) for c in conditions) and random.random() <= chance:  # all() returns true if all iterable conditions inside are true
                # print("chance of this was: ", chance)
                # print("state_runtime detected transition to:", t["to"])
                return (
                    t["to"],  # return the destination state
                    t.get("transition_anim", None),  # may be None
                    t.get("transition_anim_cfg", {})
                )
            
        exit_conditions = self.config.get("exit_when")
        if exit_conditions and all(self._check_condition(c) for c in exit_conditions):
            # print("exiting state")
            return(self.config["exit_to"], self.config.get("exit_animation", None), self.config.get("exit_animation_cfg", None))

        return None
