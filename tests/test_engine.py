"""Tests for pacman.game.engine: fixed timestep, scoring, progression."""

from pathlib import Path

import pytest

import pacman.game.engine as engine_mod
from pacman.config import GameConfig
from pacman.entities.ghost import GhostState
from pacman.entities.pellets import Pellets
from pacman.game.engine import (
    CHASE_MOVE_PERIOD, DEATH_PAUSE_SECONDS, FRIGHTENED_MOVE_PERIOD,
    LEVEL_TRANSITION_SECONDS, MAX_TICKS_PER_UPDATE, PLAYER_MOVE_PERIOD,
    TICKS_PER_SECOND, Cheats, Engine, to_ticks)
from pacman.game.level import Level
from pacman.game.states import GameState
from pacman.highscores import load_highscores
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


def tick_one_move(eng: Engine) -> None:
    """Run exactly enough ticks for one player move to land."""
    for _ in range(PLAYER_MOVE_PERIOD):
        eng._tick()


def test_to_ticks_rounds_and_floors_at_one() -> None:
    """Seconds convert at TICKS_PER_SECOND, tiny values still tick."""
    assert to_ticks(1.0) == TICKS_PER_SECOND
    assert to_ticks(7.0) == 7 * TICKS_PER_SECOND
    assert to_ticks(0.001) == 1


def test_update_converts_elapsed_time_to_ticks(
        engine: Engine, clock: FakeClock) -> None:
    """Four tick-durations of real time run exactly 4 simulation steps."""
    before = playing_level(engine).ticks_left
    clock.advance(4 / TICKS_PER_SECOND)
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
    clock.advance(1.5 / TICKS_PER_SECOND)
    engine.update()
    assert before - playing_level(engine).ticks_left == 1


def test_eating_pacgum_scores(engine: Engine) -> None:
    """Stepping on a pacgum adds points_per_pacgum exactly once."""
    level = playing_level(engine)
    here = (level.player.x, level.player.y)
    level.pellets = Pellets(pacgums={here, (0, 0)}, super_pacgums=set())
    tick_one_move(engine)
    assert engine.score == engine.config.points_per_pacgum
    tick_one_move(engine)
    assert engine.score == engine.config.points_per_pacgum


def test_eating_super_pacgum_scores(engine: Engine) -> None:
    """A super-pacgum is worth points_per_super_pacgum."""
    level = playing_level(engine)
    here = (level.player.x, level.player.y)
    level.pellets = Pellets(pacgums={(0, 0)}, super_pacgums={here})
    tick_one_move(engine)
    assert engine.score == engine.config.points_per_super_pacgum


def test_empty_cell_scores_nothing(engine: Engine) -> None:
    """Ticking on an empty cell leaves the score untouched."""
    level = playing_level(engine)
    level.pellets = Pellets(pacgums={(0, 0)}, super_pacgums=set())
    tick_one_move(engine)
    assert engine.score == 0


def test_level_completion_carries_score_and_lives(
        engine: Engine, clock: FakeClock) -> None:
    """Clearing a level shows the banner, then loads the next one
    keeping score and lives."""
    level = playing_level(engine)
    level.player.lives = 2
    here = (level.player.x, level.player.y)
    level.pellets = Pellets(pacgums={here}, super_pacgums=set())
    tick_one_move(engine)
    assert engine.machine.state is GameState.LEVEL_TRANSITION
    assert engine.pending_level_number == 2
    clock.advance(LEVEL_TRANSITION_SECONDS)
    engine.update()
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
    tick_one_move(engine)
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
    tick_one_move(engine)
    for ghost in level.ghosts:
        assert ghost.state is GhostState.FRIGHTENED


def test_chase_ghosts_move_on_their_period(engine: Engine) -> None:
    """A CHASE ghost moves exactly on every CHASE_MOVE_PERIOD-th tick."""
    ghost = playing_level(engine).ghosts[0]
    moved = []
    for _ in range(CHASE_MOVE_PERIOD):
        before = (ghost.x, ghost.y)
        engine._tick()
        moved.append((ghost.x, ghost.y) != before)
    assert moved == [False] * (CHASE_MOVE_PERIOD - 1) + [True]


def test_frightened_ghosts_move_on_their_period(engine: Engine) -> None:
    """A FRIGHTENED ghost moves once per FRIGHTENED_MOVE_PERIOD ticks."""
    ghost = playing_level(engine).ghosts[0]
    ghost.frighten(100)
    moved = []
    for _ in range(FRIGHTENED_MOVE_PERIOD):
        before = (ghost.x, ghost.y)
        engine._tick()
        moved.append((ghost.x, ghost.y) != before)
    assert moved == [False] * (FRIGHTENED_MOVE_PERIOD - 1) + [True]


def test_chase_ghost_takes_a_life_and_resets_the_round(
        engine: Engine) -> None:
    """Ghost contact costs a life; everyone respawns at home."""
    level = playing_level(engine)
    ghost = level.ghosts[0]
    ghost.x, ghost.y = level.player.x, level.player.y
    for _ in range(1 + to_ticks(DEATH_PAUSE_SECONDS)):
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
    for _ in range(1 + to_ticks(DEATH_PAUSE_SECONDS)):
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


def test_fatal_contact_pauses_before_the_reset(engine: Engine) -> None:
    """Death lands only after the freeze, never on the contact tick."""
    level = playing_level(engine)
    ghost = level.ghosts[0]
    ghost.x, ghost.y = level.player.x, level.player.y
    engine._tick()
    assert level.player.lives == engine.config.lives
    for _ in range(to_ticks(DEATH_PAUSE_SECONDS)):
        engine._tick()
    assert level.player.lives == engine.config.lives - 1


