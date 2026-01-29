import sys, os, random, time, math
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget, QApplication

from engine.asset_loader import AssetLoader
from engine.enums import EmitterShape

from data.render_config import RENDER_CONFIG
from data.particles import PARTICLES


import ctypes

#data class
class Particle:
    def __init__(self, pos, vel, anim_name, animations):
        self.pos = QPointF(pos)
        self.vel = QPointF(vel)

        self.anim = animations[anim_name]
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
         

#widget drawing particles, fullscreen transparent to clicks
class ParticleOverlayWidget(QWidget):
    def __init__(self):
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

        self.scale = 1

        self.particles = []

         # get all particle animations in a dictionary
        self.animations = {}

        current_folder = os.path.dirname(os.path.abspath(__file__))
        base = os.path.dirname(current_folder)

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


    def start_emitting(particle):
        particle = PARTICLES[particle]
        return

    def emit(self, pos, vel, name="default"):
        if len(self.particles) >= RENDER_CONFIG.get("max_particle_count", 1000):
            return
        
        self.particles.append(
            Particle(
                pos=pos,
                vel=vel,
                anim_name=name,
                animations=self.animations
            )
        )

    #only triggers update_particle for now, maybe will add something later or remove
    def update_logic(self, dt):
        self.update_particles(dt)

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

            print("drawing a particle at", p.pos.x(), p.pos.y())

            painter.restore()

