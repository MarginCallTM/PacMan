# Team organization

Two-person team: **acombier** and **sloubiat**.

## Split (agreed at kickoff, held throughout)

| Area | Owner |
|---|---|
| 0 kickoff, 8 engine, 10 cheats, 12 PM docs, 14 quality, 15 defense | pair |
| 2 config, 3 maze loader, 4 highscores, 6 pellets, 7 entities, 11 packaging | acombier |
| 1 entry point, 5 rendering, 9 menus/HUD, 13 README | sloubiat |

The split follows the natural seam of the architecture: data layer +
game logic (headless, testable on macOS) vs MLX rendering + screens
(needs Linux). In practice the engine (task 8) and its cheat hooks
(task 10) were implemented on acombier's side (with AI assistance, see
README), and the README draft (13) was produced during the pair
documentation pass — deviations recorded here for the "who did what"
question.

## Workflow

- One long-lived branch per person (`engine` for acombier, `sloubiat`
  for sloubiat), merged into each other at integration points
  (2026-07-22 via PR #1, 2026-07-28 both ways). `main` lags behind and
  is fast-forwarded at stable points.
- `TODO.txt` at the repo root is the shared Kanban: statuses `[ ]/[~]/[x]`,
  dated notes, decisions tagged `DECISION ... -> README`. Both edit it;
  merge conflicts on it are resolved by keeping both sides' notes.
- Quality gate before every push: `make lint` + `uv run pytest`.
- Decisions: proposed by whoever owns the task, recorded in TODO.txt,
  challenged at merge time. Subject rules always win over preferences.

## Issue handling

Problems are logged as dated notes in `TODO.txt` on the task they hit,
then summarized in `blocking-points.md` once resolved. Example: the
2026-07-28 merge broke the headless UI tests (numpy refactor); fixed the
same day, and the fix commit references the cause.
