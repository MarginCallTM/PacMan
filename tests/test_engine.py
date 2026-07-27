"""Tests for pacman.game.engine: fixed timestep, scoring, progression."""

import pytest

import pacman.game.engine as engine_mod
from pacman.config import GameConfig
from pacman.entities.ghost import GhostState
from pacman.entities.pellets import Pellets
from pacman.game.engine import (
    MAX_TICKS_PER_UPDATE, TICKS_PER_SECOND, Engine, to_ticks)
from pacman.game.level import Level
from pacman.game.states import GameState
from pacman.maze_loader import NORTH


class FakeClock:
    """Deterministic stand-in for time.monotonic."""

    def __init__(self) -> None:
        """Start the fake clock at zero."""
        self.now = 0.0

    def advance(self, seconds: float) -> None:
        """Move the clock forward by ``seconds``."""
        self.now += seconds

    def monotonic(self) -> float:
        """Return the current fake time (time.monotonic signature)."""
        return self.now


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    """Replace the engine's clock with a controllable one."""
    fake = FakeClock()
    monkeypatch.setattr(engine_mod.time, "monotonic", fake.monotonic)
    return fake


@pytest.fixture
def engine(clock: FakeClock) -> Engine:
    """An engine on the default config, already in level 1."""
    eng = Engine(GameConfig())
    eng.start_game()
    return eng


def playing_level(eng: Engine) -> Level:
    """Return the current level, asserting it exists (mypy narrowing)."""
    assert eng.level is not None
    return eng.level


def test_to_ticks_rounds_and_floors_at_one() -> None:
    """Seconds convert at TICKS_PER_SECOND, tiny values still tick."""
    assert to_ticks(1.0) == TICKS_PER_SECOND
    assert to_ticks(7.0) == 7 * TICKS_PER_SECOND
    assert to_ticks(0.001) == 1


def test_update_converts_elapsed_time_to_ticks(
        engine: Engine, clock: FakeClock) -> None:
    """Half a second at 8 ticks/s runs exactly 4 simulation steps."""
    before = playing_level(engine).ticks_left
    clock.advance(0.5)
    engine.update()
    assert before - playing_level(engine).ticks_left == 4


def test_update_clamps_catch_up_ticks(
        engine: Engine, clock: FakeClock) -> None:
    """An OS freeze pauses the game instead of fast-forwarding it."""
    before = playing_level(engine).ticks_left
    clock.advance(10.0)
    engine.update()
    assert before - playing_level(engine).ticks_left == MAX_TICKS_PER_UPDATE


def test_pause_drains_clock_without_ticking(
        engine: Engine, clock: FakeClock) -> None:
    """Time spent paused never turns into catch-up ticks on resume."""
    engine.machine.transition_to(GameState.PAUSED)
    clock.advance(5.0)
    engine.update()
    before = playing_level(engine).ticks_left
    engine.machine.transition_to(GameState.PLAYING)
    clock.advance(1.0 / TICKS_PER_SECOND)
    engine.update()
    assert before - playing_level(engine).ticks_left == 1


def test_eating_pacgum_scores(engine: Engine) -> None:
    """Stepping on a pacgum adds points_per_pacgum exactly once."""
    level = playing_level(engine)
    here = (level.player.x, level.player.y)
    level.pellets = Pellets(pacgums={here, (0, 0)}, super_pacgums=set())
    engine._tick()
    assert engine.score == engine.config.points_per_pacgum
    engine._tick()
    assert engine.score == engine.config.points_per_pacgum


def test_eating_super_pacgum_scores(engine: Engine) -> None:
    """A super-pacgum is worth points_per_super_pacgum."""
    level = playing_level(engine)
    here = (level.player.x, level.player.y)
    level.pellets = Pellets(pacgums={(0, 0)}, super_pacgums={here})
    engine._tick()
    assert engine.score == engine.config.points_per_super_pacgum


def test_empty_cell_scores_nothing(engine: Engine) -> None:
    """Ticking on an empty cell leaves the score untouched."""
    level = playing_level(engine)
    level.pellets = Pellets(pacgums={(0, 0)}, super_pacgums=set())
    engine._tick()
    assert engine.score == 0


def test_level_completion_carries_score_and_lives(engine: Engine) -> None:
    """Clearing a level keeps score and lives, and loads the next one."""
    level = playing_level(engine)
    level.player.lives = 2
    here = (level.player.x, level.player.y)
    level.pellets = Pellets(pacgums={here}, super_pacgums=set())
    engine._tick()
    after = playing_level(engine)
    assert after.number == 2
    assert after.player.lives == 2
    assert engine.score == engine.config.points_per_pacgum
    assert engine.machine.state is GameState.PLAYING


def test_last_level_completion_wins(engine: Engine) -> None:
    """Clearing the final level moves to the VICTORY screen."""
    level = playing_level(engine)
    level.number = len(engine.config.levels)
    here = (level.player.x, level.player.y)
    level.pellets = Pellets(pacgums={here}, super_pacgums=set())
    engine._tick()
    assert engine.machine.state is GameState.VICTORY


def test_turn_buffers_only_while_playing(clock: FakeClock) -> None:
    """turn() is safe on the menu and buffers a direction in game."""
    eng = Engine(GameConfig())
    eng.turn(NORTH)
    assert eng.level is None
    eng.start_game()
    eng.turn(NORTH)
    assert playing_level(eng).player.wanted == NORTH


def test_super_pacgum_frightens_all_ghosts(engine: Engine) -> None:
    """Eating a super-pacgum flips every ghost to FRIGHTENED."""
    level = playing_level(engine)
    here = (level.player.x, level.player.y)
    level.pellets = Pellets(pacgums={(0, 0)}, super_pacgums={here})
    engine._tick()
    for ghost in level.ghosts:
        assert ghost.state is GhostState.FRIGHTENED


def test_chasing_ghosts_move_every_tick(engine: Engine) -> None:
    """Each tick, every non-eaten ghost leaves its current cell."""
    level = playing_level(engine)
    start = [(g.x, g.y) for g in level.ghosts]
    engine._tick()
    for ghost, position in zip(level.ghosts, start):
        assert (ghost.x, ghost.y) != position


def test_chase_ghost_takes_a_life_and_resets_the_round(
        engine: Engine) -> None:
    """Ghost contact costs a life; everyone respawns at home."""
    level = playing_level(engine)
    ghost = level.ghosts[0]
    ghost.x, ghost.y = level.player.x, level.player.y
    engine._tick()
    assert level.player.lives == engine.config.lives - 1
    assert (level.player.x, level.player.y) == level.player.spawn
    for ghost in level.ghosts:
        assert (ghost.x, ghost.y) == ghost.corner
        assert ghost.state is GhostState.CHASE


def test_last_life_lost_is_game_over(engine: Engine) -> None:
    """Losing the final life moves the state machine to GAME_OVER."""
    level = playing_level(engine)
    level.player.lives = 1
    ghost = level.ghosts[0]
    ghost.x, ghost.y = level.player.x, level.player.y
    engine._tick()
    assert engine.machine.state is GameState.GAME_OVER


def test_player_eats_frightened_ghost(engine: Engine) -> None:
    """A frightened ghost is worth points and goes home EATEN."""
    level = playing_level(engine)
    ghost = level.ghosts[0]
    ghost.frighten(100)
    ghost.x, ghost.y = level.player.x, level.player.y
    engine._tick()
    assert engine.score == engine.config.points_per_ghost
    assert ghost.state is GhostState.EATEN
    assert (ghost.x, ghost.y) == ghost.corner
    assert level.player.lives == engine.config.lives
