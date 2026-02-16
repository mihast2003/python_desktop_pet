import sys, os, random, time, math
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QPixmap, QPen, QColor
from PySide6.QtCore import Qt, QTimer, QPointF

from engine.enums import Flag, Pulse, MovementType, Facing

# helper function to detect clicks or holds on pet sprite
class ClickDetector:
    def __init__(self, pet):
        self.pet = pet
        self.sm = pet.state_machine

        self.press_time = None
        self.press_pos = None
        self.moved = False
        self.hold_triggered = False

        self.click_time = 0.1
        self.long_press_time = 0.1
        self.move_tolerance = 1   # CHANGE

    def press(self, pos: QPointF):
        self.press_time = time.monotonic()
        self.press_pos = pos
        self.moved = False
        self.hold_triggered = False

    def move(self, pos: QPointF):
        if not self.press_pos:
            return

        if (pos - self.press_pos).manhattanLength() > self.move_tolerance:
            self.moved = True

    def update(self):
        if self.press_time is None or self.hold_triggered:
            return

        elapsed = time.monotonic() - self.press_time

        if elapsed >= self.long_press_time and not self.moved:
            self.hold_triggered = True
            self.sm.raise_flag(Flag.CLICK_HELD)
            self.sm.raise_flag(Flag.DRAGGING)
            print("HOLDIIING")

        if self.moved:
            self.sm.raise_flag(Flag.DRAGGING)

    def release(self):
        self.sm.remove_flag(Flag.DRAGGING)

        if self.press_time is None:
            return

        duration = time.monotonic() - self.press_time


        self.press_time = None
        self.press_pos = None

        if self.hold_triggered:
            self.sm.remove_flag(Flag.CLICK_HELD)
            self.sm.pulse(Pulse.LETGO)
            print("stopped holding")
            return

        # if self.moved:
        #     return

        if duration <= self.click_time:
            self.sm.pulse(Pulse.CLICK)
            self.pet.variables.add("times_clicked_this_state", 1)
            print("CLICK")
