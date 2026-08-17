*This project has been created as part of the 42 curriculum by acombier, sloubiat.*

# Pac-Man — "Ghosts! More ghosts!"

## Description

A complete, playable Pac-Man written in Python 3.10+, on top of the school
MLX graphics library (`mlx_CLXV` v2.2, C/X11 + official Python ctypes
wrapper). Mazes are produced by the assigned external `mazegenerator`
package; gameplay, scoring, ghost AI, highscores and the whole UI are our
own code, organized as a reusable, fully unit-tested package.

Eat every pacgum to clear a level; clear all 10 (or more) levels to win.
Four autonomous ghosts hunt you down — unless you grab a super-pacgum in a
corner and hunt them instead.

> **Platform note:** the MLX shared library is a Linux/X11 binary. The
> game window therefore requires Linux (or an X11 server). The data layer,
> game logic, linting and the whole pytest suite run on any OS.

## Instructions

### Install & run

Everything goes through [uv](https://docs.astral.sh/uv/):

```bash
make install        # uv sync — creates .venv with exact locked versions
make run            # uv run python3 pac-man.py config.json
make debug          # same, under pdb
make lint           # flake8 + mypy (mandatory flags)
make test           # pytest (127 tests)
make clean          # remove caches and build artifacts
make build          # regenerate the Itch.io bundle (dist/pacman-42.zip)
```

No uv on the machine? Fallback:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install numpy flake8 mypy pytest \
    ./mazegenerator-2.0.2-py3-none-any.whl ./mlx-2.2-py3-none-any.whl
python3 pac-man.py config.json
```

Launch contract: `python3 pac-man.py <config.json>` — exactly one
argument, the JSON configuration file. Any error (wrong argument count,
missing file, invalid JSON, bad values) prints a clear message and never a
Python traceback.

### Packaging

`make build` (i.e. `./package.sh`, the packaging spec at the repo
root) regenerates the full Itch.io bundle in one command:
`dist/pacman-42.zip`. The bundle is self-contained — our game wheel
(built by `uv build` from `pyproject.toml`), the two assigned wheels
as-is, the commented `config.json`, `INSTRUCTIONS.txt` (controls,
cheats, config), and a single **`./pacman` launcher**: on first run it
creates a local venv and installs the wheels, then (and on every later
run) starts the game. Player-side requirements: Linux/X11 (the MLX
wheel ships a prebuilt `.so`, nothing to compile), Python 3.10+,
internet once for numpy.

The game wheel itself is **directly runnable** —
`python3 pacman-0.1.0-py3-none-any.whl config.json` — thanks to a
root-level `__main__.py` inside the archive that forwards to
`pacman.app`, the exact code path behind `pac-man.py` (that's what the
`pacman` launcher execs). The build is deployed on Itch.io as a free,
unlisted download.

### Controls

| Key | Action |
|---|---|
| Arrow keys / WASD | Move Pac-Man |
| Enter | Validate (menus, name entry) |
| Escape | Back (instructions, highscores) |
| P | Pause / resume |
| Q | Quit |

### Cheat mode (for reviewers)

Five cheats are built into the engine so every feature can be tested
quickly:

| Key | Cheat | Effect |
|---|---|---|
| F1 | Invincibility | Ghost contact costs no life (frightened ghosts stay edible) |
| F2 | Ghost freeze | Ghosts stop moving (their state timers freeze too) |
| F3 | Speed boost | Pac-Man moves 3x faster (still one cell per step) |
| F4 | Extra life | +1 life |
| F5 | Level skip | Instantly win the current level (score/lives carry over) |

Cheat keys only work during gameplay (never on menu screens); they are
also listed on the in-game Instructions screen.

## Resources

Project material:

- Subject: "Ghosts! More ghosts!" v1.5 (42 curriculum, `en.subject.pdf`).
- `mazegenerator` v2.0.2 — assigned external package (wheel at repo root).
- School MLX `mlx_CLXV` v2.2 — graphics library (wheel at repo root;
  Linux/X11 `.so` + official Python ctypes wrapper).

References we actually used:

- *The Pac-Man Dossier* (Jamey Pittman) — the classic write-up of the
  original game's ghost behaviours; inspired our chase/frightened/eaten
  state machine and the buffered-turn feel.
- BFS on grids: *Introduction to Algorithms* (CLRS), ch. 22 — basis of
  the shared ghost distance map.
- Python docs: `dataclasses`, `enum`, `json`, `time.monotonic`,
  `sys.setrecursionlimit`.
- [uv documentation](https://docs.astral.sh/uv/) (environment & lockfile),
  flake8, mypy, pytest, numpy documentation.

### How AI was used

As framed by subject chapter II, we used an AI assistant as a learning
and productivity aid, under one strict rule: nothing enters the
repository unless we understand it well enough to explain, defend and
modify it live. We take full responsibility for every line.

- **Design discussions (all tasks):** used as a sparring partner to
  compare approaches (ghost AI strategies, fixed-timestep loop, config
  validation policy); the decisions are ours and are recorded in
  `project-management/technical-choices.md`.
- **Data layer, entities and game states (tasks 2–4, 6–7, 8.1–8.2):**
  written by hand by acombier, from designs discussed with the AI.
- **Game engine and cheat mode (tasks 8.3, 10) and parts of the test
  suite:** AI-assisted drafts, then reviewed, tested and maintained by
  acombier.
- **UI layer (tasks 5, 9):** sloubiat's work, written by hand. AI was
  used for two things: **debugging** (tracking down issues in the MLX
  window/renderer integration, e.g. reading tracebacks and pinpointing
  root causes when a drawing or input hook misbehaved) and
  **restructuring the `ui/` files** as the screen count grew
  (splitting responsibilities across `renderer.py`, `menus.py`,
  `mlx_window.py` and `screen.py` instead of one growing file). Every
  suggestion was reviewed, tested (`make lint` / `make test`) and
  understood before being kept.
- **Documentation:** drafted with AI assistance from our project log
  (`TODO.txt`), reviewed and edited by the team.

Every AI-assisted piece went through the same gates as the rest of the
code: flake8 + mypy clean, covered by the pytest suite, and re-read
before the defense.

## Configuration

The config file is JSON; **lines whose first non-blank character is `#`
are comments** (blanked before parsing, so JSON error line numbers still
match the file). Unknown keys are ignored with a log line. Wrong types
fall back to the default; out-of-range values are clamped — the game
always starts with safe values. Only an unreadable / non-JSON file or a
non-object root is fatal (clean error message, no traceback).

| Key | Type | Default | Accepted range / rule |
|---|---|---|---|
| `highscore_filename` | string | `"highscores.json"` | non-empty string |
| `level` | array of `{width, height}` | 10 × 21×15 | width 15–41, height 10–41; padded with defaults up to 10 levels |
| `lives` | int | 3 | 1–9 |
| `pacgum` | int | 42 | 1–10000 (also capped by available corridor cells) |
| `points_per_pacgum` | int | 10 | 0–1000000 |
| `points_per_super_pacgum` | int | 50 | 0–1000000 |
| `points_per_ghost` | int | 200 | 0–1000000 |
| `seed` | int | 42 | 1–2^31-1 (level 1 only; later levels are random) |
| `level_max_time` | int (seconds) | 90 | 5–3600 |

Booleans are explicitly rejected for int keys (`bool` is a subclass of
`int` in Python). A commented example ships at the repo root
(`config.json`).

## Highscore

Top-10 persistent scoreboard, stored as a **JSON file** (path from
`highscore_filename`). Why JSON: human-readable, diffable, already part of
the project's vocabulary (config), and trivially validated — a binary
format would only obscure corruption.

- Loaded at startup with a context manager; a missing or corrupt file
  yields an empty board (logged, never a crash).
- Entries are validated on load *and* on save: name ≤ 10 chars,
  alphanumeric + spaces only; score = non-negative int. Invalid entries
  are dropped.
- Only the 10 best (name, score) pairs are kept, sorted descending.
- Saving is atomic-ish: write to `<file>.tmp`, then `os.replace` — a
  crash mid-write can never destroy the previous file.
- The name prompt appears on both victory and game over; the same
  validation rule (`highscores.is_valid_name`) is used by the input
  widget while typing and re-checked by the engine before saving —
  single source of truth.

## Maze Generation

Mazes come from the assigned `mazegenerator` package, used **as-is**
through a single adapter module, `pacman/maze_loader.py` (anti-corruption
layer): no other module imports the package.

- **Real API, not the package README** (which is wrong): the constructor
  takes `size=(w, h)` (not `width=`/`height=`), and `maze_entry`/`maze_exit`
  return `(x, y)` (not "(row, col)"). We probed the source, adapted to the
  code, and normalize everything once at the boundary: one convention
  everywhere — `(x, y)`, grid indexed `maze[y][x]`, wall bitmask N=1 E=2
  S=4 W=8.
- **Seed policy:** level 1 uses the fixed config seed (reproducible, per
  subject); every later level passes seed 0 (system randomness).
- **Recursion guard:** generation is recursive DFS, so
  `sys.setrecursionlimit` is raised proportionally to `w*h` before each
  call, and `RecursionError` / any generator failure is converted into a
  clean `MazeError`.
- **Value-15 cells** (the embedded "42" pattern) are solid, unreachable
  blocks: excluded from pellet placement and pathfinding, drawn as filled
  blue blocks.
- `perfect=False` always: Pac-Man needs corridor loops.

## Implementation

- **Fixed timestep:** MLX has no clock, so timing uses stdlib `time`. The
  engine converts elapsed real time into ticks (21/s) with a monotonic
  accumulator; a stall longer than 10 ticks pauses the game instead of
  fast-forwarding it. Entities count time in ticks, never seconds.
- **Simulation order per tick:** timer → player step (on its movement
  period; buffered turns: the last requested direction is taken as soon
  as it becomes legal) → pellet consumption → collisions → ghost moves
  (each on its period) → collisions again. Timers and collisions run
  every tick; the double collision check prevents player and ghost from
  swapping cells through each other.
- **Ghost AI:** one BFS distance map from the player per tick, shared by
  all ghosts. Personalities: direct chase (min distance, N/E/S/W
  tie-break) and random-at-intersections (never reverses except in dead
  ends), assigned in cycling order. Frightened ghosts flee (max distance,
  greedy — a ghost may trap itself in a dead end, accepted trade-off).
  Eaten ghosts teleport home and respawn after 7 s (no "eyes travel home"
  animation — deliberate simplification).
- **Movement periods:** every entity moves on a constant beat, a whole
  number of ticks per cell — the player every 6 ticks (3.5 cells/s;
  halved from 7 after the 2026-08-17 playtest found the game
  unplayably fast), chasing ghosts every 8 (2.625 cells/s, 75% of the
  player) and frightened ghosts every 12 (1.75 cells/s, 50%), keeping
  the arcade ratios: the player can escape a chaser and catch a fleer.
  At 21 ticks/s every period is a whole number of ticks; a *regular*
  rhythm per entity is what the renderer needs to interpolate
  perfectly smooth motion. Timed states still tick every tick, so
  their real-time durations are unaffected.
- **Death pause:** a fatal ghost contact freezes the simulation for
  0.7 s before the round resets. The display eases up to one movement
  period behind the simulation, so an instant reset would land while
  the sprites still looked one cell apart; the pause lets the slides
  complete and makes the contact visible. A level timeout resets
  instantly instead — there is no contact to show.
- **Timer expiry:** costs one life, the timer refills, the round resets
  (player to center, ghosts to corners). At 0 lives it naturally becomes
  game over.
- **Score** never decreases; score and lives carry over between levels.
  Clearing a level requires eating super-pacgums too.
- **Rendering:** MLX-equivalent only — an off-screen image buffer written
  pixel by pixel, blitted once per frame, plus `mlx_string_put` for text
  and hooks for input. `fill_rect`/`fill_disc` are our own per-pixel
  writes; numpy only vectorizes those same writes in C (zero-copy view
  over the MLX buffer), it draws nothing by itself. Screens redraw only
  when dirty. Entity motion is interpolated between cells at each
  entity's own observed pace; a move landing mid-slide continues from
  the exact drawn position, and a perpendicular one follows an L-shaped
  path through the corner cell — sprites never jump and never cut
  through walls.

## General Software Architecture

```
pac-man.py                  launch-contract shim (python3 pac-man.py config.json)
__main__.py                 wheel-root shim (python3 <wheel> config.json)
pacman/
    app.py                  arg parsing, UI/engine wiring, error guard
    config.py               JSON + comments -> validated GameConfig
    maze_loader.py          ONLY importer of mazegenerator (anti-corruption)
    highscores.py           top-10 persistence (atomic save)
    entities/
        player.py           position, buffered direction, lives
        ghost.py            CHASE / FRIGHTENED / EATEN state machine
        ghost_ai.py         BFS map + Chase / Flee / Random strategies
        pellets.py          pacgum & super-pacgum placement/consumption
    game/
        states.py           screen enum + legal-transition state machine
        level.py            maze + pellets + entities + countdown
        engine.py           fixed-timestep loop, scoring, collisions, cheats
    ui/
        mlx_window.py       ONLY importer of mlx (window + pixel buffer)
        screen.py           dirty-flag base class for every screen
        renderer.py         maze/pellet rasterizer
        menus.py            menus, instructions, highscores, end screens
        keys.py             X11 keycodes
tests/                      127 pytest tests, all headless
project-management/         timeline, risks, choices, test plan...
```

Principles: two anti-corruption layers (`maze_loader` for the maze
package, `mlx_window` for the graphics library); game logic is
graphics-free and fully unit-testable (the suite runs on macOS where MLX
cannot even load); a state machine with an explicit legal-transition
table drives every screen; ghost behaviours are small strategy classes,
each explainable in two minutes.

## Project Management

Planning, progress tracking, risk analysis, technical choices, team
organization, acceptance tests and blocking points are documented in
[`project-management/`](project-management/).
