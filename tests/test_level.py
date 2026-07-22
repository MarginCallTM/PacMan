"""Tests for pacman.game.level: assembling one playable board."""

from pacman.config import GameConfig
from pacman.entities.ghost import GhostState
from pacman.entities.ghost_ai import ChaseStrategy, RandomStrategy
from pacman.game.level import Level, build_level


def make_level(number: int = 1, lives: int = 3,
               time_limit: int = 100) -> Level:
    """Build a level from the default (valid) config."""
    return build_level(GameConfig(), number, lives, time_limit)


def test_level_one_is_reproducible() -> None:
    """Two builds of level 1 share the same maze: fixed seed rule."""
    assert make_level(1).maze.grid == make_level(1).maze.grid


def test_later_levels_are_random() -> None:
    """Two builds of level 2 differ (probabilistic, and fine)."""
    assert make_level(2).maze.grid != make_level(2).maze.grid


def test_four_ghosts_spawn_on_their_corners() -> None:
    """One ghost per corner, home saved, everyone starts chasing."""
    level = make_level()
    corners = level.maze.corners()
    assert len(level.ghosts) == len(corners) == 4
    for ghost, corner in zip(level.ghosts, corners):
        assert (ghost.x, ghost.y) == corner
        assert ghost.corner == corner
        assert ghost.state is GhostState.CHASE


def test_personalities_alternate() -> None:
    """Corners get Chase, Random, Chase, Random — in that order."""
    types = [type(s) for s in make_level().strategies]
    assert types == [ChaseStrategy, RandomStrategy,
                     ChaseStrategy, RandomStrategy]


def test_player_spawns_at_center_with_carried_lives() -> None:
    """The player stands on the center cell with the given lives."""
    level = make_level(lives=5)
    assert (level.player.x, level.player.y) == level.maze.center()
    assert level.player.lives == 5


def test_timer_counts_down_and_stops_at_zero() -> None:
    """Ticks expire the level, and never go negative."""
    level = make_level(time_limit=2)
    assert not level.timed_out()
    level.tick()
    level.tick()
    assert level.timed_out()
    level.tick()
    assert level.ticks_left == 0


def test_new_level_is_not_complete() -> None:
    """A fresh board still has pellets to eat."""
    assert not make_level().complete()
