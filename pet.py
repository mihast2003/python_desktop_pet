# Main script with pet behavior: physics, drawing sprites, retrieving data


import sys, os, random, time
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtCore import Qt, QTimer, QPointF

from data.states import STATES
from data.animations import ANIMATIONS
from engine.state_machine import StateMachine
from engine.enums import Flag, Pulse, BehaviourStates
from enum import Enum, auto

FPS = 60 #fps of logic processes
PET_SIZE_X, PET_SIZE_Y = 100, 80

# helper function to detect clicks or holds on pet sprite
class ClickDetector:
    def __init__(self, state_machine):
        self.sm = state_machine

        self.press_time = None
        self.press_pos = None
        self.moved = False
        self.hold_triggered = False

        self.click_time = 0.1
        self.long_press_time = 0.1
        self.move_tolerance = 6

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
            print("HOLDIIING")

    def release(self, pos: QPointF):
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

        if self.moved:
            return

        if duration <= self.click_time:
            self.sm.pulse(Pulse.CLICK)
            print("CLICK")

class MovementType(Enum):
    LINEAR = auto()
    ACCELERATING = auto()
    LERP = auto()


class Mover: # contains movement functions
    # Handles smooth movement with acceleration
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.velocity_x = 0.0
        self.velocity_y = 0.0

        self.target_x = 0.0
        self.target_y = 0.0

        self.acceleration = 1200.0
        self.max_speed = 700.0
        self.slow_radius = 100.0
        self.snap_distance = 25.0

        self.movement_type = None

        self.active = False

    def set_position(self, x, y): # instantly sets position of sprite to x, y (sprite origin is left top corner)
        self.x = float(x)
        self.y = float(y)

    def move_to(self, x, y, movement_type): # sets a coordinate target for movement
        self.target_x = float(x)
        self.target_y = float(y)
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.active = True
        self.movement_type = movement_type
        print("i am at ", self.x, self.y)
        print("now going to ", x, y)

    def update(self, delta): #updates moving logic(helper function)
        if not self.active:
            return False  # not moving

        abs_distance = abs(self.target_x - self.x) + abs(self.target_y - self.y)
        difference_x = self.target_x - self.x
        difference_y = self.target_y - self.y

        # print(self.movement_type)

        if abs_distance <= self.snap_distance:
            self.x = self.target_x
            self.y = self.target_y
            self.velocity_x = 0.0
            self.velocity_y = 0.0
            self.active = False
            self.movement_type = None
            return True  # arrived
        
        direction = 1 if difference_x > 0 else -1
        verticality = 1 if difference_y > 0 else -1

        desired_max = self.max_speed

        match self.movement_type:    # process different type of movement
            case MovementType.LINEAR:
                self.velocity_x = 100
                self.velocity_y = 100

            case MovementType.ACCELERATING:
                self.velocity_x += direction * self.acceleration * delta
                self.velocity_x = max(-desired_max, min(self.velocity_x, desired_max))

                self.velocity_x += verticality * self.acceleration * delta
                self.velocity_y = max(-desired_max, min(self.velocity_y, desired_max))

            case MovementType.LERP:
                if abs_distance < self.slow_radius:
                    desired_max *= abs_distance / self.slow_radius
                    print("slowing down to ", desired_max)

                self.velocity_x += direction * self.acceleration * delta
                self.velocity_x = max(-desired_max, min(self.velocity_x, desired_max))

                self.velocity_x += verticality * self.acceleration * delta
                self.velocity_y = max(-desired_max, min(self.velocity_y, desired_max))

                print("velocity is ", self.velocity_x)

        #print(self.velocity_x)

        self.x += self.velocity_x * delta
        #self.y += self.velocity_y * delta

        return False

