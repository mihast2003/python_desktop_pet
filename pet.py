# Main script with pet behavior: physics, drawing sprites, retrieving data


import sys, os, random
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtCore import Qt, QTimer

from data.states import STATES
from data.animations import ANIMATIONS
from engine.state_machine import StateMachine
from engine.enums import Flag, Pulse, BehaviourStates


FPS = 60 #fps of logic processes
PET_SIZE_X, PET_SIZE_Y = 100, 80

class Mover: # contains movement functions
    # Handles smooth movement with acceleration
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.velocity = 0.0
        self.target_x = 0.0

        self.acceleration = 1200.0
        self.max_speed = 700.0
        self.slow_radius = 100.0
        self.snap_distance = 25.0

        self.active = False

    def set_position(self, x, y): # instantly sets position of sprite to x, y (sprite origin is left top corner)
        self.x = float(x)
        self.y = float(y)

    def move_to(self, x): # sets an x coordinate target for movement
        self.target_x = float(x)
        self.velocity = 0.0
        self.active = True

    def update(self, delta): #updates moving logic(helper function)
        if not self.active:
            return False  # not moving

        distance = self.target_x - self.x

        if abs(distance) <= self.snap_distance:
            self.x = self.target_x
            self.velocity = 0.0
            self.active = False
            return True  # arrived

        direction = 1 if distance > 0 else -1
        desired_max = self.max_speed

        if abs(distance) < self.slow_radius:
            desired_max *= abs(distance) / self.slow_radius

        self.velocity += direction * self.acceleration * delta
        self.velocity = max(-desired_max, min(self.velocity, desired_max))
        self.x += self.velocity * delta

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
                  
        #instancing Animator and Mover
        self.animator = Animator()
        self.mover = Mover()
        
        screen = QApplication.primaryScreen() # Screen detection
        self.taskbar_top = screen.availableGeometry().bottom() # Taskbar position detection
        self.mover.set_position(self.x(), self.taskbar_top - self.height() + 1) # set initial position

        self.state_machine = StateMachine(pet=self, configs=STATES, initial="IDLE") # set initial state

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

        if self.behaviour is BehaviourStates.MOVING_RANDOM:
            screen = QApplication.primaryScreen().geometry()
            target_x = random.randint(0, screen.width() - self.width())
            self.mover.set_position(self.x(), self.y())
            self.mover.move_to(target_x)
            self.state_machine.remove_flag(Flag.MOVEMENT_FINISHED)

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
        self.update()

    def mousePressEvent(self, event): #detects clicks on sprite
        self.state_machine.pulse(Pulse.CLICK) #sends CLICK pulse to state_machine.py

    def paintEvent(self, e): #draws the frame reveived from Animator 
        p = QPainter(self)
        p.drawPixmap(0, 0, self.animator.frame())


if __name__ == "__main__": # QT stuff, idk idc
    app = QApplication(sys.argv)
    pet = Pet()
    pet.move(300, 900)
    pet.show()
    sys.exit(app.exec())
