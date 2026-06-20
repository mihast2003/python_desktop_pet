import sys
import random

from PySide6.QtWidgets import QApplication
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor

from OpenGL.GL import * # type: ignore

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

        self.particles = []
        self.spawn_more = True

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_logic)
        self.timer.start(1000//SIMULATION_FPS) # это чето на умном, он считает сколько милисекунд между кадрами при SIMULATION_FPS фпс


# helper functions (это ты не трогаешь)

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

            print(p["scale"])

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

        spawn_one = True  # я так сделал чтоб можно было один партикл дебагить. Просто тут поставь False и он будет много спавнить

        if self.spawn_more:
            self.spawn_new()
            if spawn_one:
                self.spawn_more = False

        self.update_particles(dt, spawn_one)

        self.update() # вызывает paintGL() и срабатывает отрисовка, должно быть в конце update_logic()


# OPenGL (тут твори че хочешь)

    def initializeGL(self):
        glClearColor(0, 0, 0, 0)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)  # 🔥 яркие искры

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)


    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT)

        # это твоя инфа, надо взять партикл под номером 0(единственный пока что), взять для него один из 6 кадров(от 0 до 5) 
        # и нарисовать этот кадр на pos_x pos_y
        # ↓↓↓↓↓↓↓↓↓

        pos_x = [p["x"] for p in self.particles]
        pos_y = [p["y"] for p in self.particles]
        type_id = [p["type_id"] for p in self.particles]
        frame = [p["frame"] for p in self.particles]
        scale = [p["scale"] for p in self.particles]


        # дальше это рендер старый

        glBegin(GL_QUADS)

        for p in self.particles:

            life = p["life"]

            r, g, b = 100, 100, 100

            # прозрачность = жизнь
            a = life

            glColor4f(r, g, b, a)

            size = 0.003

            x = p["x"]
            y = p["y"]

            glVertex2f(x - size, y - size)
            glVertex2f(x + size, y - size)
            glVertex2f(x + size, y + size)
            glVertex2f(x - size, y + size)

        glEnd()


app = QApplication(sys.argv)

window = OpenGLWidget()
window.showMaximized()

sys.exit(app.exec())