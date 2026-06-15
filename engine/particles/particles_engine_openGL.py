import sys, os, random, time, math
from PySide6.QtCore import Qt, QPointF, QRect
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget, QApplication, QLabel
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from engine.asset_loader import AssetLoader
from engine.enums import EmitterShape
from engine.vec2 import Vec2

from engine.particles.particle_emitter import ParticleEmitter
from engine.particles.particle import Particle

from OpenGL.GL import * #type: ignore

from data.render_config import RENDER_CONFIG
from data.particles import PARTICLES

from collections import defaultdict

import numpy as np
from numba import njit

import ctypes


def get_frame_index(anim, age):
    """
    Given a particle's total frame count and current age, returns the frame_index for the current frame.
    
    :param anim: taken from self.animations dist, contains information about a particle type.
    :param age: age of particle.
    """
    frame_index = int(age * anim["fps"])

    if anim["loop"]:
        frame_index %= len(anim["frames"])
    else:
        frame_index = min(frame_index, len(anim["frames"]) - 1)

    return frame_index


#widget drawing particles, fullscreen transparent to clicks
class ParticleOverlayWidget(QOpenGLWidget):
    def __init__(self, pet):
        super().__init__()

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.setWindowFlags(
            Qt.FramelessWindowHint | #type: ignore
            Qt.WindowStaysOnTopHint | #type: ignore
            Qt.Tool #type: ignore
        )

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # Make window fully windows click-through
        hwnd = int(self.winId())
        extended_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, extended_style | 0x80000 | 0x20)

        # Create dummy data with FINAL types
        dummy_positions = np.zeros(1000, dtype=np.float32)
        dummy_vels = np.zeros(1000, dtype=np.float32)
        dummy_id = np.zeros(1000, dtype=np.int16)
        dummy_alive = np.zeros(1000, dtype=np.bool)
        dt = np.float32(0.016)

        update_particles(dt, np.uint32(1000), dummy_positions, dummy_positions, dummy_vels, dummy_vels, dummy_vels, dummy_vels, dummy_positions, dummy_id, dummy_alive, np.float32(1351))

        self.pet = pet
        self.taskbar_top = self.pet.taskbar_top

        self.debug_counter = 0 # for debugging

        self.scale = 1

        self.emitters = []

        self.emitters_by_type = defaultdict(int)
        self.particles_by_type = defaultdict(int)

        self.MAX_PARTICLES = RENDER_CONFIG.get("max_particle_count", 1000)
        MAX_PARTICLES = self.MAX_PARTICLES

        self.count = np.uint32(0)  # active particle count

        # ---- ARRAYS (SoA) ----
        self.pos_x = np.zeros(MAX_PARTICLES, dtype=np.float32)
        self.pos_y = np.zeros(MAX_PARTICLES, dtype=np.float32)

        self.vel_x = np.zeros(MAX_PARTICLES, dtype=np.float32)
        self.vel_y = np.zeros(MAX_PARTICLES, dtype=np.float32)

        self.acc_x = np.zeros(MAX_PARTICLES, dtype=np.float32)
        self.acc_y = np.zeros(MAX_PARTICLES, dtype=np.float32)

        self.age = np.zeros(MAX_PARTICLES, dtype=np.float32)

        self.size_p = np.zeros(MAX_PARTICLES, dtype=np.float32)

        self.alive = np.zeros(MAX_PARTICLES, dtype=bool)

        self.type_id = np.zeros(MAX_PARTICLES, dtype=np.int16)

        self.anim_lifetimes_by_id = np.zeros(len(PARTICLES), dtype=np.float32)

        self.show()

        # get all particle animations in a dictionary
        self.animations = {}

        #for references
        self.anim_name_to_id = {}

        current_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # we go back three folders
        base = os.path.dirname(current_folder)

        print("----- LOADING PARTICLES -----")

        for name in list(PARTICLES):
            cfg = PARTICLES[name]
            folder = os.path.join(base, cfg["folder"])

            frames = []

            frames = AssetLoader.load_QPixmap_frames(folder=folder)

            if not frames:
                raise RuntimeError(f"No frames found for animation '{name}'")
            
            #registring animations for reference by id
            anim_id = len(self.animations) # starts with 0 and goes up as we add animations
            self.anim_name_to_id[name] = anim_id

            # precompute lifetime once
            lifetime = (
                len(frames) / cfg["fps"]
                if not cfg["loop"]
                else 1e9)  # effectively infinite
            
            #store lifetime for each particle type by id
            self.anim_lifetimes_by_id[anim_id] = lifetime
            
            self.animations[anim_id] = { # we enter them by id to then reference by id
                "frames": frames,
                "fps": cfg["fps"],
                "loop": cfg["loop"],
                "holds": cfg.get("holds", {}), # holds are not implemented yet
                "times_to_loop": cfg.get("times_to_loop", 1),
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

        # print("adding emitter", name)

        self.emitters.append(ParticleEmitter(particleSystem=self, name=name, cfg=cfg, hitbox_width=self.pet_hitbox_w, hitbox_height=self.pet_hitbox_h))    


    def emit_particle(self, *, pos_x, pos_y, vel_x, vel_y, acc_x, acc_y, name, size):
        if self.count >= self.MAX_PARTICLES:
            return
        
        anim_id = self.anim_name_to_id[name]
        
        i = self.count

        self.pos_x[i] = pos_x
        self.pos_y[i] = pos_y

        self.vel_x[i] = vel_x
        self.vel_y[i] = vel_y

        self.acc_x[i] = acc_x
        self.acc_y[i] = acc_y

        self.age[i] = 0.0
        self.type_id[i] = anim_id
        self.alive[i] = 1

        self.size_p[i] = size

        self.count += 1


    def update_logic(self, dt):
        t0 = time.perf_counter()

        # --- EMITTERS ---
        for emitter in self.emitters:
            emitter.update(dt) # updating all emitters

        self.emitters = [e for e in self.emitters if not e.done_emitting] #pruning emitters

        # --- PARTICLES ---
        # print("self count is ", self.count) # printing particle count

        i = 0
        while i < self.count:
            if self.age[i] >= self.anim_lifetimes_by_id[self.type_id[i]]:
                self.alive[i] = 0
            i += 1

        self.count = update_particles(
            np.float32(dt),
            self.count,
            self.pos_x, self.pos_y,
            self.vel_x, self.vel_y,
            self.acc_x, self.acc_y,
            self.age, self.type_id,
            self.alive,
            np.float32(self.taskbar_top))
        
        # -- DEBUGGING TEXT --
        self.emitters_by_type = defaultdict(int)
        self.particles_by_type = defaultdict(int)

        for emitter in self.emitters:
            self.emitters_by_type[emitter.name] += 1
            self.particles_by_type[emitter.name] += emitter.emitted  # shows only total emitted particles

        # print("( particles \"dirt\"", self.particles_by_type["dirt"], ", time spent", time.perf_counter() - t0, ")") # for debugging
        


    # --- DRAWING ---
    def draw(self):
        self.update()  # triggers paintGL


    def initializeGL(self):
        # print("START TEST")
        glClearColor(0, 0, 0, 0)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)

        glEnable(GL_TEXTURE_2D)

        # загрузка текстуры-атласа
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = "stars_atlas.png"
        full_path = os.path.join(base_dir, path)
        self.atlas_texture = AssetLoader.load_openGL_texture(full_path)

        # print("TEXTURES LOADED:", len(self.textures))

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        self.aspect = w / h


    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT)
        
        # дебаг штука
        total_particles = self.count
        culled_particles = 0
        drawn_particles = 0

        vertices = []
        texcoords = []

        # делим нашу текстуру-атлас и выбираем нужный кадр
        frame_width = 1.0 / 6.0

        for i in range(self.count):
            anim = self.animations[self.type_id[i]]
            frame_id = get_frame_index(anim, self.age[i]) # not needed

            x_px = self.pos_x[i]
            y_px = self.pos_y[i]

            x = (x_px / self.width()) * 2.0 - 1.0
            y = 1.0 - (y_px / self.height()) * 2.0

            size = 0.02 * self.size_p[i]

            sx = size
            sy = size * self.aspect

            # скип партиклов за пределами экрана
            if (
                x + sx < -1.0 or
                x - sx > 1.0 or
                y + sy < -1.0 or
                y - sy > 1.0
            ):
                culled_particles += 1
                continue

            drawn_particles += 1
            vertices.extend([
                x - sx, y - sy,
                x + sx, y - sy,
                x + sx, y + sy,
                x - sx, y + sy,
            ])

            u0 = frame_id * frame_width
            u1 = u0 + frame_width

            texcoords.extend([
                u0, 0.0,
                u1, 0.0,
                u1, 1.0,
                u0, 1.0,
            ])

        # end of loop. now we draw

        if not vertices:
            return
        
        vertices = np.array(vertices, dtype=np.float32)
        texcoords = np.array(texcoords, dtype=np.float32)

        glColor4f(1, 1, 1, 1)

        glBindTexture(GL_TEXTURE_2D, self.atlas_texture)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)

        glVertexPointer(2, GL_FLOAT, 0, vertices)
        glTexCoordPointer(2, GL_FLOAT, 0, texcoords)

        glDrawArrays(GL_QUADS, 0, len(vertices) // 2)

        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)

        # подсчёт партиклов для дебага
        self.debug_counter += 1

        if self.debug_counter >= 60:
            self.debug_counter = 0

            print(
                f"Total: {total_particles} | "
                f"Drawn: {drawn_particles} | "
                f"Culled: {culled_particles}"
            )

        glBindTexture(GL_TEXTURE_2D, 0)

        # --- DEBUG TEXT ---
        return  # if you want to debug particle coint - dont return
        painter = QPainter(self)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Consolas", 10))

        lines = []

        for type_name, emitter_count in self.emitters_by_type.items():
            particle_count = self.particles_by_type.get(type_name, 0)

            lines.append(
                f'{emitter_count} emitters of type "{type_name}" – {particle_count} particles'
            )

        lines.append(
            f' \n {(self.count)} active particles, {self.MAX_PARTICLES - self.count} free particles'
        )

        debug_text = "\n".join(lines)

        rect = QRect(10, 20, 300, 200)
        painter.drawText(rect, Qt.AlignLeft | Qt.AlignTop, debug_text) #type: ignore


# Numba method, outside of ParticleEngine class
@njit(cache=True,fastmath=True)
def update_particles(
    dt,
    count,
    pos_x, pos_y,
    vel_x, vel_y,
    acc_x, acc_y,
    age, type_id,
    alive,
    taskbar_top):
    i = 0
    while i < count:
        age[i] += dt
        vel_x[i] += acc_x[i] * dt
        vel_y[i] += acc_y[i] * dt
        pos_x[i] += vel_x[i] * dt
        pos_y[i] += vel_y[i] * dt

        # kill conditions
        if not alive[i] or pos_y[i] > taskbar_top:
            last = count - 1
            pos_x[i] = pos_x[last]
            pos_y[i] = pos_y[last]
            vel_x[i] = vel_x[last]
            vel_y[i] = vel_y[last]
            acc_x[i] = acc_x[last]
            acc_y[i] = acc_y[last]
            age[i] = age[last]
            type_id[i] = type_id[last]
            count -= 1
        else:
            i += 1
    return count