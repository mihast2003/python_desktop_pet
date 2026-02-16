# Main script with pet behavior: physics, drawing sprites, retrieving data


import sys, os, random, time, math
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QPixmap, QPen, QColor
from PySide6.QtCore import Qt, QTimer, QPointF

from enum import Enum, auto
import warnings

from data.states import STATES, INITIAL_STATE
from data.animations import ANIMATIONS
from data.render_config import RENDER_CONFIG

from engine.state_machine import StateMachine
from engine.click_detector import ClickDetector
from engine.mover import Mover
from engine.enums import Flag, Pulse, MovementType, Facing
from engine.vec2 import Vec2
from engine.behaviour_resolver import BehaviourResolver


from data.variables import VARIABLES
from engine.variable_manager import VariableManager

FPS = RENDER_CONFIG.get("logic_FPS", 60) #fps of logic processes

# ANIMATION STUFF
def load_frames(folder):  # function for loading frames, recieves a string path to a folder, returns a list of png files( converted to PixMap ) in name order
    frames = []

    files = sorted(                # get the png files
    f for f in os.listdir(folder)
    if f.lower().endswith(".png")
    )

    for i, filename in enumerate(files):
        pix = QPixmap(os.path.join(folder, filename))

        frames.append(pix)

    return frames

def scan_animation_bounds(frames):
    max_w = 0
    max_h = 0

    for pix in frames:
        max_w = max(max_w, pix.width())
        max_h = max(max_h, pix.height())

    return max_w, max_h

class Animator:  # contains different animation functions
    def __init__(self,):
        self.frames = []
        self.index = 0
        self.timer = 0
        self.loop = True
        self.ticks_left = 0
        self.done = False

    def set(self, frames, fps, loop, times_to_loop, holds=None): #sets the animatios. receives a list of PixMap (frames), int (fps) and a bool(loop)
        self.frames = frames
        self.fps = fps if fps > 0 else 0.001
        self.loop = loop
        self.times_to_loop = times_to_loop
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

                # print(self.index)

                if self.index >= len(self.frames):
                    print("Animator: Pulse.ANIMATION_END ")
                    pet.state_machine.pulse(Pulse.ANIMATION_END)  # if the index of the frame is more than we have frames, the animation is considered finished(for ease of connecting animations together), else - not

                    if self.loop or self.times_to_loop >= 2 :
                        self.index = 0
                        self.times_to_loop -= 1
                    else:
                        self.index = len(self.frames) - 1
                        print("Animator: Flag.ANIMATION_FINISHED ")
                        pet.state_machine.raise_flag(Flag.ANIMATION_FINISHED)
                        self.done = True


                self.ticks_left = self.hold_for(self.index)


    def hold_for(self, index):
        return self.holds.get(index + 1, 1)

    def frame(self): #returns a single frame which should be displayed at the moment
        return self.frames[self.index]


