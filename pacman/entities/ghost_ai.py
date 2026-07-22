"""Ghost AI: BFS distance map and movement strategies."""

import random
from abc import ABC, abstractmethod
from collections import deque

from pacman.entities.ghost import Ghost
from pacman.entities.player import Player
from pacman.maze_loader import DELTAS, OPPOSITE, Maze

# A BFS distance map, as returned by bfs_distances().
Distances = dict[tuple[int, int], int]


def bfs_distances(maze: Maze, start: tuple[int, int]
                  ) -> dict[tuple[int, int], int]:
    """Map every cell reachable from ``start`` to its step distance.

    One breadth-first search from the player's cell per tick serves
    every ghost: chasing means moving to the neighbour with the
    smallest distance, fleeing to the one with the largest.

    Args:
        maze: The current level maze.
        start: Source cell (x, y), typically the player's position.

    Returns:
        A dict mapping each reachable (x, y) cell to its distance
        in steps from ``start``. Unreachable cells are absent.
    """
    distances = {start: 0}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for direction, (dx, dy) in DELTAS.items():
            neighbour = (x + dx, y + dy)
            if neighbour in distances:
                continue
            if maze.can_move(x, y, direction):
                distances[neighbour] = distances[(x, y)] + 1
                queue.append(neighbour)
    return distances


class Strategy(ABC):
    """Contract shared by every ghost movement strategy."""

    @abstractmethod
    def choose_direction(self, ghost: Ghost, player: Player,
                         maze: Maze, distances: Distances,
                         rng: random.Random) -> int:
        """Return the direction to take this tick.

        Args:
            ghost: The deciding ghost (position matters).
            player: The player (position and facing direction).
            maze: The current level maze.
            distances: BFS map from the player, shared per tick.
            rng: Seeded generator, for the random strategies.

        Returns:
            One of NORTH/EAST/SOUTH/WEST or 0 to stay put.
        """


class ChaseStrategy(Strategy):
    """Strategy A: always step onto the cell closest to the player."""

    def choose_direction(self, ghost: Ghost, player: Player,
                         maze: Maze, distances: Distances,
                         rng: random.Random) -> int:
        """Pick the legal neighbour with the smallest distance.

        Ties break deterministically in N/E/S/W order (strict ``<``
        keeps the first best). Falls back to 0 when no reachable
        neighbour exists.

        Args:
            ghost: The deciding ghost.
            player: Unused here: the distance map already encodes it.
            maze: The current level maze.
            distances: BFS map from the player, shared per tick.
            rng: Unused here: chasing is deterministic.

        Returns:
            The chosen direction, or 0 when stuck.
        """
        best, best_dist = 0, None
        for direction, (dx, dy) in DELTAS.items():
            if not maze.can_move(ghost.x, ghost.y, direction):
                continue
            dist = distances.get((ghost.x + dx, ghost.y + dy))
            if dist is None:
                continue
            if best_dist is None or dist < best_dist:
                best, best_dist = direction, dist
        return best


class FleeStrategy(Strategy):
    """Frightened mode: always step onto the cell furthest away."""

    def choose_direction(self, ghost: Ghost, player: Player,
                         maze: Maze, distances: Distances,
                         rng: random.Random) -> int:
        """Pick the legal neighbour with the largest distance.

        Exact mirror of ChaseStrategy: same loop, ``>`` instead of
        ``<``. Greedy and local, so a fleeing ghost can trap itself
        in a dead end - accepted trade-off, documented in README.

        Args:
            ghost: The deciding ghost.
            player: Unused here: the distance map already encodes it.
            maze: The current level maze.
            distances: BFS map from the player, shared per tick.
            rng: Unused here: fleeing is deterministic.

        Returns:
            The chosen direction, or 0 when stuck.
        """
        best, best_dist = 0, None
        for direction, (dx, dy) in DELTAS.items():
            if not maze.can_move(ghost.x, ghost.y, direction):
                continue
            dist = distances.get((ghost.x + dx, ghost.y + dy))
            if dist is None:
                continue
            if best_dist is None or dist > best_dist:
                best, best_dist = direction, dist
        return best


class RandomStrategy(Strategy):
    """Strategy B: straight in corridors, random at intersections."""

    def choose_direction(self, ghost: Ghost, player: Player,
                         maze: Maze, distances: Distances,
                         rng: random.Random) -> int:
        """Pick randomly among legal moves, never reversing.

        In a corridor exactly one non-reverse direction is legal, so
        the ghost keeps going straight; a real choice only happens at
        intersections. Reversing is allowed only in dead ends.

        Args:
            ghost: The deciding ghost (direction matters).
            player: Unused here: this strategy ignores the player.
            maze: The current level maze.
            distances: Unused here: no pathfinding involved.
            rng: Seeded generator, so tests can reproduce runs.

        Returns:
            The chosen direction, or 0 when the ghost is walled in.
        """
        options = [d for d in DELTAS
                   if maze.can_move(ghost.x, ghost.y, d)
                   and d != OPPOSITE.get(ghost.direction)]
        if options:
            return rng.choice(options)
        back = OPPOSITE.get(ghost.direction, 0)
        return back if maze.can_move(ghost.x, ghost.y, back) else 0
