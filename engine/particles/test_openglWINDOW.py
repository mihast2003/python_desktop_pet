import sys

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtOpenGL import QOpenGLWindow

from OpenGL.GL import * #type: ignore


class PetWindow(QOpenGLWindow):

    def __init__(self):
        super().__init__()

        self.frames = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000 // 60)

        self.debug_timer = QTimer()
        self.debug_timer.timeout.connect(self.print_fps)
        self.debug_timer.start(1000)

    def initializeGL(self):
        print(glGetString(GL_RENDERER))
        print(glGetString(GL_VENDOR))
        print(glGetString(GL_VERSION))

        glClearColor(0, 0, 0, 0)

    def paintGL(self):
        self.frames += 1

        glClear(GL_COLOR_BUFFER_BIT)

    def print_fps(self):
        print("FPS:", self.frames)
        self.frames = 0


app = QGuiApplication(sys.argv)

window = PetWindow()

window.setFlags(
    # Qt.FramelessWindowHint  #type: ignore
    Qt.WindowStaysOnTopHint #type: ignore
    | Qt.Tool #type: ignore
)


screen = app.primaryScreen().geometry()
window.setGeometry(screen)

window.show()

sys.exit(app.exec())