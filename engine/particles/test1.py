import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import QTimer, Qt

from PySide6.QtGui import QSurfaceFormat

from OpenGL.GL import * #type: ignore


class OpenGLWidget(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) #type: ignore
        self.setAutoFillBackground(False)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(16)

        self.frames = 0

        self.debug_timer = QTimer()
        self.debug_timer.timeout.connect(self.print_fps)
        self.debug_timer.start(1000)


    def initializeGL(self):
        pass

    def paintGL(self):
        self.frames += 1
        pass

    def print_fps(self):
        print("FPS:", self.frames)
        self.frames = 0

fmt = QSurfaceFormat()
fmt.setSwapInterval(-1)
QSurfaceFormat.setDefaultFormat(fmt)

app = QApplication(sys.argv)

window = OpenGLWidget()
window.resize(600, 600)
window.show()

sys.exit(app.exec())