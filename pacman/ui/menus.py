"""Menus: main, pause, game over, victory and name input."""

from typing import Any

from pacman.highscores import MAX_NAME_LENGTH, is_valid_name
from pacman.ui.keys import (KEY_BACKSPACE, KEY_DOWN, KEY_ENTER, KEY_ESCAPE,
                            KEY_UP)
from pacman.ui.mlx_window import MlxWindow
from pacman.ui.screen import Screen

_TEXT_CHAR_WIDTH_PX = 8  # MLX has no text-measurement primitive, so
# every screen below approximates horizontal centering with this
# fixed average glyph width instead


def _draw_centered(window: MlxWindow, center_x: int, y: int, color: int,
                   text: str) -> None:
    """Draw one line of text horizontally centered on ``center_x``.

    Args:
        window: The shared MLX window to draw into.
        center_x: Pixel column the text should be centered on.
        y: Baseline row in pixels.
        color: 0xAARRGGBB pixel value.
        text: String to draw.
    """
    x = center_x - (len(text) * _TEXT_CHAR_WIDTH_PX) // 2
    window.draw_text(x, y, color, text)


class MainMenu(Screen):
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
        super().__init__()
        self._window = window
        self._selected = 0
        self.chosen: str | None = None

    def handle_key(self, *params: Any) -> None:
        """React to a key press: move the selection or confirm it.

        Args:
            params: MLX hook payload; ``params[0]`` is the keycode.
        """
        keycode = params[0]
        if keycode == KEY_UP:
            self._selected = (self._selected - 1) % len(self.OPTIONS)
            self.refresh()
        elif keycode == KEY_DOWN:
            self._selected = (self._selected + 1) % len(self.OPTIONS)
            self.refresh()
        elif keycode == KEY_ENTER:
            self.chosen = self.OPTIONS[self._selected]

    def _render(self) -> None:
        """Redraw the background and buttons, then the labels."""
        self._window.clear(0xFF000000)
        self._draw_buttons()
        self._window.present()
        self._draw_labels()

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


class InstructionsScreen(Screen):
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
        super().__init__()
        self._window = window
        self.done = False

    def handle_key(self, *params: Any) -> None:
        """Any of Enter/Escape flags this screen as done.

        Args:
            params: MLX hook payload; ``params[0]`` is the keycode.
        """
        if params[0] in (KEY_ENTER, KEY_ESCAPE):
            self.done = True

    def _render(self) -> None:
        """Draw the background then each instruction line."""
        self._window.clear(0xFF000000)
        self._window.present()
        start_y = self._window.height // 2 - len(self.LINES) * 15
        for i, line in enumerate(self.LINES):
            self._window.draw_text(
                self._window.width // 2 - 150,
                start_y + i * 30, 0xFFFFFFFF, line)


class HighscoresScreen(Screen):
    """Read-only top-10 board: rank, name, score, then back to the menu.

    Scores are injected through :meth:`load` rather than the
    constructor, mirroring ``MazeRenderer.load``/``_EndScreen.set_score``:
    the screen is built once when the app starts, but its content can
    be refreshed later (e.g. right after a new result is saved to
    ``highscores.json`` at game end).
    """

    TITLE = "Highscores"
    _EMPTY_MESSAGE = "No scores yet -- be the first!"
    _LINE_HEIGHT = 30

    def __init__(self, window: MlxWindow) -> None:
        """Bind this screen to an already-created window.

        Args:
            window: The shared MLX window to draw into.
        """
        super().__init__()
        self._window = window
        self._scores: list[tuple[str, int]] = []
        self.done = False

    def load(self, scores: list[tuple[str, int]]) -> None:
        """Record the scores to display and mark the view dirty.

        Args:
            scores: Up to 10 (name, score) pairs, best first --
                exactly what ``highscores.load_highscores`` returns.
        """
        self._scores = scores
        self.refresh()

    def handle_key(self, *params: Any) -> None:
        """Any of Enter/Escape flags this screen as done.

        Args:
            params: MLX hook payload; ``params[0]`` is the keycode.
        """
        if params[0] in (KEY_ENTER, KEY_ESCAPE):
            self.done = True

    def _render(self) -> None:
        """Draw the title, then one ranked line per score (or a
        placeholder when the board is empty)."""
        self._window.clear(0xFF000000)
        self._window.present()
        center_x = self._window.width // 2
        rows = max(len(self._scores), 1)
        top = self._window.height // 2 - (rows + 2) * self._LINE_HEIGHT // 2
        _draw_centered(self._window, center_x, top, 0xFFFFFF00, self.TITLE)
        if not self._scores:
            _draw_centered(self._window, center_x,
                           top + self._LINE_HEIGHT * 2,
                           0xFFFFFFFF, self._EMPTY_MESSAGE)
        else:
            for rank, (name, score) in enumerate(self._scores, start=1):
                line = f"{rank:>2}. {name:<10} {score}"
                _draw_centered(self._window, center_x,
                               top + (rank + 1) * self._LINE_HEIGHT,
                               0xFFFFFFFF, line)
        _draw_centered(self._window, center_x,
                       top + (rows + 2) * self._LINE_HEIGHT,
                       0xFFFFFFFF, "Press Enter to go back")


