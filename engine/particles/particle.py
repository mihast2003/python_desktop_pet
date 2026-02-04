import sys, os, random, time, math
from PySide6.QtCore import Qt, QPointF


#data class
class Particle:
    def __init__(self, pos, vel, anim_name, animations):
        self.pos = QPointF(pos)
        self.vel = QPointF(vel)

        self.name = anim_name
        self.anim = animations
        self.frames = self.anim["frames"]
        self.fps = self.anim["fps"]
        self.loop = self.anim["loop"]


        self.age = 0.0
        self.lifetime = len(self.frames) / self.fps if not self.loop else float("inf")

    def update(self, dt):
        self.age += dt
        self.pos += self.vel * dt

    def alive(self):
        return self.loop or self.age < self.lifetime

    def current_frame(self):
        frame_index = int(self.age * self.fps)

        if self.loop:
            frame_index %= len(self.frames)
        else:
            frame_index = min(frame_index, len(self.frames) - 1)

        return self.frames[frame_index]