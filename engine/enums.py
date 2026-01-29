# engine/events.py
# Enumerator of all Flags and Pulse possible. Makes it so we can do Flag.MOVEMENT_FINISHED or Pulse.CLICK, for example

from enum import Enum, auto

class Flag(Enum):
    STATE_RANDOM_TIMER_EXPIRED = auto()
    MOVEMENT_FINISHED = auto()
    CLICK_HELD = auto()
    ANIMATION_FINISHED = auto()
    DRAGGING = auto()


class Pulse(Enum):
    ANIMATION_END = auto()
    CLICK = auto()
    LETGO = auto()
    DRAGGING_STARTED = auto()
    DRAGGING_ENDED = auto()

class MovementType(Enum):
    LINEAR = auto()
    ACCELERATE = auto()
    LERP = auto()
    JUMP = auto()
    DRAG = auto() 
    INSTANT = auto()
    STATIONARY = auto()

class EmitterShape(Enum):
    DOT = auto()
    CIRCLE = auto()
    HITBOX = auto()
    RECTANGLE = auto()