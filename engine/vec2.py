import math

#vector class for vector stuff
class Vec2:
    __slots__ = ("x", "y")

    def __init__(self, x=0.0, y=None):
        
        # print("trying to make a vector2 out of ", x, y)

        if y is None:
            if isinstance(x, (tuple, list)):
                x, y = x
            else: y = 0.0

        self.x = float(x)
        self.y = float(y)


    def __repr__(self):
        return f"Vec2({self.x}, {self.y})"

    def copy(self):
        return Vec2(self.x, self.y)

    # math
    def __add__(self, other):
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, value):
        if isinstance(value, float):
            return Vec2(self.x * value, self.y * value)
        if isinstance(value, Vec2):
            return Vec2(self.x * value.x, self.y * value.y)

    __rmul__ = __mul__
        

    def __iter__(self):
        yield self.x
        yield self.y

    # utilities
    def length(self):
        return math.hypot(self.x, self.y)

    def normalized(self):
        l = self.length()
        if l == 0:
            return Vec2()
        return Vec2(self.x / l, self.y / l)

    def distance_to(self, other):
        return (self - other).length()

    def lerp(self, target, t: float):
        return self + (target - self) * t