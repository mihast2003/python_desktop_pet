import random
from PySide6.QtWidgets import QApplication
from engine.enums import MovementType
from data.behaviours import BEHAVIOURS


class BehaviourResolver:
    def __init__(self, pet):
        self.pet = pet

    def resolve(self, behaviour_name):
        cfg = BEHAVIOURS.get(behaviour_name)
        if not cfg:
            raise ValueError(f"Unknown behaviour: {behaviour_name}")

        movement = MovementType[cfg.get("movement", "STATIONARY")] # defaults to STATIONARY movement type

        settings = cfg.get("settings", {})

        target_cfg = cfg.get("target")
        if not target_cfg:
            return None, None, movement, settings
        
        x = self._resolve_axis("x", target_cfg["x"])
        y = self._resolve_axis("y", target_cfg["y"])


        return x, y, movement, settings
    
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
    
    def _resolve_bound(self, name, axis):
        screen = QApplication.primaryScreen().availableGeometry()

        if name == "screen.left":
            return self.pet.hitbox_width / 2

        if name == "screen.right":
            return screen.width() - self.pet.hitbox_width / 2

        if name == "screen.top":
            return self.pet.hitbox_height

        if name == "screen.bottom":
            return screen.height()

        raise ValueError(f"Unknown bound: {name}")

