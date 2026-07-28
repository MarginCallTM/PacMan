# Blocking points & conflicts — summary

Chronological summary of everything that actually blocked us, and how it
was resolved. Details live as dated notes in `TODO.txt`.

## 1. Subject changed twice mid-project (biggest impact)

- **07-16 (v1.5):** graphics rule hardened — every library function used
  must have an MLX equivalent; `pygame.draw.*`, mixer, alpha, rotations
  banned. Our plan (plain pygame) died; we designed a pygame-framebuffer
  approach with a 1:1 MLX mapping table.
- **07-20:** MLX itself (school `mlx_CLXV` v2.2) became the working
  target — the framebuffer plan was dropped entirely and task 5 restarted
  on the real MLX ctypes wrapper.
- **Why it didn't hurt more:** the data layer and game logic are
  graphics-free by design, so tasks 2-4 and 6-8 were untouched both
  times. Lesson recorded in technical-choices.md.

## 2. mazegenerator package quirks

Wrong README (constructor and coordinate conventions), recursive DFS that
can blow the recursion limit, misnamed wheel file rejected by pip/uv.
Resolved by probing the source, an anti-corruption loader, a recursion
guard, and committing the wheel under its metadata-true name. No upstream
modification (forbidden).

## 3. Cross-platform split: MLX is Linux-only

acombier develops on macOS where the MLX `.so` cannot load: half the team
cannot open the game window at all. Resolved by strict layering (only
`ui/mlx_window.py` imports mlx), headless tests with an injected fake
pixel buffer, and window testing on sloubiat's machine. Permanent
constraint, carried into packaging (Linux/X11 requirement).

## 4. Merge frictions

- **07-22 (PR #1)** first integration: sloubiat's sandbox `pac-man.py`
  temporarily replaced the entry-point contract (rewrite tracked as
  task 1).
- **07-28** full two-way merge: `TODO.txt` conflicted (both sides edit it
  by design — resolved keeping both sides' notes) and the numpy renderer
  refactor broke 4 headless tests + mypy (fixed within the hour, see
  acceptance-test-plan.md bug log). `uv.lock` had not been regenerated
  after numpy was added — caught because `uv sync` is part of the
  post-merge routine.

## 5. Process frictions (minor)

- The same import-typo class of bug shipped twice before we accepted
  that lint cannot catch it and added test coverage for it.
- AI-assisted files (engine.py and its tests) created a "understood
  well enough to defend?" risk — tracked as R7 in risk-analysis.md with
  scheduled re-read + recode drills before the defense.

No interpersonal conflicts to report: disagreements were settled by
"the subject wins, to the letter" and recorded as decisions in TODO.txt.
