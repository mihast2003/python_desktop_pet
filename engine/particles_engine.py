import sys, os, random, time, math
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget, QApplication, QLabel

from engine.asset_loader import AssetLoader
from engine.enums import EmitterShape
from engine.vec2 import Vec2

from data.render_config import RENDER_CONFIG
from data.particles import PARTICLES

from collections import defaultdict

import ctypes

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

        self.shape = EmitterShape.DOT

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
        
        to_emit = 0

        # math to determine how many particles to emit
        emit_interval = 1.0 / self.rate

        self.time += dt
        self.elapsed += dt

        print("elapsed", self.elapsed)

        # emitting those particles
        while self.elapsed >= emit_interval:
            print("should spawn", to_emit, " particles")
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



#widget drawing particles, fullscreen transparent to clicks
class ParticleOverlayWidget(QWidget):
    def __init__(self, pet):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # Make window fully windows click-through
        hwnd = int(self.winId())
        extended_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, extended_style | 0x80000 | 0x20)

        self.show()

        self.pet = pet

        self.scale = 1

        self.emitters = []
        self.particles = []

        # get all particle animations in a dictionary
        self.animations = {}

        current_folder = os.path.dirname(os.path.abspath(__file__))
        base = os.path.dirname(current_folder)

        print("----- LOADING PARTICLES -----")

        for name in list(PARTICLES):
            cfg = PARTICLES[name]
            folder = os.path.join(base, cfg["folder"])

            frames = []

            frames = AssetLoader.load_frames(folder=folder)

            if not frames:
                raise RuntimeError(f"No frames found for animation '{name}'")

            self.animations[name] = {
                "frames": frames,
                "fps": cfg["fps"],
                "loop": cfg["loop"],
                "holds": cfg.get("holds", {}),
                "times_to_loop": cfg.get("times_to_loop", 1)
            }
            print(f"[PARTICLES LOADED] {name}: {len(frames)} frames")

    def update_dpi_and_scale(self, new_scale):
        self.scale = new_scale


    def start_emitting(self, name):
        cfg = PARTICLES.get(name)

        if not cfg:
            print("No particle named ", name, " found")
            raise Exception("PARTICLE", name, "NOT FOUND")  #no idea what this does will add user notification that error occured

        shape = cfg.get("emitter_shape")
        emitter_shape = EmitterShape.__members__.get(shape, EmitterShape.DOT)
    
        print("adding emitter", name)

        self.emitters.append(
            ParticleEmitter(particleSystem=self, name=name, cfg=cfg, animations=self.animations[name], shape=emitter_shape)
        )    


    def emit(self, new_particle):
        if len(self.particles) >= RENDER_CONFIG.get("max_particle_count", 100):
            return
        
        self.particles.append(new_particle)



    #only triggers update_particle for now, maybe will add something later or remove
    def update_logic(self, dt):

        for emitter in self.emitters:
            emitter.update(dt) # updating all emitters

        self.emitters = [e for e in self.emitters if not e.done] #pruning emitters

        self.update_particles(dt) # updating particles

        # -- DEBUGGING TEXT --
        self.emitters_by_type = defaultdict(int)
        self.particles_by_type = defaultdict(int)

        for emitter in self.emitters:
            self.emitters_by_type[emitter.name] += 1
        
        for p in self.particles:
            self.particles_by_type[p.name] += 1


    # updates particle lifetime and deletes those who expired
    def update_particles(self, dt):

        for p in self.particles:
            p.update(dt)

        self.particles = [p for p in self.particles if p.alive()]

    def draw(self):
        self.update()  # triggers paintEvent

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        painter.save()

        # painter.scale(self.scale, self.scale)

        for p in self.particles:
            frame = p.current_frame()
            if not frame:
                continue

            # draw sprite so its middle is at given possition
            true_pos_x = p.pos.x() / self.scale
            true_pos_y = p.pos.y() / self.scale

            offset_x = frame.width() / 2
            offset_y = frame.height() / 2

            corner_x = true_pos_x - offset_x
            corner_y = true_pos_y - offset_y

            painter.save()

            painter.scale(self.scale, self.scale)

            painter.drawPixmap(corner_x, corner_y, frame)

            # painter.setPen(QPen(Qt.red, 3))
            # painter.drawEllipse(true_pos_x, true_pos_y, 50, 50)

            # print("drawing a particle at", p.pos.x(), p.pos.y())

            painter.restore()

            # --- DEBUG TEXT ---
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Consolas", 10))

            lines = []

            for type_name, emitter_count in self.emitters_by_type.items():
                particle_count = self.particles_by_type.get(type_name, 0)

                lines.append(
                    f'{emitter_count} emitters of type "{type_name}" – {particle_count} particles'
                )

            debug_text = "\n".join(lines)

            painter.drawText(10, 20, debug_text)

