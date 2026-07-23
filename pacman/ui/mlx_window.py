"""Thin, reusable wrapper around the MLX graphics library.

This is the ONLY module allowed to import ``mlx`` directly. Every
screen (maze, HUD, menus, name-entry...) draws into the same
off-screen buffer through :meth:`MlxWindow.fill_rect` and
:meth:`MlxWindow.draw_text`, then shows it with
:meth:`MlxWindow.present`. Game-specific drawing (e.g. maze walls)
belongs in a separate renderer that *holds* an ``MlxWindow``, not in
this file.
"""

from typing import Any, Callable

import numpy as np
from mlx import Mlx


class MlxWindow:
    """Owns one MLX window and one off-screen pixel buffer."""

    def __init__(self, width_ratio: float = 0.9,
                 height_ratio: float = 0.9) -> None:
        """Initialize MLX and allocate the off-screen buffer.

        Args:
            width_ratio: Fraction of the screen width to use.
            height_ratio: Fraction of the screen height to use.
        """
        self._mx = Mlx()
        self._mlx_ptr = self._mx.mlx_init()
        _, screen_w, screen_h = self._mx.mlx_get_screen_size(self._mlx_ptr)
        self.width = int(screen_w * width_ratio)
        self.height = int(screen_h * height_ratio)
        self._img = self._mx.mlx_new_image(
            self._mlx_ptr, self.width, self.height)
        addr_raw, bpp, line_size, _ = self._mx.mlx_get_data_addr(self._img)
        self._stride = line_size // (bpp // 8)
        # Zero-copy view: writes to this array land directly in MLX's
        # own image buffer, no data ever gets duplicated.
        self._pixels: np.ndarray = np.frombuffer(
            addr_raw, dtype=np.uint32,
            count=self.height * self._stride,
        ).reshape(self.height, self._stride)
        self._window: Any = None

    def create_window(self, title: str) -> None:
        """Open the visible window.

        Args:
            title: Text shown in the window's title bar.
        """
        self._window = self._mx.mlx_new_window(
            self._mlx_ptr, self.width, self.height, title)

    def clear(self, color: int) -> None:
        """Fill the whole off-screen buffer with a single flat color.

        Every screen (maze, menus, HUD...) calls this first, before
        drawing anything else: :meth:`present` blits the full buffer,
        so without this the previous screen's pixels would still show
        through wherever the new screen doesn't draw over them.

        Args:
            color: 0xAARRGGBB pixel value.
        """
        self._pixels[:] = color

    def fill_rect(self, x_from: int, x_to: int, y_from: int, y_to: int,
                  color: int) -> None:
        """Fill an axis-aligned pixel rectangle in the off-screen buffer.

        This is our MLX-equivalent of ``pixel_put`` called in a loop:
        MLX has no rectangle-fill function, so we still decide and
        write every pixel ourselves. numpy just vectorizes that same
        loop in C instead of running it through the Python
        interpreter one pixel at a time.

        Args:
            x_from: Left edge, inclusive.
            x_to: Right edge, inclusive.
            y_from: Top edge, inclusive.
            y_to: Bottom edge, inclusive.
            color: 0xAARRGGBB pixel value.
        """
        self._pixels[y_from:y_to + 1, x_from:x_to + 1] = color

    def fill_disc(self, cx: int, cy: int, radius: int, color: int) -> None:
        """Fill a filled circle in the off-screen buffer.

        Same MLX-equivalence reasoning as :meth:`fill_rect`: MLX has no
        disc-fill primitive, so every pixel inside the circle is
        tested and written by hand, using the same squared-distance
        test as before, vectorized with numpy instead of a nested
        Python loop.

        Args:
            cx: Center x, in pixels.
            cy: Center y, in pixels.
            radius: Circle radius, in pixels.
            color: 0xAARRGGBB pixel value.
        """
        y_from, y_to = cy - radius, cy + radius + 1
        x_from, x_to = cx - radius, cx + radius + 1
        y_indices, x_indices = np.ogrid[y_from:y_to, x_from:x_to]
        mask = (x_indices - cx) ** 2 + (y_indices - cy) ** 2 <= radius ** 2
        self._pixels[y_from:y_to, x_from:x_to][mask] = color

    def draw_text(self, x: int, y: int, color: int, text: str) -> None:
        """Draw a text string (thin wrapper over ``mlx_string_put``).

        Args:
            x: Left position in pixels.
            y: Baseline position in pixels.
            color: 0xAARRGGBB pixel value.
            text: String to draw.
        """
        self._mx.mlx_string_put(
            self._mlx_ptr, self._window, x, y, color, text)

    def present(self, x: int = 0, y: int = 0) -> None:
        """Blit the off-screen buffer onto the visible window.

        Args:
            x: Horizontal offset in the window.
            y: Vertical offset in the window.
        """
        self._mx.mlx_put_image_to_window(
            self._mlx_ptr, self._window, self._img, x, y)

    def hook_key(self, callback: Callable[..., Any]) -> None:
        """Register a callback fired on every key press.

        Args:
            callback: Called by MLX with the keycode as first arg.
        """
        self._mx.mlx_hook(self._window, 2, 1, callback, self)

    def hook_close_icon(self, callback: Callable[..., Any]) -> None:
        """Register a callback fired when the window's close icon is
        clicked.

        Args:
            callback: Called by MLX with no meaningful argument.
        """
        self._mx.mlx_hook(self._window, 33, 0, callback, self)

    def hook_loop(self, callback: Callable[..., Any]) -> None:
        """Register a callback fired on every iteration of the MLX loop.

        Args:
            callback: Called once per loop tick.
        """
        self._mx.mlx_loop_hook(self._mlx_ptr, callback, None)

    def start_loop(self) -> None:
        """Block and run the MLX event loop until :meth:`destroy`."""
        self._mx.mlx_loop(self._mlx_ptr)

    def destroy(self, *_: Any) -> None:
        """Release the image, the window, and stop the event loop."""
        self._mx.mlx_destroy_image(self._mlx_ptr, self._img)
        self._mx.mlx_destroy_window(self._mlx_ptr, self._window)
        self._mx.mlx_loop_exit(self._mlx_ptr)
