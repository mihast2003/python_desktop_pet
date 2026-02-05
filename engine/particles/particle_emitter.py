import sys, os, random, time, math
from PySide6.QtCore import Qt, QPointF

from engine.vec2 import Vec2
from engine.particles.particle import Particle

from engine.enums import EmitterShape

class ParticleEmitter:
    def __init__(self, particleSystem, name, cfg, animations, hitbox):

        self.particleSystem = particleSystem

        self.name = name
        self.cfg = cfg
        self.animations = animations

        self.hitbox = hitbox

        self.time = 0.0
        self.emitted = 0
        self.elapsed = 0
        self.done = False

        shape = cfg.get("emitter_shape")
        self.emitter_shape = EmitterShape.__members__.get(shape, EmitterShape.DOT)

        offset = Vec2(cfg.get("emitter_offset", (0, 0)))
        self.emitter_offset = Vec2(self.hitbox.x * -offset.x, self.hitbox.y * offset.y)

        self.type = self.cfg.get("emitter_type", 1)
        self.lifetime = self.cfg.get("lifetime", 1)
        self.rate = self.cfg.get("rate_over_time", 1)
        self.total_count = self.cfg.get("total_count", 0)
        self.duration = self.cfg.get("duration", 1)  
        self.start_size =  self.cfg.get("start_size", 1)
        

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
            self.spawn_particle()
            self.emitted += 1
            self.elapsed -= emit_interval        


        if self.emitted >= self.total_count and self.rate != 0 or self.time >= self.duration:
            self.done = True

    def spawn_particle(self):
        # randomize vel, lifetime, etc
        name = self.name
        values = self.cfg.get("start_vel", (0, 0))

        if len(values) != 2:
            raise Exception("VELOCITY OF PARTICLE ", name, " IS NOT TWO VALUES")  #no idea what this does will add user notification that error occured 
        vel = Vec2(values)

        # print("shape", self.emitter_shape)

        match self.emitter_shape:
            case EmitterShape.DOT:
                pos = self.particleSystem.pet.anchor - self.emitter_offset
            case EmitterShape.LINE:
                point1 = Vec2(self.cfg.get("point1"))
                point2 = Vec2(self.cfg.get("point2"))
                if not point1 and not point2:
                    print("NO POINTS TO FORM A LINE, CHECK CONFIG")

                t = random.random()
                x1, y1 = point1
                x2, y2 = point2

                x = x1 + t * (x2 - x1)
                y = y1 + t * (y2 - y1)

                pos = self.particleSystem.pet.anchor - (Vec2(-x, y) * self.hitbox)

            case EmitterShape.CIRCLE:
                theta = random.uniform(0, 2 * math.pi) # Random angle 0-2π

                center = self.particleSystem.pet.anchor - self.emitter_offset

                r = self.cfg.get("radius") * (self.hitbox.x + self.hitbox.y)/2

                hollow: bool = self.cfg.get("hollow", False)
                if not hollow:
                    r *= math.sqrt(random.uniform(0, 1))

                x = center.x + r * math.cos(theta)
                y = center.y + r * math.sin(theta)
                
                pos = Vec2(x, y)
            
            case EmitterShape.HITBOX:
                return
            case EmitterShape.RECTANGLE:
                return
            
        # print("emitting a particle of type ", self.name, " at ", pos)
            
        new_particle = Particle(
                pos=QPointF(pos.x, pos.y),
                vel=QPointF(vel.x, -vel.y),  # vel.y is inverted because upside down
                anim_name=name,
                animations=self.animations,
                start_size=self.start_size
            )
        
        self.particleSystem.emit(new_particle)