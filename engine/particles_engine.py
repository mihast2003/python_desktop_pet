import sys, os, random, time, math
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget, QApplication

from engine.asset_loader import AssetLoader

from data.render_config import RENDER_CONFIG
from data.particles import PARTICLES


import ctypes

#data class
class Particle:
    def __init__(self, pos, vel, lifetime, radius, color):
        self.pos = QPointF(pos)
        self.vel = QPointF(vel)
        self.lifetime = lifetime
        self.age = 0.0
        self.radius = radius
        self.color = QColor(color)

    def update(self, dt):
        self.age += dt
        self.pos += self.vel * dt

    def alive(self):
        return self.age < self.lifetime
         

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


    def emit(self, pos, vel, lifetime=0.5, radius=3, color=Qt.white):
        if len(self.particles) >= RENDER_CONFIG.get("max_particle_count", 1000):   #dont emit new particles if particle count is more than max
            return 

        self.particles.append(
            Particle(pos, vel, lifetime, radius, color)
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

        painter.save()
        for p in self.particles:
            painter.setBrush(p.color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(p.pos, p.radius, p.radius)
        painter.restore()
