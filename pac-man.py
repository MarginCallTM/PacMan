"""Launch-contract shim required by the subject.

Contract: `python3 pac-man.py config.json`.

The filename ``pac-man.py`` contains a hyphen and therefore cannot be
imported as a Python module (``import pac-man`` is a syntax error), so
it can't live inside the ``pacman`` package itself. All of the actual
logic lives in :mod:`pacman.app` instead, shared with the root-level
``__main__.py`` used to run the built wheel directly.
"""
from pacman.app import run

if __name__ == "__main__":
    run()
