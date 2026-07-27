"""Game engine: fixed-timestep simulation, scoring, collisions."""

import time

from pacman.config import GameConfig
from pacman.game.level import Level, build_level
from pacman.game.states import GameState, StateMachine

# Simulation cadence: entities move at most one cell per tick.
TICKS_PER_SECOND = 8
# Timed effects, in seconds (converted with to_ticks by the engine).
FRIGHTENED_SECONDS = 7.0
RESPAWN_SECONDS = 7.0
# Hard cap per update: an OS freeze must pause the game, not
# fast-forward it when the window comes back.
MAX_TICKS_PER_UPDATE = 4


def to_ticks(seconds: float) -> int:
    """Convert a duration in seconds to whole engine ticks.

    Args:
        seconds: Duration to convert.

    Returns:
        The duration in ticks, never less than 1.
    """
    return max(1, round(seconds * TICKS_PER_SECOND))


class Engine:
    """Owns the game simulation; knows nothing about graphics.

    The UI calls :meth:`update` from its loop hook at an arbitrary
    rate; the engine converts elapsed real time into fixed ticks so
    the game speed never depends on the frame rate.
    """

    def __init__(self, config: GameConfig) -> None:
        """Store the config and start idle, on the menu.

        Args:
            config: Validated game settings.
        """
        self.config = config
        self.machine = StateMachine()
        self.score = 0
        self.level: Level | None = None
        self.running = True
        self._last_time = time.monotonic()
        self._accumulator = 0.0

    def start_game(self) -> None:
        """Reset the score and enter level 1 (MENU -> PLAYING)."""
        self.score = 0
        self.machine.transition_to(GameState.PLAYING)
        self._load_level(1, self.config.lives)

    def _load_level(self, number: int, lives: int) -> None:
        """Build and install the given level, resetting the clock.

        Args:
            number: 1-based level number.
            lives: Lives carried into this level.
        """
        self.level = build_level(
            self.config, number, lives,
            to_ticks(self.config.level_max_time))
        self._last_time = time.monotonic()
        self._accumulator = 0.0

    def update(self) -> None:
        """Advance the simulation by however much real time passed.

        Outside PLAYING the clock is drained but nothing moves, so
        pausing never accumulates catch-up ticks.
        """
        now = time.monotonic()
        elapsed, self._last_time = now - self._last_time, now
        if self.machine.state is not GameState.PLAYING:
            self._accumulator = 0.0
            return
        self._accumulator += elapsed
        tick_duration = 1.0 / TICKS_PER_SECOND
        ticks = int(self._accumulator / tick_duration)
        if ticks > MAX_TICKS_PER_UPDATE:
            ticks = MAX_TICKS_PER_UPDATE
            self._accumulator = 0.0
        else:
            self._accumulator -= ticks * tick_duration
        for _ in range(ticks):
            self._tick()

    def _tick(self) -> None:
        """Run one fixed simulation step (grows in later increments)."""
        if self.level is None:
            return
        self.level.tick()
