"""Menus: main, pause, game over, victory and name input."""

from typing import Any

from pacman.ui.mlx_window import MlxWindow

KEY_UP = 65362
KEY_DOWN = 65364
KEY_ENTER = 65293
KEY_ESCAPE = 65307


class MainMenu:
    """Main menu: Start Game / View Highscores / Instructions / Exit."""

    OPTIONS = ("Start Game", "View Highscores", "Instructions", "Exit")

    def __init__(self, window: MlxWindow) -> None:
        """Bind this menu to an already-created window.

        Args:
            window: The shared MLX window to draw into.
        """
        self._window = window
        self._selected = 0
        self._dirty = True
        self.chosen: str | None = None

    def refresh(self) -> None:
        """Force a redraw next tick (call this when re-entering)."""
        self._dirty = True

    def handle_key(self, *params: Any) -> None:
        """React to a key press: move the selection or confirm it.

        Args:
            params: MLX hook payload; ``params[0]`` is the keycode.
        """
        keycode = params[0]
        if keycode == KEY_UP:
            self._selected = (self._selected - 1) % len(self.OPTIONS)
            self._dirty = True
        elif keycode == KEY_DOWN:
            self._selected = (self._selected + 1) % len(self.OPTIONS)
            self._dirty = True
        elif keycode == KEY_ENTER:
            self.chosen = self.OPTIONS[self._selected]

    def render_if_dirty(self, *_: Any) -> None:
        """MLX loop-hook: redraw only when the selection changed."""
        if not self._dirty:
            return
        self._draw_background()
        self._window.present()
        self._draw_labels()
        self._dirty = False

    def _draw_background(self) -> None:
        """Fill the off-screen buffer with a solid background.

        ``fill_rect`` writes into the image buffer, which only
        reaches the screen once :meth:`MlxWindow.present` blits it,
        so this must run *before* ``present``.
        """
        self._window.fill_rect(
            0, self._window.width - 1,
            0, self._window.height - 1, 0xFF000000)

    def _draw_labels(self) -> None:
        """Draw the option list directly onto the window.

        Unlike ``fill_rect``, MLX's ``mlx_string_put`` paints
        straight onto the visible window, not into the off-screen
        buffer. Calling it before :meth:`MlxWindow.present` would
        get wiped out by the buffer blit, so this must run *after*
        ``present``.
        """
        start_y = self._window.height // 2 - len(self.OPTIONS) * 20
        for i, label in enumerate(self.OPTIONS):
            is_selected = i == self._selected
            color = 0xFFFFFF00 if is_selected else 0xFFFFFFFF
            prefix = "> " if is_selected else "  "
            self._window.draw_text(
                self._window.width // 2 - 80,
                start_y + i * 40, color, prefix + label)


class InstructionsScreen:
    """Static help screen: controls, then back to the main menu."""

    LINES = (
        "Arrows or WASD: Move Pac-Man",
        "P: Pause",
        "Q: Quit",
        "",
        "Press Enter or Escape to go back",
    )

    def __init__(self, window: MlxWindow) -> None:
        """Bind this screen to an already-created window.

        Args:
            window: The shared MLX window to draw into.
        """
        self._window = window
        self._dirty = True
        self.done = False

    def refresh(self) -> None:
        """Force a redraw next tick (call this when re-entering)."""
        self._dirty = True

    def handle_key(self, *params: Any) -> None:
        """Any of Enter/Escape flags this screen as done.

        Args:
            params: MLX hook payload; ``params[0]`` is the keycode.
        """
        if params[0] in (KEY_ENTER, KEY_ESCAPE):
            self.done = True

    def render_if_dirty(self, *_: Any) -> None:
        """MLX loop-hook: redraw only once, until refreshed again."""
        if not self._dirty:
            return
        self._window.fill_rect(
            0, self._window.width - 1,
            0, self._window.height - 1, 0xFF000000)
        self._window.present()
        start_y = self._window.height // 2 - len(self.LINES) * 15
        for i, line in enumerate(self.LINES):
            self._window.draw_text(
                self._window.width // 2 - 150,
                start_y + i * 30, 0xFFFFFFFF, line)
        self._dirty = False
