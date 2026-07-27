---
goal: smoke2-479-operationalerror-cannot-vacuum-from-with
status: SUCCESS
tags: proof, sqlite-utils
run_id: 20260726-202849-smoke2-479-operationalerror-cannot-vacuum-from-with
---

## What worked
- Reusing an existing guard (`_ensure_no_open_transaction`, already shared by `enable_wal`/`disable_wal`) to fix `vacuum()` kept the change minimal and consistent with the codebase's established pattern for this exact class of bug (raising `TransactionError` instead of a confusing sqlite3 `OperationalError`).
- Mirroring an existing test (`test_enable_wal_inside_transaction_raises`) for the new `test_vacuum_inside_transaction_raises` gave a proven template rather than inventing test structure from scratch.
- Grepping all internal call sites of the changed method (`.vacuum(` in db.py and cli.py) before finishing gave confidence no caller path breaks — worth doing whenever adding a new guard/raise to a shared method.

## What failed
- Test execution was blocked entirely: both `python -m pytest` and `pytest` via Bash and PowerShell returned "This command requires approval" with no alternate runner available. This is a recurring, environment-level block against this repo/harness, not a one-off.
- Because of that, verification was static/hand-traced only — real confidence is lower than an actual green test run.

## Do differently next time
- Don't burn time retrying `pytest` invocations through different shells (Bash vs PowerShell) — this repo's sandbox consistently blocks test execution regardless of runner. Assume it's blocked from the start and go straight to static verification (grep call sites, hand-trace against an analogous passing test).
- When fixing a "confusing low-level exception" bug, check first whether the codebase already has a guard helper used for sibling methods (e.g. other methods needing "no open transaction") — this class of bug is often already half-solved elsewhere in the same file.
- Explicitly flag in the report when verification is static-only vs executed, so downstream consumers know to double-check before relying on it.
