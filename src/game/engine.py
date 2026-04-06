import math
import src.game.object as object
import src.game.map    as map_module
from src.game.config   import GameConfig


def _length(v: object.Vec2) -> float:
    return math.sqrt(v.x ** 2 + v.y ** 2)


def _normalize(v: object.Vec2) -> object.Vec2:
    return v.normalized()

def _clamp_speed(v: object.Vec2, max_speed: float) -> object.Vec2:
    l = _length(v)
    if l > max_speed:
        s = max_speed / l
        return object.Vec2(v.x * s, v.y * s)
    return v


def _circles_overlap(a: object.Circle, b: object.Circle) -> bool:
    dx = a.pos.x - b.pos.x
    dy = a.pos.y - b.pos.y
    dist_sq = dx * dx + dy * dy
    min_dist = a.radius + b.radius
    return dist_sq < min_dist * min_dist


def _resolve_circle_overlap(a: object.Circle, b: object.Circle) -> None:
    """Push two circles apart so they no longer overlap (equal mass, positional correction)."""
    dx = b.pos.x - a.pos.x
    dy = b.pos.y - a.pos.y
    dist = math.sqrt(dx * dx + dy * dy)
    if dist == 0:
        dist = 0.001
        dx, dy = 1.0, 0.0
    overlap = (a.radius + b.radius) - dist
    nx, ny = dx / dist, dy / dist

    a.pos.x -= nx * overlap * 0.5
    a.pos.y -= ny * overlap * 0.5
    b.pos.x += nx * overlap * 0.5
    b.pos.y += ny * overlap * 0.5


def normalizePos(pos: object.Vec2, width: float, height: float) -> object.Vec2:
    return object.Vec2(
        2.0 * pos.x / width  - 1.0,
        2.0 * pos.y / height - 1.0,
    )


def goTo(from_pos: object.Vec2, to_pos: object.Vec2) -> object.Vec2:
    return object.Vec2(to_pos.x - from_pos.x, to_pos.y - from_pos.y)


def collision_two_circle(circle1: object.Circle, circle2: object.Circle) -> bool:
    distance = math.sqrt(
        (circle1.pos.x - circle2.pos.x) ** 2 +
        (circle1.pos.y - circle2.pos.y) ** 2
    )
    return distance < circle1.radius + circle2.radius


def point_projection(point: object.Vec2,
                     line_start: object.Vec2,
                     line_end:   object.Vec2) -> object.Vec2:
    ax = line_end.x - line_start.x
    ay = line_end.y - line_start.y
    t = ((point.x - line_start.x) * ax + (point.y - line_start.y) * ay) / (ax * ax + ay * ay)
    return object.Vec2(line_start.x + t * ax, line_start.y + t * ay)


