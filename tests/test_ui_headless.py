"""Headless tests for the MLX UI layer: pixel logic, no window.

The MLX C library cannot load on macOS (Linux-only .so), and tests
must never require a display anyway. So ``MlxWindow.__init__`` is
bypassed and a plain numpy buffer is injected in place of the
zero-copy view over the MLX image: ``fill_rect``/``fill_disc`` and
``MazeRenderer._draw_walls`` are pure array writes, testable on any
machine by reading pixels back.
"""

import numpy as np

from pacman.maze_loader import NORTH, SOLID, Maze, generate_maze
from pacman.ui import renderer
from pacman.ui.mlx_window import MlxWindow


def make_headless_window(width: int, height: int) -> MlxWindow:
    """Build an MlxWindow without touching the MLX C library."""
    window = MlxWindow.__new__(MlxWindow)
    window.width = width
    window.height = height
    window._pixels = np.zeros((height, width), dtype=np.uint32)
    window._stride = width
    window._window = None
    return window


def pixel(window: MlxWindow, x: int, y: int) -> int:
    """Read one pixel back from the fake buffer."""
    return int(window._pixels[y, x])


def draw_seed42() -> tuple[MlxWindow, renderer.MazeRenderer, Maze]:
    """Render the reproducible 15x10 maze into a fake buffer.

    Mirrors ``MazeRenderer._render`` without the MLX-only present():
    clear the buffer, then rasterize the maze.
    """
    window = make_headless_window(400, 400)
    maze = generate_maze(15, 10, seed=42)
    painter = renderer.MazeRenderer(window)
    painter.load(maze)
    window.clear(renderer._BACKGROUND_COLOR)
    painter._draw_walls(maze)
    return window, painter, maze


def test_fill_rect_writes_inclusive_bounds() -> None:
    """Every pixel inside the rectangle is written, none outside."""
    window = make_headless_window(8, 8)
    window.fill_rect(2, 4, 3, 5, 0xFF123456)
    for y in range(8):
        for x in range(8):
            inside = 2 <= x <= 4 and 3 <= y <= 5
            expected = 0xFF123456 if inside else 0
            assert pixel(window, x, y) == expected


def test_draw_paints_the_whole_background() -> None:
    """clear + _draw covers the buffer: no pixel keeps its old value."""
    window, _, _ = draw_seed42()
    assert bool((window._pixels != 0).all())


def test_solid_cells_are_blue_blocks() -> None:
    """Every value-15 cell (the "42" pattern) is a filled blue block."""
    window, painter, maze = draw_seed42()
    solids = [(x, y)
              for y in range(maze.height) for x in range(maze.width)
              if maze.grid[y][x] == SOLID]
    assert solids
    cell = painter._cell_size
    for x, y in solids:
        px = painter._offset_x + x * cell + cell // 2
        py = painter._offset_y + y * cell + cell // 2
        assert pixel(window, px, py) == renderer._SOLID_COLOR


def test_glide_spreads_over_observed_pace() -> None:
    """A move landing after a rest tick slides over 2 ticks, not 1."""
    glide = renderer._Glide(0.0, 0.0, 0, 0, max_gap=2)
    glide.advance(0, 0)
    glide.advance(1, 0)
    assert glide.at(0.0) == (0.0, 0.0)
    assert glide.at(1.0) == (0.5, 0.0)
    glide.advance(1, 0)
    assert glide.at(1.0) == (1.0, 0.0)


def test_glide_new_move_continues_from_drawn_position() -> None:
    """A move landing mid-slide never makes the sprite jump."""
    glide = renderer._Glide(0.0, 0.0, 0, 0, max_gap=2)
    glide.advance(0, 0)
    glide.advance(1, 0)
    glide.advance(2, 0)
    assert glide.at(0.0) == (0.5, 0.0)
    assert glide.gap == 1


def test_glide_parked_entity_restarts_at_full_speed() -> None:
    """An interval beyond max_gap is a stop, not a pace: no slow-motion."""
    glide = renderer._Glide(0.0, 0.0, 0, 0, max_gap=2)
    for _ in range(5):
        glide.advance(0, 0)
    glide.advance(1, 0)
    assert glide.gap == 1
    assert glide.at(0.5) == (0.5, 0.0)


def test_north_walls_are_painted_white() -> None:
    """Each corridor cell with a NORTH bit shows a white wall line."""
    window, painter, maze = draw_seed42()
    walls = 0
    for y in range(maze.height):
        for x in range(maze.width):
            if maze.grid[y][x] != SOLID and maze.grid[y][x] & NORTH:
                cell = painter._cell_size
                px = painter._offset_x + x * cell + cell // 2
                py = painter._offset_y + y * cell
                assert pixel(window, px, py) == renderer._WALL_COLOR
                walls += 1
    assert walls > 0
