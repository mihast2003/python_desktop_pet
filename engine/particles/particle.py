import sys, os, random, time, math
from PySide6.QtCore import Qt, QPointF


#data class
class Particle:
    __slots__ = ("size", "frames", "fps", "loop", "animation_finished", "age", "lifetime",
                 "pos_x", "pos_y", 'vel_x', 'vel_y', 'acc_x', 'acc_y', "taskbar")

    def __init__(self, taskbar):
        self.taskbar = taskbar


    def reset(self, size, frames, fps, loop, lifetime,
              pos_x, pos_y, vel_x, vel_y, acc_x, acc_y):
        
        self.size = size

        self.frames = frames
        self.fps = fps
        self.loop = loop
        self.animation_finished: bool = False

        self.age = 0.0
        self.lifetime = lifetime

        self.pos_x=pos_x
        self.pos_y=pos_y
        self.vel_x=vel_x
        self.vel_y=vel_y
        self.acc_x=acc_x
        self.acc_y=acc_y

    def current_frame(self):
        frame_index = int(self.age * self.fps)

        if self.loop:
            frame_index %= len(self.frames)
        else:
            frame_index = min(frame_index, len(self.frames) - 1)
            if frame_index >= len(self.frames)-1:
                self.animation_finished = True

        return self.frames[frame_index]
    
