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
        

        self.emit_top = self.cfg.get("emit_top", True)
        self.emit_bottom = self.cfg.get("emit_bottom", True)
        self.emit_left = self.cfg.get("emit_left", True)
        self.emit_right = self.cfg.get("emit_right", True)


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

                t = random.uniform(0, 1)
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
                center = self.particleSystem.pet.anchor - self.emitter_offset

                rand_x = random.uniform(0, 1)
                rand_y = random.uniform(0, 1)

                border = Vec2(self.cfg.get("modify_border", (0,0))) # get proportions
                expand = Vec2(self.hitbox.x * -border.x, self.hitbox.y * border.y) # convert to pixel distances

                x = center.x + ((self.hitbox.x - expand.x) * rand_x) - (self.hitbox.x - expand.x)/2
                y = center.y - ((self.hitbox.y + expand.y) * rand_y)

                hollow: bool = self.cfg.get("hollow", False)
                if hollow:
                    pass
                
                pos = Vec2(x, y)

            case EmitterShape.RECTANGLE:

                # weight = min(self.hitbox.x*2, self.hitbox.y) / max(self.hitbox.x*2, self.hitbox.y)
                
                corner1 = self.particleSystem.pet.anchor + Vec2(-self.hitbox.x/2, 0)
                corner2 = self.particleSystem.pet.anchor + Vec2(-self.hitbox.x/2, -self.hitbox.y)
                corner3 = self.particleSystem.pet.anchor + Vec2(+self.hitbox.x/2, -self.hitbox.y)
                corner4 = self.particleSystem.pet.anchor + Vec2(+self.hitbox.x/2, 0)

                sides_list = []

                if self.emit_left:
                    side_left = corner2 - corner1
                    sides_list.append({"vec": side_left, "orig": corner1})
                if self.emit_top:
                    side_top = corner3 - corner2 
                    sides_list.append({"vec": side_top, "orig": corner2})
                if self.emit_right:
                    side_right = corner4 - corner3
                    sides_list.append({"vec": side_right, "orig": corner3})
                if self.emit_bottom:
                    side_bottom = corner1 - corner4
                    sides_list.append({"vec": side_bottom, "orig": corner4})

                line = random.choice(sides_list)
                
                r = random.uniform(0, 1)

                point = line["orig"] + (line["vec"] * r)

                circlage = self.cfg.get("round_square")

                if circlage is None:
                    pos = point
                else:                 # math for circling a square doesnt work because its not a unit circle and not a circle at all
                    xn = x / self.hitbox.x*2
                    yn = y / self.hitbox.y

                    xe = self.hitbox.x * xn * math.sqrt(1 - (yn**2) / 2)
                    ye = self.hitbox.y * yn * math.sqrt(1 - (xn**2) / 2)

                    xr = (1 - r) * x + r * xe
                    yr = (1 - r) * y + r * ye

                    pos = Vec2(xr, yr)


            
        # print("emitting a particle of type ", self.name, " at ", pos)
            
        new_particle = Particle(
                pos=QPointF(pos.x, pos.y),
                vel=QPointF(vel.x, -vel.y),  # vel.y is inverted because upside down
                anim_name=name,
                animations=self.animations,
                start_size=self.start_size
            )
        
        self.particleSystem.emit(new_particle)