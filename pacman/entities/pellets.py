"""Pacgum and super-pacgum placement and consumption."""

import random
from dataclasses import dataclass
from enum import Enum, auto

from pacman.maze_loader import Maze


class PelletType(Enum):
    """What the player just ate (the engine maps this to points)"""

    PACGUM = auto()
    SUPER = auto()


@dataclass
class Pellets:
    """Mutable pellet state for one level.

    Attributes:
        pacgums: Cells still holding a regular pacgum
        super_pacgums: Cells still holding a super-pacgum
    """
    pacgums: set[tuple[int, int]]
    super_pacgums: set[tuple[int, int]]

    def eat(self, x: int, y: int) -> PelletType | None:
        """Consume whatever pellet sits on (x, y), if any

        Args:
            x: Cell column.
            y: Cell row.

        Returns:
            The type of the eaten pellet, or None for an empty cell.
        """
        cell = (x, y)
        if cell in self.super_pacgums:
            self.super_pacgums.discard(cell)
            return PelletType.SUPER
        if cell in self.pacgums:
            self.pacgums.discard(cell)
            return PelletType.PACGUM
        return None

    def remaining(self) -> int:
        """Return how many pellets (both kinds) are left to eat"""
        return len(self.pacgums) + len(self.super_pacgums)

    def all_eaten(self) -> bool:
        """Return True when the level is cleared (win condition)"""
        return self.remaining() == 0


def place_pellets(maze: Maze, count: int, seed: int) -> Pellets:
    """Place super-pacgums in the corners and pacgums in corridors.

    The four walkable corner cells get super-pacgums. Regular pacgums
    are drawn from every other corridor cell except the player spawn
    (maze center), using a seeded RNG so a given level is always laid
    out the same way. If count exceeds the available cells, every
    available cell is filled ("most corridors", per the subject).

    Args:
        maze: The level maze.
        count: Number of pacgums to place (config key 'pacgum').
        seed: Level seed, for a reproducible layout.

    Returns:
        A freshly stocked Pellets instance.
    """
    corners = set(maze.corners())
    reserved = corners | {maze.center()}
    eligible = sorted(
        cell for cell in maze.corridors() if cell not in reserved)
    rng = random.Random(seed)
    chosen = rng.sample(eligible, min(count, len(eligible)))
    return Pellets(pacgums=set(chosen), super_pacgums=corners)
