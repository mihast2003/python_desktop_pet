import sys

from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QPixmap, QPen, QColor
from PySide6.QtCore import Qt, QTimer, QPointF


class TestWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint | #type: ignore
            Qt.WindowStaysOnTopHint | #type: ignore
            Qt.Tool #type: ignore
        )
        self.setAttribute(Qt.WA_TranslucentBackground) #type: ignore

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_wid)
        self.timer.start(1000 // 60)

    def update_wid(self):
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 0, 0, 255))


app = QApplication(sys.argv)

window = TestWidget()
window.resize(600, 600)
window.show()

sys.exit(app.exec())