class Engine:
    """
    Base physics engine — no game rules, no win/lose logic.
    Subclass this and override `_evaluate_rules()` to implement a game.

    All tunable values come from the GameConfig; no magic numbers in logic.

    `step()` returns a dict with at minimum:
        "step"       : int   — current step count
        "player_pos" : Vec2  — player position
        "done"       : bool  — whether the episode has ended (always False here)
        "won"        : bool  — always False in base class
        "lost"       : bool  — always False in base class
    """

    def __init__(self, game_map: map_module.Map, cfg: GameConfig):
        self.map        = game_map
        self.cfg        = cfg
        self.step_count = 0
        self._initial_state: dict = {}

    def reset(self) -> None:
        self.step_count = 0
        state = self._initial_state
        if not state:
            return

        p = self.map.player
        if p and "player" in state:
            s = state["player"]
            p.pos           = object.Vec2(s["x"], s["y"])
            p.velocity      = object.Vec2(0.0, 0.0)
            p.has_ball      = False
            p.push_cooldown = 0
            p.throw_cooldown = 0

        for i, e in enumerate(self.map.enemies):
            if i < len(state.get("enemies", [])):
                s = state["enemies"][i]
                e.pos         = object.Vec2(s["x"], s["y"])
                e.velocity    = object.Vec2(0.0, 0.0)
                e.has_ball    = False
                e.stun_frames = 0

        b = self.map.ball
        if b and "ball" in state:
            s = state["ball"]
            b.pos      = object.Vec2(s["x"], s["y"])
            b.velocity = object.Vec2(0.0, 0.0)
            b.is_held  = False
            b.holder   = None

    def save_initial_state(self) -> None:
        p = self.map.player
        self._initial_state["player"] = {"x": p.pos.x, "y": p.pos.y} if p else {}
        self._initial_state["enemies"] = [
            {"x": e.pos.x, "y": e.pos.y} for e in self.map.enemies
        ]
        b = self.map.ball
        self._initial_state["ball"] = {"x": b.pos.x, "y": b.pos.y} if b else {}

    def step(self, action: dict) -> dict:
        self.step_count += 1

        self._apply_player_action(action)
        self._update_enemies()
        self._update_ball()
        self._handle_ball_pickup()
        self._resolve_all_collisions()
        self._clamp_all_to_field()

        result = self._evaluate_rules()
        result["player_pos"] = self.map.player.pos.copy() if self.map.player else None
        result["step"]       = self.step_count
        return result

    def _evaluate_rules(self) -> dict:
        """Override in subclasses to apply game-specific win/lose logic."""
        return {"done": False, "won": False, "lost": False}

    def _apply_player_action(self, action: dict) -> None:
        player = self.map.player
        if player is None:
            return

        # --- Movement ---
        move_dir: object.Vec2 = action.get("move", object.Vec2(0.0, 0.0))
        if _length(move_dir) > 0:
            move_dir = _normalize(move_dir)
            # Check ground under player for speed cap
            tile = self.map.get_tile_at(player.pos)
            speed = player.max_speed * (tile.slow_factor if tile else 1.0)
            player.velocity.x += move_dir.x * speed
            player.velocity.y += move_dir.y * speed

        # Apply ground friction
        tile = self.map.get_tile_at(player.pos)
        friction = tile.friction if tile else self.cfg.player.friction
        player.velocity.x *= friction
        player.velocity.y *= friction

        player.velocity = _clamp_speed(player.velocity, player.max_speed)
        player.pos.x += player.velocity.x
        player.pos.y += player.velocity.y

        # Decrement push cooldown
        if player.push_cooldown > 0:
            player.push_cooldown -= 1

        # --- Push ---
        if action.get("push", False) and player.push_cooldown == 0:
            self._player_push(player)
            player.push_cooldown = player.push_every_n_steps

        # --- Throw ---
        throw_dir: object.Vec2 | None = action.get("throw", None)
        if throw_dir is not None and player.has_ball:
            self._player_throw(player, throw_dir)

        # Keep ball glued to player if held
        if player.has_ball and self.map.ball is not None:
            self.map.ball.pos.x = player.pos.x
            self.map.ball.pos.y = player.pos.y

    def _player_push(self, player: object.Player) -> None:
        """Apply an impulse to the nearest enemy within push range."""
        pc         = self.cfg.player
        best_enemy : object.Enemy | None = None
        best_dist  : float               = float("inf")
        push_range : float               = player.radius * pc.push_range_factor

        for enemy in self.map.enemies:
            dx   = enemy.pos.x - player.pos.x
            dy   = enemy.pos.y - player.pos.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < push_range and dist < best_dist:
                best_dist  = dist
                best_enemy = enemy

        if best_enemy is not None:
            dx = best_enemy.pos.x - player.pos.x
            dy = best_enemy.pos.y - player.pos.y
            dist = math.sqrt(dx * dx + dy * dy) or 0.001
            nx, ny = dx / dist, dy / dist
            best_enemy.velocity.x = nx * pc.push_force
            best_enemy.velocity.y = ny * pc.push_force
            best_enemy.stun_frames = pc.push_stun_frames

    def _player_throw(self, player: object.Player, direction: object.Vec2) -> None:
        """Detach the ball from the player and give it a velocity."""
        ball = self.map.ball
        if ball is None:
            return
        direction = _normalize(direction)
        ball.velocity.x = direction.x * player.throw_force
        ball.velocity.y = direction.y * player.throw_force
        ball.is_held          = False
        ball.holder           = None
        player.has_ball       = False
        player.throw_cooldown = self.cfg.player.throw_cooldown


    def _update_enemies(self) -> None:
        player = self.map.player
        if player is None:
            return

        for i, enemy in enumerate(self.map.enemies):
            if enemy.stun_frames > 0:
                # stunned — just coast, apply friction, no chasing
                enemy.stun_frames -= 1
            else:
                # Move toward the player
                dx = player.pos.x - enemy.pos.x
                dy = player.pos.y - enemy.pos.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > 0:
                    nx, ny = dx / dist, dy / dist
                    tile = self.map.get_tile_at(enemy.pos)
                    speed = enemy.max_speed * (tile.slow_factor if tile else 1.0)
                    enemy.velocity.x += nx * speed
                    enemy.velocity.y += ny * speed

            # Friction always applied — use per-enemy config friction if available,
            # otherwise fall back to the engine-level default from cfg
            tile = self.map.get_tile_at(enemy.pos)
            enemy_cfg_friction = self.cfg.enemies[i].friction if i < len(self.cfg.enemies) else self.cfg.default_enemy_friction
            friction = tile.friction if tile else enemy_cfg_friction
            enemy.velocity.x *= friction
            enemy.velocity.y *= friction

            enemy.velocity = _clamp_speed(enemy.velocity, enemy.max_speed)
            enemy.pos.x += enemy.velocity.x
            enemy.pos.y += enemy.velocity.y


    def _update_ball(self) -> None:
        ball = self.map.ball
        if ball is None or ball.is_held:
            return

        # Wall bouncing
        w, h = self.map.width, self.map.height
        next_x = ball.pos.x + ball.velocity.x
        next_y = ball.pos.y + ball.velocity.y

        if next_x - ball.radius < 0:
            next_x = ball.radius
            ball.velocity.x = abs(ball.velocity.x) * ball.bounce_damp
        elif next_x + ball.radius > w:
            next_x = w - ball.radius
            ball.velocity.x = -abs(ball.velocity.x) * ball.bounce_damp

        if next_y - ball.radius < 0:
            next_y = ball.radius
            ball.velocity.y = abs(ball.velocity.y) * ball.bounce_damp
        elif next_y + ball.radius > h:
            next_y = h - ball.radius
            ball.velocity.y = -abs(ball.velocity.y) * ball.bounce_damp

        ball.pos.x = next_x
        ball.pos.y = next_y

        # Rolling friction from ground tile
        tile = self.map.get_tile_at(ball.pos)
        friction = tile.friction if tile else self.cfg.default_ball_friction
        ball.velocity.x *= friction
        ball.velocity.y *= friction

    def _handle_ball_pickup(self) -> None:
        """Player picks up the ball on contact (if the ball is free)."""
        player = self.map.player
        ball   = self.map.ball
        if player is None or ball is None or ball.is_held:
            return

        # Cooldown prevents immediately re-catching a just-thrown ball
        if player.throw_cooldown > 0:
            player.throw_cooldown -= 1
            return

        if _circles_overlap(player, ball):
            ball.is_held    = True
            ball.holder     = player
            ball.velocity   = object.Vec2(0.0, 0.0)
            player.has_ball = True

    def _resolve_all_collisions(self) -> None:
        player  = self.map.player
        enemies = self.map.enemies

        if player is not None:
            for enemy in enemies:
                if _circles_overlap(player, enemy):
                    _resolve_circle_overlap(player, enemy)
                    self._elastic_bounce(player, enemy)

        for i in range(len(enemies)):
            for j in range(i + 1, len(enemies)):
                if _circles_overlap(enemies[i], enemies[j]):
                    _resolve_circle_overlap(enemies[i], enemies[j])
                    self._elastic_bounce(enemies[i], enemies[j])

    @staticmethod
    def _elastic_bounce(a: object.Entity, b: object.Entity) -> None:
        """
        1-D elastic collision along the contact normal.
        Assumes equal mass for simplicity (swap velocities along normal).
        """
        nx = b.pos.x - a.pos.x
        ny = b.pos.y - a.pos.y
        dist = math.sqrt(nx * nx + ny * ny) or 0.001
        nx /= dist
        ny /= dist

        # Relative velocity along normal
        dvx = a.velocity.x - b.velocity.x
        dvy = a.velocity.y - b.velocity.y
        dot = dvx * nx + dvy * ny

        if dot > 0:   # only resolve if approaching
            a.velocity.x -= dot * nx
            a.velocity.y -= dot * ny
            b.velocity.x += dot * nx
            b.velocity.y += dot * ny

    def _clamp_all_to_field(self) -> None:
        w, h = self.map.width, self.map.height
        entities: list[object.Entity] = list(self.map.enemies)
        if self.map.player:
            entities.append(self.map.player)

        for e in entities:
            e.pos.x = max(e.radius, min(w - e.radius, e.pos.x))
            e.pos.y = max(e.radius, min(h - e.radius, e.pos.y))
