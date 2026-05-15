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
from engine.animator import Animator
from engine.enums import Flag, Pulse, MovementType, Facing, SurfaceType
from engine.vec2 import Vec2
from engine.behaviour_resolver import BehaviourResolver
# from engine.windows_detector import WindowsDetector
from engine.windows_detector import WindowsOverlay


from data.variables import VARIABLES
from engine.variable_manager import VariableManager

LOGIC_FPS = RENDER_CONFIG.get("logic_FPS", 60) #fps of logic processes

#region --- HELPERS ---
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

#endregion

class Pet(QWidget): # main logic
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)   # type: ignore # QT stuff idk idc
        self.setAttribute(Qt.WA_TranslucentBackground) # type: ignore

        # get all animations in a dictionary
        self.animations = {}
        base = os.path.dirname(os.path.abspath(__file__))

        max_bounds_w = 0
        max_bounds_h = 0

        for name in list(ANIMATIONS):
            cfg = ANIMATIONS[name]
            folder = os.path.join(base, cfg["folder"])

            frames = []

            frames = load_frames(folder)

            if not frames:
                raise RuntimeError(f"No frames found for animation '{name}'")
            
            bounds_w, bounds_h = scan_animation_bounds(frames)
            max_bounds_w = max(max_bounds_w, bounds_w)
            max_bounds_h = max(max_bounds_h, bounds_h)

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
        self.animator = Animator(self)

        self.hitbox_width = 0
        self.hitbox_height = 0

        self.parent_window_hwnd = None
        self.parent_window_rect_last = None

        self.stay_on_window_when_resize = RENDER_CONFIG.get("stay_on_window_when_resize", False) 
        
        self.mover = Mover(self)
        self.anchor = Vec2(500, 500)

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

        max_measurement = max(max_bounds_w, max_bounds_h)
        self.resize_keep_anchor(int(max_measurement * self.scale * 2), int(max_measurement * self.scale * 2))

        self.state_machine = StateMachine(pet=self, configs=STATES, initial=initial_state) # set initial state
        self.click_detector = ClickDetector(pet=self) #initialising ClickDetector

        self.windowsOverlay = WindowsOverlay(self)


        self.last_mouse_pos = Vec2()

        self.drag_offset = Vec2(0,0)
        self.rotation_angle = 0

        self.update_hitbox_size_and_drag_offset() # initial hitbox update


        # Timer for updating logic
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_logic)
        self.timer.start(1000 // LOGIC_FPS)


    def on_state_enter(self, state): #called in state_machine when entering a new state
        print("STATE:", state)
        self.current_state = state
        if self.parent_window_hwnd:
            print(f"Position: {self.anchor.x}, {self.anchor.y}\nState: {self.current_state}\nParent window: {self.parent_window_hwnd}\nParent window position: {self.parent_window_rect_last}")
        
        self.variables.set("times_clicked_this_state", 0)
        self.variables.set("time_spent_in_this_state", 0)

        cfg = STATES[state]      # gets the config for the state from states.py
        anim_name = cfg.get("animation")

        movement_settings = cfg.get("settings", {})

        if movement_settings:
            acceleration = movement_settings.get("acceleration", self.mover.acceleration)
            max_speed = movement_settings.get("max_speed", self.mover.max_speed)
            slow_radius = movement_settings.get("slow_radius", self.mover.slow_radius)
            snap_distance = movement_settings.get("snap_distance", self.mover.snap_distance)
            # drag specific
            max_angle = movement_settings.get("max_angle", self.mover.max_angle)
            inertia = movement_settings.get("inertia", self.mover.inertia)
            damping = movement_settings.get("damping", self.mover.damping)
            # jump specific
            jump_velocity = movement_settings.get("jump_velocity", self.mover.jump_velocity)
            gravity = movement_settings.get("gravity", self.mover.gravity)
            self.mover.set_settings(acceleration=acceleration, max_speed=max_speed, slow_radius=slow_radius, snap_distance=snap_distance, max_angle=max_angle, inertia=inertia, damping=damping, jump_velocity=jump_velocity,gravity=gravity)
        else:
            self.mover.reset_settings()

        self.behaviour_name = cfg.get("behaviour", "STATIONARY")
        # print(self.behaviour_name)

        target_x, target_y, type, mover_settings, collision_settings, parenting_settings = self.behaviour_resolver.resolve(self.behaviour_name)
        self.surface_to_collide_with = collision_settings
        self.surfaces_to_parent_to = parenting_settings

        isAbletoRotate = True if type == MovementType.DRAG else False

        self.play_animation(anim_name=anim_name, cfg=cfg, isAbletoRotate=isAbletoRotate)

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

        self.mover.set_position(self.anchor) #type: ignore
        self.mover.move_to(target_x, target_y, type)

       
    def on_state_exit(self, state): #just does nothing when the state is done
        pass

    def play_animation(self, anim_name, cfg, isTransitionAnimation = False, isAbletoRotate = False):
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

        # if not isAbletoRotate:
        #     self.resize_keep_anchor(int(bounds_w * self.scale), int(bounds_h * self.scale))
        # else: 
        #     self.resize_keep_anchor(int(bounds_h * self.scale * 2), int(bounds_h * self.scale * 2))

        if isTransitionAnimation: 
            loop = False  #if receiving a transition animation, looping is disabled
            # print("transition animation playing")

        # print("starting animation", anim_name, " Frame count:", len(frames), " loop:", loop, " times to loop:", times_to_loop, " holds:", holds)
        self.animator.set(frames=frames, fps=fps, loop=loop, times_to_loop=times_to_loop, holds=holds) #sets animation in animator

    def _mouse_vec(self, event):   #helper function for converting Qt points to Vec2
        p = event.globalPosition()
        return Vec2(p.x(), p.y())
    
    def update_logic(self):  # UPDATE LOGIC
        dt = 1 / LOGIC_FPS

        t0 = time.perf_counter()

        # --- INPUT PHASE ---
        if self.mover.movement_type == MovementType.DRAG:
            self.mover.update_drag_target(self.last_mouse_pos, dt)
            self._clear_parent_window()
    
        self.click_detector.update()
        self.variables.update(dt)

        t1 = time.perf_counter()
    
        # --- STATE / SIMULATION PHASE ---
        # surface = self.windowsOverlay.get_nearest_surface("up", hitbox_h=self.hitbox_height, hitbox_w=self.hitbox_width)
        # print(surface)

        self.animator.update(dt)
        t3 = time.perf_counter()

        self.windowsOverlay.update_frame()
        
        # pply parent window movement
        self._follow_parent_window()
        t4 = time.perf_counter()

        # --- updating Mover and movement collisions ---
        arrived = self.mover.update(dt)
        
        dx = self.mover.pos.x - self.anchor.x
        dy = self.mover.pos.y - self.anchor.y

        col_x, col_y = False, False
        surface_data = None

        # --- checking for collisions and applying delta ---
        if self.mover.movement_type != MovementType.DRAG and dx != 0:
            # print("arrived", arrived)
            # print("before", dx)
            dx, col_x, surface_data = self.windowsOverlay.collide_horizontal(self.anchor.x, self.anchor.y, dx, collision_mask=self.surface_to_collide_with)
            # print("after", dx, "col_x:" , col_x)

        self.anchor.x += dx

        if not col_x and self.mover.movement_type != MovementType.DRAG and dy != 0:
            dy, col_y, surface_data = self.windowsOverlay.collide_vertical(self.anchor.x, self.anchor.y, dy, collision_mask=self.surface_to_collide_with)
            # print(dy)
        
        self.anchor.y += dy
        
        # --- if mover reached destination or collision occured - movement finished ---
        if arrived or col_x or col_y:
            # print("col_x: ", col_x, "self.surfaces: ", self.surfaces_to_parent_to)
            # print("making mover set position cuz", arrived, col_x, col_y)
            self.mover.set_position(self.anchor.x, self.anchor.y)
            self.click_detector.release()
            self.state_machine.raise_flag(Flag.MOVEMENT_FINISHED)

            if surface_data:
                # if not col_y: col_y = False
                if col_x in self.surfaces_to_parent_to or col_y in self.surfaces_to_parent_to:
                    self._set_parent_window(col_x, col_y, surface_data)

            arrived, col_x, col_y = False, False, False

        # print("position is", self.mover.pos.x, self.mover.pos.y)
        # print("facing is", self.facing)
        t5 = time.perf_counter()

        self.state_machine.update(dt)
        t6 = time.perf_counter()

        # --- SYNC PHASE ---
        self.clamp_position_to_screen()

        self.apply_window_position()
        t7 = time.perf_counter()

        # print(f"update windows frames takes {t3-t1}")

        self.update()  # repaint
    

    def clamp_position_to_screen(self):
        clamped_x = self.anchor.x
        clamped_x = min(self.primary_screen.availableGeometry().width() - self.hitbox_width / 2, max(self.anchor.x, self.hitbox_width / 2))

        clamped_y = self.anchor.y
        clamped_y = min(self.primary_screen.geometry().bottom(), max(self.anchor.y, self.hitbox_height))

        if self.anchor.y < self.hitbox_height:
            self._clear_parent_window()

        dx = clamped_x - self.anchor.x
        dy = clamped_y - self.anchor.y

        self.mover.move_global(dx,dy)

        self.anchor = Vec2(clamped_x, clamped_y)

    def _follow_parent_window(self):
        if not self.parent_window_hwnd:
            return

        # print("getting parent rect")
        rect = self.windowsOverlay.pet_parent_window_rect
        if not rect or not self.parent_window_rect_last:
            self.parent_window_rect_last = rect
            return

        x1, y1, x2, y2 = rect
        px1, py1, px2, py2 = self.parent_window_rect_last
        dx, dy = 0, 0

        # --- staying on windows or falling off ---
        resize = False
        if self.stay_on_window_when_resize:
            if self.parent_surface_type == SurfaceType.TOP or self.parent_surface_type == SurfaceType.BOTTOM:
                if self.anchor.x < x1 + self.hitbox_width/2:
                    self.anchor.x = x1 + self.hitbox_width/2
                    resize = True
                elif self.anchor.x > x2 - self.hitbox_width/2:
                    self.anchor.x = x2 - self.hitbox_width/2
                    resize = True
            elif self.parent_surface_type == SurfaceType.LEFT or self.parent_surface_type == SurfaceType.RIGHT:
                if self.anchor.y < y1 + self.hitbox_height:
                    self.anchor.y = y1 + self.hitbox_height
                    resize = True
                elif self.anchor.y > y2:
                    self.anchor.y = y2
                    resize = True

            if resize: self.mover.set_position(self.anchor.x, self.anchor.y)  # moving to the edge when resizing

        # if RENDER_CONFIG "stay_on_window_when_resize" == False pet should just fall off
        else:
            if self.parent_surface_type == SurfaceType.TOP or self.parent_surface_type == SurfaceType.BOTTOM:
                if self.anchor.x <= x1 - 2 or self.anchor.x >= x2 + 2:
                    self._clear_parent_window()
            if self.parent_surface_type == SurfaceType.LEFT or self.parent_surface_type == SurfaceType.RIGHT:
                if self.anchor.y <= y1 - 2 or self.anchor.y >= y2 + 2:
                    self._clear_parent_window()


        # --- following general movement ---
        match self.parent_surface_type:
            case SurfaceType.LEFT:
                if (y1 - py1) == (y2 - py2): dy = y1 - py1 
                dx = x1 - px1
                if dx == 0 and self.anchor.x != x1: dx = x1 - self.anchor.x
            case SurfaceType.TOP:
                if (x1 - px1) == (x2 - px2): dx = x1 - px1 
                dy = y1 - py1
                if dy == 0 and self.anchor.y != y1: dy = y1 - self.anchor.y
            case SurfaceType.RIGHT:
                if (y1 - py1) == (y2 - py2): dy = y1 - py1 
                dx = x2 - px2
                if dx == 0 and self.anchor.x != x2: dx = x2 - self.anchor.x
            case SurfaceType.BOTTOM:
                if (x1 - px1) == (x2 - px2): dx = x1 - px1 
                dy = y2 - py2
                if dy == 0 and self.anchor.y != y2: dy = y2 - self.anchor.y

        # Applying global movement
        if dx != 0 or dy != 0:
            self.mover.move_global(dx, dy)

        self.parent_window_rect_last = rect

    def _clear_parent_window(self):
        self.state_machine.pulse(Pulse.LOST_PARENT)
        self.state_machine.raise_flag(Flag.NOT_PARENTED_TO_WINDOW)
        self.state_machine.remove_flag(Flag.PARENTED_TO_WINDOW)
        self.parent_window_hwnd = None
        self.parent_surface_type = None
        self.parent_window_rect_last = None

    def _set_parent_window(self, col_x, col_y, surface_data):
        hwnd = surface_data[0]

        if col_x:  
            self.parent_surface_type = col_x
        else: self.parent_surface_type = col_y
        # print("surface type:", self.parent_surface_type)

        if hwnd == "taskbar": return
        self.parent_window_hwnd = hwnd
        self.state_machine.pulse(Pulse.GAINED_PARENT)
        self.state_machine.raise_flag(Flag.PARENTED_TO_WINDOW)
        # self.parent_window_rect_last = self.windowsOverlay.pet_parent_window_rect   # it was causing weird behaviour when window moves
        # print("Parent window:", hwnd)

    def apply_window_position(self):
        self.move(
            int(self.anchor.x - self.width() / 2),
            int(self.anchor.y - self.height())
        )

    def resize_keep_anchor(self, new_w, new_h):
        old_pos = self.pos()
        old_w = self.width()
        old_h = self.height()

        # world-space anchor (bottom-middle)
        self.anchor.x = old_pos.x() + old_w // 2
        self.anchor.y = old_pos.y() + old_h

        new_x = self.anchor.x - new_w // 2
        new_y = self.anchor.y - new_h

        self.setGeometry(new_x, new_y, new_w, new_h)
    
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

            self.windowsOverlay.update_hitbox(self.hitbox_width, self.hitbox_height)

            # print(self.hitbox_height)
            # print(self.hitbox_width)

            self.drag_offset = Vec2(self.hitbox_width * RENDER_CONFIG["drag_offset_x"], self.hitbox_height * RENDER_CONFIG["drag_offset_y"])
            self.mover.drag_offset = self.drag_offset

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

    def keyPressEvent(self, e): #doesnt work when app is in background
        if e.key() == Qt.Key.Key_F4:
            print(f"______________________________\n\n  PET REPORT\n\nPosition: {self.anchor.x}, {self.anchor.y}\nState: {self.current_state}\nCurrent behaviour: {self.behaviour_name}\nParent window: {self.parent_window_hwnd}\nParent window position: {self.parent_window_rect_last}\n\n  ^^^.>.\n______________________________")
        elif e.key() == Qt.Key.Key_L:
            print("yeah okay")

    # def moveEvent(self, e):
    #     print("Move:", self.pos())

    # def resizeEvent(self, e):
    #     print("Resize:", self.size())

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

        # draws pets hitbox, pretty neat (says there are problems but works anyway)
        # p.setPen(QPen(Qt.red, 3))
        # p.drawRect(-self.hitbox_width/2, -self.hitbox_height, self.hitbox_width, self.hitbox_height)
        

        # p.setPen(QPen(Qt.green, 6))
        # p.drawEllipse(QPointF(0, 0), 2, 2)

        # p.setPen(QPen(Qt.blue, 3))
        # p.drawLine(self.width(), 0, 0, self.height())
        # p.drawLine(offset_x, offset_y, anchor_x, anchor_y)

        if self.rotation_angle != 0:
            cx, cy = self.drag_offset
            # // translate point back to origin:
            p.translate(cx, cy)
            # // rotate
            p.rotate(self.rotation_angle)
            # // translate point back:
            p.translate(-cx, -cy)

        p.scale(sx, self.scale)
        p.drawPixmap(-offset_x, -offset_y, frame)

        p.restore()


if __name__ == "__main__": # QT stuff, idk idc
    app = QApplication(sys.argv)
    pet = Pet()
    # pet.move(300, 900)
    pet.show()
    sys.exit(app.exec())
