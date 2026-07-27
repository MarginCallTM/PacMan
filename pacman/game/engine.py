"""Game engine: fixed-timestep simulation, scoring, collisions."""

import time

from pacman.config import GameConfig
from pacman.entities.pellets import PelletType
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

    def turn(self, direction: int) -> None:
        """Buffer a keyboard direction for the player.

        Called by the UI on key presses; ignored outside gameplay.

        Args:
            direction: One of NORTH, EAST, SOUTH, WEST.
        """
        if self.machine.state is GameState.PLAYING and self.level:
            self.level.player.turn(direction)

    def _tick(self) -> None:
        """Run one fixed simulation step."""
        if self.level is None:
            return
        self.level.tick()
        self.level.player.step(self.level.maze)
        self._eat_pellet(self.level)
        if self.level.complete():
            self._advance_level(self.level)

    def _eat_pellet(self, level: Level) -> None:
        """Consume the pellet under the player and score it.

        Args:
            level: The current level, already nil-checked by the caller.
        """
        eaten = level.pellets.eat(level.player.x, level.player.y)
        if eaten is PelletType.PACGUM:
            self.score += self.config.points_per_pacgum
        elif eaten is PelletType.SUPER:
            self.score += self.config.points_per_super_pacgum
            # Frightened-mode trigger lands with the ghosts (inc 3).

    def _advance_level(self, level: Level) -> None:
        """Enter the next level, or VICTORY after the last one.

        The score is deliberately untouched (subject: carries over);
        lives are read from the outgoing player to carry over too.

        Args:
            level: The level that was just completed.
        """
        if level.number >= len(self.config.levels):
            self.machine.transition_to(GameState.VICTORY)
            return
        self._load_level(level.number + 1, level.player.lives)
