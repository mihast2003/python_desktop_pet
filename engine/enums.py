# engine/events.py
# Enumerator of all Flags and Pulse possible. Makes it so we can do Flag.MOVEMENT_FINISHED or Pulse.CLICK, for example

from enum import Enum, auto

class Flag(Enum):
    STATE_RANDOM_TIMER_EXPIRED = auto()
    MOVEMENT_FINISHED = auto()
    CLICK_HELD = auto()
    ANIMATION_FINISHED = auto()
    DRAGGING = auto()
    PARENTED_TO_WINDOW = auto()
    NOT_PARENTED_TO_WINDOW = auto()

class Pulse(Enum):
    ANIMATION_END = auto()
    CLICK = auto()
    LETGO = auto()
    DRAGGING_STARTED = auto()
    DRAGGING_ENDED = auto()
    LOST_PARENT = auto()
    GAINED_PARENT = auto()

class MovementType(Enum):
    LINEAR = auto()
    ACCELERATION = auto()
    LERP = auto()
    JUMP = auto()
    DRAG = auto() 
    INSTANT = auto()
    STATIONARY = auto()

class Facing(Enum):
    LEFT = auto()
    RIGHT = auto()

class SurfaceType(Enum):
    LEFT = auto()
    TOP = auto()
    RIGHT = auto()
    BOTTOM = auto()

class EmitterType(Enum):
    BURST = auto()
    CONTINUOUS = auto()


class EmitterShape(Enum):
    DOT = auto()
    LINE = auto()
    CIRCLE = auto()
    HITBOX = auto()
    RECTANGLE = auto()
