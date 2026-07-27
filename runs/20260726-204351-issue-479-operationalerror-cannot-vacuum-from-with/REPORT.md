## Status
SUCCESS

## What I did
- `sqlite_utils/db.py`: `Database.vacuum()` now calls the existing `_ensure_no_open_transaction("vacuum()")` guard (the same helper already used by `enable_wal()`/`disable_wal()`) before running `VACUUM;`. This turns the confusing `sqlite3.OperationalError: cannot VACUUM from within a transaction` into a clear `sqlite_utils.db.TransactionError: vacuum() cannot be used while a transaction is open`, and documented the new `:raises TransactionError:` behavior in the docstring.
- `tests/test_create.py`: added `test_vacuum_inside_transaction_raises`, modeled directly on the existing `test_enable_wal_inside_transaction_raises` in `tests/test_wal.py`. It inserts a row, opens `db.atomic()`, inserts a second row, calls `vacuum()` inside the block, and asserts `TransactionError` is raised and that the `atomic()` block rolled back cleanly (only the first row persists).

## Evidence
- Hand-traced the fix against the existing, already-tested `enable_wal`/`disable_wal` pattern in the same file (`sqlite_utils/db.py:1164-1195`), which uses the identical `_ensure_no_open_transaction` guard and is covered by `tests/test_wal.py::test_enable_wal_inside_transaction_raises`, confirming the guard mechanism (checking `self.conn.in_transaction` and raising `TransactionError`) is proven to work and to allow `atomic()` to roll back correctly on the raised exception.
- Attempted to run `python -m pytest tests/test_create.py -k vacuum -v` via both Bash and PowerShell; both are blocked in this sandbox with "This command requires approval" (consistent with prior runs against this repo/harness — test execution is unavailable here). Verification is therefore static/hand-traced only, not an executed test run.
- Grepped all internal call sites of `.vacuum(` (`sqlite_utils/db.py`, `sqlite_utils/cli.py`, `tests/test_create.py`, `tests/test_cli.py`) — no caller relies on `vacuum()` succeeding while a transaction is open, so the new guard does not break existing behavior.

Recommended command for the operator to confirm: `python -m pytest tests/test_create.py -k vacuum -v`
