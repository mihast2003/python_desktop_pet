# Main script with pet behavior: physics, drawing sprites, retrieving data


import sys, os, random, time, math
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QPixmap, QPen, QColor
from PySide6.QtCore import Qt, QTimer, QPointF

from data.states import STATES
from data.animations import ANIMATIONS
from data.render_config import RENDER_CONFIG

from engine.state_machine import StateMachine
from engine.enums import Flag, Pulse, BehaviourStates, MovementType
from engine.vec2 import Vec2

from data.variables import VARIABLES
from engine.variable_manager import VariableManager

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

        if elapsed >= self.long_press_time and not self.moved or self.moved:
            self.hold_triggered = True
            self.sm.raise_flag(Flag.CLICK_HELD)
            print("HOLDIIING")


    def release(self):
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
            print("CLICK")


class Mover:
    def __init__(self):
        self.pos = Vec2()
        self.vel = Vec2()
        self.target = Vec2()

        self.drag_offset = Vec2()

        self.acceleration = 1200.0
        self.max_speed = 700.0
        self.slow_radius = 120.0
        self.snap_distance = 8.0

        self.movement_type = None
        self.active = False

        # jump specific
        self.jump_velocity = -900.0
        self.gravity = 2500.0
        self.grounded_y = None

    def set_position(self, x, y):
        self.pos = Vec2(x, y)

    def move_to(self, x, y, movement_type: MovementType):
        self.target = Vec2(x, y)
        self.vel = Vec2()
        self.movement_type = movement_type
        self.active = True
        pet.state_machine.remove_flag(Flag.MOVEMENT_FINISHED)

        if movement_type == MovementType.JUMP:
            self.grounded_y = self.pos.y
            self.vel.y = self.jump_velocity

    def update(self, dt):
        if not self.active:
            return False

        match self.movement_type:

            case MovementType.DRAG:
                return False

            case MovementType.LINEAR:
                return self._update_linear(dt)

            case MovementType.ACCELERATING:
                return self._update_accelerating(dt)

            case MovementType.LERP:
                return self._update_lerp(dt)

            case MovementType.JUMP:
                return self._update_jump(dt)

    # ---------------- movement types ---------------- #

    def _update_linear(self, dt):
        direction = (self.target - self.pos).normalized()
        self.vel = direction * self.max_speed
        self.pos += self.vel * dt

        if self.pos.distance_to(self.target) <= self.snap_distance:
            self.pos = self.target.copy()
            self.active = False
            return True

        return False

    def _update_accelerating(self, dt):
        direction = (self.target - self.pos).normalized()
        self.vel += direction * self.acceleration * dt

        if self.vel.length() > self.max_speed:
            self.vel = self.vel.normalized() * self.max_speed

        self.pos += self.vel * dt

        if self.pos.distance_to(self.target) <= self.snap_distance:
            self.pos = self.target.copy()
            self.vel = Vec2()
            self.active = False
            return True

        return False

    def _update_lerp(self, dt):
        to_target = self.target - self.pos
        dist = to_target.length()

        if dist <= self.snap_distance:
            self.pos = self.target.copy()
            self.vel = Vec2()
            self.active = False
            return True

        direction = to_target.normalized()

        # --- desired speed (ease OUT) ---
        desired_speed = self.max_speed
        if dist < self.slow_radius:
            desired_speed *= dist / self.slow_radius

        desired_velocity = direction * desired_speed

        # --- accelerate toward desired velocity (ease IN) ---
        steering = desired_velocity - self.vel
        max_change = self.acceleration * dt

        if steering.length() > max_change:
            steering = steering.normalized() * max_change

        self.vel += steering
        self.pos += self.vel * dt

        return False

    def _update_jump(self, dt):
        # x moves toward target
        direction_x = 1 if self.target.x > self.pos.x else -1
        self.vel.x = direction_x * self.max_speed

        # gravity
        self.vel.y += self.gravity * dt

        self.pos += self.vel * dt

        # landing
        if self.pos.y >= self.grounded_y:
            self.pos.y = self.grounded_y
            self.vel = Vec2()
            self.active = False
            return True

        return False
    
    def begin_drag(self, mouse_pos: Vec2):
        self.active = True
        self.movement_type = MovementType.DRAG
        self.vel = Vec2()
        pet.state_machine.pulse(Pulse.DRAGGING_STARTED)
        self.pos = mouse_pos - self.drag_offset # initial snapping to cursor movement

    def update_drag_target(self, mouse_pos: Vec2):
        if self.movement_type == MovementType.DRAG:
            screen = QApplication.primaryScreen().availableGeometry()
            if mouse_pos.x > screen.width() - pet.logical_width/2 or mouse_pos.x <= pet.logical_width/2 or mouse_pos.y >= screen.bottom() - (pet.logical_height / 2):
                self.end_drag()
                return
            
            self.pos = mouse_pos - self.drag_offset
            

    def end_drag(self):
        if self.movement_type == MovementType.DRAG:
            self.active = False
            self.movement_type = None
            pet.state_machine.pulse(Pulse.DRAGGING_ENDED)
            pet.click_detector.release()


