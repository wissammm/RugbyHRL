# Go to a certain position without being touched
import math
import src.game.object as object
import src.game.map    as map_module
from src.game.config   import GameConfig
from src.game.engine   import Engine


class Game1Engine(Engine):
    """
    Carrier game engine.

    Rules
    -----
    WIN  : player carries the ball into the goal zone.
    LOSE : an enemy touches the player while the player holds the ball.

    All tunable parameters come from GameConfig — no magic numbers.
    """

    def __init__(self, game_map: map_module.Map, cfg: GameConfig):
        super().__init__(game_map, cfg)
        self._invincible_countdown = 0

    def reset(self) -> None:
        super().reset()
        self._invincible_countdown = 0

    def _player_push(self, player: object.Player) -> None:
        super()._player_push(player)
        self._invincible_countdown = self.cfg.invincible_frames

    def _evaluate_rules(self) -> dict:
        player = self.map.player
        ball   = self.map.ball

        if player is None:
            return {"done": False, "won": False, "lost": False, "has_ball": False}

        has_ball = player.has_ball

        if self._invincible_countdown > 0:
            self._invincible_countdown -= 1

        if has_ball and ball is not None and :
            return {"done": True, "won": True, "lost": False, "has_ball": True}

        if has_ball and self._invincible_countdown == 0:
            for enemy in self.map.enemies:
                if _enemy_touches_player(enemy, player):
                    return {"done": True, "won": False, "lost": True, "has_ball": True}

        return {"done": False, "won": False, "lost": False, "has_ball": has_ball}


def _enemy_touches_player(enemy: object.Enemy, player: object.Player) -> bool:
    dx   = enemy.pos.x - player.pos.x
    dy   = enemy.pos.y - player.pos.y
    dist = math.sqrt(dx * dx + dy * dy)
    return dist < enemy.radius + player.radius