import sys
import os
import ctypes
import random
import numpy as np

from PIL import Image

from PySide6.QtWidgets import QApplication
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import QTimer, Qt

from OpenGL.GL import * #type: ignore
from OpenGL.GL.shaders import compileProgram, compileShader

VERTEX_SHADER = """
#version 330 core

layout(location = 0) in vec3 position;
layout(location = 1) in vec2 texCoord;

out vec2 uv;

uniform float time;

uniform float offsetX;

uniform float phase;
uniform float delay;

uniform float swayAmplitude;
uniform float swaySpeed;

uniform float rotationAmplitude;
uniform float fallSpeed;

void main()
{
    // =========================
    // ИНДИВИДУАЛЬНОЕ ВРЕМЯ
    // =========================

    float t = time - delay + phase;

    // Если время ещё не пришло —
    // прячем лепесток
    if(t < 0.0)
    {
        gl_Position = vec4(9999.0);
        uv = texCoord;
        return;
    }

    // =========================
    // ПАДЕНИЕ
    // =========================

    float fall =
        mod(t * fallSpeed, 2.8);

    // =========================
    // ВИЛЯНИЕ
    // =========================

    float sway =
        sin(t * swaySpeed)
        * swayAmplitude;

    // =========================
    // ПОВОРОТ
    // =========================

    float rotationAmount =
        -cos(t * swaySpeed)
        * rotationAmplitude;

    // =========================
    // МАТРИЦА ПОВОРОТА
    // =========================

    mat2 rotation = mat2(
        cos(rotationAmount),
        -sin(rotationAmount),

        sin(rotationAmount),
         cos(rotationAmount)
    );

    // =========================
    // ВРАЩАЕМ ВЕРШИНЫ
    // =========================

    vec2 rotated =
        rotation * position.xy;

    // =========================
    // ПОЗИЦИЯ
    // =========================

    gl_Position = vec4(
        rotated.x + sway + offsetX,
        rotated.y + 1.3 - fall,
        position.z,
        1.0
    );

    uv = texCoord;
}
"""


# =========================================================
# FRAGMENT SHADER
# =========================================================

FRAGMENT_SHADER = """
#version 330 core

in vec2 uv;

out vec4 FragColor;

uniform sampler2D texture1;

void main()
{
    vec4 texColor =
        texture(texture1, uv);

    if(texColor.a < 0.1)
        discard;

    FragColor = texColor;
}
"""