# ANIMATION STUFF
def load_frames(folder):  # function for loading frames, recieves a string path to a folder, returns a list of png files( converted to PixMap ) in name order
    frames = []

    for file in sorted(os.listdir(folder)):
        files = sorted(                # get the png files
        f for f in os.listdir(folder)
        if f.lower().endswith(".png")
        )

        for i, filename in enumerate(files):
            pix = QPixmap(os.path.join(folder, filename))

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
        # resize window to match FIRST frame (scaled)

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
        self.variables = VariableManager(VARIABLES)
        self.mover = Mover()

        self.logical_width = 0
        self.logical_height = 0
        
        screen = QApplication.primaryScreen() # Screen detection
        self.taskbar_top = screen.availableGeometry().bottom() # Taskbar position detection
        self.mover.set_position(100, 100 + 1) # set initial position

        self.dpi_scale = self.devicePixelRatioF()
        self.pixel_ratio = RENDER_CONFIG["pixel_ratio"]
        self.mover.drag_offset = Vec2(self.logical_width * RENDER_CONFIG["drag_offset_x"], self.logical_height * RENDER_CONFIG["drag_offset_x"])

        self.state_machine = StateMachine(pet=self, configs=STATES, initial="IDLE") # set initial state

        self.click_detector = ClickDetector(state_machine=self.state_machine) #initialising ClickDetector

        self.update_window_size() # initial update window size

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
        # print(self.behaviour)

        match self.behaviour:
            case BehaviourStates.MOVING_RANDOM:
                screen = QApplication.primaryScreen().geometry()
                target_x = random.randint(0, screen.width() - round(self.logical_width))
                self.mover.set_position(self.x(), self.y())
                self.mover.move_to(target_x, self.y(), MovementType.LERP)
            case BehaviourStates.DRAGGING:
                pos = Vec2(self.click_detector.press_pos.x(), self.click_detector.press_pos.y())
                self.mover.begin_drag(pos)
                self.state_machine.pulse(Pulse.DRAGGING_STARTED)
            case BehaviourStates.FALLING:
                self.mover.move_to(self.x(), self.taskbar_top + 1, MovementType.ACCELERATING)
            
    def on_state_exit(self, state): #just does nothing when the state is done
        pass

    def _mouse_vec(self, event):   #helper function for converting Qt points to Vec2
        p = event.globalPosition()
        return Vec2(p.x(), p.y())
    
    def update_logic(self):
        dt = 1 / 60

        arrived = self.mover.update(dt)
        self.move(int(self.mover.pos.x), int(self.mover.pos.y))

        if arrived:
            self.state_machine.raise_flag(Flag.MOVEMENT_FINISHED)

        if self.animator.update(dt):
            self.state_machine.pulse(Pulse.ANIMATION_END)
        

        self.variables.update(dt)
        self.state_machine.update()
        self.click_detector.update()
        self.update()

    def update_window_size(self):
            frame = self.animator.frame()
            if not frame:
                return
            
            scale = self.pixel_ratio * self.devicePixelRatioF()
            
            self.logical_width = frame.width() * scale
            self.logical_height = frame.height() * scale

            # print(self.logical_height)
            # print(self.logical_width)

            w = int(frame.width() * scale)
            h = int(frame.height() * scale)
            self.resize(w, h)


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.click_detector.press(event.globalPosition())


    def mouseMoveEvent(self, event):
        self.click_detector.move(event.globalPosition())
        if self.mover.movement_type == MovementType.DRAG:
            self.mover.update_drag_target(self._mouse_vec(event))

    def mouseReleaseEvent(self, event):
        self.click_detector.release()
        if self.mover.movement_type == MovementType.DRAG:
            self.mover.end_drag()      


    def paintEvent(self, e): #draws the frame reveived from Animator 
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        p.fillRect(self.rect(), QColor(80, 80, 80))  # dark gray

        frame = self.animator.frame()
        if not frame:
            return

        scale = self.pixel_ratio * self.dpi_scale

        # draw sprite so its bottom-middle is at (self.x, self.y)
        anchor_x = self.width() / 2
        anchor_y = self.height()

        p.setPen(QPen(Qt.red, 6))
        p.drawLine(0, 0, self.width(), self.height())
        p.drawLine(self.width(), 0, 0, self.height())
        
        p.save()
        p.translate(anchor_x, anchor_y)
    

        p.setPen(QPen(Qt.green, 6))
        p.drawEllipse(QPointF(0, 0), 2, 2)

        p.scale(scale, scale)
        p.drawPixmap(-anchor_x * 4, -anchor_y * 4, frame)

        p.restore()


if __name__ == "__main__": # QT stuff, idk idc
    app = QApplication(sys.argv)
    pet = Pet()
    pet.move(300, 900)
    pet.show()
    sys.exit(app.exec())
