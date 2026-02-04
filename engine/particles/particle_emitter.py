import sys, os, random, time, math
from PySide6.QtCore import Qt, QPointF

from engine.vec2 import Vec2
from engine.particles.particle import Particle

from engine.enums import EmitterShape

class ParticleEmitter:
    def __init__(self, particleSystem, name, cfg, animations, shape):
        self.name = name
        self.cfg = cfg
        self.animations = animations

        self.particleSystem = particleSystem

        self.time = 0.0
        self.emitted = 0
        self.elapsed = 0
        self.done = False

        self.type = self.cfg.get("emitter_type", 1)
        self.lifetime = self.cfg.get("lifetime", 1)
        self.emitter_shape = shape
        self.rate = self.cfg.get("rate_over_time", 0)
        self.count = self.cfg.get("total_count", 0)
        self.duration = self.cfg.get("duration", 1)   
        

    def update(self, dt):
        if self.done:
            return

        # math to determine how many particles to emit
        emit_interval = 1.0 / self.rate

        self.time += dt
        self.elapsed += dt

        # print("elapsed", self.elapsed)

        # emitting those particles
        while self.elapsed >= emit_interval:
            print("emitting a particle of type ", self.name)
            self.spawn_particle()
            self.emitted += 1
            self.elapsed -= emit_interval        


        if self.emitted >= self.count and self.rate != 0 or self.time >= self.duration:
            self.done = True

    def spawn_particle(self):
        # randomize vel, lifetime, etc
        name = self.name
        values = self.cfg.get("start_vel", (0, 0))
        if len(values) != 2:
            raise Exception("VELOCITY OF PARTICLE ", name, " IS NOT TWO VALUES")  #no idea what this does will add user notification that error occured 
        vel = Vec2(values[0], values[1])

        match self.emitter_shape:
            case EmitterShape.DOT:
                pos = Vec2(self.particleSystem.pet.anchor_x, self.particleSystem.pet.anchor_y)
            case EmitterShape.CIRCLE:
                return
            case EmitterShape.HITBOX:
                return
            case EmitterShape.RECTANGLE:
                return
            
        new_particle = Particle(
                pos=QPointF(pos.x, pos.y),
                vel=QPointF(vel.x, vel.y),
                anim_name=name,
                animations=self.animations
            )
        self.particleSystem.emit(new_particle)