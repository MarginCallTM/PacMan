"""Maze rendering: walls, colors and keyboard shortcuts.

``MazeRenderer`` owns no MLX state itself: it only writes pixels
through the :class:`~pacman.ui.mlx_window.MlxWindow` it is given, so
other screens (HUD, menus...) can share the same window and buffer
without inheriting from this class.
"""

from dataclasses import dataclass
from typing import Any

from pacman.entities.ghost import Ghost, GhostState
from pacman.entities.pellets import Pellets
from pacman.entities.player import Player
from pacman.maze_loader import DELTAS, EAST, NORTH, SOLID, SOUTH, WEST, Maze
from pacman.ui.keys import KEY_Q
from pacman.ui.mlx_window import MlxWindow
from pacman.ui.screen import Screen

_SOLID_COLOR = 0xFF0000FF  # fixed blue for the "42" pattern (SOLID cells)
_WALL_COLOR = 0xFFFFFFFF  # fixed white outline for the "42" pattern
_BACKGROUND_COLOR = 0xFF000000  # fixed black for the background
_PACGUM_COLOR = 0xFFFFFFAA  # small pale-yellow dot
_SUPER_PACGUM_COLOR = 0xFFFF8000  # bigger orange dot, in the corners
_PACGUM_RATIO = 0.2  # dot side, as a fraction of the cell size
_SUPER_PACGUM_RATIO = 0.5
_PLAYER_COLOR = 0xFFFFFF00  # classic Pac-Man yellow
_PLAYER_RATIO = 0.7
_MOUTH_HALF_ANGLE = 35.0  # mouth opening, in degrees on each side
# Mouth direction, in degrees clockwise from the positive x-axis
# (screen coordinates: y grows downward) -- matches fill_wedge.
_DIRECTION_ANGLES = {EAST: 0.0, SOUTH: 90.0, WEST: 180.0, NORTH: 270.0}
_GHOST_RATIO = 0.7
# One flat color per ghost (by its position in Level.ghosts), like the
# four named ghosts of the original arcade game -- lost as soon as a
# ghost turns FRIGHTENED, exactly like the original too.
_GHOST_PALETTE = (0xFFFF0000, 0xFFFFB8FF, 0xFF00FFFF, 0xFFFFB851)
_GHOST_FRIGHTENED_COLOR = 0xFFB266FF  # edible: distinct from every
# CHASE color above and from the "42" pattern's wall blue
_EYE_RATIO = 0.28
_EYE_COLOR = 0xFFFFFFFF
_PUPIL_COLOR = 0xFF000000
_HUD_TEXT_COLOR = 0xFFFFFFFF
_HUD_WARNING_COLOR = 0xFFFF4040  # remaining time, once it is running low
_HUD_WARNING_SECONDS = 10
_MARGIN = 50  # breathing room kept around the maze on every side
_HUD_HEIGHT = 100  # space reserved at the bottom of the window for the HUD
# Slowest believable pace for a slide, in ticks per move: throttled
# ghosts move at worst every 2nd tick. A longer measured interval
# means the entity was parked (wall, freeze cheat, rest), not pacing
# -- its next move must restart at full speed, not in slow motion.
_GLIDE_MAX_GAP = 2


