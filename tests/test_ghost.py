"""Tests for pacman.entities.ghost: state machine and timers."""

from pacman.entities.ghost import Ghost, GhostState


def make_ghost() -> Ghost:
    """Return a fresh CHASE ghost parked away from its corner."""
    return Ghost(x=1, y=1, corner=(0, 0))


def test_spawns_chasing() -> None:
    """A new ghost chases immediately, no timer running"""
    ghost = make_ghost()
    assert ghost.state is GhostState.CHASE
    assert ghost.timer == 0


def test_frighten_starts_timer() -> None:
    """A super-pacgum flips the ghost to FRIGHTENED for N ticks"""
    ghost = make_ghost()
    assert ghost.state is GhostState.CHASE
    assert ghost.timer == 0


def test_second_super_pacgum_resets_timer() -> None:
    """Re-frightening restarts the full duration (no stacking)."""
    ghost = make_ghost()
    ghost.frighten(10)
    ghost.tick()
    ghost.frighten(10)
    assert ghost.timer == 10


def test_frightened_expires_back_to_chase() -> None:
    """FRIGHTENED ends after exactly ``duration`` ticks."""
    ghost = make_ghost()
    ghost.frighten(2)
    ghost.tick()
    assert ghost.state is GhostState.FRIGHTENED
    ghost.tick()
    assert ghost.state is GhostState.CHASE


def test_eaten_teleports_home_then_respawns() -> None:
    """EATEN parks the ghost at its corner until the delay expires."""
    ghost = make_ghost()
    ghost.frighten(10)
    ghost.get_eaten(2)
    assert ghost.state is GhostState.EATEN
    assert (ghost.x, ghost.y) == (0, 0)
    ghost.tick()
    assert ghost.state is GhostState.EATEN
    ghost.tick()
    assert ghost.state is GhostState.CHASE
    assert ghost.timer == 0


def test_super_pacgum_ignores_eaten_ghost() -> None:
    """A super-pacgum must not resurrect a ghost that is out of play."""
    ghost = make_ghost()
    ghost.get_eaten(5)
    ghost.frighten(10)
    assert ghost.state is GhostState.EATEN
    assert ghost.timer == 5


def test_tick_is_a_no_op_while_chasing() -> None:
    """CHASE is not a timed state: ticking it changes nothing."""
    ghost = make_ghost()
    ghost.tick()
    ghost.tick()
    assert ghost.state is GhostState.CHASE
    assert ghost.timer == 0