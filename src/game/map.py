import src.game.object as object


class Map:
    """
    Holds all game objects and the static description of the field.

    Build it directly for full control, or use Map.from_config(cfg) to
    construct everything from a GameConfig in one call.
    """

    def __init__(
        self,
        width       : int   = 600,
        height      : int   = 400,
        goal_width  : float = 80.0,
        goal_height : float = 20.0,
        ground_tiles: list[object.GroundTile] | None = None,
    ):
        self.width  = width
        self.height = height

        self.player  : object.Player | None = None
        self.enemies : list[object.Enemy]   = []
        self.ball    : object.Ball  | None  = None

        goal_x = (width - goal_width) / 2
        self.goal = object.Goal(
            pos    = object.Vec2(goal_x, 0),
            width  = goal_width,
            height = goal_height,
        )

        self.ground_tiles: list[object.GroundTile] = ground_tiles or []

    @classmethod
    def from_config(cls, cfg: "GameConfig",                          # type: ignore[name-defined]
                    ground_tiles: list[object.GroundTile] | None = None) -> "Map":
        """
        cfg          : GameConfig instance.
        ground_tiles : optional list of GroundTile zones
        """
        # Import here to avoid circular imports at module level
        from src.game.config import GameConfig  # noqa: F401 — type hint only

        m = cls(
            width       = cfg.map.width,
            height      = cfg.map.height,
            goal_width  = cfg.map.goal_width,
            goal_height = cfg.map.goal_height,
            ground_tiles= ground_tiles,
        )

        pc = cfg.player
        m.set_player(object.Player(
            pos               = pc.start_pos,
            radius            = pc.radius,
            team              = pc.team,
            max_speed         = pc.max_speed,
            push_every_n_steps= pc.push_cooldown_steps,
            push_force        = pc.push_force,
            throw_force       = pc.throw_force,
        ))

        for ec in cfg.enemies:
            m.add_enemy(object.Enemy(
                pos      = ec.start_pos,
                radius   = ec.radius,
                team     = ec.team,
                max_speed= ec.max_speed,
            ))

        bc = cfg.ball
        m.set_ball(object.Ball(
            pos         = bc.start_pos,
            radius      = bc.radius,
            bounce_damp = bc.bounce_damp,
            friction    = bc.friction,
        ))

        return m

    def get_tile_at(self, pos: object.Vec2) -> object.GroundTile | None:
        """Return the first ground tile that contains *pos*, or None."""
        for tile in self.ground_tiles:
            if tile.contains(pos):
                return tile
        return None

    def add_enemy(self, enemy: object.Enemy) -> None:
        self.enemies.append(enemy)

    def set_player(self, player: object.Player) -> None:
        self.player = player

    def set_ball(self, ball: object.Ball) -> None:
        self.ball = ball

