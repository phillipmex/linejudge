## Learnings from previous runs

### issue-478-sqlite-utils-tables-data-db-table1-table — SUCCESS (20260726-203855-issue-478-sqlite-utils-tables-data-db-table1-table)

I need permission to write this file — please approve the write, or let me know if you'd like a different location/format for the LearningReport.

### issue-439-misleading-progress-bar-against-utf-16-l — SUCCESS (20260726-203352-issue-439-misleading-progress-bar-against-utf-16-l)

## What worked
- Root-causing via byte-vs-character mismatch: tracing that `os.path.getsize()` (bytes) is compared against `len()` of decoded text chunks explains "stalls at ~49%" for 2-bytes/char encodings like utf-16-le exactly. This diagnostic pattern (progress numerator/denominator unit mismatch) generalizes to any progress-bar bug report with a suspiciously round fractional stall point.
- Threading an `encoding` param through with a safe default (`utf-8`) preserved backward compatibility for the one existing call site while fixing the bug — good minimal-diff approach for a single-call-site utility function.
- Grepping for all call sites of the changed function (`UpdateWrapper`, `file_progress`) before finishing, to confirm no other caller depended on old behavior, is a cheap and effective safety check worth repeating.
- Added a targeted regression test that fails pre-fix and passes post-fix (encodes ASCII content as utf-16-le, checks sum of reported chunk sizes equals encoded byte length).

## What failed
- Could not execute `python`/`pytest`/`git` at all — Bash and PowerShell both blocked them with "requires approval" and no operator responded. This is a recurring, environment-level restriction against this repo/harness, not a one-off.
- As a result, verification was static/hand-traced only; no actual test run confirmed the fix works.

## Do differently next time
- Don't burn time retrying `python`/`pytest`/`git` invocations in this sandbox — treat them as unavailable from the first failure and go straight to static/hand-trace verification plus a clearly labeled "recommended verification command for the operator" in the report.
- When hand-tracing test logic in lieu of execution, explicitly note any simplifying assumption (e.g. "all ASCII, no surrogate pairs") since it affects how much the trace actually proves.
- Since this sandbox restriction has now recurred across multiple runs on this repo, future agents should assume no code execution is possible here and budget effort accordingly (don't attempt multiple execution workarounds).

### smoke2-479-operationalerror-cannot-vacuum-from-with — SUCCESS (20260726-202849-smoke2-479-operationalerror-cannot-vacuum-from-with)

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


# OperationalError: cannot VACUUM from within a transaction

GitHub issue #479 — https://github.com/simonw/sqlite-utils/issues/479

Maybe when calling `.vacuum()` and other DB-level write-lock operations `sqlite_utils` could guard against this error message by automatically committing first?

```
     46 db["media"].optimize()  # type: ignore
---> 47 db.vacuum()

File ~/.local/lib/python3.10/site-packages/sqlite_utils/db.py:1047, in Database.vacuum(self)
   1045 def vacuum(self):
   1046     "Run a SQLite ``VACUUM`` against the database."
-> 1047     self.execute("VACUUM;")

File ~/.local/lib/python3.10/site-packages/sqlite_utils/db.py:470, in Database.execute(self, sql, parameters)
    468     return self.conn.execute(sql, parameters)
    469 else:
--> 470     return self.conn.execute(sql)

OperationalError: cannot VACUUM from within a transaction
```

It might also be nice to add a sentence or two about how transactions are committed on the [docs page](https://sqlite-utils.datasette.io/en/latest/python-api.html#detect-fts). When I was swapping out my sqlite3 code for this library it was nice that everything was pretty much drop-in but I was/am unsure what to do about the places I explicitly call `.commit()` in my code

Related to https://github.com/simonw/sqlite-utils/issues/121

## Write access

Make your changes inside this directory — it is an isolated git worktree of the target repo:
- <harness-root>\runs\20260726-204351-issue-479-operationalerror-cannot-vacuum-from-with\write_worktree

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

