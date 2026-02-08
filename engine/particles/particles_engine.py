import sys, os, random, time, math
from PySide6.QtCore import Qt, QPointF, QRect
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget, QApplication, QLabel

from engine.asset_loader import AssetLoader
from engine.enums import EmitterShape
from engine.vec2 import Vec2

from engine.particles.particle_emitter import ParticleEmitter
from engine.particles.particle import Particle

from data.render_config import RENDER_CONFIG
from data.particles import PARTICLES

from collections import defaultdict

import ctypes
         

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

        self.pet = pet
        taskbar = self.pet.taskbar_top

        self.scale = 1

        self.emitters = []

        MAX_PARTICLES = RENDER_CONFIG.get("max_particle_count", 1000)

        self.active_particles = []
        self.free_particles = [Particle(taskbar=taskbar) for _ in range(MAX_PARTICLES)]

        self.show()

        # get all particle animations in a dictionary
        self.animations = {}

        current_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # we go back three folders
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

    def update_hitbox(self, hitbox_width, hitbox_height):
        self.pet_hitbox_w = hitbox_width
        self.pet_hitbox_h = hitbox_height

    def update_taskbar_position(self, taskbar):
        self.taskbar = taskbar

    def start_emitting(self, name):
        cfg = PARTICLES.get(name)

        if not cfg:
            print("No particle named ", name, " found")
            raise Exception("PARTICLE", name, "NOT FOUND")  #no idea what this does will add user notification that error occured

        print("adding emitter", name)

        self.emitters.append(
            ParticleEmitter(particleSystem=self, name=name, cfg=cfg, animations=self.animations[name], hitbox_width=self.pet_hitbox_w, hitbox_height=self.pet_hitbox_h)
        )    


    def emit(self, *, pos_x, pos_y, vel_x, vel_y, acc_x, acc_y, lifetime, frames, fps, loop, size):
        if not self.free_particles:
            return

        p = self.free_particles.pop()

        p.reset(size=size, frames=frames, fps=fps, loop=loop, lifetime=lifetime,
                pos_x=pos_x, pos_y=pos_y, vel_x=vel_x, vel_y=vel_y, acc_x=acc_x, acc_y=acc_y)

        self.active_particles.append(p)


    def update_logic(self, dt):

        # --- EMITTERS ---

        for emitter in self.emitters:
            emitter.update(dt) # updating all emitters

        self.emitters = [e for e in self.emitters if not e.done] #pruning emitters

        # --- PARTICLES ---

        i = 0
        while i < len(self.active_particles):
            p: Particle = self.active_particles[i]

            p.age += dt

            p.pos_x += p.vel_x * dt
            p.pos_y += p.vel_y * dt
            p.vel_x += p.acc_x * dt
            p.vel_y += p.acc_y * dt

            if(p.pos_y > self.taskbar) and ((p.loop and p.age > p.lifetime) or (not p.loop and p.animation_finished)):
                # recycle particle object
                self.free_particles.append(p)

                # swap-remove particle
                self.active_particles[i] = self.active_particles[-1]
                self.active_particles.pop()
            else:
                i += 1
        
        # -- DEBUGGING TEXT --
        self.emitters_by_type = defaultdict(int)
        self.particles_by_type = defaultdict(int)

        for emitter in self.emitters:
            self.emitters_by_type[emitter.name] += 1
            self.particles_by_type[emitter.name] += emitter.emitted  # doesnt work i dunno why maybe remove


    # --- DRAWING ---

    def draw(self):
        self.update()  # triggers paintEvent

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        painter.save()

        # painter.scale(self.scale, self.scale)

        for p in self.active_particles:
            frame = p.current_frame()

            if not frame:
                continue

            # draw sprite so its middle is at given possition
            true_pos_x = p.pos_x / self.scale
            true_pos_y = p.pos_y / self.scale

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

            lines.append(
                f' \n {len(self.active_particles)} active particles, {len(self.free_particles)} free particles'
            )

            debug_text = "\n".join(lines)

            rect = QRect(10, 20, 300, 200)
            painter.drawText(rect, Qt.AlignLeft | Qt.AlignTop, debug_text)