class Pet(QWidget): # main logic
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)   # type: ignore # QT stuff idk idc
        self.setAttribute(Qt.WA_TranslucentBackground) # type: ignore

        # get all animations in a dictionary
        self.animations = {}
        base = os.path.dirname(os.path.abspath(__file__))
        for name in list(ANIMATIONS):
            cfg = ANIMATIONS[name]
            folder = os.path.join(base, cfg["folder"])

            frames = []

            frames = load_frames(folder)

            if not frames:
                raise RuntimeError(f"No frames found for animation '{name}'")

            self.animations[name] = {
                "frames": frames,
                "fps": cfg["fps"],
                "loop": cfg["loop"],
                "holds": cfg.get("holds", {}),
                "bounds": scan_animation_bounds(frames),
                "times_to_loop": cfg.get("times_to_loop", 1)
            }
            print(f"[ANIM LOAD] {name}: {len(frames)} frames")

                  
        self.variables = VariableManager(VARIABLES)
        self.animator = Animator()

        self.hitbox_width = 0
        self.hitbox_height = 0
        
        self.mover = Mover(self)
        self.anchor_x = 500
        self.anchor_y = 500

        self.primary_screen = QApplication.primaryScreen()
        screen = QApplication.primaryScreen() # Screen detection
        self.taskbar_top = screen.availableGeometry().bottom() # Taskbar position detection
        self.mover.set_position(100, self.taskbar_top + 1) # set initial position

        cfg_facing = RENDER_CONFIG.get("default_facing")
        self.facing = Facing.__members__.get(cfg_facing, Facing.RIGHT)  # type: ignore # defining dacing direction

        self.behaviour_resolver = BehaviourResolver(self)

        h = screen.availableGeometry().height()
        initial_state = INITIAL_STATE.get("default", next(iter(INITIAL_STATE))) #either get the "default" from the INITIAL STATE, or the first item in the STATES dictinary
        
        self.update_dpi_and_scale(h=h, initial_state=initial_state)

        self.state_machine = StateMachine(pet=self, configs=STATES, initial=initial_state) # set initial state
        self.click_detector = ClickDetector(pet=self) #initialising ClickDetector

        self.last_mouse_pos = Vec2()

        self.update_hitbox_size_and_drag_offset() # initial hitbox update


        # Timer for updating logic
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_logic)
        self.timer.start(1000 // FPS)


    def on_state_enter(self, state): #called in state_machine when entering a new state
        print("STATE:", state)
        
        self.variables.set("times_clicked_this_state", 0)
        self.variables.set("time_spent_in_this_state", 0)

        cfg = STATES[state]      # gets the config for the state from states.py
        anim_name = cfg.get("animation")

        self.play_animation(anim_name=anim_name, cfg=cfg)
        # self.update() # I think it helps with glitching, so it repaints right after a new animation is set

        movement_settings = cfg.get("settings", {})
        acceleration = movement_settings.get("acceleration", self.mover.acceleration)
        max_speed = movement_settings.get("max_speed", self.mover.max_speed)
        slow_radius = movement_settings.get("slow_radius", self.mover.slow_radius)
        snap_distance = movement_settings.get("snap_distance", self.mover.snap_distance)
        jump_velocity = movement_settings.get("jump_velocity", self.mover.jump_velocity)
        gravity = movement_settings.get("gravity", self.mover.gravity)
        self.mover.set_settings(acceleration=acceleration, max_speed=max_speed, slow_radius=slow_radius, snap_distance=snap_distance, jump_velocity=jump_velocity,gravity=gravity)

        behaviour_name = cfg.get("behaviour", "STATIONARY")
        # print(behaviour_name)

        target_x, target_y, type, settings = self.behaviour_resolver.resolve(behaviour_name)

        if type == MovementType.STATIONARY: # hardcoded doing nothing for stationary
            return

        if type == MovementType.DRAG:  # hardcoded behaviour for drag
            self.mover.movement_type = MovementType.DRAG

            if not self.click_detector.press_pos: #safe check
                self.mover.end_drag()
                return
            
            pos = Vec2(self.click_detector.press_pos.x(), self.click_detector.press_pos.y())
            self.mover.begin_drag(pos)
            return

        self.mover.set_position(self.anchor_x, self.anchor_y)
        self.mover.move_to(target_x, target_y, type)

       
    def on_state_exit(self, state): #just does nothing when the state is done
        pass

    def play_animation(self, anim_name, cfg, isTransitionAnimation = False):
        anim_name = anim_name

        if anim_name not in ANIMATIONS:
            raise Exception("ANIMATION", anim_name, "NOT FOUND")  #no idea what this does will add user notification that error occured

        anim_cfg = ANIMATIONS[anim_name]

        frames = self.animations[anim_name]["frames"]
        fps = cfg.get("fps", anim_cfg.get("fps", 6)) # safestate, will default to the latter
        loop_option = RENDER_CONFIG.get("default_loop_option", False)
        loop = cfg.get("loop", anim_cfg.get("loop", loop_option)) # safestate, will default to the latter
        times_to_loop = cfg.get("times_to_loop", anim_cfg.get("times_to_loop", 1))
        holds = cfg.get("holds", anim_cfg.get("holds", {}))  # safestate, will default to empty directory

        bounds_w, bounds_h = self.animations[anim_name]["bounds"]
        self.resize_keep_anchor(int(bounds_w * self.scale), int(bounds_h * self.scale))

        if isTransitionAnimation: 
            loop = False  #if receiving a transition animation, looping is disabled
            # print("transition animation playing")

        # print("starting animation", anim_name, " Frame count:", len(frames), " loop:", loop, " times to loop:", times_to_loop, " holds:", holds)
        self.animator.set(frames=frames, fps=fps, loop=loop, times_to_loop=times_to_loop, holds=holds) #sets animation in animator

    def _mouse_vec(self, event):   #helper function for converting Qt points to Vec2
        p = event.globalPosition()
        return Vec2(p.x(), p.y())
    
    def update_logic(self):
        dt = 1 / 60

        # --- INPUT PHASE ---
        if self.mover.movement_type == MovementType.DRAG:
            self.mover.update_drag_target(self.last_mouse_pos)
    
        self.click_detector.update()
        self.variables.update(dt)
    
        # --- STATE / SIMULATION PHASE ---
        self.animator.update(dt)
        arrived = self.mover.update(dt)

        
        if arrived:
            self.click_detector.release()
            self.state_machine.raise_flag(Flag.MOVEMENT_FINISHED)

        self.state_machine.update(dt)

        # print("position is", self.mover.pos.x, self.mover.pos.y)
        # print("facing is", self.facing)
    
        # --- POSITION SYNC PHASE ---
        self.anchor_x = self.mover.pos.x
        self.anchor_y = self.mover.pos.y
    
        self.apply_window_position()
    
        self.update()  # repaint
    

    def apply_window_position(self):
        self.move(
            int(self.anchor_x - self.width() / 2),
            int(self.anchor_y - self.height())
        )

    def resize_keep_anchor(self, new_w, new_h):
        old_pos = self.pos()
        old_w = self.width()
        old_h = self.height()

        # world-space anchor (bottom-middle)
        self.anchor_x = old_pos.x() + old_w // 2
        self.anchor_y = old_pos.y() + old_h

        # move window so anchor stays fixed
        self.move(
            self.anchor_x - new_w // 2,
            self.anchor_y - new_h
        )

        # resize
        self.resize(new_w, new_h)
    
    def update_dpi_and_scale(self, h, initial_state):
        percentage = RENDER_CONFIG["pet_size_on_screen"] / 100
        
        self.dpi_scale = self.devicePixelRatioF()
        first_frame = self.animations[STATES[initial_state]["animation"]]["frames"][0]
        self.pixel_ratio = (h * percentage) / first_frame.height() / self.dpi_scale
        print("screen height", h)
        print("dirst frame h:", first_frame.height())
        print("pixel ratio", self.pixel_ratio)

        self.scale = self.pixel_ratio * self.dpi_scale

        print("screen dpi", self.dpi_scale)
        print("new scale", self.scale)

    def update_hitbox_size_and_drag_offset(self):
            frame = self.animator.frame()
            if not frame:
                return
                      
            self.hitbox_width = frame.width() * self.scale
            self.hitbox_height = frame.height() * self.scale

            # print(self.hitbox_height)
            # print(self.hitbox_width)

            self.mover.drag_offset = Vec2(self.hitbox_width * RENDER_CONFIG["drag_offset_x"], self.hitbox_height * RENDER_CONFIG["drag_offset_y"])


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: # type: ignore
            self.click_detector.press(event.globalPosition())
            self.last_mouse_pos = self._mouse_vec(event)


    def mouseMoveEvent(self, event):
        self.click_detector.move(event.globalPosition())

        self.last_mouse_pos = self._mouse_vec(event)


    def mouseReleaseEvent(self, event):
        self.click_detector.release()
        if self.mover.movement_type == MovementType.DRAG:
            self.mover.end_drag()      

    def focusOutEvent(self, event):
        self.mover.end_drag()  

    def leaveEvent(self, event):
        self.mover.end_drag()  


    def paintEvent(self, e): #draws the frame reveived from Animator 
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True) # pyright: ignore[reportAttributeAccessIssue]

        # p.fillRect(self.rect(), QColor(80, 80, 80))  # dark gray

        frame = self.animator.frame()
        if not frame:
            return

        # draw sprite so its bottom-middle is at (self.x, self.y)
        anchor_x = self.width() / 2
        anchor_y = self.height()

        offset_x = frame.width() / 2
        offset_y = frame.height()

        p.save()

        sx = self.scale
        if self.facing == Facing.LEFT:
            sx *= -1

        # p.scale(sx, self.scale)

        p.translate(anchor_x, anchor_y)

        #draws pets hitbox, pretty neat
        # p.setPen(QPen(Qt.red, 3))
        # p.drawRect(-self.hitbox_width/2, -self.hitbox_height, self.hitbox_width, self.hitbox_height)
        

        # p.setPen(QPen(Qt.green, 6))
        # p.drawEllipse(QPointF(0, 0), 2, 2)

        # p.setPen(QPen(Qt.blue, 3))
        # p.drawLine(self.width(), 0, 0, self.height())
        # p.drawLine(offset_x, offset_y, anchor_x, anchor_y)

        p.scale(sx, self.scale)
        p.drawPixmap(-offset_x, -offset_y, frame)

        p.restore()


if __name__ == "__main__": # QT stuff, idk idc
    app = QApplication(sys.argv)
    pet = Pet()
    # pet.move(300, 900)
    pet.show()
    sys.exit(app.exec())
