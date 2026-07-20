"""Pacman player: position, direction, lives and movement."""

from dataclasses import dataclass

from pacman.maze_loader import DELTAS, Maze


@dataclass
class Player:
    """The player's mutable state.

    Attributes:
            x: Current cell column.
            y: Current cell row.
            spawn: Respawn cell (maze center), fixed at creation.
            lives: Remaining lives.
            direction: Current motion direction (0 = standing still)
            wanted: Buffered keyboard direction, applied when legal.
    """
    x: int
    y: int
    spawn: tuple[int, int]
    lives: int
    direction: int = 0
    wanted: int = 0

    def turn(self, direction: int) -> None:
        """Record the direction requested by the keyboard

        The turn is not applied immediately: it is buffered
        and taken on the first step where it becomes legal
        (classic Pac-Man feel).

        Args:
                direction: One of NORTH, EAST, SOUTH, WEST.
        """
        if direction in DELTAS:
            self.wanted = direction

    def step(self, maze: Maze) -> bool:
        """Advance one cell, preferring the buffered turn.

        Args:
                maze: The current level maze.

        Returns:
                True if the player moved, False if blocked on all sides
        """
        for direction in (self.wanted, self.direction):
            if direction and maze.can_move(self.x, self.y, direction):
                dx, dy = DELTAS[direction]
                self.x, self.y = self.x + dx, self.y + dy
                self.direction = direction
                return True
        return False

    def lose_life(self) -> None:
        """Lose one life and respawn at the center, standing still."""
        self.lives -= 1
        self.x, self.y = self.spawn
        self.direction = 0
        self.wanted = 0

    def is_dead(self) -> bool:
        """Return True when no life is left (Game-over condition)"""
        return self.lives <= 0


def spawn_player(maze: Maze, lives: int) -> Player:
    """Create the player at the maze center with full lives.

    Args:
            maze: The level maze.
            lives: Starting lives (config key ``lives``)

    Returns:
            A ready-to-play Player.
    """
    x, y = maze.center()
    return Player(x=x, y=y, spawn=(x, y), lives=lives)