@dataclass
class _Glide:
    """Tracks one entity's on-screen slide toward its current cell.

    The simulation only ever occupies whole cells, a few times a
    second -- and throttled ghosts do not even move on every tick.
    Animating every move over exactly one tick would freeze such a
    ghost on its rest ticks (a visible stutter), so each slide is
    spread over the entity's *observed pace*: the number of ticks it
    actually waited between its last two moves (1 for the player, 2
    for a frightened ghost). And because a new move can land before
    the previous slide finished, every slide starts from the exact
    fractional position currently drawn -- the sprite's path is
    continuous by construction, never a jump.

    Attributes:
        prev_x: Fractional column the current slide started from.
        prev_y: Fractional row the current slide started from.
        x: Column the entity currently occupies (slide target).
        y: Row the entity currently occupies (slide target).
        gap: Ticks the current slide takes to reach its target.
        age: Whole ticks elapsed since the current slide started.
    """

    prev_x: float
    prev_y: float
    x: int
    y: int
    gap: int = 1
    age: int = 0

    def advance(self, x: int, y: int) -> None:
        """Register the cell reached after one freshly-elapsed tick.

        Must be called exactly once per simulation tick, never more
        (the caller, :meth:`MazeRenderer.sync_tick`, enforces that):
        ``age`` counts ticks, so the measured pace would be wrong
        otherwise. Three cases:

        - No move: the slide ages one tick -- it keeps easing toward
          its target (progress is capped there, so a long stand-still
          simply rests on the cell).
        - A jump of more than one cell (a teleport: respawn at the
          center, a ghost sent home or eaten): snap to the target,
          gliding across the maze would look broken.
        - A one-cell move: start a new slide from the position drawn
          right now, spread over the interval since the previous move
          -- unless that interval exceeds _GLIDE_MAX_GAP, meaning the
          entity was parked, in which case full speed again.

        Args:
            x: The entity's column after this tick.
            y: The entity's row after this tick.
        """
        if (x, y) == (self.x, self.y):
            self.age += 1
            return
        if abs(x - self.x) + abs(y - self.y) > 1:
            self.prev_x, self.prev_y = float(x), float(y)
            self.gap, self.age = 1, 0
        else:
            self.age += 1
            self.prev_x, self.prev_y = self.at(0.0)
            self.gap = self.age if self.age <= _GLIDE_MAX_GAP else 1
            self.age = 0
        self.x, self.y = x, y

    def at(self, alpha: float) -> tuple[float, float]:
        """Interpolate the on-screen position along the current slide.

        Args:
            alpha: Progress toward the next tick, in [0, 1) -- the
                slide advances by (age + alpha) / gap, capped on its
                target cell once complete.

        Returns:
            Fractional (x, y) cell coordinates to draw at.
        """
        progress = min(1.0, (self.age + alpha) / self.gap)
        return (self.prev_x + (self.x - self.prev_x) * progress,
                self.prev_y + (self.y - self.prev_y) * progress)


