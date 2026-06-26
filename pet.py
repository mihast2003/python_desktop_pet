# Main script with pet behavior: physics, drawing sprites, retrieving data
import sys, os, random, time, math
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QPixmap, QPen, QColor
from PySide6.QtCore import Qt, QTimer, QPointF

import threading

from ctypes import POINTER, cast
from ctypes.wintypes import MSG
import win32con

from enum import Enum, auto

from data.states import STATES, INITIAL_STATE
from data.animations import ANIMATIONS
from data.render_config import RENDER_CONFIG

from engine.asset_loader import AssetLoader
from engine.state_machine import StateMachine
from engine.click_detector import ClickDetector
from engine.mover import Mover
from engine.animator import Animator
from engine.enums import Flag, Pulse, MovementType, Facing, SurfaceType
from engine.vec2 import Vec2
from engine.behaviour_resolver import BehaviourResolver
from engine.windows_detector import WindowsOverlay
from engine.hotkey_manager import HotkeyManager
from engine.particles.particles_engine_openGL import ParticleOverlayWidget

import cProfile


from engine.variable_manager import VariableManager

LOGIC_FPS = RENDER_CONFIG.get("pet_logic_FPS", 30) #fps of logic processes
# DRAW_FPS = RENDER_CONFIG.get("pet_draw_FPS", 30) # not needed because it depends on the animation, might add later?

PARTICLE_LOGIC_FPS = RENDER_CONFIG.get("particles_logic_FPS", 30)
PARTICLE_DRAW_FPS = RENDER_CONFIG.get("particles_draw_FPS", 30)

