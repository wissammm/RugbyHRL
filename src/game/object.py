import math


class Vec2:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> "Vec2":
        return self.__mul__(scalar)

    def __repr__(self) -> str:
        return f"Vec2({self.x:.3f}, {self.y:.3f})"

    def length(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalized(self) -> "Vec2":
        l = self.length()
        if l == 0:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / l, self.y / l)

    def dot(self, other: "Vec2") -> float:
        return self.x * other.x + self.y * other.y

    def copy(self) -> "Vec2":
        return Vec2(self.x, self.y)


class Circle:
    def __init__(self, pos: Vec2, radius: float):
        self.pos = pos
        self.radius = radius


class Rectangle:
    def __init__(self, pos: Vec2, width: float, height: float):
        self.pos = pos          # top-left corner
        self.width = width
        self.height = height

class GroundTile(Rectangle):
    def __init__(self, pos: Vec2, width: float, height: float,
                 friction: float = 0.9, slow_factor: float = 1.0):
        super().__init__(pos, width, height)
        self.friction = friction
        self.slow_factor = slow_factor

    def contains(self, point: Vec2) -> bool:
        return (self.pos.x <= point.x <= self.pos.x + self.width and
                self.pos.y <= point.y <= self.pos.y + self.height)

class Ball(Circle):

    def __init__(self, pos: Vec2, radius: float,
                 bounce_damp: float = 0.75, friction: float = 0.95):
        super().__init__(pos, radius)
        self.velocity    : Vec2  = Vec2(0.0, 0.0)
        self.is_held     : bool  = False
        self.holder      : "Entity | None" = None
        self.bounce_damp : float = bounce_damp # loss energy while doing a bounce 
        self.friction    : float = friction


class Entity(Circle):
    def __init__(self, pos: Vec2, radius: float, team: int,
                 max_speed: float = 3.0):
        super().__init__(pos, radius)
        self.team           : int   = team
        self.velocity       : Vec2  = Vec2(0.0, 0.0)
        self.max_speed      : float = max_speed
        self.has_ball       : bool  = False
        self.push_cooldown  : int   = 0


class Player(Entity):
    def __init__(self, pos: Vec2, radius: float = 10.0, team: int = 0,
                 max_speed: float = 3.5,
                 push_every_n_steps: int = 10,
                 push_force: float = 8.0,
                 throw_force: float = 12.0):
        super().__init__(pos, radius, team, max_speed)
        self.push_every_n_steps : int   = push_every_n_steps
        self.push_force         : float = push_force
        self.throw_force        : float = throw_force
        self.throw_cooldown     : int   = 0   # pickup blocked while > 0


class Enemy(Entity):
    def __init__(self, pos: Vec2, radius: float = 10.0, team: int = 1,
                 max_speed: float = 2.0):
        super().__init__(pos, radius, team, max_speed)
        self.stun_frames : int = 0   # chase is paused while > 0



class Goal(Rectangle):
    def __init__(self, pos: Vec2, width: float, height: float):
        super().__init__(pos, width, height)

    def contains_ball(self, ball: Ball) -> bool:
        cx, cy = ball.pos.x, ball.pos.y
        return (self.pos.x <= cx <= self.pos.x + self.width and
                self.pos.y <= cy <= self.pos.y + self.height)