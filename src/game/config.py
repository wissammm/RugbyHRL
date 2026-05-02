"""
config.py
---------
Single source of truth for every tunable parameter in the simulation.
Pass a GameConfig instance to Engine (or any game engine subclass) instead
of scattering magic numbers across the codebase.

All values have sensible defaults so you only need to override what you care
about.
"""

from dataclasses import dataclass, field
from src.game.object import Vec2


@dataclass
class PlayerConfig:
    # Spawn
    start_pos           : Vec2  = field(default_factory=lambda: Vec2(350, 440))
    radius              : float = 12.0
    team                : int   = 0

    max_speed           : float = 5
    friction            : float = 0.85   # applied every frame when no tile overrides

    push_force          : float = 20.0   # impulse magnitude on the target enemy
    push_range_factor   : float = 3.5    # push_range = radius * push_range_factor
    push_cooldown_steps : int   = 15     # steps between allowed pushes
    push_stun_frames    : int   = 40     # frames the hit enemy stops chasing

    throw_force         : float = 14.0
    throw_cooldown      : int   = 20     # frames before player can re-catch


@dataclass
class EnemyConfig:
    """Config for a single enemy instance."""
    start_pos   : Vec2  = field(default_factory=lambda: Vec2(150, 120))
    radius      : float = 12.0
    team        : int   = 1
    max_speed   : float = 2.2
    friction    : float = 0.82           # per-enemy friction (overrides engine default)


@dataclass
class BallConfig:
    start_pos   : Vec2  = field(default_factory=lambda: Vec2(350, 250))
    radius      : float = 7.0
    bounce_damp : float = 0.72           # energy kept after each wall bounce
    friction    : float = 0.96           # rolling friction per frame


@dataclass
class MapConfig:
    width       : int   = 700
    height      : int   = 500
    goal_width  : float = 100.0
    goal_height : float = 25.0


# ---------------------------------------------------------------------------
# Top-level config
# ---------------------------------------------------------------------------

@dataclass
class GameConfig:
    """
    Complete configuration for one episode.

    Usage
    -----
    cfg = GameConfig()                  # all defaults
    cfg.player.max_speed = 5.0          # tweak one thing
    engine = Game1Engine(game_map, cfg) # pass to engine
    """
    map     : MapConfig    = field(default_factory=MapConfig)
    player  : PlayerConfig = field(default_factory=PlayerConfig)
    ball    : BallConfig   = field(default_factory=BallConfig)
    enemies : list[EnemyConfig] = field(default_factory=lambda: [
        EnemyConfig(start_pos=Vec2(150, 120)),
        EnemyConfig(start_pos=Vec2(350, 100), max_speed=2.0),
        EnemyConfig(start_pos=Vec2(560, 140), max_speed=2.5),
        EnemyConfig(start_pos=Vec2(200, 260), max_speed=1.8),
        EnemyConfig(start_pos=Vec2(500, 240), max_speed=2.3),
    ])

    default_enemy_friction : float = 0.82   # fallback when no tile and no per-enemy value
    default_ball_friction  : float = 0.95   # fallback when ball rolls on plain ground

    invincible_frames : int = 20   # player invincibility frames after a push
