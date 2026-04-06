"""
main.py
-------
Debug entry-point for Game 1: Carrier.

Rules
-----
  Pick up the ball (walk into it), carry it to the gold goal zone = WIN.
  An enemy touches you while you hold the ball               = LOSE.
  Space pushes the nearest enemy away (grants brief invincibility).

Controls
--------
WASD   : move
Space  : push nearest enemy
R      : restart
Esc/Q  : quit
"""

import pygame
import sys

import src.game.object  as object
import src.game.map     as map_module
from src.game.config             import GameConfig, PlayerConfig, BallConfig, MapConfig, EnemyConfig
from src.game.games.game1_engine import Game1Engine
from src.renderer.renderer       import Renderer

cfg = GameConfig(
    map = MapConfig(
        width       = 700,
        height      = 500,
        goal_width  = 100.0,
        goal_height = 25.0,
    ),
    player = PlayerConfig(
        start_pos           = object.Vec2(350, 440),
        radius              = 12.0,
        max_speed           = 4.0,
        friction            = 0.85,
        push_force          = 20.0,
        push_range_factor   = 3.5,
        push_cooldown_steps = 15,
        push_stun_frames    = 40,
        throw_force         = 14.0,
        throw_cooldown      = 20,
    ),
    ball = BallConfig(
        start_pos   = object.Vec2(350, 250),
        radius      = 7.0,
        bounce_damp = 0.72,
        friction    = 0.96,
    ),
    enemies = [
        EnemyConfig(start_pos=object.Vec2(150, 120), max_speed=2.2, friction=0.82),
    ],
    default_enemy_friction = 0.82,
    default_ball_friction  = 0.95,
    invincible_frames      = 20,
)


ground_tiles = [
    object.GroundTile(object.Vec2(0, 0),       200, 150, friction=1.02, slow_factor=0.9),
    object.GroundTile(object.Vec2(450, 320),   250, 180, friction=0.70, slow_factor=0.55),
]

game_map = map_module.Map.from_config(cfg, ground_tiles=ground_tiles)

engine   = Game1Engine(game_map, cfg)
engine.save_initial_state()

renderer = Renderer(game_map, fps=60, scale=1.0)

info: dict = {}
done: bool = False

PHYSICS_HZ      = 60
PHYSICS_DT      = 1.0 / PHYSICS_HZ   # seconds per physics step
time_accumulator = 0.0

while True:
    frame_dt = renderer.clock.tick() / 1000.0  
    frame_dt = min(frame_dt, 0.1)               # clamp: don't spiral if window is moved/paused
    time_accumulator += frame_dt

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            renderer.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                renderer.quit()
                sys.exit()
            if event.key == pygame.K_r:
                engine.reset()
                info = {}
                done = False
                time_accumulator = 0.0

    # Sample input once per display frame, then consume accumulated physics steps
    keys    = pygame.key.get_pressed()
    move_x  = float(keys[pygame.K_d] - keys[pygame.K_a])
    move_y  = float(keys[pygame.K_s] - keys[pygame.K_w])
    do_push = bool(keys[pygame.K_SPACE])
    action  = {"move": object.Vec2(move_x, move_y), "push": do_push, "throw": None}

    while time_accumulator >= PHYSICS_DT:
        if not done:
            info = engine.step(action)
            done = info.get("done", False)
        time_accumulator -= PHYSICS_DT

    renderer.render(info)

