# Timeline — plan vs actual

Working mode: Kanban held in `TODO.txt` at the repo root (single source
of truth, task numbers cited in every commit and document). This file
tracks the milestone-level plan against what actually happened.

## Planned milestones (set 2026-07-07)

| Milestone | Content | Target |
|---|---|---|
| M1 | setup + entry point, lint green | week 1 |
| M2 | data layer (config, maze, highscores) + tests | week 2 |
| M3 | playable rendering sandbox | week 2-3 |
| M4 | full game loop (pellets, ghosts, engine) | week 3 |
| M5 | UI screens + cheats | week 4 |
| M6 | packaging + README (ship) | week 4 |
| M7 | defense rehearsal | continuous + final |

## Actual progress (from git history)

| Date | Who | What |
|---|---|---|
| 07-07/08 | acombier | Repo init, uv env, Makefile, lint pipeline (M1 minus entry point) |
| 07-08 → 16 | acombier | Task 2 config.py (slower than planned — see blocking-points) |
| 07-16 | — | **Subject v1.5 update**: graphics rule hardened (see risk R1) |
| 07-16/17 | acombier | Tasks 3-4: maze_loader + highscores + tests; evil-config drill files |
| 07-17 | acombier | Task 6 pellets + ascii_view dev tool |
| 07-20 | — | **Subject update: MLX itself mandated** — pygame plan dropped |
| 07-20/22 | acombier | Task 7: player, ghost state machine, 3 AI strategies (76 tests) |
| 07-21/22 | sloubiat | Task 5 start: MlxWindow + MazeRenderer, main menu + instructions |
| 07-22 | both | First cross-merge (PR #1); states.py + level.py + headless UI tests (93) |
| 07-23 | acombier* | Engine increment 1 (fixed timestep) |
| 07-23/25 | sloubiat | Pellet drawing + numpy vectorization; square-cell resize |
| 07-27 | acombier* | Engine increments 2-4 + cheat mode engine side (113 → 119 tests) |
| 07-27 | sloubiat | GameOver/Victory/NameEntry screens + highscores screen |
| 07-28 | both | Full merge sloubiat ↔ engine; headless tests adapted to numpy; docs |
| 07-29 | both | Task 1 done: pac-man.py wired to launch contract; UI ↔ engine linked; game fluidity pass |
| 08-08/09 | sloubiat | Level-finished UI transition, log on missing config key, cheat key bindings (F1-F5) |
| 08-17 | sloubiat | Packaging groundwork (task 11): entry logic moved to `pacman/app.py`, wheel build via pyproject, runnable-wheel `__main__.py` |
| 08-17 | acombier* | Playtest: game speed halved (periods 3/4/6 → 6/8/12); glide clipping fixed (normal-pace restart + L-path around corners); pre-review audit against subject v1.5 |

\* AI-assisted implementation, reviewed and committed by acombier (see
README "How AI was used").

## Status vs plan (as of 2026-08-17, pre-review)

- M1-M5 done (full game loop, UI screens, HUD, pause, cheats, key
  bindings). M6 ~70%: README and PM docs done, wheel build works
  (`make package`), Itch.io page/upload still pending. M7 pending.
- Remaining critical path: 11.2-11.5 (in-package instructions, clean
  machine test, Itch.io upload, live-regen rehearsal) → sloubiat's AI
  usage note in README → 15 (defense drills).
