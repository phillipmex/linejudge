## Learnings from previous runs

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

### smoke-479-operationalerror-cannot-vacuum-from-with — FAILED (20260726-202328-smoke-479-operationalerror-cannot-vacuum-from-with)

# LearningReport: smoke-479-operationalerror-cannot-vacuum-from-with

## What worked
- Agent correctly diagnosed the VACUUM-in-transaction bug and implemented a minimal fix
- Added appropriate error handling (`TransactionError`) with helpful messaging
- Wrote tests validating the fix in both `begin()` and `atomic()` contexts
- Implementation strategy was sound: check transaction state before VACUUM, match library's documented no-auto-commit policy

## What failed
- **Agent did not write `REPORT.md`** — violated the output contract and marked run as FAILED despite completing the technical work
- No validation that required outputs existed before signing off as "complete"

## Do differently next time
- Add explicit pre-completion checklist: "Before finishing, verify REPORT.md exists with: impact summary, test coverage, edge cases"
- In agent prompts, state output requirements prominently: "Always write REPORT.md before reporting success"
- Consider a validation wrapper that checks for required files before accepting agent completion
- Distinguish between "work is correct" (true here) and "output contract satisfied" (false here) — both must be true


# `sqlite-utils tables data.db table1 table2`

GitHub issue #478 — https://github.com/simonw/sqlite-utils/issues/478

The `sqlite-utils tables` command currently lists all tables.

If you have a huge table in there then running it with `--counts` can get expensive, because of the huge table.

Would be useful if it could accept an optional list of tables that it should execute against, as an alternative to the default of all of them.

This should be a backwards compatible change. Current design is:  https://sqlite-utils.datasette.io/en/stable/cli-reference.html#tables

```
Usage: sqlite-utils tables [OPTIONS] PATH

  List the tables in the database

  Example:

      sqlite-utils tables trees.db
```

## Write access

Make your changes inside this directory — it is an isolated git worktree of the target repo:
- <harness-root>\runs\20260726-203855-issue-478-sqlite-utils-tables-data-db-table1-table\write_worktree

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

