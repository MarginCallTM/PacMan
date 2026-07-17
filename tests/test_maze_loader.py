"""Tests for pacman.maze_loader: seeds, symmetry, normalization."""

import pytest

from pacman.maze_loader import (
    DELTAS, RANDOM_SEED, SOLID,
    EAST, NORTH, SOUTH, WEST,
    MazeError, _normalize, generate_maze,
)

OPPOSITE = {NORTH: SOUTH, SOUTH: NORTH, EAST: WEST, WEST: EAST}


def test_seed_reproducibility() -> None:
    """Same seed twice -> identical grid (level 1 is fixed)."""
    first = generate_maze(15, 10, seed=42)
    second = generate_maze(15, 10, seed=42)
    assert first.grid == second.grid


def test_random_seed_generates_a_maze() -> None:
    """RANDOM_SEED (0) must also produce a valid maze (levels 2+)."""
    maze = generate_maze(15, 10, seed=RANDOM_SEED)
    assert maze.corridors()


def test_wall_symmetry() -> None:
    """A wall between two neighbors is stored on both sides."""
    maze = generate_maze(21, 15, seed=42)
    for y in range(maze.height):
        for x in range(maze.width):
            for direction, (dx, dy) in DELTAS.items():
                nx, ny = x + dx, y + dy
                if not maze.is_inside(nx, ny):
                    continue
                here = bool(maze.grid[y][x] & direction)
                there = bool(maze.grid[ny][nx] & OPPOSITE[direction])
                assert here == there


def test_solid_cells_excluded_from_corridors() -> None:
    """corridors() never returns a value-15 ("42" pattern) cell."""
    maze = generate_maze(21, 15, seed=42)
    for x, y in maze.corridors():
        assert maze.grid[y][x] != SOLID


def test_cannot_move_into_solid_cell() -> None:
    """can_move never allows walking into a solid cell."""
    maze = generate_maze(21, 15, seed=42)
    for y in range(maze.height):
        for x in range(maze.width):
            for direction, (dx, dy) in DELTAS.items():
                if maze.can_move(x, y, direction):
                    assert not maze.is_solid(x + dx, y + dy)


def test_can_move_rejects_invalid_direction() -> None:
    """A direction outside N/E/S/W is refused (3 = N|E combined)."""
    maze = generate_maze(15, 10, seed=42)
    x, y = maze.center()
    assert not maze.can_move(x, y, 3)


def test_center_and_corners_are_walkable() -> None:
    """Spawn cells (player center, ghost corners) are never solid."""
    maze = generate_maze(21, 15, seed=42)
    for x, y in [maze.center(), *maze.corners()]:
        assert not maze.is_solid(x, y)


def test_normalize_rejects_bad_shape() -> None:
    """A grid with the wrong number of rows is a MazeError."""
    with pytest.raises(MazeError):
        _normalize([[0, 0]], width=2, height=2)


def test_normalize_rejects_bad_cells() -> None:
    """Cell values outside [0, 15] or booleans are a MazeError."""
    with pytest.raises(MazeError):
        _normalize([[0, 16]], width=2, height=1)
    with pytest.raises(MazeError):
        _normalize([[0, True]], width=2, height=1)
