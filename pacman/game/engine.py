"""Game engine: fixed-timestep simulation, scoring, collisions."""

import random
import time
from dataclasses import dataclass

from pacman.config import GameConfig
from pacman.entities.ghost import GhostState
from pacman.entities.ghost_ai import FleeStrategy, bfs_distances
from pacman.entities.pellets import PelletType
from pacman.game.level import Level, build_level
from pacman.game.states import GameState, StateMachine
from pacman.highscores import (
    add_score, is_valid_name, load_highscores, save_highscores)
from pacman.maze_loader import DELTAS

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


@dataclass
class Cheats:
    """Active cheat toggles (reviewer tools, subject VI.5).

    Attributes:
        invincible: Ghost contact costs no life.
        frozen: Ghosts stop moving (their timers freeze too).
        boost: The player moves two cells per tick instead of one.
    """

    invincible: bool = False
    frozen: bool = False
    boost: bool = False


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
        self.ticks_elapsed = 0
        self._rng = random.Random(config.seed)
        self._flee = FleeStrategy()
        self.cheats = Cheats()

    def start_game(self) -> None:
        """Reset score and cheats, enter level 1 (MENU -> PLAYING)."""
        self.score = 0
        self.cheats = Cheats()
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

    def tick_progress(self) -> float:
        """Return how far we are toward the next simulation tick.

        Purely informational: the simulation never reads this itself,
        it only lets the UI interpolate an entity's on-screen position
        between its last cell and its next one instead of jumping,
        since ticks only run ``TICKS_PER_SECOND`` times a second while
        the display refreshes much faster.

        Returns:
            A value in [0, 1): 0 right after a tick just ran, growing
            toward 1 as real time passes until the next one fires.
        """
        return self._accumulator * TICKS_PER_SECOND

    def turn(self, direction: int) -> None:
        """Buffer a keyboard direction for the player.

        Called by the UI on key presses; ignored outside gameplay.

        Args:
            direction: One of NORTH, EAST, SOUTH, WEST.
        """
        if self.machine.state is GameState.PLAYING and self.level:
            self.level.player.turn(direction)

    def toggle_pause(self) -> None:
        """Flip between PLAYING and PAUSED; ignored on other screens."""
        if self.machine.state is GameState.PLAYING:
            self.machine.transition_to(GameState.PAUSED)
        elif self.machine.state is GameState.PAUSED:
            self.machine.transition_to(GameState.PLAYING)

    def quit_to_menu(self) -> None:
        """Abandon the paused game and return to the main menu."""
        if self.machine.state is GameState.PAUSED:
            self.level = None
            self.machine.transition_to(GameState.MENU)

    def enter_name_entry(self) -> None:
        """Move from an end screen (win or lose) to the name prompt."""
        if self.machine.state in (GameState.GAME_OVER, GameState.VICTORY):
            self.machine.transition_to(GameState.NAME_ENTRY)

    def submit_name(self, name: str) -> bool:
        """Persist the final score under ``name`` and go to the menu.

        The name is re-validated here even though the UI validates
        while typing: the engine is the last line of defense before
        the highscore file.

        Args:
            name: Player name typed on the name-entry screen.

        Returns:
            True on success; False when the name is invalid or the
            game is not on the name-entry screen (the UI should keep
            that screen open).
        """
        if self.machine.state is not GameState.NAME_ENTRY:
            return False
        if not is_valid_name(name):
            return False
        path = self.config.highscore_filename
        scores = add_score(load_highscores(path), name, self.score)
        save_highscores(path, scores)
        self.level = None
        self.machine.transition_to(GameState.MENU)
        return True

    def cheat_toggle_invincibility(self) -> None:
        """Cheat: toggle 'ghost contact costs no life'."""
        self.cheats.invincible = not self.cheats.invincible

    def cheat_toggle_ghost_freeze(self) -> None:
        """Cheat: toggle 'ghosts stop moving' (timers freeze too)."""
        self.cheats.frozen = not self.cheats.frozen

    def cheat_toggle_speed_boost(self) -> None:
        """Cheat: toggle 'player moves two cells per tick'."""
        self.cheats.boost = not self.cheats.boost

    def cheat_extra_life(self) -> None:
        """Cheat: grant one extra life; only during gameplay."""
        if self.machine.state is GameState.PLAYING and self.level:
            self.level.player.lives += 1

    def cheat_level_skip(self) -> None:
        """Cheat: instantly win the current level; only in gameplay.

        Reuses _advance_level, so score/lives carry-over and the
        VICTORY transition on the last level behave exactly like a
        real level clear.
        """
        if self.machine.state is GameState.PLAYING and self.level:
            self._advance_level(self.level)

    def _tick(self) -> None:
        """Run one fixed simulation step.

        Collisions are checked twice - after the player moves and
        after the ghosts move - so neither side can walk through the
        other within one tick. A lost life ends the tick early
        (round reset); so does leaving PLAYING (game over).
        Cheats hook in here: boost doubles the player steps (eating
        between steps, so no pellet is jumped over) and freeze skips
        the whole ghost half of the tick.
        """
        if self.level is None or self.machine.state is not GameState.PLAYING:
            return
        self.ticks_elapsed += 1  # UI-only: lets it detect a tick just ran
        level = self.level
        level.tick()
        if level.timed_out():
            # DECISION (task 8.5): a timeout costs one life and the
            # timer restarts - documented in the README.
            level.ticks_left = to_ticks(self.config.level_max_time)
            self._lose_life(level)
            return
        steps = 2 if self.cheats.boost else 1
        for _ in range(steps):
            level.player.step(level.maze)
            self._eat_pellet(level)
        if self._handle_collisions(level):
            return
        if not self.cheats.frozen:
            self._move_ghosts(level)
            if self._handle_collisions(level):
                return
        if level.complete():
            self._advance_level(level)

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
            for ghost in level.ghosts:
                ghost.frighten(to_ticks(FRIGHTENED_SECONDS))

    def _move_ghosts(self, level: Level) -> None:
        """Advance ghost timers, then step every active ghost.

        One BFS distance map from the player is computed per tick and
        shared by all ghosts. FRIGHTENED ghosts flee (engine-owned
        FleeStrategy); CHASE ghosts follow their own personality;
        EATEN ghosts wait at home and do not move.

        Args:
            level: The current level, already nil-checked by the caller.
        """
        distances = bfs_distances(
            level.maze, (level.player.x, level.player.y))
        for ghost, personality in zip(level.ghosts, level.strategies):
            ghost.tick()
            if ghost.state is GhostState.EATEN:
                continue
            strategy = (self._flee
                        if ghost.state is GhostState.FRIGHTENED
                        else personality)
            direction = strategy.choose_direction(
                ghost, level.player, level.maze, distances, self._rng)
            if direction:
                dx, dy = DELTAS[direction]
                ghost.x, ghost.y = ghost.x + dx, ghost.y + dy
                ghost.direction = direction

    def _handle_collisions(self, level: Level) -> bool:
        """Resolve every ghost sharing the player's cell.

        FRIGHTENED ghost -> eaten: points_per_ghost, sent home for
        RESPAWN_SECONDS. CHASE ghost -> the player loses a life.
        EATEN ghosts are out of play and harmless.

        Args:
            level: The current level, already nil-checked by the caller.

        Returns:
            True when the player lost a life (the tick must stop:
            the round has been reset).
        """
        for ghost in level.ghosts:
            if (ghost.x, ghost.y) != (level.player.x, level.player.y):
                continue
            if ghost.state is GhostState.FRIGHTENED:
                self.score += self.config.points_per_ghost
                ghost.get_eaten(to_ticks(RESPAWN_SECONDS))
            elif (ghost.state is GhostState.CHASE
                    and not self.cheats.invincible):
                self._lose_life(level)
                return True
        return False

    def _lose_life(self, level: Level) -> None:
        """Take one life and reset the round, or end the game.

        The player respawns at the center, every ghost goes back to
        its corner (send_home); at zero lives the state machine moves
        to GAME_OVER.

        Args:
            level: The current level, already nil-checked by the caller.
        """
        level.player.lose_life()
        for ghost in level.ghosts:
            ghost.send_home()
        if level.player.is_dead():
            self.machine.transition_to(GameState.GAME_OVER)

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
