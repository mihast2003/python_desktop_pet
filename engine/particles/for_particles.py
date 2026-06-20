import sys
import numpy as np

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL import GL
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtCore import Qt


VERTEX_SHADER = """
#version 330 core
layout (location = 0) in vec2 position;

void main()
{
    gl_Position = vec4(position, 0.0, 1.0);
}
"""

FRAGMENT_SHADER = """
#version 330 core
out vec4 FragColor;

void main()
{
    FragColor = vec4(0.2, 0.8, 0.3, 1.0);  // green-ish
}
"""


class GLWidget(QOpenGLWidget):
    def initializeGL(self):
        GL.glClearColor(0.0, 0.0, 0.0, 0.0)

        # Enable alpha blending
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        # ---- Compile shaders ----
        self.program = GL.glCreateProgram()

        vs = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        GL.glShaderSource(vs, VERTEX_SHADER)
        GL.glCompileShader(vs)

        fs = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(fs, FRAGMENT_SHADER)
        GL.glCompileShader(fs)

        GL.glAttachShader(self.program, vs)
        GL.glAttachShader(self.program, fs)
        GL.glLinkProgram(self.program)

        GL.glDeleteShader(vs)
        GL.glDeleteShader(fs)

        # ---- Quad data (2 triangles) ----
        vertices = np.array([ 
            # First triangle
            -0.5, -0.5,
             0.5, -0.5,
             0.5,  0.5,

            # Second triangle
            -0.5, -0.5,
             0.5,  0.5,
            -0.5,  0.5,
        ], dtype=np.float32)

        # ---- Create VAO + VBO ----
        self.vao = GL.glGenVertexArrays(1)
        self.vbo = GL.glGenBuffers(1)

        GL.glBindVertexArray(self.vao)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        GL.glBufferData(
            GL.GL_ARRAY_BUFFER,
            vertices.nbytes,
            vertices,
            GL.GL_STATIC_DRAW
        )

        # layout(location = 0) → vec2 position
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(
            0,              # attribute index
            2,              # x, y
            GL.GL_FLOAT,
            False,
            2 * 4,          # stride (2 floats × 4 bytes)
            None
        )

        GL.glBindVertexArray(0)

    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glClear(GL.GL_DEPTH_BUFFER_BIT)

        GL.glUseProgram(self.program)
        GL.glBindVertexArray(self.vao)

        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)

        GL.glBindVertexArray(0)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        self.setWindowTitle("Quad Example (VAO + VBO)")
        self.resize(600, 400)

        gl = GLWidget()
        gl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) 
        gl.setAutoFillBackground(False)

        self.setCentralWidget(gl)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())