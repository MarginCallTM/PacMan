"""Maze rendering: walls, colors and keyboard shortcuts.

``MazeRenderer`` owns no MLX state itself: it only writes pixels
through the :class:`~pacman.ui.mlx_window.MlxWindow` it is given, so
other screens (HUD, menus...) can share the same window and buffer
without inheriting from this class.
"""

from typing import Any

from pacman.entities.pellets import Pellets
from pacman.maze_loader import EAST, NORTH, SOLID, SOUTH, WEST, Maze
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
        self._cell_w = 0
        self._cell_h = 0
        self._offset_x = 0
        self._offset_y = 0

    def load(self, maze: Maze) -> None:
        """Compute the cell size for ``maze`` and mark the view dirty.

        Args:
            maze: The maze to display starting next frame.
        """
        self._maze = maze
        usable_w = self._window.width - 50
        usable_h = self._window.height - 150
        size = min(usable_w, usable_h)
        self._cell_w = size // maze.width
        self._cell_h = size // maze.height
        self._offset_x = (
            (self._window.width - self._cell_w * maze.width) // 2)
        self._offset_y = (
            ((self._window.height - 100) - self._cell_h * maze.height)
            // 2)
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

    def _draw(self, maze: Maze) -> None:
        """Rasterize every cell of ``maze`` into the off-screen buffer.

        Args:
            maze: The maze to rasterize.
        """
        for y in range(maze.height):
            for x in range(maze.width):
                real_x = self._offset_x + x * self._cell_w
                real_y = self._offset_y + y * self._cell_h
                if maze.grid[y][x] == SOLID:
                    self._window.fill_rect(
                        real_x, real_x + self._cell_w,
                        real_y, real_y + self._cell_h, _SOLID_COLOR)
                    self._window.fill_rect(
                        real_x, real_x + self._cell_w,
                        real_y, real_y, _WALL_COLOR)
                    self._window.fill_rect(
                        real_x, real_x + self._cell_w,
                        real_y + self._cell_h, real_y + self._cell_h,
                        _WALL_COLOR)
                    self._window.fill_rect(
                        real_x + self._cell_w, real_x + self._cell_w,
                        real_y, real_y + self._cell_h, _WALL_COLOR)
                    self._window.fill_rect(
                        real_x, real_x, real_y, real_y + self._cell_h,
                        _WALL_COLOR)
                    continue
                if maze.grid[y][x] & NORTH:
                    self._window.fill_rect(
                        real_x, real_x + self._cell_w,
                        real_y, real_y, _WALL_COLOR)
                if maze.grid[y][x] & SOUTH:
                    self._window.fill_rect(
                        real_x, real_x + self._cell_w,
                        real_y + self._cell_h, real_y + self._cell_h,
                        _WALL_COLOR)
                if maze.grid[y][x] & EAST:
                    self._window.fill_rect(
                        real_x + self._cell_w, real_x + self._cell_w,
                        real_y, real_y + self._cell_h, _WALL_COLOR)
                if maze.grid[y][x] & WEST:
                    self._window.fill_rect(
                        real_x, real_x, real_y, real_y + self._cell_h,
                        _WALL_COLOR)
        if self._pellets is not None:
            self._draw_pellets(self._pellets)

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
        radius = max(1, int(min(self._cell_w, self._cell_h) * ratio / 2))
        center_x = self._offset_x + x * self._cell_w + self._cell_w // 2
        center_y = self._offset_y + y * self._cell_h + self._cell_h // 2
        self._window.fill_disc(center_x, center_y, radius, color)
