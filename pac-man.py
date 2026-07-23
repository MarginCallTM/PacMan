from typing import Any

from pacman.entities.pellets import place_pellets
from pacman.maze_loader import generate_maze
from pacman.ui.menus import InstructionsScreen, MainMenu
from pacman.ui.mlx_window import MlxWindow
from pacman.ui.renderer import MazeRenderer


def main() -> None:
    """Show the main menu, then the maze sandbox on Start Game."""
    maze = generate_maze(15, 15, 12)
    window = MlxWindow()
    window.create_window("PacMan")

    menu = MainMenu(window)
    instructions = InstructionsScreen(window)
    maze_renderer = MazeRenderer(window)
    maze_renderer.load(maze)
    pellets = place_pellets(maze, count=42, seed=12)
    maze_renderer.load_pellets(pellets)

    def show_menu(*_: Any) -> None:
        menu.render_if_dirty()
        if menu.chosen == "Start Game":
            menu.chosen = None
            window.hook_key(maze_renderer.handle_key)
            window.hook_loop(maze_renderer.render_if_dirty)
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

    window.hook_key(menu.handle_key)
    window.hook_loop(show_menu)
    window.hook_close_icon(window.destroy)
    window.start_loop()


if __name__ == "__main__":
    main()
