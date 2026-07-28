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

\* AI-assisted implementation, reviewed and committed by acombier (see
README "How AI was used").

## Status vs plan (as of 2026-07-28)

- M1 ~90% (entry point rewrite pending — task 1), M2 done, M3 ~70%
  (player/ghost drawing pending), M4 done (engine side), M5 ~60%
  (cheats engine-side done; HUD, pause menu, key bindings pending),
  M6 started (this docs pass), M7 not started.
- Remaining critical path: task 1 (pac-man.py wiring) → 5.3-5.7 (draw
  player/ghosts) → 9.2/9.3 (HUD, pause menu) → 10.6 (cheat keys + docs)
  → 11 (Itch.io packaging) → 15 (defense drills).
