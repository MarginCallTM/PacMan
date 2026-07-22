"""Tests for pacman.entities.ghost_ai: BFS map and strategies."""

import random

from pacman.entities.ghost import Ghost
from pacman.entities.ghost_ai import (ChaseStrategy, FleeStrategy,
                                      RandomStrategy, bfs_distances)
from pacman.entities.player import Player, spawn_player
from pacman.maze_loader import (DELTAS, EAST, NORTH, SOUTH, WEST,
                                Maze, generate_maze)

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


def flee(maze: Maze, ghost_at: tuple[int, int],
         player_at: tuple[int, int]) -> int:
    """Run one FleeStrategy decision from a hand-placed setup."""
    ghost = Ghost(x=ghost_at[0], y=ghost_at[1], corner=(0, 0))
    player = Player(x=player_at[0], y=player_at[1],
                    spawn=player_at, lives=3)
    distances = bfs_distances(maze, player_at)
    return FleeStrategy().choose_direction(
        ghost, player, maze, distances, random.Random(42))


def test_flee_steps_away_from_player() -> None:
    """Edge ghost, player below: NORTH is the unique furthest cell."""
    assert flee(ROOM, ghost_at=(0, 1), player_at=(1, 2)) == NORTH


def test_flee_ties_break_in_nesw_order() -> None:
    """Center ghost, three equidistant escapes: first wins (NORTH)."""
    assert flee(PLUS, ghost_at=(1, 1), player_at=(0, 1)) == NORTH


def test_cornered_ghost_flees_into_the_player() -> None:
    """One-exit arm: greedy flee walks toward the player (trade-off)."""
    assert flee(PLUS, ghost_at=(0, 1), player_at=(1, 1)) == EAST


def wander(maze: Maze, at: tuple[int, int], facing: int,
           rng: random.Random) -> int:
    """Run one RandomStrategy decision from a hand-placed setup."""
    ghost = Ghost(x=at[0], y=at[1], corner=(0, 0), direction=facing)
    player = Player(x=1, y=1, spawn=(1, 1), lives=3)
    return RandomStrategy().choose_direction(
        ghost, player, maze, bfs_distances(maze, (1, 1)), rng)


def test_random_never_reverses_at_intersections() -> None:
    """100 draws at an open crossroads: no U-turn, all else covered."""
    rng = random.Random(42)
    picks = {wander(ROOM, (1, 1), NORTH, rng) for _ in range(100)}
    assert picks == {NORTH, EAST, WEST}


def test_dead_end_forces_a_u_turn() -> None:
    """Top arm of the plus, facing NORTH: SOUTH is the only way out."""
    assert wander(PLUS, (1, 0), NORTH, random.Random(42)) == SOUTH


def test_first_move_allows_any_direction() -> None:
    """direction=0 (spawn) forbids nothing: the one exit is taken."""
    assert wander(PLUS, (0, 1), 0, random.Random(42)) == EAST


def test_walled_in_ghost_returns_zero() -> None:
    """A ghost on a solid cell stays put, without crashing."""
    assert wander(PLUS, (0, 0), 0, random.Random(42)) == 0


def test_random_is_reproducible_with_same_seed() -> None:
    """Two runs with the same seed pick the same 20 directions."""
    runs = [[wander(ROOM, (1, 1), NORTH, random.Random(7))
             for _ in range(20)]
            for _ in range(2)]
    assert runs[0] == runs[1]
