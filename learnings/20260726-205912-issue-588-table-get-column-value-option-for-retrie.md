---
goal: issue-588-table-get-column-value-option-for-retrie
status: SUCCESS
tags: proof, sqlite-utils
run_id: 20260726-205912-issue-588-table-get-column-value-option-for-retrie
---

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
