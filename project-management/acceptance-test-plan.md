# Acceptance test plan

Two layers: the **automated pytest suite** (119 tests, headless, run on
every commit via `make test`) and a **manual checklist** for what only a
real window can prove (run on Linux before the defense and after
packaging). Subject chapter references in parentheses.

## Automated coverage (pytest, 119 tests)

| Area | Subject | Test file | What is asserted |
|---|---|---|---|
| Config parsing | V.2, V.3 | test_config.py | comments stripped, bad types → defaults, out-of-range → clamped, unknown keys ignored, empty/corrupt file → ConfigError, never a traceback (5 evil config files, parametrized) |
| Maze adapter | V.4 | test_maze_loader.py | real API used, seed reproducibility, wall symmetry, value-15 exclusion, garbage → MazeError |
| Highscores | V.5 | test_highscores.py | corrupt file → empty board, name/score validation, top-10 trim, sort order, save/load round-trip |
| Pellets | VI.1, VI.4 | test_pellets.py | supers in 4 corners, pacgums in corridors only, spawn cell free, consumption, win detection |
| Player | VI.2 | test_player.py | corridor-only moves, buffered turns, respawn at center, lives |
| Ghosts | VI.3 | test_ghost.py, test_ghost_ai.py | state machine, BFS map, chase converges, flee maximizes, random never reverses, respawn timer |
| States | VI.8 | test_states.py | legal screen transitions only |
| Level | VI.1, VI.7 | test_level.py | level 1 fixed seed / level 2+ random, 4 ghosts on corners, countdown |
| Engine | VI.2/3/6/7 | test_engine.py (26 tests) | tick cadence & freeze-clamp, pause drains clock, scoring per pellet type, frightened trigger, both collision outcomes, life loss & round reset, game over, level advance with score/lives carry-over, victory, timer expiry rule, name entry → highscore file written, invalid name refused, all 5 cheats |
| Rendering logic | VI.1 | test_ui_headless.py | fill_rect bounds, full background, SOLID cells blue, wall lines white — via injected fake buffer, no X11 needed |

## Manual checklist (Linux, before defense + after packaging)

- [ ] `python3 pac-man.py` (no arg) and with 2 args → usage message (V.1)
- [ ] `make run` opens the window; maze matches seed 42 (VI.1)
- [ ] Arrows AND WASD move Pac-Man; walls block (VI.2)
- [ ] HUD shows score / lives / level / time at all times (VI.8)
- [ ] Super-pacgum turns ghosts blue + they flee; eating one scores (VI.3)
- [ ] Pause → resume and pause → main menu (VI.7, VI.8)
- [ ] Lose all lives → Game Over → name entry → menu shows the score (IV)
- [ ] Win a level → next level, score and lives kept (VI.7)
- [ ] Every cheat key works and is listed in Instructions (VI.5)
- [ ] Config swap drill: run against each evil config (V.3)
- [ ] Fresh `git clone` → `make install` → `make run` works (VII)
- [ ] Packaged build from Itch.io installs and runs (VII)

## Bugs found & fixed (log)

| Date | Bug | Fix |
|---|---|---|
| 07-16 | W292 missing final newline on all 16 skeleton files | added, lint gate kept green since |
| 07-16 | mazegenerator wheel filename rejected by pip/uv (metadata says 2.0.2, filename said 00001) | committed byte-identical wheel under its true version |
| 07-21/22 | enum/constant import typo shipped twice (lint cannot catch it) | import-level test coverage added — the incident is now a test |
| 07-22 | ascii_view showed no pellets | its main() predated task 6 and never called place_pellets; wired |
| 07-28 | headless UI tests broken by numpy renderer refactor (`_addr` → `_pixels`, `_cell_w/_cell_h` → `_cell_size`, background clear moved out of `_draw`) | fake buffer re-implemented as numpy array; helper now mirrors `_render` |
