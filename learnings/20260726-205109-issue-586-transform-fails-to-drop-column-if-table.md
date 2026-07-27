---
goal: issue-586-transform-fails-to-drop-column-if-table
status: SUCCESS
tags: proof, sqlite-utils, bug, enhancement, transform
run_id: 20260726-205109-issue-586-transform-fails-to-drop-column-if-table
---

## What worked
- Root-causing via SQLite semantics (view re-resolution during table drop/rename in `transform_sql`) before touching code — let the fix target the actual mechanism instead of symptom-patching.
- Implementing the fix as an opt-in flag (`recreate_views=False` default) that exactly matches the fix already proposed in the issue thread — low-risk, preserves existing behavior for all other callers, no need to invent a new design.
- Threading the new parameter through both layers that need it (`Table.transform()` → `transform_sql()` → CLI `--recreate-views` flag) in one pass, plus docs in all three doc files, rather than doing it piecemeal.
- Writing tests that assert the exact generated SQL statement list for the dry-run path (`transform_sql(..., recreate_views=True)`) in addition to an end-to-end behavioral test — catches both wiring bugs and behavioral regressions.
- Confirming no regression by checking that `recreate_views=False` leaves generated SQL byte-for-byte identical to before, across all existing parametrized `transform_sql` cases.
- Adding both a Python-API test and a CLI test for the same feature, since the CLI wiring (flag parsing, threading into `--sql` vs executing paths) is a separate failure surface from the underlying library logic.

## What failed
- Could not execute `pytest`/`python` in the sandbox — same execution block seen in prior runs against this repo. Verification was static/hand-trace only, not run.

## Do differently next time
- This repo's sandbox reliably blocks `pytest`/`python` execution — don't spend time retrying it; go straight to static/hand-trace verification and clearly flag the recommended verification command for the operator, as was done here.
- When a GitHub issue already proposes a concrete workaround/API shape (e.g. "maybe a `recreate_views=True` argument"), adopt that shape directly rather than designing a new one — it's already been discussed with maintainers and reduces review friction.
- For any fix touching a rebuild-via-copy/drop/rename pattern (common in SQLite wrapper libraries), check specifically for view/trigger/foreign-key references to the table being rebuilt — these are the recurring class of bug in that pattern.