def test_timer_expiry_costs_a_life_and_restarts(engine: Engine) -> None:
    """Running out of time loses a life and refills the timer."""
    level = playing_level(engine)
    level.ticks_left = 1
    engine._tick()
    assert level.player.lives == engine.config.lives - 1
    assert level.ticks_left == to_ticks(engine.config.level_max_time)
    assert (level.player.x, level.player.y) == level.player.spawn


def test_toggle_pause_flips_playing_and_paused(engine: Engine) -> None:
    """Pause toggles from gameplay, and back; menu is unaffected."""
    engine.toggle_pause()
    assert engine.machine.state is GameState.PAUSED
    engine.toggle_pause()
    assert engine.machine.state is GameState.PLAYING
    fresh = Engine(GameConfig())
    fresh.toggle_pause()
    assert fresh.machine.state is GameState.MENU


def test_quit_to_menu_only_from_pause(engine: Engine) -> None:
    """The pause menu can abandon the game; gameplay cannot."""
    engine.quit_to_menu()
    assert engine.machine.state is GameState.PLAYING
    engine.toggle_pause()
    engine.quit_to_menu()
    assert engine.machine.state is GameState.MENU
    assert engine.level is None


def test_game_end_saves_score_and_returns_to_menu(
        tmp_path: Path) -> None:
    """GAME_OVER -> name entry -> saved highscore -> main menu."""
    path = str(tmp_path / "highscores.json")
    eng = Engine(GameConfig(highscore_filename=path))
    eng.start_game()
    eng.score = 300
    eng.machine.transition_to(GameState.GAME_OVER)
    eng.enter_name_entry()
    assert eng.machine.state is GameState.NAME_ENTRY
    assert eng.submit_name("Bob")
    assert eng.machine.state is GameState.MENU
    assert eng.level is None
    assert load_highscores(path) == [("Bob", 300)]


def test_submit_name_rejects_invalid_input(tmp_path: Path) -> None:
    """A bad name is refused and the name-entry screen stays open."""
    path = str(tmp_path / "highscores.json")
    eng = Engine(GameConfig(highscore_filename=path))
    eng.start_game()
    eng.machine.transition_to(GameState.VICTORY)
    eng.enter_name_entry()
    assert not eng.submit_name("way too long name")
    assert not eng.submit_name("")
    assert not eng.submit_name("no!")
    assert eng.machine.state is GameState.NAME_ENTRY
    assert load_highscores(path) == []


def test_cheat_invincibility_ignores_ghost_contact(engine: Engine) -> None:
    """With invincibility on, a chasing ghost costs nothing."""
    engine.cheat_toggle_invincibility()
    level = playing_level(engine)
    ghost = level.ghosts[0]
    ghost.x, ghost.y = level.player.x, level.player.y
    engine._tick()
    assert level.player.lives == engine.config.lives
    assert engine.machine.state is GameState.PLAYING


def test_cheat_freeze_stops_ghosts_but_not_the_player(
        engine: Engine) -> None:
    """Frozen ghosts stay put while the game keeps ticking."""
    engine.cheat_toggle_ghost_freeze()
    level = playing_level(engine)
    start = [(g.x, g.y) for g in level.ghosts]
    before = level.ticks_left
    for _ in range(CHASE_MOVE_PERIOD):
        engine._tick()
    assert [(g.x, g.y) for g in level.ghosts] == start
    assert level.ticks_left == before - CHASE_MOVE_PERIOD


def test_cheat_speed_boost_doubles_player_steps(
        engine: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    """Boost makes the player step twice per move, once when off."""
    level = playing_level(engine)
    calls: list[int] = []

    def fake_step(maze: object) -> bool:
        calls.append(1)
        return True

    monkeypatch.setattr(level.player, "step", fake_step)
    engine.cheat_toggle_speed_boost()
    tick_one_move(engine)
    assert len(calls) == 2
    engine.cheat_toggle_speed_boost()
    tick_one_move(engine)
    assert len(calls) == 3


def test_cheat_extra_life_adds_one(engine: Engine) -> None:
    """The extra-life cheat grants exactly one life, in game only."""
    engine.cheat_extra_life()
    assert playing_level(engine).player.lives == engine.config.lives + 1


def test_cheat_level_skip_wins_the_level(
        engine: Engine, clock: FakeClock) -> None:
    """Skip advances like a real clear, VICTORY on the last level."""
    engine.score = 70
    engine.cheat_level_skip()
    assert engine.machine.state is GameState.LEVEL_TRANSITION
    assert engine.pending_level_number == 2
    clock.advance(LEVEL_TRANSITION_SECONDS)
    engine.update()
    assert playing_level(engine).number == 2
    assert engine.score == 70
    playing_level(engine).number = len(engine.config.levels)
    engine.cheat_level_skip()
    assert engine.machine.state is GameState.VICTORY


def test_cheats_reset_on_new_game(engine: Engine) -> None:
    """Leftover cheats never leak into the next game."""
    engine.cheat_toggle_invincibility()
    engine.cheat_toggle_ghost_freeze()
    engine.cheat_toggle_speed_boost()
    engine.toggle_pause()
    engine.quit_to_menu()
    engine.start_game()
    assert engine.cheats == Cheats()
