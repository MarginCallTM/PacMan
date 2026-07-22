"""Headless tests for the MLX UI layer: pixel logic, no window.

The MLX C library cannot load on macOS (Linux-only .so), and tests
must never require a display anyway. So ``MlxWindow.__init__`` is
bypassed and a plain Python buffer is injected in place of the MLX
image: ``fill_rect`` and ``MazeRenderer._draw`` are pure index
arithmetic, testable on any machine by reading pixels back.
"""

from array import array

from pacman.maze_loader import NORTH, SOLID, Maze, generate_maze
from pacman.ui import renderer
from pacman.ui.mlx_window import MlxWindow


def make_headless_window(width: int, height: int) -> MlxWindow:
    """Build an MlxWindow without touching the MLX C library."""
    window = MlxWindow.__new__(MlxWindow)
    window.width = width
    window.height = height
    window._addr = memoryview(array("I", [0] * (width * height)))
    window._stride = width
    window._window = None
    return window


def pixel(window: MlxWindow, x: int, y: int) -> int:
    """Read one pixel back from the fake buffer."""
    return int(window._addr[y * window._stride + x])


def draw_seed42() -> tuple[MlxWindow, renderer.MazeRenderer, Maze]:
    """Render the reproducible 15x10 maze into a fake buffer."""
    window = make_headless_window(400, 400)
    maze = generate_maze(15, 10, seed=42)
    painter = renderer.MazeRenderer(window)
    painter.load(maze)
    painter._draw(maze)
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
    """_draw clears the full buffer: no pixel keeps its old value."""
    window, _, _ = draw_seed42()
    assert all(value != 0 for value in window._addr)


def test_solid_cells_are_blue_blocks() -> None:
    """Every value-15 cell (the "42" pattern) is a filled blue block."""
    window, painter, maze = draw_seed42()
    solids = [(x, y)
              for y in range(maze.height) for x in range(maze.width)
              if maze.grid[y][x] == SOLID]
    assert solids
    for x, y in solids:
        px = painter._offset_x + x * painter._cell_w + painter._cell_w // 2
        py = painter._offset_y + y * painter._cell_h + painter._cell_h // 2
        assert pixel(window, px, py) == renderer._SOLID_COLOR


def test_north_walls_are_painted_white() -> None:
    """Each corridor cell with a NORTH bit shows a white wall line."""
    window, painter, maze = draw_seed42()
    walls = 0
    for y in range(maze.height):
        for x in range(maze.width):
            if maze.grid[y][x] != SOLID and maze.grid[y][x] & NORTH:
                px = (painter._offset_x + x * painter._cell_w
                      + painter._cell_w // 2)
                py = painter._offset_y + y * painter._cell_h
                assert pixel(window, px, py) == renderer._WALL_COLOR
                walls += 1
    assert walls > 0
