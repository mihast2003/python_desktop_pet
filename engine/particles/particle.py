import sys, os, random, time, math
from PySide6.QtCore import Qt, QPointF
from engine.vec2 import Vec2


#data class
class Particle:
    __slots__ = ("idx", "name", "size", "frames", "fps", "loop", "animation_finished", "age", "lifetime", "alive_flag")

    def __init__(self):
        self.alive_flag = False

        self.idx = -1

    def reset(self, idx, name, size, frames, fps, loop, lifetime):
        self.idx = idx

        self.name = name
        self.size = size

        self.frames = frames
        self.fps = fps
        self.loop = loop
        self.animation_finished: bool = False

        self.age = 0.0
        self.lifetime = lifetime
        self.alive_flag = True

    def alive(self):
        if not self.alive_flag:
            return False
        
        if self.loop:
            return self.age < self.lifetime
        else:
            return not self.animation_finished

    def current_frame(self):
        frame_index = int(self.age * self.fps)

        if self.loop:
            frame_index %= len(self.frames)
        else:
            frame_index = min(frame_index, len(self.frames) - 1)
            if frame_index >= len(self.frames)-1:
                self.animation_finished = True

        return self.frames[frame_index]
    
