import sys, os, random, time, math
from PySide6.QtCore import Qt, QPointF

from engine.vec2 import Vec2
from engine.particles.particle import Particle

from engine.enums import EmitterShape

class ParticleEmitter:
    def __init__(self, particleSystem, name, cfg, animations, hitbox_width, hitbox_height):

        self.particleSystem = particleSystem

        self.name = name
        self.cfg = cfg
        self.anim = animations

        self.hitbox_x = hitbox_width 
        self.hitbox_y = hitbox_height

        self.time = 0.0
        self.emitted = 0
        self.elapsed = 0
        self.done = False

        shape = cfg.get("emitter_shape")
        self.emitter_shape = EmitterShape.__members__.get(shape, EmitterShape.DOT)

        offset_x, offset_y = cfg.get("emitter_offset", (0, 0))
        self.emitter_offset_x = self.hitbox_x * -offset_x
        self.emitter_offset_y = self.hitbox_y * offset_y

        self.type = self.cfg.get("emitter_type", 1)
        self.lifetime = self.cfg.get("lifetime", 1)
        self.rate = self.cfg.get("rate_over_time", 1)
        self.random_timing = self.cfg.get("random_timing", 0)
        self.total_count = self.cfg.get("total_count", 0)
        self.duration = self.cfg.get("duration", 1)  
        self.start_size =  self.cfg.get("start_size", 1)
        self.radius = self.cfg.get("radius", 1)
        self.hollow: bool = self.cfg.get("hollow", False)
        self.border = Vec2(self.cfg.get("modify_border", (0,0))) # get proportions
        print("border is", self.border.x)
        self.expand: Vec2 = Vec2(self.hitbox_x * self.border.x, self.hitbox_y * self.border.y / 2) # convert to pixel distances
        print("expand is", self.expand.x)
        self.circlage = self.cfg.get("round_square")

        self.start_vel = self.cfg.get("start_vel", (0, 0))
        self.start_acc = self.cfg.get("start_acceleration", (0, 0))
        
        self.emit_top = self.cfg.get("emit_top", True)
        self.emit_bottom = self.cfg.get("emit_bottom", True)
        self.emit_left = self.cfg.get("emit_left", True)
        self.emit_right = self.cfg.get("emit_right", True)

        #for particles directly
        self.frames = self.anim["frames"]
        self.fps = self.anim["fps"]
        self.loop = self.anim.get("loop", False)
        self.lifetime = len(self.frames) / self.fps if not self.loop else float("inf")


    def update(self, dt):
        if self.done:
            return

        # math to determine how many particles to emit
        emit_interval = 1.0 / self.rate

        if self.random_timing != 0:
            jitter = random.random() * emit_interval * self.random_timing
            emit_interval += jitter - emit_interval/2


        self.time += dt
        self.elapsed += dt

        # print("elapsed", self.elapsed)

        # emitting those particles
        count = int(self.elapsed / emit_interval)
        for _ in range(count):
            self.spawn_particle()

        self.elapsed %= emit_interval


        if self.emitted >= self.total_count or self.time >= self.duration:
            self.done = True
            print("done")

    def spawn_particle(self):
        # randomize vel, lifetime, etc
        anchor_x, anchor_y = self.particleSystem.pet.anchor

        pos_x: float
        pos_y: float

        vel = (self.start_vel[0], -self.start_vel[1])

        acceleration = (self.start_acc[0], -self.start_acc[1])

        hollow = self.hollow
        circlage = self.circlage
        expand = self.expand

        # print("shape", self.emitter_shape)

        match self.emitter_shape:
            case EmitterShape.DOT:
                pos_x = anchor_x - self.emitter_offset_x
                pos_y = anchor_y - self.emitter_offset_y
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

                pos_x = anchor_x - (-x) * self.hitbox_x
                pos_y = anchor_y - y * self.hitbox_y

            case EmitterShape.CIRCLE:
                theta = random.uniform(0, 2 * math.pi) # Random angle 0-2π

                center_x = anchor_x - self.emitter_offset_x
                center_y = anchor_y - self.emitter_offset_y

                r = self.radius * (self.hitbox_x + self.hitbox_y)/2

                if not hollow:
                    r *= math.sqrt(random.random())

                pos_x = center_x + r * math.cos(theta)
                pos_y = center_y + r * math.sin(theta)
            
            case EmitterShape.HITBOX:
                center = self.particleSystem.pet.anchor - self.emitter_offset

                rand_x = random.random()
                rand_y = random.random()

                border = Vec2(self.cfg.get("modify_border", (0,0))) # get proportions
                expand = Vec2(self.hitbox.x * -border.x, self.hitbox.y * border.y) # convert to pixel distances

                x = center.x + ((self.hitbox.x - expand.x) * rand_x) - (self.hitbox.x - expand.x)/2
                y = center.y - ((self.hitbox.y + expand.y) * rand_y)

                hollow: bool = self.cfg.get("hollow", False)
                if hollow:
                    pass
                
                pos_x = x
                pos_y = y

            case EmitterShape.RECTANGLE:
                # corner1 = self.particleSystem.pet.anchor + Vec2(-self.hitbox_x/2 -expand.x, +expand.y) - self.emitter_offset
                corner1 = Vec2(anchor_x - self.hitbox_x/2 - expand.x - self.emitter_offset_x, anchor_y + expand.y - self.emitter_offset_y)

                self.emitter_offset = Vec2(self.emitter_offset_x, self.emitter_offset_y)
                anchor = Vec2(anchor_x, anchor_y)

                corner2 = anchor + Vec2(-self.hitbox_x/2 -expand.x, -self.hitbox_y -expand.y) - self.emitter_offset
                corner3 = anchor + Vec2(+self.hitbox_x/2 +expand.x, -self.hitbox_y -expand.y) - self.emitter_offset
                corner4 = anchor + Vec2(+self.hitbox_x/2 +expand.x, +expand.y) - self.emitter_offset

                rec_width: Vec2 = corner3 - corner2 
                rec_height: Vec2 = corner2 - corner1

                sides_list = []

                if hollow:
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


                if circlage is None:
                    pos = point
                else:                # math for circling a square doesnt work because its not a unit circle and not a circle at all
                    px = point.x
                    py = point.y
                    cx = self.particleSystem.pet.anchor.x  - self.emitter_offset_x 
                    cy = self.particleSystem.pet.anchor.y - rec_height.length()/2  - self.emitter_offset_y
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

                    t_interp = (1 - circlage) * t_rect + circlage * t_ellipse

                    if not hollow and t_interp > 1:
                        xw, yw = point.x, point.y
                    else:
                        # warped point
                        xw = cx + x * t_interp
                        yw = cy + y * t_interp

                    
                    pos_x = xw
                    pos_y = yw

        # pos_x, pos_y = pos
        vel_x, vel_y = vel
        acc_x, acc_y = acceleration

        self.particleSystem.emit(
            name=self.name,
            pos_x=pos_x,
            pos_y=pos_y,
            vel_x=vel_x,
            vel_y=vel_y,
            acc_x=acc_x,
            acc_y=acc_y,
            lifetime=self.lifetime,
            frames=self.frames,
            fps=self.fps,
            loop=self.loop,
            size=self.start_size
        )