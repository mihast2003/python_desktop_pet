from engine.enums import Flag, Pulse, MovementType, Facing
from engine.vec2 import Vec2

class Mover:
    def __init__(self, pet):
        self.pos = Vec2()
        self.vel = Vec2()
        self.target = Vec2()

        self.pet = pet

        self.drag_offset = Vec2()

        self.acceleration = 1200.0
        self.max_speed = 700.0
        self.slow_radius = 120.0
        self.snap_distance = 8.0

        self.movement_type = None
        self.active = False

        # jump specific
        self.jump_velocity = 1000
        self.gravity = 2500.0
        self.grounded_y = None

    def set_settings(self, acceleration, max_speed, slow_radius, snap_distance, jump_velocity, gravity):
        self.acceleration = acceleration
        self.max_speed = max_speed
        self.slow_radius = slow_radius
        self.snap_distance = snap_distance
        # jump specific
        self.jump_velocity = jump_velocity
        self.gravity = gravity

    def set_position(self, x, y):
        self.pos = Vec2(x, y)

    def move_to(self, x, y, movement_type: MovementType):
        self.target = Vec2(x, y)
        self.vel = Vec2()
        self.movement_type = movement_type
        self.active = True

        if x < self.pos.x:
            self.pet.facing = Facing.LEFT
        elif x > self.pos.x:
            self.pet.facing = Facing.RIGHT

        if movement_type == MovementType.INSTANT:
            self.set_position(x, y)
        
        if movement_type == MovementType.JUMP:
            self.grounded_y = self.pos.y
            self.vel.y = -self.jump_velocity


        # print(pet.facing)

    def update(self, dt):
        if not self.active:
            return False

        match self.movement_type:

            case MovementType.DRAG:
                return False

            case MovementType.INSTANT:
                return True

            case MovementType.LINEAR:
                return self._update_linear(dt)

            case MovementType.ACCELERATE:
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
        # direction_x = 1 if self.target.x > self.pos.x else -1
        # self.vel.x = direction_x * self.max_speed # normal option, where it just shoots at the max speed at that direction

        self.vel.x = self.target.x - self.pos.x  # moves to whatever x you need with whatever speed is required

        # gravity
        self.vel.y += self.gravity * dt

        self.pos += self.vel * dt

        # landing
        if self.pos.y >= self.grounded_y:
            self.pos.y = self.grounded_y
            self.vel = Vec2()
            self.active = False
            print("landed after jumping")
            return True

        return False
    
    def begin_drag(self, mouse_pos: Vec2):
        self.movement_type = MovementType.DRAG
        self.pos = mouse_pos - self.drag_offset # initial snapping to cursor movement
        print ("SNAP")
        self.active = True
        self.vel = Vec2()

    def update_drag_target(self, mouse_pos: Vec2):
        if not self.movement_type == MovementType.DRAG:
            return

        screen = self.pet.primary_screen.availableGeometry()
        if mouse_pos.x >= screen.width() - self.pet.hitbox_width/2 or mouse_pos.x <= self.pet.hitbox_width/2 or mouse_pos.y >= screen.bottom():
            self.end_drag()
            return
        
        self.pos = mouse_pos - self.drag_offset
            

    def end_drag(self):
        if self.movement_type == MovementType.DRAG:
            self.active = False
            self.movement_type = None
            self.pet.state_machine.pulse(Pulse.DRAGGING_ENDED)
            self.pet.click_detector.release()