class OpenGLWidget(QOpenGLWidget):

    def __init__(self):
        super().__init__()

        # =========================================================
        # OVERLAY WINDOW
        # =========================================================

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        self.setAutoFillBackground(False)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        # =========================================================
        # TIME
        # =========================================================

        self.time = 0.0

        # =========================================================
        # ЛЕПЕСТКИ
        # =========================================================

        self.petals = []

        for i in range(50):

            petal = {

                # Позиция по X
                "offsetX":
                    random.uniform(-1.2, 1.2),

                # Сдвиг анимации
                "phase":
                    random.uniform(0.0, 10.0),

                # Задержка появления
                "delay":
                    random.uniform(0.0, 8.0),

                # Амплитуда движения
                "swayAmplitude":
                    random.uniform(0.08, 0.28),

                # Скорость sway
                "swaySpeed":
                    random.uniform(0.5, 1.4),

                # Интенсивность поворота
                "rotationAmplitude":
                    random.uniform(0.08, 0.35),

                # Скорость падения
                "fallSpeed":
                    random.uniform(0.12, 0.28),
            }

            self.petals.append(petal)

        # =========================================================
        # TIMER
        # =========================================================

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.animate
        )

        self.timer.start(16)

        QTimer.singleShot(
            0,
            self.update
        )

    def animate(self):

        self.time += 0.016

        self.update()

    def initializeGL(self):

        # =========================================================
        # ПРОЗРАЧНЫЙ ФОН
        # =========================================================

        glClearColor(
            0.0,
            0.0,
            0.0,
            0.0
        )

        # =========================================================
        # BLENDING
        # =========================================================

        glEnable(GL_BLEND)

        glBlendFunc(
            GL_SRC_ALPHA,
            GL_ONE_MINUS_SRC_ALPHA
        )

        # =========================================================
        # SHADER PROGRAM
        # =========================================================

        self.shader = compileProgram(
            compileShader(
                VERTEX_SHADER,
                GL_VERTEX_SHADER
            ),

            compileShader(
                FRAGMENT_SHADER,
                GL_FRAGMENT_SHADER
            )
        )

        # =========================================================
        # МАЛЕНЬКИЙ КВАДРАТ
        # =========================================================

        vertices = np.array([

            # x       y      z      u     v

            -0.035,  0.035, 0.0,   0.0, 0.0,
            -0.035, -0.035, 0.0,   0.0, 1.0,
             0.035, -0.035, 0.0,   1.0, 1.0,

            -0.035,  0.035, 0.0,   0.0, 0.0,
             0.035, -0.035, 0.0,   1.0, 1.0,
             0.035,  0.035, 0.0,   1.0, 0.0

        ], dtype=np.float32)

        # =========================================================
        # VAO
        # =========================================================

        self.VAO = glGenVertexArrays(1)

        glBindVertexArray(self.VAO)

        # =========================================================
        # VBO
        # =========================================================

        self.VBO = glGenBuffers(1)

        glBindBuffer(
            GL_ARRAY_BUFFER,
            self.VBO
        )

        glBufferData(
            GL_ARRAY_BUFFER,
            vertices.nbytes,
            vertices,
            GL_STATIC_DRAW
        )

        # =========================================================
        # POSITION ATTRIBUTE
        # =========================================================

        glVertexAttribPointer(
            0,
            3,
            GL_FLOAT,
            GL_FALSE,
            5 * 4,
            None
        )

        glEnableVertexAttribArray(0)

        # =========================================================
        # UV ATTRIBUTE
        # =========================================================

        glVertexAttribPointer(
            1,
            2,
            GL_FLOAT,
            GL_FALSE,
            5 * 4,
            ctypes.c_void_p(3 * 4)
        )

        glEnableVertexAttribArray(1)

        # =========================================================
        # TEXTURE
        # =========================================================

        self.texture = glGenTextures(1)

        glBindTexture(
            GL_TEXTURE_2D,
            self.texture
        )

        glTexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_WRAP_S,
            GL_CLAMP_TO_EDGE
        )

        glTexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_WRAP_T,
            GL_CLAMP_TO_EDGE
        )

        glTexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_MIN_FILTER,
            GL_LINEAR
        )

        glTexParameteri(
            GL_TEXTURE_2D,
            GL_TEXTURE_MAG_FILTER,
            GL_LINEAR
        )

        # =========================================================
        # PNG
        # =========================================================

        BASE_DIR = os.path.dirname(
            os.path.abspath(__file__)
        )

        texture_path = os.path.join(
            BASE_DIR,
            "texturee.png"
        )

        image = Image.open(texture_path)

        image = image.transpose(
            Image.FLIP_TOP_BOTTOM #type: ignore
        )

        image = image.convert("RGBA")

        img_data = image.tobytes()

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            image.width,
            image.height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            img_data
        )

        glGenerateMipmap(GL_TEXTURE_2D)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

    def draw_petal(self, petal):

        glUseProgram(self.shader)

        # =========================================================
        # TIME
        # =========================================================

        glUniform1f(
            glGetUniformLocation(
                self.shader,
                "time"
            ),
            self.time
        )

        # =========================================================
        # UNIFORMS
        # =========================================================

        for key, value in petal.items():

            glUniform1f(
                glGetUniformLocation(
                    self.shader,
                    key
                ),
                value
            )

        # =========================================================
        # DRAW
        # =========================================================

        glBindTexture(
            GL_TEXTURE_2D,
            self.texture
        )

        glBindVertexArray(self.VAO)

        glDrawArrays(
            GL_TRIANGLES,
            0,
            6
        )

    def paintGL(self):

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) #type: ignore

        # # =========================================================
        # # ALL PETALS
        # # =========================================================

        petal = self.petals[0]
        self.draw_petal(petal)

        # for petal in self.petals:
        #     self.draw_petal(petal)


# =========================================================
# APP
# =========================================================

app = QApplication(sys.argv)

window = OpenGLWidget()

window.showMaximized()

# window.resize(100, 100)

sys.exit(app.exec())