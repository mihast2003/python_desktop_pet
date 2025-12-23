# engine/events.py
# Enumerator of all Flags and Pulse possible. Makes it so we can do Flag.MOVEMENT_FINISHED or Pulse.CLICK, for example

from enum import Enum, auto

class Flag(Enum):
    STATE_RANDOM_TIMER_EXPIRED = auto()
    MOVEMENT_FINISHED = auto()


class Pulse(Enum):
    ANIMATION_END = auto()
    CLICK = auto()

class BehaviourStates(Enum):
    STATIONARY = auto()
    WANDERING = auto()
    MOVING_RANDOM = auto()
