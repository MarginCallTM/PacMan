"""Shared base class for every dirty-flag-driven MLX screen.

``MazeRenderer``, ``MainMenu`` and ``InstructionsScreen`` all used to
repeat the same "redraw only if something changed, then clear the
flag" boilerplate. This is the Template Method pattern: the
when-to-redraw logic lives here, once; each screen only implements
``_render`` to say how it draws itself.
"""

from abc import ABC, abstractmethod
from typing import Any


class Screen(ABC):
    """Base for screens that redraw only when their state changed."""

    def __init__(self) -> None:
        """Mark the screen dirty so it draws itself on the first tick."""
        self._dirty = True

    def refresh(self) -> None:
        """Force a redraw next tick (call this when state changes)."""
        self._dirty = True

    def render_if_dirty(self, *_: Any) -> None:
        """MLX loop-hook: redraw only when something actually changed.

        Args:
            _: Unused MLX loop-hook payload.
        """
        if not self._dirty:
            return
        self._render()
        self._dirty = False

    @abstractmethod
    def _render(self) -> None:
        """Draw exactly one frame. Called only while dirty.

        Subclasses not yet ready to draw (e.g. no maze loaded) should
        return immediately without calling ``present`` -- the base
        class still clears the flag, and the next state change will
        set it again through :meth:`refresh`.
        """
        raise NotImplementedError