#region --- HELPERS ---
# ANIMATION STUFF

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
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        print("----- LOADING ANIMATIONS -----")
        # get all animations in a dictionary
        self.animations = {}
        base = os.path.dirname(os.path.abspath(__file__))

        max_bounds_w = 0
        max_bounds_h = 0

        for name in list(ANIMATIONS):
            cfg = ANIMATIONS[name]
            folder = os.path.join(base, cfg["folder"])

            frames = []

            frames = AssetLoader.load_QPixmap_frames(folder=folder)

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
                "bounds": (bounds_w, bounds_h),
                "times_to_loop": cfg.get("times_to_loop", 1)
            }
            print(f"[ANIM LOAD] {name}: {len(frames)} frames")
    
        self.variables = VariableManager()
        self.animator = Animator(self)
        self.prev_index = None

        self.hotkeys = HotkeyManager(self) # not doing anything for now, meh
        # self.hotkeys.messagag()

        self.profiler = cProfile.Profile()
        self.not_first_time_update: bool = False
        self.start_debugging = False

        self.hitbox_width = 0
        self.hitbox_height = 0

        self.parent_window_hwnd = None
        self.parent_window_rect_last = None

        self.stay_on_window_when_resize = RENDER_CONFIG.get("stay_on_window_when_resize", False) 

        self.primary_screen = QApplication.primaryScreen()
        init_pos = Vec2(RENDER_CONFIG.get("initial_position", (100, 0)))
        
        self.mover = Mover(self)
        self.primary_screen = QApplication.primaryScreen() # Screen detection
        self.taskbar_top = self.primary_screen.availableGeometry().bottom() # Taskbar position detection
        self.mover.set_position(init_pos.x, self.taskbar_top + init_pos.y + 1) # set initial position
        self.anchor = Vec2(init_pos.x, self.taskbar_top + init_pos.y + 1)

        # print("ACNHOCRR", self.anchor)

        cfg_facing = RENDER_CONFIG.get("default_facing")
        self.facing = Facing.__members__.get(cfg_facing, Facing.RIGHT) # type: ignore  # defining facing direction

        self.behaviour_resolver = BehaviourResolver(self)

        self.windowsOverlay = WindowsOverlay(self)
        self.particle_engine = ParticleOverlayWidget(pet=self)
        self.particle_logic_acc = 0
        self.particle_draw_acc = 0
        
        initial_state = INITIAL_STATE.get("default", next(iter(INITIAL_STATE))) #either get the "default" from the INITIAL STATE, or the first item in the STATES dictinary
        
        h = self.primary_screen.availableGeometry().height()
        self.update_dpi_and_scale(h=h, initial_state=initial_state)

        # print("ACNHOCRR 222", self.anchor)
        max_measurement = max(max_bounds_w, max_bounds_h)
        self.resize_keep_anchor(int(max_measurement * self.scale * 2), int(max_measurement * self.scale * 2))

        # print("ACNHOCRR 333", self.anchor)

        self.last_mouse_pos = Vec2()

        self.drag_offset = Vec2(0,0)
        self.rotation_angle = 0
        
        anim_name = RENDER_CONFIG.get("hitbox_from_animation")
        if anim_name not in self.animations:
            cfg = STATES[initial_state]      # gets the config for the state from states.py
            anim_name = cfg.get("animation")
        frame = self.animations[anim_name]["frames"][0]
        self.update_hitbox_size_and_drag_offset(frame=frame) # initial hitbox update

        self.state_machine = StateMachine(pet=self, configs=STATES, initial=initial_state) # set initial state
        self.click_detector = ClickDetector(pet=self)

        print("----- LOADING SUCCESSFUL -----\n")

        # Timer for updating logic
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_logic)
        self.timer.start(1000 // LOGIC_FPS)


    def on_state_enter(self, state): # called in state_machine when entering a new state
        # print("STATE:", state)
        self.current_state = state
        if self.parent_window_hwnd:
            print(f"Position: {self.anchor.x}, {self.anchor.y}\nState: {self.current_state}\nParent window: {self.parent_window_hwnd}\nParent window position: {self.parent_window_rect_last}")
        
        self.variables.set("times_clicked_this_state", 0)
        self.variables.set("time_spent_in_this_state", 0)

        cfg = STATES[state]      # gets the config for the state from states.py

        next_behaviour = cfg.get("behaviour", "STATIONARY") # engage behaviours.py
        self.resolve_behavior(next_behaviour, cfg)

        anim_name = cfg.get("animation")
        # isAbletoRotate = True if self.mover.movement_type == MovementType.DRAG else False   # not used anymore but maybe later
        self.play_animation(anim_name=anim_name, cfg=cfg)

       
    def on_state_exit(self, state): # called in state_machine when exiting a state
        cfg = STATES[state]
        # print("exiting state", state)
        # if state == "FALLING":
        #     self.emit_particles("dirt") 
        pass

    def resolve_behavior(self, behaviour, cfg):
        # print(self.behaviour_name)
        self.behaviour_name = behaviour
        target_x, target_y, type, mover_settings, collision_settings, parenting_settings = self.behaviour_resolver.resolve(self.behaviour_name)
        self.surface_to_collide_with = collision_settings
        self.surfaces_to_parent_to = parenting_settings

        if mover_settings: # using mover settings from behaviours first
            acceleration = mover_settings.get("acceleration", self.mover.acceleration)
            max_speed = mover_settings.get("max_speed", self.mover.max_speed)
            slow_radius = mover_settings.get("slow_radius", self.mover.slow_radius)
            snap_distance = mover_settings.get("snap_distance", self.mover.snap_distance)
            # drag specific
            max_angle = mover_settings.get("max_angle", self.mover.max_angle)
            inertia = mover_settings.get("inertia", self.mover.inertia)
            damping = mover_settings.get("damping", self.mover.damping)
            # jump specific
            jump_velocity = mover_settings.get("jump_velocity", self.mover.jump_velocity)
            gravity = mover_settings.get("gravity", self.mover.gravity)
            self.mover.set_settings(acceleration=acceleration, max_speed=max_speed, slow_radius=slow_radius, snap_distance=snap_distance, max_angle=max_angle, inertia=inertia, damping=damping, jump_velocity=jump_velocity,gravity=gravity)

        movement_settings = cfg.get("settings", {}) # get mover settings from states.py

        if movement_settings: # adding overrides from states
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

        # print("on state change", end="")
        self.mover.move_to(target_x, target_y, type)

    def emit_particles(self, name):
        self.particle_engine.raise_() # raises particles above pet
        self.particle_engine.start_emitting(name, False) 

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

        # bounds_w, bounds_h = self.animations[anim_name]["bounds"]  # not used yet but its there if needed

        if isTransitionAnimation:
            loop = False  #if receiving a transition animation, looping is disabled
            # print("transition animation playing")

        # print("starting animation", anim_name, " Frame count:", len(frames), " loop:", loop, " times to loop:", times_to_loop, " holds:", holds)
        self.animator.set(frames=frames, fps=fps, loop=loop, times_to_loop=times_to_loop, holds=holds) # sets animation in animator

    def _update_apps(self, active, visible, maximised, fullscreen):
        self.state_machine.update_apps(active, visible, maximised, fullscreen)

    def update_logic(self):  # UPDATE LOGIC
        dt = 1 / LOGIC_FPS

        if self.start_debugging:
            self.profiler.disable()
            self.profiler.enable()  # start profiling
        
        # --- INPUT PHASE ---
        if self.mover.movement_type == MovementType.DRAG:
            self.mover.update_drag_target(self.last_mouse_pos, dt)
            if self.parent_window_hwnd:
                self._clear_parent_window()
    
        self.click_detector.update()
        self.variables.update(dt)

        t1 = time.perf_counter()
    
        # --- STATE / SIMULATION PHASE ---
        # surface = self.windowsOverlay.get_nearest_surface("up", hitbox_h=self.hitbox_height, hitbox_w=self.hitbox_width)
        # print(surface)

        # self.windowsOverlay.update_frame() # experimenting with automatic windows hook updates instead of 60 fps

        self.parent_window_rect = None
        if self.parent_window_hwnd:
            self.parent_window_rect = self.windowsOverlay.update_parent_window(self.parent_window_hwnd)
    
        # --- STATE / SIMULATION PHASE ---
        
        # Apply parent window movement
        followed_parent = self._follow_parent_window(self.parent_window_rect)
        t3 = time.perf_counter()

        self.animator.update(dt)
        t4 = time.perf_counter()

        # --- updating Mover and movement collisions ---
        arrived = self.mover.update(dt) # getting theoretical movement from mover.py
        
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
            print("if arrived", end="")
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
        self._clamp_position_to_screen()

        if dx or dy or followed_parent:
            self.apply_window_position()
        t7 = time.perf_counter()

        # checking if next frame is not the same as current and updating then
        index = self.animator.index
        if not self.prev_index: self.prev_index = index + 1

        if index != self.prev_index or self.mover.movement_type == MovementType.DRAG: 
            # print("triggering update because", index, self.prev_index)
            self.update()  # repaint
        self.prev_index = index

        # --- UPDATING PARTICLES ---
        t8 = time.perf_counter()
        self.particle_logic_acc += dt
        self.particle_draw_acc += dt

        if self.particle_logic_acc >= 1 / PARTICLE_LOGIC_FPS:
            self.particle_logic_acc -= 1 / PARTICLE_LOGIC_FPS
            self.particle_engine.update_logic(1 / PARTICLE_LOGIC_FPS)

        t9 = time.perf_counter()

        if self.particle_draw_acc >= 1 / PARTICLE_DRAW_FPS:
            self.particle_draw_acc -= 1 / PARTICLE_DRAW_FPS
            self.particle_engine.draw()

        t10 = time.perf_counter()
        # print(f"Particle update: {t1-t0}\nParticles draw: {t2-t1}")

        # print(f"update windows frames takes {t3-t1}")
        self.profiler.disable()  # stop profiling
        self.profiler.dump_stats("test.prof")

    def _clamp_position_to_screen(self):
        # clamped_x = self.anchor.x
        clamped_x = min(self.primary_screen.availableGeometry().width() - self.hitbox_width / 2, max(self.anchor.x, self.hitbox_width / 2))

        # clamped_y = self.anchor.y
        clamped_y = min(self.primary_screen.geometry().bottom(), max(self.anchor.y, self.hitbox_height))

        if self.anchor.y < self.hitbox_height:  # if going above the screen - clear parent window
            self._clear_parent_window()

        dx = clamped_x - self.anchor.x
        dy = clamped_y - self.anchor.y

        self.mover.move_global(dx,dy)

        self.anchor.x = clamped_x
        self.anchor.y = clamped_y

    def _follow_parent_window(self, rect):
        if not self.parent_window_hwnd:
            return

        # print("getting parent rect")

        # rect = self.windowsOverlay.pet_parent_window_rect

        if not rect or not self.parent_window_rect_last:
            self.parent_window_rect_last = rect
            return

        x1, y1, x2, y2 = rect
        px1, py1, px2, py2 = self.parent_window_rect_last
        dx, dy = 0, 0

        # --- following general movement ---
        global_move_x = (x1 - px1) == (x2 - px2)
        global_move_y = (y1 - py1) == (y2 - py2)


        match self.parent_surface_type:   # previously had {if dx == 0 and } but removed to better snap to windows
            case SurfaceType.LEFT:
                if global_move_y: dy = y1 - py1 
                dx = x1 - px1
                if self.anchor.x != x1: dx = x1 - self.anchor.x
            case SurfaceType.TOP:
                if global_move_x: dx = x1 - px1 
                dy = y1 - py1
                if self.anchor.y != y1: dy = y1 - self.anchor.y
            case SurfaceType.RIGHT:
                if global_move_y: dy = y1 - py1 
                dx = x2 - px2
                if self.anchor.x != x2: dx = x2 - self.anchor.x
            case SurfaceType.BOTTOM:
                if global_move_x: dx = x1 - px1 
                dy = y2 - py2
                if self.anchor.y != y2: dy = y2 - self.anchor.y

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
            
            if resize: 
                # print("if resize", end="")
                self.mover.set_position(self.anchor.x, self.anchor.y)  # moving to the edge when resizing

        # if RENDER_CONFIG "stay_on_window_when_resize" == False pet should just fall off
        else:
            if not global_move_x and self.parent_surface_type in (SurfaceType.TOP, SurfaceType.BOTTOM): # its so much more nice to read, i hope its not too bad for performance
                if self.anchor.x <= x1 - 2 or self.anchor.x >= x2 + 2:
                    self._clear_parent_window()
            if not global_move_y and self.parent_surface_type in (SurfaceType.LEFT, SurfaceType.RIGHT):
                if self.anchor.y <= y1 - 2 or self.anchor.y >= y2 + 2:
                    self._clear_parent_window()

        # Applying global movement
        if dx != 0 or dy != 0:
            self.mover.move_global(dx, dy)

        self.parent_window_rect_last = rect

        return resize

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
        self.state_machine.remove_flag(Flag.NOT_PARENTED_TO_WINDOW)
        # print("Parent window:", hwnd)

    def apply_window_position(self):
        self.move(
            int(self.anchor.x - self.width() / 2),
            int(self.anchor.y - self.height())
        )

    def resize_keep_anchor(self, new_w, new_h):
        # old_pos = self.pos()
        # old_w = self.width()
        # old_h = self.height()
        # world-space anchor (bottom-middle)  # was it something useful? i commented out because it messed up anchor position when initialising
        new_x = self.anchor.x - new_w // 2
        new_y = self.anchor.y - new_h
        self.setGeometry(new_x, new_y, new_w, new_h)
    
    def update_dpi_and_scale(self, h, initial_state):
        percentage = RENDER_CONFIG["pet_size_on_screen"] / 100
        
        self.dpi_scale = self.devicePixelRatioF()
        first_frame = self.animations[STATES[initial_state]["animation"]]["frames"][0]
        self.pixel_ratio = (h * percentage) / first_frame.height() / self.dpi_scale
        print("screen height", h)
        print("first frame h:", first_frame.height())
        print("pixel ratio", self.pixel_ratio)

        self.scale = self.pixel_ratio * self.dpi_scale

        self.particle_engine.update_dpi_and_scale(self.scale)
        self.particle_engine.update_taskbar_position(self.taskbar_top)

        print("screen dpi", self.dpi_scale)
        print("new scale", self.scale)

    def update_hitbox_size_and_drag_offset(self, frame):
            if not frame:
                frame = self.animator.frame()
                      
            self.hitbox_width = frame.width() * self.scale
            self.hitbox_height = frame.height() * self.scale

            self.windowsOverlay.update_hitbox(self.hitbox_width, self.hitbox_height)
            self.particle_engine.update_hitbox(self.hitbox_width, self.hitbox_height)

            # print(self.hitbox_height)
            # print(self.hitbox_width)

            self.drag_offset = Vec2(self.hitbox_width * RENDER_CONFIG["drag_offset_x"], self.hitbox_height * RENDER_CONFIG["drag_offset_y"])
            self.mover.drag_offset = self.drag_offset

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: # type: ignore
            p = event.globalPosition()
            self.click_detector.press(p)
            self.last_mouse_pos =  Vec2(p.x(), p.y())

    def mouseMoveEvent(self, event):
        p = event.globalPosition()
        self.click_detector.move(p)
        self.last_mouse_pos =  Vec2(p.x(), p.y())

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
            print("Start debugging")
            self.start_debugging = True
    
    # def moveEvent(self, e):
    #     print("Move:", self.pos())

    # def resizeEvent(self, e):
    #     print("Resize:", self.size())

    def paintEvent(self, e): #draws the frame reveived from Animator 
        frame = self.animator.frame()
        if not frame:
            return
        
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True) # pyright: ignore[reportAttributeAccessIssue]

        # p.fillRect(self.rect(), QColor(80, 80, 80))  # dark gray

        # draw sprite so its bottom-middle is at (self.x, self.y)
        anchor_x = self.width() / 2
        anchor_y = self.height()

        offset_x = frame.width() / 2
        offset_y = frame.height()

        p.save()

        sx = self.scale
        if self.facing == Facing.LEFT:
            sx *= -1

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
    pet.show()
    pet.particle_engine.raise_()  # particles above
    sys.exit(app.exec())