# ANIMATION STUFF
def load_frames(folder):  # function for loading frames, recieves a string path to a folder, returns a list of png files( converted to PixMap ) in name order
    frames = []

    screen = QApplication.primaryScreen()
    dpr = screen.devicePixelRatio()

    for file in sorted(os.listdir(folder)):
        files = sorted(                # get the png files
        f for f in os.listdir(folder)
        if f.lower().endswith(".png")
        )

        frames = []

        for i, filename in enumerate(files):
            pix = QPixmap(os.path.join(folder, filename)).scaled(
                int(PET_SIZE_X * dpr), int(PET_SIZE_Y * dpr),      # scaled for DPI
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            pix.setDevicePixelRatio(dpr)  # helps with pixelisation

            frames.append(pix)

    return frames


class Animator:  # contains different animation functions
    def __init__(self):
        self.frames = []
        self.index = 0
        self.timer = 0
        self.loop = True
        self.ticks_left = 0
        self.done = False

    def set(self, frames, fps, loop, holds=None): #sets the animatios. receives a list of PixMap (frames), int (fps) and a bool(loop)
        self.frames = frames
        self.fps = fps
        self.loop = loop
        self.index = 0
        self.timer = 0
        self.holds = holds or {}
        self.ticks_left = self.hold_for(0)
        self.done = False

    def update(self, dt): #iterates over the list of frames with the speed of fps, loops if loop==True
        if self.done or not self.frames:
            return False

        self.timer += dt
        frame_time = 1 / self.fps

        if self.timer >= frame_time:
            self.timer -= frame_time
            self.ticks_left -= 1

            if self.ticks_left <= 0:
                self.index += 1

                if self.index >= len(self.frames):
                    if self.loop:
                        self.index = 0
                    else:
                        self.index = len(self.frames) - 1
                        self.done = True

                    return True # if the index of the frame is more than we have frames, the animation is considered finished(for ease of connecting animations together), else - not

                self.ticks_left = self.hold_for(self.index)

            else: return False

    def hold_for(self, index):
        return self.holds.get(index + 1, 1)

    def frame(self): #returns a single frame which should be displayed at the moment
        return self.frames[self.index]


class Pet(QWidget): # main logic
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)   # QT stuff idk idc
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(PET_SIZE_X, PET_SIZE_Y)

        # get all animations in a dictionary

        self.animations = {}
        base = os.path.dirname(os.path.abspath(__file__))
        for name, cfg in ANIMATIONS.items():
            folder = os.path.join(base, cfg["folder"])

            frames = []
            
            frames = load_frames(folder)
            print("loaded animation: ", name)

            if not frames:
                raise RuntimeError(f"No frames found for animation '{name}'")

            self.animations[name] = {
                "frames": frames,
                "fps": cfg["fps"],
                "loop": cfg["loop"],
                "holds": cfg.get("holds", {})
            }

                  
        #instancing Animator, Mover
        self.animator = Animator()
        self.mover = Mover()
        
        screen = QApplication.primaryScreen() # Screen detection
        self.taskbar_top = screen.availableGeometry().bottom() # Taskbar position detection
        self.mover.set_position(self.x(), self.taskbar_top - self.height() + 1) # set initial position

        self.state_machine = StateMachine(pet=self, configs=STATES, initial="IDLE") # set initial state

        self.click_detector = ClickDetector(state_machine=self.state_machine) #initialising ClickDetector

        # Timer for updating logic
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_logic)
        self.timer.start(1000 // FPS)


    def on_state_enter(self, state): #called in state_machine when entering a new state
        print("STATE:", state)

        cfg = STATES[state]      # gets the config for the state from states.py
        anim_name = cfg["animation"]
        anim_cfg = ANIMATIONS[anim_name]

        frames = self.animations[anim_name]["frames"]
        fps = cfg.get("fps", anim_cfg.get("fps", 6)) # safestate, will default to the latter
        loop = cfg.get("loop", anim_cfg.get("loop", True)) # safestate, will default to the latter
        holds = cfg.get("holds", anim_cfg.get("holds", {}))  # safestate, will default to empty directory

        self.animator.set(frames=frames, fps=fps, loop=loop, holds=holds) #sets animation in animator

        self.behaviour = BehaviourStates.__members__.get(cfg.get("behaviour", "STATIONARY"))
        print(self.behaviour)

        match self.behaviour:
            case BehaviourStates.MOVING_RANDOM:
                screen = QApplication.primaryScreen().geometry()
                target_x = random.randint(0, screen.width() - self.width())
                self.mover.set_position(self.x(), self.y())
                self.state_machine.remove_flag(Flag.MOVEMENT_FINISHED)
                self.mover.move_to(target_x, self.y(), MovementType.LINEAR)
            case BehaviourStates.DRAGGING:
                pos = self.click_detector.press_pos
                self.mover.set_position(pos.x(), pos.y())
            case BehaviourStates.FALLING:
                self.mover.move_to(self.x(), self.taskbar_top - self.height() + 1, MovementType.ACCELERATING)
            
    def pointQFtocoords(self, x, y):

        return

    def on_state_exit(self, state): #just does nothing when the state is done
        pass

    def update_logic(self):
        dt = 1 / 60

        arrived = self.mover.update(dt)
        self.move(int(self.mover.x), int(self.mover.y))

        if arrived:
            self.state_machine.raise_flag(Flag.MOVEMENT_FINISHED)

        if self.animator.update(dt):
            self.state_machine.pulse(Pulse.ANIMATION_END)
            
        self.state_machine.update()
        self.click_detector.update()
        self.update()


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.click_detector.press(event.position())

    def mouseMoveEvent(self, event):
        print(event)
        self.click_detector.move(event.position())

    def mouseReleaseEvent(self, event):
        self.click_detector.release(event.position())


    def paintEvent(self, e): #draws the frame reveived from Animator 
        p = QPainter(self)
        p.drawPixmap(0, 0, self.animator.frame())


if __name__ == "__main__": # QT stuff, idk idc
    app = QApplication(sys.argv)
    pet = Pet()
    pet.move(300, 900)
    pet.show()
    sys.exit(app.exec())
