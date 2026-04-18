import math
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import pygame
import src.game.object as obj
import src.game.map    as map_module
from src.game.config             import GameConfig
from src.game.games.game1_engine import Game1Engine

MAX_ENEMIES = 5


class Game1Env(gym.Env):
    """
    Gymnasium wrapper around Game1Engine.

    Parameters
    ----------
    cfg          : GameConfig — controls every physics/rule parameter.
    max_steps    : episode is truncated after this many physics steps.
    ground_tiles : optional list of GroundTile zones for the field.
    render_mode  : "human" renders with pygame; None = headless (for training).
    """

    metadata = {"render_modes": ["human"], "render_fps": 60}

    def __init__(
        self,
        cfg          : GameConfig | None         = None,
        max_steps    : int                       = 1_000,
        ground_tiles : list | None               = None,
        render_mode  : str | None                = None,
    ):
        super().__init__()

        self.cfg          = cfg or GameConfig()
        self.max_steps    = max_steps
        self.ground_tiles = ground_tiles or []
        self.render_mode  = render_mode

        # obs dim: player(4) + ball(4) + has_ball(1) + goal(2) + enemies(2*MAX)
        obs_dim = 4 + 4 + 1 + 2 + 2 * MAX_ENEMIES
        self.observation_space = spaces.Box(
            low  = -1.0,
            high =  1.0,
            shape = (obs_dim,),
            dtype = np.float32,
        )

        # 5 movement actions + 1 push = 6 total
        self.action_space = spaces.Discrete(6)

        self._engine  : "Game1Engine | None" = None
        self._game_map: "map_module.Map | None" = None
        self._renderer = None

        # tracked across steps for delta-based progress rewards
        self._prev_dist_to_ball : float | None = None
        self._prev_dist_to_goal : float | None = None

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)

        self._game_map = map_module.Map.from_config(self.cfg, self.ground_tiles)
        self._engine   = Game1Engine(self._game_map, self.cfg)
        self._engine.save_initial_state()

        self._prev_dist_to_ball = None
        self._prev_dist_to_goal = None

        obs  = self._get_obs()
        info = {}
        return obs, info

    def step(self, action: int):
        assert self._engine is not None, "call reset() before step()"

        move, do_push = self._decode_action(action)
        result = self._engine.step({"move": move, "push": do_push, "throw": None})

        obs        = self._get_obs()
        reward     = self._compute_reward(result)
        terminated = result["done"]
        truncated  = self._engine.step_count >= self.max_steps
        info       = {
            "won"     : result.get("won",  False),
            "lost"    : result.get("lost", False),
            "has_ball": result.get("has_ball", False),
            "step"    : result["step"],
        }

        return obs, reward, terminated, truncated, info

    def render(self):
        if self.render_mode != "human":
            return

        if self._renderer is None:
            from src.renderer.renderer import Renderer
            assert self._game_map is not None
            self._renderer = Renderer(self._game_map, fps=60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
        self._renderer.render()

    def close(self):
        if self._renderer is not None:
            self._renderer.quit()
            self._renderer = None

    def _get_obs(self) -> np.ndarray:
        assert self._game_map is not None
        m   = self._game_map
        cfg = self.cfg

        W, H = float(cfg.map.width), float(cfg.map.height)

        def nx(x): return 2.0 * x / W - 1.0   # normalise x to [-1,1]
        def ny(y): return 2.0 * y / H - 1.0  

        def nvx(vx): return np.clip(vx / cfg.player.max_speed, -1.0, 1.0)
        def nvy(vy): return np.clip(vy / cfg.player.max_speed, -1.0, 1.0)

        p = m.player
        b = m.ball

        px  = nx(p.pos.x)       if p else 0.0
        py  = ny(p.pos.y)       if p else 0.0
        pvx = nvx(p.velocity.x) if p else 0.0
        pvy = nvy(p.velocity.y) if p else 0.0

        bx  = nx(b.pos.x)  if b else 0.0
        by  = ny(b.pos.y)  if b else 0.0
        bvx = np.clip(b.velocity.x / 20.0, -1.0, 1.0) if b else 0.0
        bvy = np.clip(b.velocity.y / 20.0, -1.0, 1.0) if b else 0.0

        has_ball = 1.0 if (p and p.has_ball) else 0.0

        g   = m.goal
        gcx = nx(g.pos.x + g.width  / 2)
        gcy = ny(g.pos.y + g.height / 2)

        enemy_obs = []
        for i in range(MAX_ENEMIES):
            if i < len(m.enemies):
                e = m.enemies[i]
                enemy_obs += [nx(e.pos.x), ny(e.pos.y)]
            else:
                enemy_obs += [0.0, 0.0]   # padding

        obs = np.array(
            [px, py, pvx, pvy,
             bx, by, bvx, bvy,
             has_ball,
             gcx, gcy]
            + enemy_obs,
            dtype=np.float32,
        )
        return obs

    def _compute_reward(self, result: dict) -> float:
        """
        Reward function for Game 1.
        """
        if result.get("won"):
            self._prev_dist_to_ball = None
            self._prev_dist_to_goal = None
            return +10.0

        if result.get("lost"):
            self._prev_dist_to_ball = None
            self._prev_dist_to_goal = None
            return -10.0

        assert self._game_map is not None
        p = self._game_map.player
        b = self._game_map.ball
        g = self._game_map.goal

        reward = 0.0

        if p is None or b is None:
            return reward

        W, H = float(self.cfg.map.width), float(self.cfg.map.height)
        max_dist = math.sqrt(W**2 + H**2)   # diagonal = max possible distance

        if not p.has_ball:
            dist_to_ball = math.sqrt(
                (p.pos.x - b.pos.x)**2 + (p.pos.y - b.pos.y)**2
            )
            # Penalise distance to ball: 0 when touching, -0.1 at the far corner.
            reward += 0.1 * (dist_to_ball / max_dist - 1.0)

            # Small bonus for getting closer to the ball than the previous step
            if self._prev_dist_to_ball is not None:
                delta = self._prev_dist_to_ball - dist_to_ball
                if delta > 0:
                    reward += 0.002 * delta / max_dist

            self._prev_dist_to_ball = dist_to_ball
            self._prev_dist_to_goal = None   # reset goal tracker while not holding ball

        else:
            goal_cx = g.pos.x + g.width  / 2
            goal_cy = g.pos.y + g.height / 2
            dist_to_goal = math.sqrt(
                (p.pos.x - goal_cx)**2 + (p.pos.y - goal_cy)**2
            )
            # Penalise distance to goal with ball: 0 when at goal, -0.2 at the far corner.
            reward += 0.2 * (dist_to_goal / max_dist - 1.0)

            # Small bonus for getting closer to the goal than the previous step
            if self._prev_dist_to_goal is not None:
                delta = self._prev_dist_to_goal - dist_to_goal
                if delta > 0:
                    reward += 0.005 * delta / max_dist

            self._prev_dist_to_goal = dist_to_goal
            self._prev_dist_to_ball = None   # reset ball tracker while holding ball

        # small per-step time penalty to encourage speed
        reward -= 0.001

        return reward

    @staticmethod
    def _decode_action(action: int) -> tuple[obj.Vec2, bool]:
        _MOVES = {
            0: (0.0,  0.0),   # idle
            1: (0.0, -1.0),   # up
            2: (0.0,  1.0),   # down
            3: (-1.0, 0.0),   # left
            4: (1.0,  0.0),   # right
            5: (0.0,  0.0),   # push (no movement)
        }
        dx, dy   = _MOVES.get(int(action), (0.0, 0.0))
        do_push  = (int(action) == 5)
        return obj.Vec2(dx, dy), do_push
