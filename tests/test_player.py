"""Tests for pacman.entities.player: movement, turns, lives"""

from pacman.maze_loader import EAST, NORTH, WEST, Maze
from pacman.entities.player import Player, spawn_player

# Handcrafted 3x3 "plus" maze: center (1,1) open on all four
# sides, one arm per direction, solid (15) corners.
PLUS = Maze(width=3, height=3, grid=(
    (15, 11, 15),
    (13, 0, 7),
    (15, 14, 15),
))


def test_step_moves_along_corridor() -> None:
    """A legal step moves the player one cell and returns True."""
    player = Player(x=0, y=1, spawn=(1, 1), lives=3)
    player.turn(EAST)
    assert player.step(PLUS) is True
    assert (player.x, player.y) == (1, 1)
    assert player.direction == EAST


def test_blocked_step_returns_false() -> None:
    """Facing a wall while standing still: no moves, False"""
    player = Player(x=0, y=1, spawn=(1, 1), lives=3)
    player.turn(WEST)
    assert player.step(PLUS) is False
    assert (player.x, player.y) == (0, 1)


def test_buffered_turn_is_taken_when_legal() -> None:
    """An illegal turn stays buffered and triggers at the junction"""
    player = Player(x=0, y=1, spawn=(1, 1), lives=3, direction=EAST)
    player.turn(NORTH)
    assert player.step(PLUS) is True
    assert (player.x, player.y) == (1, 1)  # north walled: Kept EAST
    assert player.step(PLUS) is True
    assert (player.x, player.y) == (1, 0)  # buffered turn taken here
    assert player.direction == NORTH


def test_turn_ignores_invalid_direction() -> None:
    """A garbage direction value leaves the buffer untouched."""
    player = Player(x=1, y=1, spawn=(1, 1), lives=3)
    player.turn(EAST)
    player.turn(99)
    assert player.wanted == EAST


def test_lose_life_respawns_at_center() -> None:
    """Losing a life sends the player back to spawn, standing still."""
    player = Player(x=1, y=0, spawn=(1, 1), lives=3, direction=NORTH)
    player.turn(NORTH)
    player.lose_life()
    assert (player.x, player.y) == (1, 1)
    assert player.lives == 2
    assert player.direction == 0
    assert player.wanted == 0
    assert not player.is_dead()


def test_is_dead_at_zero_lives() -> None:
    """The last life flips is_dead to True."""
    player = Player(x=1, y=1, spawn=(1, 1), lives=1)
    player.lose_life()
    assert player.is_dead()


def test_spawn_player_starts_at_maze_center() -> None:
    """The factory places the player on the walkable center cell."""
    player = spawn_player(PLUS, lives=3)
    assert (player.x, player.y) == PLUS.center()
    assert player.spawn == PLUS.center()
    assert player.lives == 3
