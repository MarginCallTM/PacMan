"""Maze rendering: walls, colors and keyboard shortcuts.

``MazeRenderer`` owns no MLX state itself: it only writes pixels
through the :class:`~pacman.ui.mlx_window.MlxWindow` it is given, so
other screens (HUD, menus...) can share the same window and buffer
without inheriting from this class.
"""

from typing import Any

from pacman.maze_loader import EAST, NORTH, SOLID, SOUTH, WEST, Maze
from pacman.ui.mlx_window import MlxWindow

_COLOR_THEMES: tuple[dict[str, int], ...] = (
    {'wall': 0xFFFFFFFF, 'paff': 0xFF123456, 'background': 0xFF000000},
    {'wall': 0xFF2C3E50, 'background': 0xFF1A1A1A, 'paff': 0xFFE74C3C},
    {'wall': 0xFF0F380F, 'background': 0xFF8BAC0F, 'paff': 0xFF9BBC0F},
    {'wall': 0xFF4B0082, 'background': 0xFF212121, 'paff': 0xFF9B59B6},
)


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
        self._theme_index = 0
        self._show_paff = False
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
        self._dirty = True

    def draw_help(self) -> None:
        """Draw the on-screen keyboard shortcuts.

        Not called automatically (same as before the refactor) —
        wire it into :meth:`render_if_dirty` if/when you want it
        visible.
        """
        lines = (
            (110, "A-Maze-Ing keyboard Help"),
            (80, "R: Regen the Maze"),
            (60, "C: change color"),
            (40, "Q: Quit the program"),
            (20, "P: Show/Hide THE BIG PAFF"),
        )
        for offset, text in lines:
            self._window.draw_text(
                25, self._window.height - offset, 0xFFFFFFFF, text)

    def handle_key(self, *params: Any) -> None:
        """React to a key press: quit, toggle paff, cycle colors.

        Args:
            params: MLX hook payload; ``params[0]`` is the keycode.
        """
        keycode = params[0]
        if keycode == 113:  # q
            self._window.destroy()
        elif keycode == 112:  # p
            self._show_paff = not self._show_paff
            self._dirty = True
        elif keycode == 99:  # c
            self._theme_index = (
                (self._theme_index + 1) % len(_COLOR_THEMES))
            self._dirty = True

    def render_if_dirty(self, *_: Any) -> None:
        """MLX loop-hook: redraw only when something actually changed."""
        if not self._dirty or self._maze is None:
            return
        self._draw(self._maze)
        self._window.present(
            (self._window.width - self._cell_w * self._maze.width) // 2,
            ((self._window.height - 100)
             - self._cell_h * self._maze.height) // 2)
        self._dirty = False

    def _draw(self, maze: Maze) -> None:
        """Fill the buffer with the maze's background and walls.

        Args:
            maze: The maze to rasterize.
        """
        theme = _COLOR_THEMES[self._theme_index]
        for y in range(maze.height):
            for x in range(maze.width):
                real_x = x * self._cell_w
                real_y = y * self._cell_h
                self._window.fill_rect(
                    real_x, real_x + self._cell_w,
                    real_y, real_y + self._cell_h, theme['background'])
                if maze.grid[y][x] == SOLID:
                    self._window.fill_rect(
                        real_x, real_x + self._cell_w,
                        real_y, real_y + self._cell_h, theme['wall'])
                    continue
                if maze.grid[y][x] & NORTH:
                    self._window.fill_rect(
                        real_x, real_x + self._cell_w,
                        real_y, real_y, theme['wall'])
                if maze.grid[y][x] & SOUTH:
                    self._window.fill_rect(
                        real_x, real_x + self._cell_w,
                        real_y + self._cell_h, real_y + self._cell_h,
                        theme['wall'])
                if maze.grid[y][x] & EAST:
                    self._window.fill_rect(
                        real_x + self._cell_w, real_x + self._cell_w,
                        real_y, real_y + self._cell_h, theme['wall'])
                if maze.grid[y][x] & WEST:
                    self._window.fill_rect(
                        real_x, real_x, real_y, real_y + self._cell_h,
                        theme['wall'])
