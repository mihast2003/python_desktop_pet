import random
from PySide6.QtWidgets import QApplication
from engine.enums import MovementType, SurfaceType
from data.behaviours import BEHAVIOURS


class BehaviourResolver:
    def __init__(self, pet):
        self.pet = pet

    def resolve(self, behaviour_name):
        cfg = BEHAVIOURS.get(behaviour_name)
        if not cfg:
            raise ValueError(f"Unknown behaviour: {behaviour_name}, check data/behaviours.py")

        movement = MovementType[cfg.get("movement", "STATIONARY")] # defaults to STATIONARY movement type

        mover_settings = cfg.get("settings", {})

        collision_cfg = cfg.get("collide_with_surfaces", set())
        collision_settings = self._resolve_surfaceType(collision_cfg)

        parenting_cfg = cfg.get("parent_to_surfaces", set())
        parenting_settings = self._resolve_surfaceType(parenting_cfg)

        target_cfg = cfg.get("target")
        if not target_cfg:
            return None, None, movement, mover_settings, collision_settings, parenting_settings
        
        x = self._resolve_axis("x", target_cfg["x"])
        y = self._resolve_axis("y", target_cfg["y"])

        return x, y, movement, mover_settings, collision_settings, parenting_settings
    

    def _resolve_axis(self, axis, spec):
        if spec["type"] == "current":
            return self.pet.anchor.x if axis == "x" else self.pet.anchor.y

        if spec["type"] == "random":
            min_val = self._resolve_bound(spec["min"], axis)
            max_val = self._resolve_bound(spec["max"], axis)
            return random.randint(int(min_val), int(max_val))
        
        if spec["type"] == "random_range":
            current_pos = self.pet.anchor.x if axis == "x" else self.pet.anchor.y
            range = spec["range"]
            min_val = self._resolve_bound(spec["min"], axis)
            max_val = self._resolve_bound(spec["max"], axis)
            new_val = current_pos + random.randrange(-range, range)
            return max(min_val, min(max_val, new_val))   # returning a clamped value
        
        if spec["type"] == "fixed":
            val = self._resolve_bound(spec["to"], axis)
            return val

        raise ValueError(f"Unknown axis spec: {spec}")
    
    def _resolve_bound(self, name: str, axis):
        screen = QApplication.primaryScreen().availableGeometry()
        name = name

        if name.startswith("surface"):
            if self.pet.parent_window_hwnd:
                x1, y1, x2, y2 = self.pet.parent_window_rect_last
            else: name = name.replace("surface", "screen")

            if name == "surface.left":
                return x1 + self.pet.hitbox_width / 2 #type: ignore

            if name == "surface.right":
                return x2 - self.pet.hitbox_width / 2 #type: ignore
            
            if name == "surface.up":   # NOT SURE IT MIGHT BE Y2 AND Y1 i dunno
                return y1 - self.pet.hitbox_height #type: ignore

            if name == "surface.down":
                return y2 - self.pet.hitbox_height #type: ignore
            
        if name == "screen.left":
            return self.pet.hitbox_width / 2

        if name == "screen.right":
            return screen.width() - self.pet.hitbox_width / 2

        if name == "screen.top":
            return self.pet.hitbox_height

        if name == "screen.bottom":
            return screen.height()
        

        raise ValueError(f"Unknown bound: {name}")

    def _resolve_surfaceType(self, cfg):
        surfaces = set()

        if not cfg: return surfaces

        cmd_cfg = str(cfg).lower() # converting to lowercase string for ease of comparing

        if cmd_cfg in ["all"]:
            surfaces = surfaces.union(SurfaceType.__members__)
        elif cmd_cfg in ["x", "horizontal"]:
            surfaces = surfaces.union([SurfaceType.LEFT, SurfaceType.RIGHT])
        elif cmd_cfg in ["y", "vertical"]:
            surfaces = surfaces.union([SurfaceType.TOP, SurfaceType.BOTTOM])
        else:
            for surface in cfg:
                surfaces.add(SurfaceType.__members__.get(surface))

        # print(surfaces)
        return surfaces