"""Tests for pacman.game.states: the screen state machine."""

import pytest

from pacman.game.states import TRANSITIONS, GameState, StateMachine


def test_starts_on_the_menu() -> None:
    """The subject requires the game to open on the main menu."""
    assert StateMachine().state is GameState.MENU


def test_full_victory_path() -> None:
    """Menu -> game -> pause -> game -> victory -> name -> menu."""
    machine = StateMachine()
    for target in (GameState.PLAYING, GameState.PAUSED,
                   GameState.PLAYING, GameState.VICTORY,
                   GameState.NAME_ENTRY, GameState.MENU):
        machine.transition_to(target)
    assert machine.state is GameState.MENU


def test_game_over_path() -> None:
    """Losing goes through the same name entry, back to the menu."""
    machine = StateMachine()
    for target in (GameState.PLAYING, GameState.GAME_OVER,
                   GameState.NAME_ENTRY, GameState.MENU):
        machine.transition_to(target)
    assert machine.state is GameState.MENU


def test_illegal_transition_raises() -> None:
    """Pausing from the menu makes no sense and must explode."""
    with pytest.raises(ValueError):
        StateMachine().transition_to(GameState.PAUSED)


def test_failed_transition_leaves_state_intact() -> None:
    """A refused move must not corrupt the current state."""
    machine = StateMachine()
    with pytest.raises(ValueError):
        machine.transition_to(GameState.VICTORY)
    assert machine.state is GameState.MENU


def test_every_state_has_rules() -> None:
    """Each screen appears in TRANSITIONS and leads somewhere."""
    for state in GameState:
        assert TRANSITIONS[state]
