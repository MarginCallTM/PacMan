"""Anti-corruption layer around the external mazegenerator package.

This is the ONLY module allowed to import ``mazegenerator``. It adapts
to the package's real API (which differs from its README), normalizes
the output into an immutable : class:`Maze`, and converts any generator
failure into a clean :class: `MazeError`
"""

import sys
from dataclasses import dataclass

from mazegenerator import MazeGenerator


# Wall bitmask (bit set = wall presnt on that side of the cell).
NORTH, EAST, SOUTH, WEST = 1, 2, 4, 8
# (dx, dy) applied to (x, y) when moving toward each direction.
DELTAS = {NORTH: (0, -1), EAST: (1, 0), SOUTH: (0, 1), WEST: (-1, 0)}

# Reverse of each direction, used by ghost AI to forbid U-turns.
OPPOSITE = {NORTH: SOUTH, SOUTH: NORTH, EAST: WEST, WEST: EAST}

# A celle with all four walls: parts of the unreachable "42 pattern."
SOLID = 15
# mazegenerator semantics: seed <= 0 means "seed from system randomness".
RANDOM_SEED = 0


class MazeError(Exception):
    """Raised when the external generator fails or returns garbage."""


@dataclass(frozen=True)
class Maze:
    """Normalized, immutable maze grid.

    Attributes:
        width: Number of columns.
        height: Number of rows.
        grid: Wall bitmasks, indexed ``grid[y][x]``
    """
    width: int
    height: int
    grid: tuple[tuple[int, ...], ...]

    def is_inside(self, x: int, y: int) -> bool:
        """Return True when (x, y) is within the grid bounds.

        Args:
            x: Column Index
            y: Row index.

        Returns:
            True when the cell exists in the grid.
        """
        return 0 <= x < self.width and 0 <= y < self.height

    def is_solid(self, x: int, y: int) -> bool:
        """Return True for out-of-nounds or "42" pattern (15) cells.

        Args:
            x: Column index.
            y: Row index.

        Returns:
            True when the cell cannot be walked on at all.
        """
        return not self.is_inside(x, y) or self.grid[y][x] == SOLID

    def can_move(self, x: int, y: int, direction: int) -> bool:
        """Return True when moving from (x, y) toward direction is legal

        Args:
            x: Current column.
            y: Current row.
            direction: One of NORTH, EAST, WEST, SOUTH

        Returns:
            True when there is no wall on that side and the target
            cell is walkable
        """
        if direction not in DELTAS or self.is_solid(x, y):
            return False
        if self.grid[y][x] & direction:
            return False
        dx, dy = DELTAS[direction]
        return not self.is_solid(x + dx, y + dy)

    def corridors(self) -> list[tuple[int, int]]:
        """Return every walkable (x, y) cell, scanned row by row.

        Returns:
            All non-solid cells of the maze
        """
        return [(x, y) for y in range(self.height)
                for x in range(self.width) if not self.is_solid(x, y)]

    def nearest_corridor(self, x: int, y: int) -> tuple[int, int]:
        """Return the walkable cell closet to (x, y) (Manhattan)

        Ties beak deterministically (smallest y, then smallest x).
        Used to place the polayer at the middle and ghosts or
        super-pacgums at the corners even when the exact target cell
        happens to be solid.

        Args:
            x: Target column.
            y: Target row.

        Returns:
            The closest walkable cell.

        Raises:
            MazeError: If the maze has no walkable cell at all.
        """
        cells = self.corridors()
        if not cells:
            raise MazeError("maze has no walkable cell")

        def rank(cell: tuple[int, int]) -> tuple[int, int, int]:
            """Sort key: distance first, then y, then x"""
            dist = abs(cell[0] - x) + abs(cell[1] - y)
            return (dist, cell[1], cell[0])
        return min(cells, key=rank)

    def center(self) -> tuple[int, int]:
        """Return the walkable cell closest to the geometric middle

        Returns:
            The player spawn cell.
        """
        return self.nearest_corridor(self.width // 2, self.height // 2)

    def corners(self) -> list[tuple[int, int]]:
        """Return the walkable cells nearest to NW, NE, SWm SE corners.

        Returns: Four cells, one per corner, in NW, NE, SW, SE order
        """
        right, bottom = self.width - 1, self.height - 1
        targets = ((0, 0), (right, 0), (0, bottom), (right, bottom))
        return [self.nearest_corridor(x, y) for x, y in targets]


def generate_maze(width: int, height: int, seed: int) -> Maze:
    """Generate a maze through the external package, safely.

    Args:
        width: Maze width in cells (already validated by config.py)
        height: Maze height in cells.
        seed: > 0 for a reproducible maze (level 1), RANDOM_SEED for
        a random one (levels 2+)

    Returns:
        A validated, normalized Maze.

    Raises:
        MazeError: If the generator raises or returns an invalid grid.
    """

    # The package carves the maze with recusive DFS: Give the
    # interpreter enough stack for large grids BEFORE calling it.
    needed = width * height * 4 + 1_000
    if sys.getrecursionlimit() < needed:
        sys.setrecursionlimit(needed)
    try:
        generator = MazeGenerator(
            size=(width, height), perfect=False, seed=seed)
    except RecursionError as exc:
        raise MazeError(
            f"maze generator blew the stack for {width}x{height}"
        ) from exc
    except Exception as exc:  # The package is a black box: catch all
        raise MazeError(f"maze generation failed: {exc}") from exc
    return _normalize(generator.maze, width, height)


def _normalize(raw: object, width: int, height: int) -> Maze:
    """Validate the generator output and freeze it into a Maze

    Args:
        raw: Whatever the package exposed as its ``.maze`` attribute.
        width: Expected number of collums.
        height: Expected number of rows.

    Returns:
        An immutable Maze whose every cell is an int in [0, 15]

    Raises:
        MazeError: If the shape or any cell value is wrong
    """
    if not isinstance(raw, list) or len(raw) != height:
        raise MazeError("generator returned an invalid grid shape")
    rows: list[tuple[int, ...]] = []
    for y, row in enumerate(raw):
        if not isinstance(row, list) or len(row) != width:
            raise MazeError(f"generator row {y} has an invalid shape")
        cells: list[int] = []
        for x, cell in enumerate(row):
            valid = (not isinstance(cell, bool)
                     and isinstance(cell, int) and 0 <= cell <= 15)
            if not valid:
                raise MazeError(
                    f"invalid cell value at ({x}, {y}): {cell!r}")
            cells.append(cell)
        rows.append(tuple(cells))
    return Maze(width=width, height=height, grid=tuple(rows))
