import sys, os, random, time, math
from PySide6.QtCore import Qt, QPointF
from engine.vec2 import Vec2


#data class
class Particle:
    __slots__ = ("pos_x", "pos_y", "vel_x", "vel_y", "acc_x", "acc_y", "name", "anim", "size", "frames", "fps", "loop", "animation_finished", "age", "lifetime", "frame_index")
    def __init__(self, pos, vel, acceleration, anim_name, animations, start_size):

        self.pos_x = pos.x
        self.pos_y = pos.y
        self.vel_x = vel.x
        self.vel_y = vel.y
        self.acc_x = acceleration.x
        self.acc_y = acceleration.y

        self.name = anim_name
        self.anim = animations
        self.size = start_size

        self.frames = self.anim["frames"]
        self.fps = self.anim["fps"]
        self.loop = self.anim["loop"]
        self.animation_finished: bool = False

        self.age = 0.0
        self.lifetime = len(self.frames) / self.fps if not self.loop else float("inf")

    # updating position and velicity in particles engine should be faster
    # def update(self, dt):
    #     self.age += dt
        # self.pos += self.vel * dt
        # self.vel += self.acceleration * dt

    def alive(self):
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
    
