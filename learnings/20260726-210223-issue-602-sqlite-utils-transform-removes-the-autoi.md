---
goal: issue-602-sqlite-utils-transform-removes-the-autoi
status: SUCCESS
tags: proof, sqlite-utils, transform
run_id: 20260726-210223-issue-602-sqlite-utils-transform-removes-the-autoi
---

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
