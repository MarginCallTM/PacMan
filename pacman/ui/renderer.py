"""Maze rendering: walls, colors and keyboard shortcuts.

``MazeRenderer`` owns no MLX state itself: it only writes pixels
through the :class:`~pacman.ui.mlx_window.MlxWindow` it is given, so
other screens (HUD, menus...) can share the same window and buffer
without inheriting from this class.
"""

from typing import Any

from pacman.maze_loader import EAST, NORTH, SOLID, SOUTH, WEST, Maze
from pacman.ui.mlx_window import MlxWindow

_SOLID_COLOR = 0xFF0000FF  # fixed blue for the "42" pattern (SOLID cells)
_WALL_COLOR = 0xFFFFFFFF  # fixed white outline for the "42" pattern
_BACKGROUND_COLOR = 0xFF000000  # fixed black for the background


class MazeRenderer:
    """Draws one :class:`Maze` into a shared :class:`MlxWindow`."""

    def __init__(self, window: MlxWindow) -> None:
        """Bind this renderer to an already-created window.

        Args:
            window: The shared MLX window to draw into.
        """
        self._window = window
        self._maze: Maze | None = None
        self._cell_w = 0
        self._cell_h = 0
        self._offset_x = 0
        self._offset_y = 0
        self._theme_index = 0
        self._dirty = True

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
        self._dirty = True

    def handle_key(self, *params: Any) -> None:
        """React to a key press: quit, toggle paff, cycle colors.

        Args:
            params: MLX hook payload; ``params[0]`` is the keycode.
        """
        keycode = params[0]
        if keycode == 113:  # q
            self._window.destroy()

    def render_if_dirty(self, *_: Any) -> None:
        """MLX loop-hook: redraw only when something actually changed."""
        if not self._dirty or self._maze is None:
            return
        self._draw(self._maze)
        self._window.present()
        self._dirty = False

    def _draw(self, maze: Maze) -> None:
        """Fill the whole buffer with the background, then the maze.

        The buffer is the size of the whole window, so it must be
        cleared here in full: :meth:`MlxWindow.present` blits it at
        ``(0, 0)`` over the entire window, and this is what erases
        whatever the previous screen (e.g. a menu) had drawn.

        Args:
            maze: The maze to rasterize.
        """
        self._window.fill_rect(
            0, self._window.width - 1,
            0, self._window.height - 1, _BACKGROUND_COLOR)
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
