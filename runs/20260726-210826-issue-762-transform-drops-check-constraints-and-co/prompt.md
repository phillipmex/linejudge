## Learnings from previous runs

### issue-586-transform-fails-to-drop-column-if-table — SUCCESS (20260726-205109-issue-586-transform-fails-to-drop-column-if-table)

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

### issue-488-sqlite-utils-transform-should-set-empty — SUCCESS (20260726-204559-issue-488-sqlite-utils-transform-should-set-empty)

## What worked
- Correct root-cause diagnosis of `Table.transform_sql()`: SQLite affinity conversion silently fails on `""` for INTEGER/FLOAT/REAL columns, leaving the empty string in place instead of nulling it. Fixing by wrapping the source column in `nullif(col, '')` in the copy `SELECT` is a minimal, targeted change.
- Scoped the fix precisely: only columns present in `types=` whose resolved SQL type is INTEGER/FLOAT/REAL get wrapped, leaving unrelated SQL generation byte-for-byte identical — verified by hand-tracing against existing test parametrizations (rename, drop, pk, column_order) to confirm no incidental breakage.
- Updated existing SQL-generation test expectations rather than just adding a new test, and added one precise regression test reproducing the exact issue scenario (mixed populated/empty rows, two converted columns).
- Wrote a concrete operator-facing verification command (pytest invocation + CLI repro steps with expected output) since the sandbox couldn't run it.

## What failed
- `python`/`pytest` are blocked in this sandbox with no operator response to approve — this is a recurring, repo-wide constraint (confirmed across multiple prior runs), not one-off flakiness.

## Do differently next time
- Don't attempt to run `python`/`pytest` at all in this repo's sandbox — it's confirmed blocked; go straight to hand-tracing the SQL/logic and documenting the verification command for the operator, saving a wasted tool-call round trip.
- When touching `transform_sql()`, always re-check all existing parametrized test cases (pk/no-pk, rename/no-rename, column_order, drop) by hand for SQL-string diffs, since this generator is shared across many transform test permutations.

### issue-602-sqlite-utils-transform-removes-the-autoi — SUCCESS (20260726-210223-issue-602-sqlite-utils-transform-removes-the-autoi)

## What worked
- Tracing the bug through the actual rebuild path (`Table.transform_sql()` → `Table.create_table_sql()`) rather than patching `transform()` itself — the AUTOINCREMENT loss was a side effect of the generic copy/drop/rename table-rebuild helper, so fixing it at that shared layer covers all callers automatically.
- Making the fix conditional and derived from existing state (`pk_autoincrement` computed by checking the old schema for `AUTOINCREMENT` + confirming the same single pk column survives the transform) instead of adding a new caller-facing flag — kept the public API unchanged and avoided a footgun where callers must remember to opt in.
- Explicitly testing the negative case (pk changed via `transform(pk="col2")` → AUTOINCREMENT correctly dropped) alongside the positive case — this guards against a shallow fix that just always re-adds AUTOINCREMENT regardless of whether the pk column identity survived.
- Hand-tracing generated SQL strings against existing parametrized tests to confirm zero-diff for all non-AUTOINCREMENT fixtures, giving reasonable confidence without running pytest.

## What failed
- Sandbox could not execute `pytest`/`python` at all — same limitation noted in prior runs against this repo. Correctness rested entirely on hand-tracing, not execution.

## Do differently next time
- Before starting, check learnings for this repo (sqlite-utils) for the "sandbox blocks pytest" constraint — it's now confirmed across multiple runs, so don't re-attempt pytest and don't burn time on it; go straight to hand-tracing generated SQL/schema strings against test assertions.
- When a bug is "operation X loses property Y during a rebuild/copy," check whether X is implemented via a shared low-level table-rebuild helper (used by multiple public methods) — fixing there is more robust than patching each public method separately.
- Always pair a "property preserved" test with a "property correctly NOT preserved when its precondition breaks" test for any conditional-preservation fix — it's cheap and catches the common shallow-fix failure mode (always preserving regardless of precondition).


# .transform() drops check constraints and comments

GitHub issue #762 — https://github.com/simonw/sqlite-utils/issues/762

Calling `.transform()` on a table currently recreates that table without check constraints and without any comments, because those live only in the SQL create table statement and are not exposed via any PRAGMA.

Separately, if the table has a column-level `UNIQUE` constraint, SQLite backs it with an internal auto-index that has no `CREATE INDEX` statement. `.transform()`'s index-rebuild step can't reproduce that, so it raises `TransformError` and aborts instead of preserving the constraint.

## Write access

Make your changes inside this directory — it is an isolated git worktree of the target repo:
- <harness-root>\runs\20260726-210826-issue-762-transform-drops-check-constraints-and-co\write_worktree

Do not run git commit/branch/merge yourself; the harness captures and commits your diff after you finish. REPORT.md still goes in your working directory, NOT in the worktree — keep the diff clean of harness artifacts.


## Notes

- Add or update a test that fails before your fix and passes after it.
- Keep the change minimal and scoped to this issue; do not reformat unrelated code.

## Output contract (required)

When you are done, write a file named REPORT.md in your working directory with:
- `## Status` — exactly one of SUCCESS or FAILED on the next line
- `## What I did` — short factual list
- `## Evidence` — how you checked it works (commands run, files produced)

Your REPORT.md is a claim, not a verdict: the harness runs its own verifiers
after you finish. A missing REPORT.md fails the run regardless of your work.

