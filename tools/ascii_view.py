"""Throwaway dev tool: render a Maze (and entities) as ASCII art.

NOT part of the game deliverable. Used to eyeball mazes and pellet
placement while the real renderer (task 5) is being built.

Usage: uv run python tools/ascii_view.py [width height seed]
"""

import sys

from pacman.maze_loader import Maze, NORTH, SOLID, WEST, generate_maze


def render_ascii(maze: Maze,
                 pellets: set[tuple[int, int]] | None = None,
                 supers: set[tuple[int, int]] | None = None,
                 player: tuple[int, int] | None = None) -> str:
    """Draw the maze grid, walls and cell contents as text.

    Args:
        maze: The normalized maze to draw
        pellets: Cells holding a pacgum draw as '.'
        supers: Cells holding a super-pacum, drawn as 'O'
        player: Player cell, draw as 'P'

    Returns:
        A multi-line string, one text row per wall/cell row
    """
    pellets = pellets or set()
    supers = supers or set()
    lines: list[str] = []
    for y in range(maze.height):
        top = ""
        mid = ""
        for x in range(maze.width):
            cell = maze.grid[y][x]
            top += "+---" if cell & NORTH else "+   "
            mid += "|" if cell & WEST else " "
            mid += f" {_cell_char(maze, x, y, pellets, supers, player)} "
        lines.append(top + "+")
        lines.append(mid + "|")
    lines.append("+---" * maze.width + "+")
    return "\n".join(lines)


def _cell_char(maze: Maze, x: int, y: int,
               pellets: set[tuple[int, int]],
               supers: set[tuple[int, int]],
               player: tuple[int, int] | None) -> str:
    """Pick the single character shown at the center of one cell."""
    if maze.grid[y][x] == SOLID:
        return "#"
    if player == (x, y):
        return "P"
    if (x, y) in supers:
        return "O"
    if (x, y) in pellets:
        return "."
    return " "


def main() -> None:
    """Generate a maze from CLI args (or defaults) and print it."""
    try:
        width = int(sys.argv[1]) if len(sys.argv) > 1 else 21
        height = int(sys.argv[2]) if len(sys.argv) > 2 else 15
        seed = int(sys.argv[3]) if len(sys.argv) > 3 else 42
        maze = generate_maze(width, height, seed)
    except Exception as exc:  # dev tool: any failure -> short message
        print(f"ascii_view: {exc}")
        return
    print(render_ascii(maze, player=maze.center()))


if __name__ == "__main__":
    main()
