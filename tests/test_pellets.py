"""Tests for pacman.entities.pellets: placement, consumption, win."""

from pacman.entities.pellets import PelletType, place_pellets
from pacman.maze_loader import generate_maze

MAZE = generate_maze(21, 15, seed=42)


def test_supers_in_corners() -> None:
    """The four walkable corner cells hold the super-pacgums."""
    pellets = place_pellets(MAZE, 42, seed=42)
    assert pellets.super_pacgums == set(MAZE.corners())


def test_pacgums_avoid_reserved_cells() -> None:
    """No pacgum on the spawn, a corner, or a solid cell."""
    pellets = place_pellets(MAZE, 10_000, seed=42)
    corridors = set(MAZE.corridors())
    for cell in pellets.pacgums:
        assert cell in corridors
        assert cell != MAZE.center()
        assert cell not in pellets.super_pacgums


def test_count_is_respected_and_clamped() -> None:
    """Exactly `count` pacgums, capped by the available cells."""
    assert len(place_pellets(MAZE, 5, seed=1).pacgums) == 5
    available = (len(MAZE.corridors())
                 - len(set(MAZE.corners())) - 1)
    huge = place_pellets(MAZE, 10_000, seed=1)
    assert len(huge.pacgums) == available


def test_layout_is_reproducible() -> None:
    """Same maze + same seed -> exact same pacgum layout."""
    first = place_pellets(MAZE, 42, seed=7)
    second = place_pellets(MAZE, 42, seed=7)
    assert first.pacgums == second.pacgums


def test_eat_pacgum_then_empty() -> None:
    """Eating a pacgum returns PACGUM once, then the cell is empty."""
    pellets = place_pellets(MAZE, 42, seed=42)
    x, y = next(iter(pellets.pacgums))
    assert pellets.eat(x, y) is PelletType.PACGUM
    assert pellets.eat(x, y) is None


def test_eat_super_pacgum() -> None:
    """Eating a corner cell returns SUPER and removes it."""
    pellets = place_pellets(MAZE, 42, seed=42)
    x, y = next(iter(pellets.super_pacgums))
    assert pellets.eat(x, y) is PelletType.SUPER
    assert (x, y) not in pellets.super_pacgums


def test_eat_empty_cell() -> None:
    """The spawn cell never holds a pellet: eating it yields None."""
    pellets = place_pellets(MAZE, 42, seed=42)
    x, y = MAZE.center()
    assert pellets.eat(x, y) is None


def test_win_condition() -> None:
    """all_eaten flips to True once every pellet is consumed."""
    pellets = place_pellets(MAZE, 3, seed=42)
    assert not pellets.all_eaten()
    cells = list(pellets.pacgums) + list(pellets.super_pacgums)
    for x, y in cells:
        pellets.eat(x, y)
    assert pellets.remaining() == 0
    assert pellets.all_eaten()
