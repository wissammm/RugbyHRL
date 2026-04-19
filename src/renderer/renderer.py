import pygame
import src.game.map    as map_module
import src.game.object as object

FIELD_GREEN   = (34,  139, 34)
FIELD_LINE    = (255, 255, 255)
GOAL_COLOUR   = (255, 215,  0)    
PLAYER_COLOUR = (30,  144, 255)    
ENEMY_COLOUR  = (220,  20,  60)    
BALL_COLOUR   = (255, 165,   0)   
HUD_BG        = (0,     0,   0, 160)
HUD_TEXT      = (255, 255, 255)
PUSH_READY    = (0,   255,   0)
PUSH_COOLDOWN = (200,   0,   0)
TILE_SLIPPERY = (173, 216, 230, 80)  
TILE_SLOW     = (139,  90,  43, 80) 


class Renderer:
    """
    Parameters
    ----------
    game_map : the Map instance to render.
    fps      : target frame-rate (vsync will cap at monitor refresh rate if
               the display supports it; fps is used as a fallback).
    scale    : pixel-per-unit multiplier (1 = map units == screen pixels).
    """

    def __init__(self, game_map: map_module.Map, fps: int = 30, scale: float = 1.0):
        self.map   = game_map
        self.fps   = fps
        self.scale = scale

        pygame.init()
        pygame.display.set_caption("RugbyHRL — debug view")

        w = int(game_map.width  * scale)
        h = int(game_map.height * scale)

        # DOUBLEBUF + vsync=1 lets the driver handle frame pacing without the
        # overhead of SCALED (which forces a software-blit path on most Linux drivers).
        self.screen = pygame.display.set_mode(
            (w, h),
            pygame.DOUBLEBUF,
            vsync=1,
        )
        self._vsync_active = True
        self.clock  = pygame.time.Clock()
        self._font  = pygame.font.SysFont("monospace", 14, bold=True)
        self._big   = pygame.font.SysFont("monospace", 32, bold=True)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def render(self, info: dict | None = None) -> None:
        """Draw one frame.  *info* is the dict returned by engine.step()."""
        self._draw_field()
        self._draw_ground_tiles()
        self._draw_goal()
        self._draw_ball()
        self._draw_enemies()
        self._draw_player()
        self._draw_hud(info)
        pygame.display.flip()

    def tick(self) -> None:
        """Advance the clock without drawing (useful when skipping frames)."""
        self.clock.tick(self.fps)

    def quit(self) -> None:
        pygame.quit()

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _s(self, x: float, y: float) -> tuple[int, int]:
        """Scale map coordinates to screen pixels."""
        return (int(x * self.scale), int(y * self.scale))

    def _sr(self, r: float) -> int:
        return max(1, int(r * self.scale))

    def _draw_field(self) -> None:
        self.screen.fill(FIELD_GREEN)
        w = int(self.map.width  * self.scale)
        h = int(self.map.height * self.scale)
        # border
        pygame.draw.rect(self.screen, FIELD_LINE, (0, 0, w, h), 2)
        # centre line
        pygame.draw.line(self.screen, FIELD_LINE, (0, h // 2), (w, h // 2), 1)
        # centre circle
        pygame.draw.circle(self.screen, FIELD_LINE, (w // 2, h // 2),
                           self._sr(40), 1)

    def _draw_ground_tiles(self) -> None:
        for tile in self.map.ground_tiles:
            surf = pygame.Surface(
                (int(tile.width * self.scale), int(tile.height * self.scale)),
                pygame.SRCALPHA,
            )
            colour = TILE_SLIPPERY if tile.friction > 0.95 else TILE_SLOW
            surf.fill(colour)
            self.screen.blit(surf, self._s(tile.pos.x, tile.pos.y))

    def _draw_goal(self) -> None:
        goal = self.map.goal
        x, y = self._s(goal.pos.x, goal.pos.y)
        w    = int(goal.width  * self.scale)
        h    = int(goal.height * self.scale)
        pygame.draw.rect(self.screen, GOAL_COLOUR, (x, y, w, h), 3)
        # label
        label = self._font.render("GOAL", True, GOAL_COLOUR)
        self.screen.blit(label, (x + w // 2 - label.get_width() // 2, y + 2))

    def _draw_ball(self) -> None:
        ball = self.map.ball
        if ball is None:
            return
        cx, cy = self._s(ball.pos.x, ball.pos.y)
        r      = self._sr(ball.radius)
        pygame.draw.circle(self.screen, BALL_COLOUR, (cx, cy), r)
        pygame.draw.circle(self.screen, (0, 0, 0),   (cx, cy), r, 1)

    def _draw_enemies(self) -> None:
        for enemy in self.map.enemies:
            cx, cy = self._s(enemy.pos.x, enemy.pos.y)
            r      = self._sr(enemy.radius)
            pygame.draw.circle(self.screen, ENEMY_COLOUR, (cx, cy), r)
            pygame.draw.circle(self.screen, (0, 0, 0),    (cx, cy), r, 1)

    def _draw_player(self) -> None:
        player = self.map.player
        if player is None:
            return
        cx, cy = self._s(player.pos.x, player.pos.y)
        r      = self._sr(player.radius)
        pygame.draw.circle(self.screen, PLAYER_COLOUR, (cx, cy), r)
        pygame.draw.circle(self.screen, (0, 0, 0),     (cx, cy), r, 1)

        # push cooldown indicator (small arc around player)
        ratio = 1.0 - player.push_cooldown / max(player.push_every_n_steps, 1)
        col   = PUSH_READY if player.push_cooldown == 0 else PUSH_COOLDOWN
        if ratio < 1.0:
            import math
            end_angle = -math.pi / 2 + ratio * 2 * math.pi
            pygame.draw.arc(
                self.screen, col,
                (cx - r - 4, cy - r - 4, (r + 4) * 2, (r + 4) * 2),
                -math.pi / 2, end_angle, 3,
            )
        else:
            pygame.draw.circle(self.screen, PUSH_READY, (cx, cy), r + 3, 2)

        # ball indicator
        if player.has_ball:
            pygame.draw.circle(self.screen, BALL_COLOUR, (cx, cy - r - 6), 5)

    def _draw_hud(self, info: dict | None) -> None:
        lines = []
        if info:
            lines.append(f"Step   : {info.get('step', 0)}")
            if "reward" in info:
                lines.append(f"Reward : {info['reward']:+.4f}")
        player = self.map.player
        if player:
            if player.has_ball:
                lines.append("Ball : HELD  — reach the goal!")
            else:
                lines.append("Ball : free  — walk into it")
            cd = player.push_cooldown
            lines.append(f"Push : {'READY  (Space)' if cd == 0 else f'CD {cd}'}")

        y_off = 6
        for line in lines:
            surf = self._font.render(line, True, HUD_TEXT)
            bg   = pygame.Surface((surf.get_width() + 6, surf.get_height() + 2),
                                  pygame.SRCALPHA)
            bg.fill((0, 0, 0, 140))
            self.screen.blit(bg,   (4, y_off - 1))
            self.screen.blit(surf, (7, y_off))
            y_off += surf.get_height() + 4

        if info and info.get("won"):
            self._draw_big_message("YOU WIN!", (50, 220, 50))
        elif info and info.get("lost"):
            self._draw_big_message("YOU LOSE!", (220, 50, 50))

    def _draw_big_message(self, text: str, colour: tuple) -> None:
        msg  = self._big.render(text, True, colour)
        sw   = self.screen.get_width()
        sh   = self.screen.get_height()
        cx   = sw // 2 - msg.get_width()  // 2
        cy   = sh // 2 - msg.get_height() // 2
        # dark backdrop
        pad  = 16
        bg   = pygame.Surface((msg.get_width() + pad * 2, msg.get_height() + pad * 2),
                               pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        self.screen.blit(bg,  (cx - pad, cy - pad))
        self.screen.blit(msg, (cx, cy))
        hint = self._font.render("Press R to restart", True, (200, 200, 200))
        self.screen.blit(hint, (sw // 2 - hint.get_width() // 2, cy + msg.get_height() + 6))
