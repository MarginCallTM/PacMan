from pacman.maze_loader import generate_maze
from pacman.ui.mlx_window import MlxWindow
from pacman.ui.renderer import MazeRenderer


def main() -> None:
    """Sandbox entry point: generate a maze and display it (task 5)."""
    maze = generate_maze(15, 15, 12)
    window = MlxWindow()
    renderer = MazeRenderer(window)

    renderer.load(maze)
    window.create_window("PacMan")
    window.hook_key(renderer.handle_key)
    window.hook_close_icon(window.destroy)
    window.hook_loop(renderer.render_if_dirty)
    window.start_loop()


if __name__ == "__main__":
    main()
