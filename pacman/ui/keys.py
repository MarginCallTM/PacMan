"""MLX keycodes shared by every screen that reacts to key presses.

Centralized here so every screen agrees on the same names for the
same physical keys, instead of each module hardcoding or redefining
its own numbers.
"""

KEY_UP = 65362
KEY_DOWN = 65364
KEY_LEFT = 65361
KEY_RIGHT = 65363
KEY_ENTER = 65293
KEY_ESCAPE = 65307
KEY_BACKSPACE = 65288
KEY_Q = 113
KEY_P = 112
KEY_W = 119
KEY_A = 97
KEY_S = 115
KEY_D = 100
# F1-F5: cheat mode (subject VI.5), documented on the Instructions screen.
KEY_F1 = 65470
KEY_F2 = 65471
KEY_F3 = 65472
KEY_F4 = 65473
KEY_F5 = 65474
