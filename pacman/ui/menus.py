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

    _BUTTON_BORDER = 0xFFFFFFFF  # white border, unselected
    _BUTTON_BORDER_SELECTED = 0xFFFFFF00  # yellow border, selected
    _BUTTON_FILL = 0xFF202020  # dark grey fill, unselected
    _BUTTON_FILL_SELECTED = 0xFF404000  # dark yellow fill, selected
    _BUTTON_BORDER_PX = 3
    _CHAR_WIDTH_PX = 8  # rough average glyph width of MLX's default
    # font; used to approximate horizontal centering since MLX has
    # no text-measurement primitive

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
        self._draw_buttons()
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

    def _button_rect(self, index: int) -> tuple[int, int, int, int]:
        """Compute one button's (left, right, top, bottom) pixel bounds.

        Args:
            index: Position of the option in ``OPTIONS``.

        Returns:
            The button's bounding box, evenly stacked and centered.
        """
        button_w = self._window.width // 3
        button_h = 60
        gap = 20
        total_h = (len(self.OPTIONS) * button_h
                   + (len(self.OPTIONS) - 1) * gap)
        start_y = self._window.height // 2 - total_h // 2
        left = self._window.width // 2 - button_w // 2
        top = start_y + index * (button_h + gap)
        return left, left + button_w, top, top + button_h

    def _draw_buttons(self) -> None:
        """Draw one border+fill rectangle per option into the buffer.

        Must run before :meth:`MlxWindow.present`: ``fill_rect``
        only writes the off-screen buffer, which is not visible
        until the next ``present`` blits it.
        """
        for i in range(len(self.OPTIONS)):
            left, right, top, bottom = self._button_rect(i)
            is_selected = i == self._selected
            border = (self._BUTTON_BORDER_SELECTED if is_selected
                      else self._BUTTON_BORDER)
            fill = (self._BUTTON_FILL_SELECTED if is_selected
                    else self._BUTTON_FILL)
            self._window.fill_rect(left, right, top, bottom, border)
            self._window.fill_rect(
                left + self._BUTTON_BORDER_PX,
                right - self._BUTTON_BORDER_PX,
                top + self._BUTTON_BORDER_PX,
                bottom - self._BUTTON_BORDER_PX, fill)

    def _draw_labels(self) -> None:
        """Draw each option's label centered inside its button.

        Unlike ``fill_rect``, MLX's ``mlx_string_put`` paints
        straight onto the visible window, not into the off-screen
        buffer. Calling it before :meth:`MlxWindow.present` would
        get wiped out by the buffer blit, so this must run *after*
        ``present``.
        """
        for i, label in enumerate(self.OPTIONS):
            left, right, top, bottom = self._button_rect(i)
            is_selected = i == self._selected
            color = 0xFFFFFF00 if is_selected else 0xFFFFFFFF
            text = ("> " if is_selected else "  ") + label
            text_w = len(text) * self._CHAR_WIDTH_PX
            x = (left + right) // 2 - text_w // 2
            y = (top + bottom) // 2 + 5
            self._window.draw_text(x, y, color, text)


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
