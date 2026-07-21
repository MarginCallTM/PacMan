"""Tests for pacman.entities.ghost_ai: BFS map and strategies."""

import random

from pacman.entities.ghost import Ghost
from pacman.entities.ghost_ai import ChaseStrategy, bfs_distances
from pacman.entities.player import Player, spawn_player
from pacman.maze_loader import DELTAS, EAST, Maze, generate_maze

# Same handcrafted 3x3 "plus" maze as test_player.py: center (1,1)
# open on all four sides, one arm per direction, solid corners.
PLUS = Maze(width=3, height=3, grid=(
    (15, 11, 15),
    (13, 0, 7),
    (15, 14, 15),
))


def test_exact_distances_on_plus_maze() -> None:
    """From the center, arms are at 1 and corners are absent"""
    assert bfs_distances(PLUS, (1, 1)) == {
        (1, 1): 0,
        (1, 0): 1, (0, 1): 1, (2, 1): 1, (1, 2): 1,
    }


def test_distances_from_an_arm() -> None:
    """From an arm, the far arms are two steps away, via the center"""
    distances = bfs_distances(PLUS, (0, 1))
    assert distances[(0, 1)] == 0
    assert distances[(1, 1)] == 1
    assert distances[(2, 1)] == 2
    assert distances[(1, 0)] == 2
    assert distances[(1, 2)] == 2


def test_solid_start_maps_only_itself() -> None:
    """A degenerate start on a solid cell must not crash"""
    assert bfs_distances(PLUS, (0, 0)) == {(0, 0): 0}


def test_neighbours_differ_by_at_most_one() -> None:
    """BFS invariant on a real maze: adjacent cells differ by <= 1.

    This is the property that guarantees a chasing ghost always has
    a strictly-closer neighbour to step onto (no local minimum)
    """
    maze = generate_maze(15, 10, seed=42)
    distances = bfs_distances(maze, maze.center())
    for (x, y), dist in distances.items():
        for direction, (dx, dy) in DELTAS.items():
            if maze.can_move(x, y, direction):
                neighbour = (x + dx, y + dy)
                assert neighbour in distances
                assert abs(distances[neighbour] - dist) <= 1


def test_distance_is_symmetric() -> None:
    """dist(a -> b) == dist(b -> a): walls are two-way"""
    maze = generate_maze(15, 10, seed=42)
    here, there = maze.center(), maze.corners()[0]
    assert bfs_distances(maze, here)[there] \
        == bfs_distances(maze, there)[here]


# Handcrafted 3x3 open room: walls on the outer border only.
ROOM = Maze(width=3, height=3, grid=(
    (9, 1, 3),
    (8, 0, 2),
    (12, 4, 6),
))


def chase(maze: Maze, ghost_at: tuple[int, int],
          player_at: tuple[int, int]) -> int:
    """Run one ChaseStrategy decision from a hand-placed setup."""
    ghost = Ghost(x=ghost_at[0], y=ghost_at[1], corner=(0, 0))
    player = Player(x=player_at[0], y=player_at[1],
                    spawn=player_at, lives=3)
    distances = bfs_distances(maze, player_at)
    return ChaseStrategy().choose_direction(
        ghost, player, maze, distances, random.Random(42))


def test_chase_steps_toward_player() -> None:
    """West arm to east arm: the only sane move is EAST."""
    assert chase(PLUS, ghost_at=(0, 1), player_at=(2, 1)) == EAST


def test_tie_breaks_in_nesw_order() -> None:
    """Corner ghost, two equidistant moves: first legal wins (EAST)."""
    assert chase(ROOM, ghost_at=(0, 0), player_at=(1, 1)) == EAST


def test_stuck_ghost_stays_put() -> None:
    """A ghost on a solid cell has no legal move and returns 0."""
    assert chase(PLUS, ghost_at=(0, 0), player_at=(1, 1)) == 0


def test_chase_always_strictly_approaches() -> None:
    """From EVERY reachable cell, the chosen step lands at dist - 1.

    This is the no-local-minimum guarantee: a chasing ghost can
    never be stuck or move away, wherever it stands.
    """
    maze = generate_maze(15, 10, seed=42)
    player = spawn_player(maze, lives=3)
    distances = bfs_distances(maze, (player.x, player.y))
    strategy = ChaseStrategy()
    rng = random.Random(42)
    for (x, y), dist in distances.items():
        if dist == 0:
            continue
        ghost = Ghost(x=x, y=y, corner=(0, 0))
        direction = strategy.choose_direction(
            ghost, player, maze, distances, rng)
        dx, dy = DELTAS[direction]
        assert distances[(x + dx, y + dy)] == dist - 1


def test_chasing_ghost_reaches_the_player() -> None:
    """Stepping the strategy in a loop reaches the player in
    exactly the BFS distance, from a far-away corner."""
    maze = generate_maze(15, 10, seed=42)
    player = spawn_player(maze, lives=3)
    distances = bfs_distances(maze, (player.x, player.y))
    corner = maze.corners()[0]
    ghost = Ghost(x=corner[0], y=corner[1], corner=corner)
    strategy = ChaseStrategy()
    rng = random.Random(42)
    for _ in range(distances[corner]):
        direction = strategy.choose_direction(
            ghost, player, maze, distances, rng)
        dx, dy = DELTAS[direction]
        ghost.x, ghost.y = ghost.x + dx, ghost.y + dy
    assert (ghost.x, ghost.y) == (player.x, player.y)