class MazeRenderer(Screen):
    """Draws one :class:`Maze` into a shared :class:`MlxWindow`."""

    def __init__(self, window: MlxWindow) -> None:
        """Bind this renderer to an already-created window.

        Args:
            window: The shared MLX window to draw into.
        """
        super().__init__()
        self._window = window
        self._maze: Maze | None = None
        self._pellets: Pellets | None = None
        self._player: Player | None = None
        self._ghosts: list[Ghost] | None = None
        self._player_glide: _Glide | None = None
        self._ghost_glides: list[_Glide] | None = None
        self._last_ticks_elapsed = 0
        self._alpha = 0.0
        self._hud: tuple[int, int, int] | None = None
        self._cell_size = 0
        self._offset_x = 0
        self._offset_y = 0

    def load(self, maze: Maze) -> None:
        """Compute the cell size for ``maze`` and mark the view dirty.

        Args:
            maze: The maze to display starting next frame.
        """
        self._maze = maze
        play_w = self._window.width - _MARGIN
        play_h = self._window.height - _HUD_HEIGHT - _MARGIN
        self._cell_size = min(
            play_w // maze.width, play_h // maze.height)
        self._offset_x = (
            (self._window.width - self._cell_size * maze.width) // 2)
        self._offset_y = (
            (self._window.height - _HUD_HEIGHT
             - self._cell_size * maze.height) // 2)
        self.refresh()

    def load_pellets(self, pellets: Pellets) -> None:
        """Attach the level's pellet state and mark the view dirty.

        Call this again (same object or not) every time a pellet gets
        eaten, so the next frame stops drawing it.

        Args:
            pellets: The pacgums/super-pacgums still on the board.
        """
        self._pellets = pellets
        self.refresh()

    def load_entities(self, player: Player, ghosts: list[Ghost]) -> None:
        """Attach the level's player and ghosts and mark the view dirty.

        Both objects are mutated in place by the engine every tick, so
        this only needs to run once per level: the caller is
        responsible for calling :meth:`refresh` again on every frame
        where the game is actually running, so the new positions get
        drawn.

        Args:
            player: The current level's player.
            ghosts: The current level's ghosts.
        """
        self._player = player
        self._ghosts = ghosts
        self._player_glide = _Glide(player.x, player.y, player.x, player.y)
        self._ghost_glides = [_Glide(g.x, g.y, g.x, g.y) for g in ghosts]
        self.refresh()

    def sync_tick(self, ticks_elapsed: int) -> None:
        """Advance every entity's glide, but only once per simulation tick.

        Called every frame from the caller's loop hook, alongside
        :meth:`set_tick_progress` -- but ``_Glide.advance`` itself must
        fire exactly once per tick (see its docstring for why), so
        this compares against ``Engine.ticks_elapsed`` and does
        nothing on the frames where no new tick has landed yet.

        Args:
            ticks_elapsed: ``Engine.ticks_elapsed``, the total number
                of simulation ticks run so far.
        """
        if ticks_elapsed == self._last_ticks_elapsed:
            return
        self._last_ticks_elapsed = ticks_elapsed
        assert self._player is not None and self._player_glide is not None
        self._player_glide.advance(self._player.x, self._player.y)
        assert self._ghosts is not None and self._ghost_glides is not None
        for ghost, glide in zip(self._ghosts, self._ghost_glides):
            glide.advance(ghost.x, ghost.y)

    def set_tick_progress(self, alpha: float) -> None:
        """Record how far we are toward the next simulation tick.

        Called every frame while playing, straight from
        :meth:`~pacman.game.engine.Engine.tick_progress`, so entities
        glide smoothly between cells instead of jumping once every
        tick.

        Args:
            alpha: Progress toward the next tick, in [0, 1).
        """
        self._alpha = alpha
        self.refresh()

    def set_hud(self, score: int, level_number: int,
                seconds_left: int) -> None:
        """Record the current HUD values and mark the view dirty.

        Lives are read live from the player already attached through
        :meth:`load_entities` (``self._player.lives``); score, level
        number and remaining time have no single mutable object to
        read from at draw time, so the caller pushes them explicitly,
        once per frame.

        Args:
            score: Current score.
            level_number: 1-based number of the level being played.
            seconds_left: Whole seconds left before the level times out.
        """
        self._hud = (score, level_number, seconds_left)
        self.refresh()

    def handle_key(self, *params: Any) -> None:
        """React to a key press: quit, toggle paff, cycle colors.

        Args:
            params: MLX hook payload; ``params[0]`` is the keycode.
        """
        keycode = params[0]
        if keycode == KEY_Q:
            self._window.destroy()

    def _render(self) -> None:
        """Redraw the maze and pellets, then present the buffer.

        Nothing to draw yet if :meth:`load` hasn't run: return without
        presenting so the previous screen stays visible until the
        maze is actually ready.
        """
        if self._maze is None:
            return
        self._window.clear(_BACKGROUND_COLOR)
        self._draw(self._maze)
        self._window.present()
        self._draw_hud()

    def _draw_hud(self) -> None:
        """Draw score, lives, level and remaining time along the bottom.

        Must run after :meth:`MlxWindow.present`: unlike ``fill_rect``,
        ``draw_text`` paints straight onto the visible window, not
        into the off-screen buffer, so calling it before ``present``
        would get wiped out by the buffer blit.

        Everything is packed into two strings instead of one per
        value: each ``draw_text`` is a synchronous X11 round-trip
        (profiled at ~2 ms each, with occasional big spikes), and
        this runs on every frame. The remaining time keeps its own
        string so it can turn red when running low.

        Nothing is drawn before the first :meth:`set_hud`/
        :meth:`load_entities` call (e.g. while the maze has never
        been shown yet).
        """
        if self._hud is None or self._player is None:
            return
        score, level_number, seconds_left = self._hud
        top = self._window.height - _HUD_HEIGHT
        time_color = (_HUD_WARNING_COLOR
                      if seconds_left <= _HUD_WARNING_SECONDS
                      else _HUD_TEXT_COLOR)
        self._window.draw_text(
            20, top + 35, _HUD_TEXT_COLOR,
            f"Score: {score}    Lives: {self._player.lives}"
            f"    Level: {level_number}")
        self._window.draw_text(
            self._window.width // 2 - 40, top + 35, time_color,
            f"Time: {seconds_left}s")

    def _draw(self, maze: Maze) -> None:
        """Rasterize every cell of ``maze`` into the off-screen buffer.

        Args:
            maze: The maze to rasterize.
        """
        for y in range(maze.height):
            for x in range(maze.width):
                real_x = self._offset_x + x * self._cell_size
                real_y = self._offset_y + y * self._cell_size
                if maze.grid[y][x] == SOLID:
                    self._window.fill_rect(
                        real_x, real_x + self._cell_size,
                        real_y, real_y + self._cell_size, _SOLID_COLOR)
                    self._window.fill_rect(
                        real_x, real_x + self._cell_size,
                        real_y, real_y, _WALL_COLOR)
                    self._window.fill_rect(
                        real_x, real_x + self._cell_size,
                        real_y + self._cell_size, real_y + self._cell_size,
                        _WALL_COLOR)
                    self._window.fill_rect(
                        real_x + self._cell_size, real_x + self._cell_size,
                        real_y, real_y + self._cell_size, _WALL_COLOR)
                    self._window.fill_rect(
                        real_x, real_x, real_y, real_y + self._cell_size,
                        _WALL_COLOR)
                    continue
                if maze.grid[y][x] & NORTH:
                    self._window.fill_rect(
                        real_x, real_x + self._cell_size,
                        real_y, real_y, _WALL_COLOR)
                if maze.grid[y][x] & SOUTH:
                    self._window.fill_rect(
                        real_x, real_x + self._cell_size,
                        real_y + self._cell_size, real_y + self._cell_size,
                        _WALL_COLOR)
                if maze.grid[y][x] & EAST:
                    self._window.fill_rect(
                        real_x + self._cell_size, real_x + self._cell_size,
                        real_y, real_y + self._cell_size, _WALL_COLOR)
                if maze.grid[y][x] & WEST:
                    self._window.fill_rect(
                        real_x, real_x, real_y, real_y + self._cell_size,
                        _WALL_COLOR)
        if self._pellets is not None:
            self._draw_pellets(self._pellets)
        if self._player is not None:
            self._draw_player(self._player)
        if self._ghosts is not None:
            self._draw_ghosts(self._ghosts)

    def _draw_player(self, player: Player) -> None:
        """Fill a yellow disc with a mouth wedge open toward its direction.

        The wedge is cut in the background color, on top of the full
        disc drawn first -- there is no "disc minus a slice" MLX
        primitive, so painting over is the simplest way to get one.

        Args:
            player: The player to draw.
        """
        assert self._player_glide is not None
        draw_x, draw_y = self._player_glide.at(self._alpha)
        cell = self._cell_size
        cx = self._offset_x + int(draw_x * cell) + cell // 2
        cy = self._offset_y + int(draw_y * cell) + cell // 2
        radius = max(1, int(cell * _PLAYER_RATIO / 2))
        self._window.fill_disc(cx, cy, radius, _PLAYER_COLOR)
        angle = _DIRECTION_ANGLES.get(player.direction, 0.0)
        self._window.fill_wedge(
            cx, cy, radius, angle - _MOUTH_HALF_ANGLE,
            angle + _MOUTH_HALF_ANGLE, _BACKGROUND_COLOR)

    def _draw_ghosts(self, ghosts: list[Ghost]) -> None:
        """Draw every ghost: a colored body (unless EATEN) plus eyes.

        Args:
            ghosts: The level's ghosts, in ``Level.ghosts`` order --
                that order is what assigns each ghost its palette color.
        """
        assert self._ghost_glides is not None
        for index, (ghost, glide) in enumerate(
                zip(ghosts, self._ghost_glides)):
            color = self._ghost_color(ghost, index)
            if color is not None:
                self._draw_ghost_body(glide, color)
            self._draw_ghost_eyes(ghost, glide)

    def _ghost_color(self, ghost: Ghost, index: int) -> int | None:
        """Return one ghost's body color, or None while EATEN.

        Args:
            ghost: The ghost to color.
            index: The ghost's position in ``Level.ghosts``.

        Returns:
            A flat 0xAARRGGBB color, or None when only the eyes
            should be drawn (EATEN: the body is gone, floating home).
        """
        if ghost.state is GhostState.EATEN:
            return None
        if ghost.state is GhostState.FRIGHTENED:
            return _GHOST_FRIGHTENED_COLOR
        return _GHOST_PALETTE[index % len(_GHOST_PALETTE)]

    def _draw_ghost_body(self, glide: _Glide, color: int) -> None:
        """Fill a dome-topped, flat-bottomed body centered on the ghost.

        A plain disc would look identical to a giant pacgum; adding a
        same-color rectangle under the disc's center squares off the
        lower half, giving the classic rounded-top silhouette instead.

        Args:
            glide: The ghost's interpolated on-screen position.
            color: 0xAARRGGBB fill color for the body.
        """
        draw_x, draw_y = glide.at(self._alpha)
        cell = self._cell_size
        cx = self._offset_x + int(draw_x * cell) + cell // 2
        cy = self._offset_y + int(draw_y * cell) + cell // 2
        radius = max(1, int(cell * _GHOST_RATIO / 2))
        self._window.fill_disc(cx, cy, radius, color)
        self._window.fill_rect(cx - radius, cx + radius, cy, cy + radius,
                               color)

    def _draw_ghost_eyes(self, ghost: Ghost, glide: _Glide) -> None:
        """Draw two eyes with pupils looking toward the ghost's direction.

        Drawn for every ghost, including EATEN ones with no body --
        that is the classic "just the eyes drifting home" look.

        Args:
            ghost: The ghost to draw (only its ``direction`` is used,
                to aim the pupils).
            glide: The ghost's interpolated on-screen position.
        """
        draw_x, draw_y = glide.at(self._alpha)
        cell = self._cell_size
        cx = self._offset_x + int(draw_x * cell) + cell // 2
        cy = self._offset_y + int(draw_y * cell) + cell // 2 - cell // 8
        eye_radius = max(1, int(cell * _EYE_RATIO / 2))
        pupil_radius = max(1, eye_radius // 2)
        dx, dy = DELTAS.get(ghost.direction, (0, 0))
        for side in (-1, 1):
            eye_x = cx + side * (eye_radius + 1)
            self._window.fill_disc(eye_x, cy, eye_radius, _EYE_COLOR)
            self._window.fill_disc(
                eye_x + dx * pupil_radius, cy + dy * pupil_radius,
                pupil_radius, _PUPIL_COLOR)

    def _draw_pellets(self, pellets: Pellets) -> None:
        """Draw one dot per remaining pellet, centered in its cell.

        Args:
            pellets: The pacgums/super-pacgums still on the board.
        """
        for x, y in pellets.pacgums:
            self._draw_dot(x, y, _PACGUM_RATIO, _PACGUM_COLOR)
        for x, y in pellets.super_pacgums:
            self._draw_dot(x, y, _SUPER_PACGUM_RATIO, _SUPER_PACGUM_COLOR)

    def _draw_dot(self, x: int, y: int, ratio: float, color: int) -> None:
        """Fill a small disc centered in cell ``(x, y)``.

        Args:
            x: Cell column.
            y: Cell row.
            ratio: Dot diameter, as a fraction of the cell size.
            color: 0xAARRGGBB pixel value.
        """
        radius = max(1, int(self._cell_size * ratio / 2))
        center_x = self._offset_x + x * self._cell_size + self._cell_size // 2
        center_y = self._offset_y + y * self._cell_size + self._cell_size // 2
        self._window.fill_disc(center_x, center_y, radius, color)
