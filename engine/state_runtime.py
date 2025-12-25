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
        
    #unified check
    def has_event(self, event):

        # print("checking if ", event, " is in Flags: ", self.flags, " or Pulses: ", self.pulses)
        
        # if Flag.__members__.get(event) in self.flags or Pulse.__members__.get(event) in self.pulses:
        #     print("yes it has")
        # else: print("fuck no")

        return Flag.__members__.get(event) in self.flags or Pulse.__members__.get(event) in self.pulses
    
    def _check_condition(self, cond):
        if "flag" in cond:
            return cond["flag"] in self.flags

        if "pulse" in cond:
            return cond["pulse"] in self.pulses

        if "var" in cond:
            val = self.variables.get(cond["var"])
            match cond["op"]:
                case "<": return val < cond["value"]
                case ">": return val > cond["value"]
                case "==": return val == cond["value"]
                case "<=": return val <= cond["value"]
                case ">=": return val >= cond["value"]

        return False


    def handle_events(self):
        transitions = self.config.get("transitions", [])

        # print("handling events: Flags: ", self.flags, " Pulses: ", self.pulses)

        for t in transitions:  # handling all "transitions" in configs
            conditions = t["when"]

            chance = t.get("chance", 1)
            
            if all(self._check_condition(c) for c in conditions) and random.random() <= chance:  # all() returns true if all iterable conditions inside are true
                print(t["to"])
                return t["to"]   # return the destination state
            
        exit_conditions = self.config.get("exit_when")
        if exit_conditions and all(self.has_event(event) for event in exit_conditions):
            print("exiting state")
            return self.config["exit_to"]

        return None
