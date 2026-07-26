import sys
from typing import Any

from pacman.config import ConfigError, GameConfig, load_config
from pacman.entities.pellets import place_pellets
from pacman.highscores import load_highscores
from pacman.maze_loader import generate_maze
from pacman.ui.keys import KEY_G, KEY_V
from pacman.ui.menus import (GameOverScreen, InstructionsScreen, MainMenu,
                             NameEntryScreen, VictoryScreen)
from pacman.ui.mlx_window import MlxWindow
from pacman.ui.renderer import MazeRenderer


def _parse_args(argv: list[str]) -> str:
    """Validate the CLI contract: python3 pac-man.py <config.json>.

    Args:
        argv: Full argument vector, i.e. sys.argv.

    Returns:
        The path to the configuration file.

    Raises:
        SystemExit: If the argument count is wrong (usage message
        printed to stderr, no traceback).
    """
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <config.json>", file=sys.stderr)
        raise SystemExit(1)
    return argv[1]


def run_app(config: GameConfig, scores: list[tuple[str, int]]) -> None:
    """Bootstrap the MLX window and hand control to the main menu.

    Args:
        config: Validated game settings.
        scores: Loaded top-10 highscores (not yet consumed here —
            reserved for the Highscores screen, task 9).
    """
    width, height = config.levels[0]
    maze = generate_maze(width, height, config.seed)
    window = MlxWindow()
    window.create_window("PacMan")

    menu = MainMenu(window)
    instructions = InstructionsScreen(window)
    name_entry = NameEntryScreen(window)
    game_over = GameOverScreen(window)
    victory = VictoryScreen(window)
    maze_renderer = MazeRenderer(window)
    maze_renderer.load(maze)
    pellets = place_pellets(maze, count=config.pacgum, seed=config.seed)
    maze_renderer.load_pellets(pellets)

    def show_menu(*_: Any) -> None:
        menu.render_if_dirty()
        if menu.chosen == "Start Game":
            menu.chosen = None
            name_entry.refresh()
            window.hook_key(name_entry.handle_key)
            window.hook_loop(show_name_entry)
        elif menu.chosen == "Instructions":
            menu.chosen = None
            instructions.refresh()
            window.hook_key(instructions.handle_key)
            window.hook_loop(show_instructions)
        elif menu.chosen == "Exit":
            window.destroy()
        elif menu.chosen is not None:
            menu.chosen = None  # Highscores: not built yet

    def show_instructions(*_: Any) -> None:
        instructions.render_if_dirty()
        if instructions.done:
            instructions.done = False
            menu.refresh()
            window.hook_key(menu.handle_key)
            window.hook_loop(show_menu)

    def show_name_entry(*_: Any) -> None:
        name_entry.render_if_dirty()
        if name_entry.confirmed is not None:
            name_entry.confirmed = None
            maze_renderer.refresh()
            window.hook_key(handle_maze_key)
            window.hook_loop(maze_renderer.render_if_dirty)

    def handle_maze_key(*params: Any) -> None:
        # TODO: dev-only shortcut, remove once the engine triggers
        # Game Over / Victory itself (0 lives / all pellets eaten).
        # G/V jump straight to those screens from the maze so they
        # can be previewed without playing a level to its end.
        keycode = params[0]
        if keycode == KEY_G:
            game_over.set_score(0)
            window.hook_key(game_over.handle_key)
            window.hook_loop(show_game_over)
            return
        if keycode == KEY_V:
            victory.set_score(0)
            window.hook_key(victory.handle_key)
            window.hook_loop(show_victory)
            return
        maze_renderer.handle_key(*params)

    def show_game_over(*_: Any) -> None:
        game_over.render_if_dirty()
        if game_over.done:
            game_over.done = False
            menu.refresh()
            window.hook_key(menu.handle_key)
            window.hook_loop(show_menu)

    def show_victory(*_: Any) -> None:
        victory.render_if_dirty()
        if victory.done:
            victory.done = False
            menu.refresh()
            window.hook_key(menu.handle_key)
            window.hook_loop(show_menu)

    window.hook_key(menu.handle_key)
    window.hook_loop(show_menu)
    window.hook_close_icon(window.destroy)
    window.start_loop()


def main(argv: list[str]) -> int:
    """Load config and highscores, then start the application.

    Args:
        argv: Full argument vector, i.e. sys.argv.

    Returns:
        Process exit code (0 on success, 1 on a controlled failure).
    """
    config_path = _parse_args(argv)
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    scores = load_highscores(config.highscore_filename)
    run_app(config, scores)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:  # last-resort guard: never a traceback
        print(f"error: unexpected failure: {exc}", file=sys.stderr)
        sys.exit(1)