class NameEntryScreen(Screen):
    """Pseudo input screen: type a name, confirm it with Enter.

    Every keystroke is validated against the same rule the
    highscore table enforces (``highscores.is_valid_name``), so a
    name typed here is guaranteed to be acceptable later -- there is
    only one place, ``highscores.py``, that defines what a valid
    name is.
    """

    def __init__(self, window: MlxWindow,
                 prompt: str = "Enter your name:") -> None:
        """Bind this screen to an already-created window.

        Args:
            window: The shared MLX window to draw into.
            prompt: Line of instructions shown above the input box.
        """
        super().__init__()
        self._window = window
        self._prompt = prompt
        self._name = ""
        self.confirmed: str | None = None

    def handle_key(self, *params: Any) -> None:
        """React to a key press: type, erase, or confirm the name.

        Args:
            params: MLX hook payload; ``params[0]`` is the keycode.
        """
        keycode = params[0]
        if keycode == KEY_ENTER:
            if is_valid_name(self._name):
                self.confirmed = self._name
            return
        if keycode == KEY_BACKSPACE:
            if self._name:
                self._name = self._name[:-1]
                self.refresh()
            return
        if 32 <= keycode <= 126:
            char = chr(keycode)
            if ((char.isalnum() or char == " ")
                    and len(self._name) < MAX_NAME_LENGTH):
                self._name += char
                self.refresh()

    def _render(self) -> None:
        """Draw the prompt, then the name typed so far with a cursor."""
        self._window.clear(0xFF000000)
        self._window.present()
        center_x = self._window.width // 2
        center_y = self._window.height // 2
        _draw_centered(self._window, center_x, center_y - 30,
                       0xFFFFFFFF, self._prompt)
        _draw_centered(self._window, center_x, center_y + 20,
                       0xFFFFFF00, self._name + "_")


class _EndScreen(Screen):
    """Shared behavior for the Game Over and Victory screens.

    Both just display the final score and wait for Enter/Escape --
    what happens next (showing :class:`NameEntryScreen`, going back
    to the main menu...) is the caller's job, not this screen's. This
    mirrors ``InstructionsScreen``'s ``done`` flag: a screen only
    reports "the player is finished looking at me", never how to
    transition away.
    """

    TITLE = ""
    MESSAGE = ""

    def __init__(self, window: MlxWindow) -> None:
        """Bind this screen to an already-created window.

        Args:
            window: The shared MLX window to draw into.
        """
        super().__init__()
        self._window = window
        self._score = 0
        self.done = False

    def set_score(self, score: int) -> None:
        """Record the final score to show and mark the view dirty.

        Args:
            score: The player's final score for this run.
        """
        self._score = score
        self.refresh()

    def handle_key(self, *params: Any) -> None:
        """Any of Enter/Escape flags this screen as done.

        Args:
            params: MLX hook payload; ``params[0]`` is the keycode.
        """
        if params[0] in (KEY_ENTER, KEY_ESCAPE):
            self.done = True

    def _render(self) -> None:
        """Draw the title, the optional message, and the final score."""
        self._window.clear(0xFF000000)
        self._window.present()
        center_x = self._window.width // 2
        center_y = self._window.height // 2
        _draw_centered(self._window, center_x, center_y - 60,
                       0xFFFFFFFF, self.TITLE)
        if self.MESSAGE:
            _draw_centered(self._window, center_x, center_y - 20,
                           0xFFFFFF00, self.MESSAGE)
        _draw_centered(self._window, center_x, center_y + 20,
                       0xFFFFFFFF, f"Final score: {self._score}")
        _draw_centered(self._window, center_x, center_y + 60,
                       0xFFFFFFFF, "Press Enter to continue")


class GameOverScreen(_EndScreen):
    """Shown when the player loses their last life (subject VI.8)."""

    TITLE = "Game Over"


class VictoryScreen(_EndScreen):
    """Shown when the player clears every level (subject VI.8)."""

    TITLE = "Victory!"
    MESSAGE = "Congratulations, you cleared every level!"
