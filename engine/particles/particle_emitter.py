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

        self.circlage = self.cfg.get("round_square")
        self.circle_radius = self.cfg.get("radius")
        self.hollow: bool = self.cfg.get("hollow", False)
        self.border = self.cfg.get("modify_border", (0,0)) # get proportions
        

        offset = Vec2(cfg.get("emitter_offset", (0, 0)))
        self.emitter_offset = Vec2(self.hitbox.x * -offset.x, self.hitbox.y * offset.y)

        self.type = self.cfg.get("emitter_type", 1)
        self.lifetime = self.cfg.get("lifetime", 1)
        self.rate = self.cfg.get("rate_over_time", 1)
        self.random_timing = self.cfg.get("random_timing", 0)
        self.total_count = self.cfg.get("total_count", 0)
        self.duration = self.cfg.get("duration", 1)  
        self.start_size =  self.cfg.get("start_size", 1)
        self.start_vel = Vec2(self.cfg.get("start_vel", (0, 0)))
        self.start_acceleration = Vec2(self.cfg.get("start_acceleration", (0, 0)))

        # math to determine how many particles to emit
        self.emit_interval = 1.0 / self.rate
        
        self.emit_top = self.cfg.get("emit_top", True)
        self.emit_bottom = self.cfg.get("emit_bottom", True)
        self.emit_left = self.cfg.get("emit_left", True)
        self.emit_right = self.cfg.get("emit_right", True)


    def update(self, dt):
        if self.done:
            return

        if self.random_timing != 0:
            jitter = random.random() * self.emit_interval * self.random_timing
            self.emit_interval += jitter - self.emit_interval/2

        self.time += dt
        self.elapsed += dt

        # print("elapsed", self.elapsed)

        # emitting those particles
        count = int(self.elapsed / self.emit_interval)
        for _ in range(count):
            self.spawn_particle()

        self.elapsed %= self.emit_interval


    def spawn_particle(self):
        # randomize vel, lifetime, etc
        name = self.name
        vel = self.start_vel
        vel.y *= -1
        acceleration = self.start_acceleration
        acceleration.y *= -1

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

                r = self.circle_radius * (self.hitbox.x + self.hitbox.y)/2

                if not self.hollow:
                    r *= math.sqrt(random.random())

                x = center.x + r * math.cos(theta)
                y = center.y + r * math.sin(theta)
                
                pos = Vec2(x, y)
            
            case EmitterShape.HITBOX:
                center = self.particleSystem.pet.anchor - self.emitter_offset

                rand_x = random.random()
                rand_y = random.random()              

                expand_x = self.hitbox.x * -self.border[0]  # convert to pixel distances
                expand_y = self.hitbox.y * self.border[1]

                x = center.x + ((self.hitbox.x - expand_x) * rand_x) - (self.hitbox.x - expand_x)/2
                y = center.y - ((self.hitbox.y + expand_y) * rand_y)

                if self.hollow:
                    pass
                
                pos = Vec2(x, y)

            case EmitterShape.RECTANGLE:

                expand_x = self.hitbox.x * -self.border[0]  # convert to pixel distances
                expand_y = self.hitbox.y * self.border[1] / 2
                
                corner1 = self.particleSystem.pet.anchor + Vec2(-self.hitbox.x/2 -expand_x, +expand_y) - self.emitter_offset
                corner2 = self.particleSystem.pet.anchor + Vec2(-self.hitbox.x/2 -expand_x, -self.hitbox.y -expand_y) - self.emitter_offset
                corner3 = self.particleSystem.pet.anchor + Vec2(+self.hitbox.x/2 +expand_x, -self.hitbox.y -expand_y) - self.emitter_offset
                corner4 = self.particleSystem.pet.anchor + Vec2(+self.hitbox.x/2 +expand_x, +expand_y) - self.emitter_offset

                rec_width: Vec2 = corner3 - corner2 
                rec_height: Vec2 = corner2 - corner1

                sides_list = []

                if self.hollow:
                    if self.emit_left:
                        sides_list.append({"vec": rec_height, "orig": corner1})
                    if self.emit_top:
                        sides_list.append({"vec": rec_width, "orig": corner2})
                    if self.emit_right:
                        sides_list.append({"vec": rec_height, "orig": corner4})
                    if self.emit_bottom:
                        sides_list.append({"vec": rec_width, "orig": corner1})

                    line = random.choice(sides_list)
                    r = random.random()
                    point = line["orig"] + (line["vec"] * r)

                else:
                    point = corner1 + (rec_width * random.random()) + (rec_height * random.random())



                if self.circlage is None:
                    pos = point
                else:                # math for circling a square doesnt work because its not a unit circle and not a circle at all
                    px = point.x
                    py = point.y
                    cx = self.particleSystem.pet.anchor.x  - self.emitter_offset.x 
                    cy = self.particleSystem.pet.anchor.y - rec_height.length()/2  - self.emitter_offset.y
                    width = rec_width.length()
                    height = rec_height.length()

                    # vector to to center
                    x = px - cx
                    y = py - cy

                    a = width / 2
                    b = height / 2

                    # # scale factor along ray
                    # t = 1.0 / math.sqrt((x*x)/(a*a) + (y*y)/(b*b))

                    t_rect = min(
                        (a / abs(x)) if x != 0 else float("inf"),
                        (b / abs(y)) if y != 0 else float("inf")
                    )

                    t_ellipse = 1.0 / math.sqrt((x*x)/(a*a) + (y*y)/(b*b))

                    t_interp = (1 - self.circlage) * t_rect + self.circlage * t_ellipse

                    if not self.hollow and t_interp > 1:
                        xw, yw = point.x, point.y
                    else:
                        # warped point
                        xw = cx + x * t_interp
                        yw = cy + y * t_interp

                    

                    pos = Vec2(xw, yw)

                    # x_interpolated = (1-circlage)*px + circlage*xw
                    # y_interpolated = (1-circlage)*py + circlage*yw

                    # pos = Vec2(x_interpolated, y_interpolated)

            
        new_particle = Particle(
                pos=pos,
                vel=vel,  # vel.y is inverted because upside down
                acceleration=acceleration,
                anim_name=name,
                animations=self.animations,
                start_size=self.start_size
            )
        
        # print("emitting a particle of type ", self.name, " at ", pos)
        self.particleSystem.emit(new_particle)