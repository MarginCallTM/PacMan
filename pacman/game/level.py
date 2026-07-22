"""One level: maze, pellets, player, ghosts and the countdown timer."""

from dataclasses import dataclass

from pacman.config import GameConfig
from pacman.entities.ghost import Ghost
from pacman.entities.ghost_ai import ChaseStrategy, RandomStrategy, Strategy
from pacman.entities.pellets import Pellets, place_pellets
from pacman.entities.player import Player, spawn_player
from pacman.maze_loader import RANDOM_SEED, Maze, generate_maze

# Ghost personalities, assigned to corners in cycling order.
PERSONALITIES: tuple[type[Strategy], ...] = (ChaseStrategy, RandomStrategy)


@dataclass
class Level:
    """Everything one playable board contains.

    Attributes:
        number: 1-based level index (level 1 uses the fixed seed).
        maze: The generated maze.
        pellets: Pacgums and super-pacgums still on the board.
        player: The player, spawned at the maze center.
        ghosts: The ghosts, one per corner.
        strategies: Personality of each ghost (same order as ghosts).
        ticks_left: Countdown to the time limit, in engine ticks.
    """

    number: int
    maze: Maze
    pellets: Pellets
    player: Player
    ghosts: list[Ghost]
    strategies: list[Strategy]
    ticks_left: int

    def tick(self) -> None:
        """Count one engine tick toward the time limit."""
        if self.ticks_left > 0:
            self.ticks_left -= 1

    def timed_out(self) -> bool:
        """Return True when the level time limit is exhausted."""
        return self.ticks_left <= 0

    def complete(self) -> bool:
        """Return True when every pellet has been eaten."""
        return self.pellets.all_eaten()


def build_level(config: GameConfig, number: int, lives: int,
                time_limit: int) -> Level:
    """Assemble a ready-to-play level.

    Level 1 uses the fixed config seed (reproducible, subject rule);
    every later level uses RANDOM_SEED for a fresh random maze.

    Args:
        config: Validated game settings.
        number: 1-based level number.
        lives: Lives the player starts this level with (carried over).
        time_limit: Level time budget, in engine ticks.

    Returns:
        A fully populated Level.

    Raises:
        MazeError: If the external generator fails (propagated).
    """
    width, height = config.levels[number - 1]
    seed = config.seed if number == 1 else RANDOM_SEED
    maze = generate_maze(width, height, seed)
    ghosts = [Ghost(x=x, y=y, corner=(x, y)) for x, y in maze.corners()]
    strategies: list[Strategy] = [PERSONALITIES[i % len(PERSONALITIES)]()
                                  for i in range(len(ghosts))]
    return Level(
        number=number,
        maze=maze,
        pellets=place_pellets(maze, config.pacgum, seed),
        player=spawn_player(maze, lives),
        ghosts=ghosts,
        strategies=strategies,
        ticks_left=time_limit,
    )
