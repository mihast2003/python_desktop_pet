import sys
import random
import numpy as np

from PySide6.QtWidgets import QApplication
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor

from OpenGL.GL import * #type: ignore

SIMULATION_FPS = 60  # сколько фпс будет


class OpenGLWidget(QOpenGLWidget):

    def __init__(self):
        super().__init__()

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        # штука для дебага
        self.debug_counter = 0

        self.textures = []
        self.particles = []
        self.spawn_more = True

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_logic)
        self.timer.start(1000//SIMULATION_FPS) # это чето на умном, он считает сколько милисекунд между кадрами при SIMULATION_FPS фпс


# helper functions (это ты не трогаешь)

    # добавил сюда функцию для загрузки текстуры/атласа
    def load_texture(self, path):
        from PIL import Image
        import os

        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, path)

        img = Image.open(full_path).convert("RGBA")
        img_data = img.tobytes("raw", "RGBA", 0, -1)

        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            img.width,
            img.height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            img_data
        )

        glBindTexture(GL_TEXTURE_2D, 0)

        return tex_id

    def get_random_position(self):
        """
        Returns a random position at the top of the screen
        """
        x = random.uniform(-1, 1)
        y = 1

        return x, y
    
    def spawn_new(self):
        """
        Appends a new particle to self.particles
        """
        x, y = self.get_random_position()

        speed_x = random.uniform(-0.05, 0.05)
        speed_y = random.uniform(0.3, 0.8)

        self.particles.append({
            "x": x,
            "y": y,
            "vx": speed_x,
            "vy": speed_y,
            "life": 5,
            "type_id": 0,
            "frame": 0,
            "scale": 1,
        })

    def update_particles(self, dt, spawn_one):
        new_particles = []

        for p in self.particles:

            p["x"] += p["vx"] * dt
            p["y"] -= p["vy"] * dt

            p["life"] -= dt

            p["scale"] -= dt * 0.09

            p["frame"] = 5 - round(p["life"])

            # print(p["scale"])

            if p["life"] < 0:
                if spawn_one:
                    self.spawn_new()
            else:
                new_particles.append(p)

        self.particles = new_particles
    

# Main update loop (эта функция вызывается SIMULATION_FPS раз в секунду)

    def update_logic(self):
        """
        Main logic loop, executed SIMULATION_FPS в секунду
        """
        dt = 1 / SIMULATION_FPS

        spawn_one = False  # я так сделал чтоб можно было один партикл дебагить. Просто тут поставь False и он будет много спавнить

        if self.spawn_more:
            for _ in range(1):
                self.spawn_new()
                if spawn_one:
                    self.spawn_more = False

        self.update_particles(dt, spawn_one)

        self.update() # вызывает paintGL() и срабатывает отрисовка, должно быть в конце update_logic()

# OPenGL (тут твори че хочешь)

    def initializeGL(self):

        # print("START TEST")

        glClearColor(0, 0, 0, 0)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)

        glEnable(GL_TEXTURE_2D)

        # загрузка текстуры-атласа
        self.atlas_texture = self.load_texture("stars_atlas.png")


        # print("TEXTURES LOADED:", len(self.textures))

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        self.aspect = w / h


    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT)

        # дебаг штука
        total_particles = len(self.particles)
        culled_particles = 0
        drawn_particles = 0

        vertices = []
        texcoords = []

        # делим нашу текстуру-атлас и выбираем нужный кадр
        frame_width = 1.0 / 6.0

        for p in self.particles:
            frame_id = max(0, min(5, int(p["frame"])))

            x = p["x"]
            y = p["y"]

            size = 0.025 * p["scale"]

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


app = QApplication(sys.argv)

window = OpenGLWidget()
window.showMaximized()

sys.exit(app.exec())