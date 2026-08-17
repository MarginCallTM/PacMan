"""Zipapp entry point: `python pacman.whl config.json`.

Python only runs an archive directly (``python <path>``) if it finds
a ``__main__.py`` at the *root* of that archive. This file exists
solely to sit at the wheel's root and forward to the real
implementation in :mod:`pacman.app`, shared with the ``pac-man.py``
shim required by the subject's launch contract.
"""
from pacman.app import run

if __name__ == "__main__":
    run()
