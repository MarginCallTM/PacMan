"""Game engine: fixed-timestep simulation, scoring, collisions."""

import random
import time
from dataclasses import dataclass

from pacman.config import GameConfig
from pacman.entities.ghost import GhostState
from pacman.entities.ghost_ai import FleeStrategy, Strategy, bfs_distances
from pacman.entities.pellets import PelletType
from pacman.game.level import Level, build_level
from pacman.game.states import GameState, StateMachine
from pacman.highscores import (
    add_score, is_valid_name, load_highscores, save_highscores)
from pacman.maze_loader import DELTAS

# Simulation cadence. 21 ticks/s is the finest quantum in which every
# movement speed below is a WHOLE number of ticks per cell: a regular
# per-entity rhythm is what lets the renderer glide smoothly (an
# irregular rhythm cannot be predicted, hence on-screen stutter).
TICKS_PER_SECOND = 21
# Movement periods, in ticks per one-cell move. The player covers
# 7 cells/s; chasing ghosts 75% of that (close to the arcade
# original); frightened ghosts 50%, so a hunted ghost can actually
# be caught. Every entity moves on a constant beat.
PLAYER_MOVE_PERIOD = 3
CHASE_MOVE_PERIOD = 4
FRIGHTENED_MOVE_PERIOD = 6
# Timed effects, in seconds (converted with to_ticks by the engine).
FRIGHTENED_SECONDS = 7.0
RESPAWN_SECONDS = 7.0
# Freeze on a fatal ghost contact, before the round resets: the
# display deliberately eases up to one movement period behind the
# simulation, so an instant reset would land while the sprites still
# look one cell apart. The pause lets the on-screen slides complete
# -- the contact becomes visible -- and it is arcade-authentic drama.
DEATH_PAUSE_SECONDS = 0.7
# Duration of the "Level N" banner between two levels, before the
# next board is actually built (same timed-pause technique as
# DEATH_PAUSE_SECONDS, just for a different moment).
LEVEL_TRANSITION_SECONDS = 2.0
# Hard cap per update: an OS freeze must pause the game, not
# fast-forward it when the window comes back (~half a second of
# catch-up at most, scaled to the tick rate).
MAX_TICKS_PER_UPDATE = 10


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
        boost: The player moves two cells per move instead of one.
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
        self._death_pause = 0
        self._player_cooldown = 0
        self._transition_ticks = 0
        self._pending_level: tuple[int, int] | None = None
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
        self._death_pause = 0
        self._player_cooldown = 0

    def update(self) -> None:
        """Advance the simulation by however much real time passed.

        Outside PLAYING and LEVEL_TRANSITION the clock is drained but
        nothing moves, so pausing never accumulates catch-up ticks.
        """
        now = time.monotonic()
        elapsed, self._last_time = now - self._last_time, now
        if self.machine.state is GameState.LEVEL_TRANSITION:
            self._run_transition(elapsed)
            return
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

        Called by the UI on key presses; ignored outside gameplay. If
        the player is currently stopped (blocked, just spawned, or
        just respawned), the next move is allowed on the very next
        tick instead of waiting out the rest of the normal movement
        cadence -- that wait only ever exists to cap the player's
        speed while he is actually progressing, so it serves no
        purpose while he isn't moving at all.

        Args:
            direction: One of NORTH, EAST, SOUTH, WEST.
        """
        if self.machine.state is GameState.PLAYING and self.level:
            player = self.level.player
            player.turn(direction)
            if not player.moving:
                self._player_cooldown = 0

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
        """Cheat: toggle 'player moves two cells per move'."""
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

        Every entity moves only on the ticks of its own period
        (PLAYER_MOVE_PERIOD ticks apart for the player, tracked by its
        own _player_cooldown so a fresh key press can shortcut the
        wait while he is stopped -- see turn(); the ghost periods live
        in _move_ghosts); everything else -- timers, collisions, level
        completion -- runs every tick. Collisions are checked twice,
        after the player half and after the ghost half, so neither
        side can walk through the other. A fatal contact ends the
        tick early (death pause); so does leaving PLAYING.
        Cheats hook in here: boost doubles the player steps (eating
        between steps, so no pellet is jumped over) and freeze skips
        the whole ghost half of the tick.
        """
        if self.level is None or self.machine.state is not GameState.PLAYING:
            return
        self.ticks_elapsed += 1  # ghost pacing (modulo) + UI tick detection
        level = self.level
        if self._death_pause:
            self._death_pause -= 1
            if self._death_pause == 0:
                self._lose_life(level)
            return
        level.tick()
        if level.timed_out():
            # DECISION (task 8.5): a timeout costs one life and the
            # timer restarts - documented in the README.
            level.ticks_left = to_ticks(self.config.level_max_time)
            self._lose_life(level)
            return
        if self._player_cooldown == 0:
            steps = 2 if self.cheats.boost else 1
            for _ in range(steps):
                level.player.step(level.maze)
                self._eat_pellet(level)
            self._player_cooldown = PLAYER_MOVE_PERIOD - 1
        else:
            self._player_cooldown -= 1
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
        """Advance ghost timers, then step every ghost due to move.

        One BFS distance map from the player is computed per tick and
        shared by all ghosts. Timers (ghost.tick) always run, so timed
        states keep their real-time duration; movement follows each
        state's constant beat: CHASE ghosts step every
        CHASE_MOVE_PERIOD ticks, FRIGHTENED ghosts every
        FRIGHTENED_MOVE_PERIOD ticks, EATEN ghosts wait at home. The
        player's period is the shortest, so he is always faster: he
        can escape a chaser and catch a fleer.

        Args:
            level: The current level, already nil-checked by the caller.
        """
        distances = bfs_distances(
            level.maze, (level.player.x, level.player.y))
        for ghost, personality in zip(level.ghosts, level.strategies):
            ghost.tick()
            if ghost.state is GhostState.EATEN:
                continue
            if ghost.state is GhostState.FRIGHTENED:
                if self.ticks_elapsed % FRIGHTENED_MOVE_PERIOD != 0:
                    continue
                strategy: Strategy = self._flee
            else:
                if self.ticks_elapsed % CHASE_MOVE_PERIOD != 0:
                    continue
                strategy = personality
            direction = strategy.choose_direction(
                ghost, level.player, level.maze, distances, self._rng)
            if direction:
                dx, dy = DELTAS[direction]
                ghost.x, ghost.y = ghost.x + dx, ghost.y + dy
                ghost.direction = direction

    def _handle_collisions(self, level: Level) -> bool:
        """Resolve every ghost sharing the player's cell.

        FRIGHTENED ghost -> eaten: points_per_ghost, sent home for
        RESPAWN_SECONDS. CHASE ghost -> fatal: the death pause is
        armed; the life itself is taken by _tick once the pause has
        run out, so the player sees the contact on screen first.
        EATEN ghosts are out of play and harmless.

        Args:
            level: The current level, already nil-checked by the caller.

        Returns:
            True on a fatal contact (the tick must stop: the round
            is now suspended in the death pause).
        """
        for ghost in level.ghosts:
            if (ghost.x, ghost.y) != (level.player.x, level.player.y):
                continue
            if ghost.state is GhostState.FRIGHTENED:
                self.score += self.config.points_per_ghost
                ghost.get_eaten(to_ticks(RESPAWN_SECONDS))
            elif (ghost.state is GhostState.CHASE
                    and not self.cheats.invincible):
                self._death_pause = to_ticks(DEATH_PAUSE_SECONDS)
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
        """Park in LEVEL_TRANSITION before the next level, or VICTORY.

        The next level is not built right away: the engine parks in
        LEVEL_TRANSITION for LEVEL_TRANSITION_SECONDS first (the
        "Level N" banner), and _start_pending_level does the actual
        build once that countdown reaches zero. The score is
        deliberately untouched (subject: carries over); lives are
        read from the outgoing player so they carry over too.

        Args:
            level: The level that was just completed.
        """
        if level.number >= len(self.config.levels):
            self.machine.transition_to(GameState.VICTORY)
            return
        self._pending_level = (level.number + 1, level.player.lives)
        self._transition_ticks = to_ticks(LEVEL_TRANSITION_SECONDS)
        self.machine.transition_to(GameState.LEVEL_TRANSITION)

    def _start_pending_level(self) -> None:
        """Build the parked next level and resume PLAYING.

        Called only once the LEVEL_TRANSITION banner has run out.
        """
        assert self._pending_level is not None
        number, lives = self._pending_level
        self._pending_level = None
        self._load_level(number, lives)
        self.machine.transition_to(GameState.PLAYING)

    @property
    def pending_level_number(self) -> int | None:
        """Level about to start, while the LEVEL_TRANSITION banner is up.

        Returns:
            The 1-based level number, or None outside LEVEL_TRANSITION.
        """
        return self._pending_level[0] if self._pending_level else None

    def _run_transition(self, elapsed: float) -> None:
        """Count down the "Level N" banner, then start the next level.

        Ticks are computed by division, like the main branch of
        update() does: repeated float subtraction would drift and
        could leave the countdown one tick short of zero.

        Args:
            elapsed: Real seconds since the previous update() call.
        """
        self._accumulator += elapsed
        tick_duration = 1.0 / TICKS_PER_SECOND
        ticks = min(int(self._accumulator / tick_duration),
                    self._transition_ticks)
        self._accumulator -= ticks * tick_duration
        self._transition_ticks -= ticks
        if self._transition_ticks == 0:
            self._accumulator = 0.0
            self._start_pending_level()
