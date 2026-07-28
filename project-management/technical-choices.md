# Technical choices & analysis

Each choice states the alternative we rejected and why.

## Tooling

- **uv** over plain pip/venv: lockfile (`uv.lock`) gives both teammates
  and the review machine the exact same environment; `make install` is
  one command. Fallback documented for machines without uv.
- **flake8 + mypy (mandatory flags) from day one** on an empty skeleton:
  no "clean it later" debt; every commit is lint-green.
- **pytest although not graded** (119 tests): the evaluator swaps the
  config and pokes the code live; tests are our early-warning system.

## Architecture

- **Anti-corruption layers (2)**: `maze_loader.py` is the only importer
  of `mazegenerator` (whose README lies about its own API);
  `mlx_window.py` is the only importer of `mlx`. The rest of the code
  sees only our types. Either dependency could be swapped by rewriting
  one file.
- **Graphics-free game logic**: engine + entities never touch MLX. This
  is also a hard constraint: MLX's `.so` is Linux-only and half the team
  develops on macOS — the whole test suite must run headless.
- **State machine with an explicit legal-transition table**
  (`states.py`): illegal screen changes raise immediately (programming
  error, never a user-visible state). No EXIT state: quitting is the
  engine `running` flag.
- **Fixed timestep (8 ticks/s)** with a monotonic-clock accumulator:
  MLX has no clock, and frame rate must never change game speed. A
  4-tick cap turns OS freezes into pauses instead of fast-forwards.
  Entities count ticks, never seconds; seconds→ticks conversion lives in
  the engine only.
- **Ghost AI as strategy classes**: one BFS distance map from the player
  per tick shared by all ghosts (O(cells), not O(ghosts × cells));
  Chase = min-distance neighbour, Flee = same loop with max, Random =
  no-reverse random walk. Each is explainable in two minutes — a design
  requirement for the defense.
- **Dirty-flag Screen base class** (Template Method): screens redraw
  only when state changed; the redraw policy lives in one place.

## Notable decisions (documented for the defense)

- Timer expiry = lose a life + timer refill + round reset (simplest rule
  that composes with the existing life system).
- Super-pacgums count toward level completion.
- Eaten ghosts teleport home (no "eyes travel home" animation).
- Ghost speed = player speed (1 cell/tick).
- Frightened flee is greedy/local — a ghost can trap itself; accepted.
- Cheat "freeze" also freezes ghost state timers.
- Highscores stored as JSON with atomic-ish save (tmp + `os.replace`).
- numpy in the UI layer only *vectorizes our own per-pixel writes* into
  the MLX buffer (zero-copy `np.frombuffer` view); it performs no
  drawing of its own, preserving MLX-equivalence.
