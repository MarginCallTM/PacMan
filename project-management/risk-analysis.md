# Risk analysis & mitigation

| # | Risk | Impact | Mitigation | Status |
|---|---|---|---|---|
| R1 | Subject changes mid-project (happened twice: v1.5 graphics rule on 07-16, MLX mandated on 07-20) | Rework of the whole rendering plan | Graphics-free data/game layers were unaffected by design; only task 5 was redone | **Hit twice, absorbed** |
| R2 | `mazegenerator` quirks: wrong README, recursive DFS (RecursionError > ~31×31), misnamed wheel file | Crash at generation, broken install | Anti-corruption layer probes the real API; recursion limit raised + MazeError; wheel committed under its metadata-correct name | Closed |
| R3 | Evaluator swaps the config at defense | Instant fail if a traceback shows | Bulletproof validation (clamp/default/ignore), 5 evil-config files in tests, ConfigError caught by top-level guard | Closed (drill 15.2 pending) |
| R4 | MLX runs only on Linux/X11; acombier develops on macOS | Half the team cannot see the game window | All logic testable headless (119 tests); window testing on sloubiat's machine; packaging will state the Linux requirement | Accepted, managed |
| R5 | Review machine without uv | `make install` fails | pip fallback documented in Makefile + README | Closed |
| R6 | numpy usage challenged against the MLX-equivalence rule | Renderer rejected at defense | Argument written down (vectorized per-pixel writes into the MLX buffer, zero-copy, no drawing primitives); both teammates able to explain `np.frombuffer`/`ogrid` | Open — rehearse at 15.4 |
| R7 | AI-assisted files (engine.py, tests) less internalized than hand-written ones | Fail the live-recode step | Re-read sessions + recode drills (15.1/15.3) before defense; AI usage documented in README | Open — scheduled |
| R8 | Cross-branch drift (both edit TODO.txt; UI refactors break headless tests) | Merge pain, broken suite | Frequent merges (07-22, 07-28), tests run right after each merge (07-28 breakage caught and fixed same hour) | Managed |
| R9 | Packaging a native C/X11 lib for Itch.io | Broken deliverable | Bundle wheels + build note; test on a clean Linux machine; rehearse live regeneration (15.5) | Open — task 11 |
| R10 | Time: 5 task groups left (1, 5, 9, 10.6, 11) close to the deadline | Unfinished deliverable | Critical path identified in timeline.md; UI work parallelizable with packaging/docs | Open — monitored |
