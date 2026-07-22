"""Ghosts: state machine (chase/frightened/eaten) and AI strategies."""

from dataclasses import dataclass
from enum import Enum, auto


class GhostState(Enum):
    """The three behaviour modes of a ghost."""

    CHASE = auto()
    FRIGHTENED = auto()
    EATEN = auto()


@dataclass
class Ghost:
    """One ghost's mutable state.

    Attributes:
            x: Current cell column.
            y: Current cell row.
            corner: Home cell - spawn point and respawn target.
            state: Current behaviour mode.
            timer: Ticks left in a timed state (FRIGHTENED or EATEN).
    """

    x: int
    y: int
    corner: tuple[int, int]
    state: GhostState = GhostState.CHASE
    timer: int = 0
    direction: int = 0

    def frighten(self, duration: int) -> None:
        """Enter FRIGHTENED for ``duration`` ticks (super-pacgum).

        An EATEN ghost is out of play and is not affected.

        Args:
                duration: Frightened time, in engine ticks.
        """
        if self.state is not GhostState.EATEN:
            self.state = GhostState.FRIGHTENED
            self.timer = duration

    def get_eaten(self, delay: int) -> None:
        """Send the ghost home: EATEN at its corner for ``delay`` ticks.

        Args:
                delay: Respawn delay, in engine ticks.
        """
        self.x, self.y = self.corner
        self.state = GhostState.EATEN
        self.timer = delay

    def tick(self) -> None:
        """Count one engine tick; timed states expire back to CHASE."""
        if self.state is GhostState.CHASE:
            return
        self.timer -= 1
        if self.timer <= 0:
            self.state = GhostState.CHASE
            self.timer = 0
