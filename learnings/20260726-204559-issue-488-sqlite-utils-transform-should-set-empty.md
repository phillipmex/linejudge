---
goal: issue-488-sqlite-utils-transform-should-set-empty
status: SUCCESS
tags: proof, sqlite-utils, bug, enhancement, python-library, cli-tool, transform
run_id: 20260726-204559-issue-488-sqlite-utils-transform-should-set-empty
---

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
