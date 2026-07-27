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

### issue-588-table-get-column-value-option-for-retrie — SUCCESS (20260726-205912-issue-588-table-get-column-value-option-for-retrie)

## What worked
- Extending an existing method with `**kwargs` as an alternate lookup path (vs. adding a new method) kept the public API surface small and matched the issue's requested call style (`table.get(name="entries")`).
- Reusing existing internal helpers (`rows_where()`) for the new code path instead of writing new SQL kept behavior consistent with the rest of the class (same NotFoundError semantics).
- Guarding against ambiguous calls (`pk_values` + kwargs together) with an explicit `ValueError` avoided silent wrong behavior.
- Pairing the code change with tests covering success, not-found, and the new error case, plus a docs update, produced a complete, reviewable change in one pass.

## What failed
- Could not run `pytest`/`python` in this sandbox — verification was limited to hand-tracing the modified method against existing test cases. This is a recurring constraint against this repo, not specific to this run.

## Do differently next time
- Since `pytest`/`python` execution is consistently blocked in this sandbox for this repo, don't spend time attempting to run tests — go straight to hand-tracing and clearly flag in the report which command the operator should run to verify (e.g. `pytest tests/test_get.py -q`).
- When extending a method to accept kwargs as an alternative input mode, explicitly hand-trace all pre-existing parametrized test cases to confirm the new branch is only reachable when the new kwargs are actually supplied — this is the fastest way to build confidence without execution.


# `sqlite-utils transform` removes the `AUTOINCREMENT` keyword

GitHub issue #602 — https://github.com/simonw/sqlite-utils/issues/602

### Context

We ran into this bug randomly, noticing that deleted `ROWID` would get reused after migrating the DB. Using `transform` to change any column in the table will also unexpectedly strip away the `AUTOINCREMENT` keyword from the primary key definition, even if it was not the transformation target.

### Reproducible example

**Original database**

```sql
$ sqlite3 test.db << EOF
CREATE TABLE mytable (
    col1 INTEGER PRIMARY KEY AUTOINCREMENT,
    col2 TEXT NOT NULL
)
EOF

$ sqlite3 test.db ".schema mytable"
CREATE TABLE mytable (
    col1 INTEGER PRIMARY KEY AUTOINCREMENT,
    col2 TEXT NOT NULL
);
```

**Modified database after sqlite-utils**

```sql
$ sqlite-utils transform test.db mytable --rename col2 renamedcol2

$ sqlite3 test.db "SELECT sql FROM sqlite_master WHERE name = 'mytable';"
CREATE TABLE IF NOT EXISTS "mytable" (
   [col1] INTEGER PRIMARY KEY,
   [renamedcol2] TEXT NOT NULL
);
```

## Write access

Make your changes inside this directory — it is an isolated git worktree of the target repo:
- <harness-root>\runs\20260726-210223-issue-602-sqlite-utils-transform-removes-the-autoi\write_worktree

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

