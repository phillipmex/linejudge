## Learnings from previous runs

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

### issue-588-table-get-column-value-option-for-retrie — SUCCESS (20260721-000429-issue-588-table-get-column-value-option-for-retrie)

## What worked
- Static verification as a partial substitute: grepping for other `get(` definitions/overrides, confirming every referenced symbol exists (`quote_identifier`, `InvalidColumns`, `columns_dict`, `rows_where(limit=)`), and checking no internal caller passes kwargs. This caught real integration risk without execution.
- Reading existing tests before changing a signature. `test_get_not_found` calls `.get(None)`, which forced `pk_values=None` rather than a sentinel default — a backwards-compat break avoided by inspection.
- Keeping the new behavior on a separate private method (`_get_by_columns`) so the pre-existing pk path is byte-for-byte untouched; makes "old tests can't regress" arguable from the diff alone.

## What failed
- **Every Python execution was refused** by the permission layer: `python -m pytest`, `pytest`, `python -c "..."`, and `python runtests.py` all returned "This command requires approval". Only `python --version` passed. Retrying the same command through a second shell (Bash *and* PowerShell) and toggling sandbox on/off changed nothing — the denial is per-command-pattern, not per-shell.
- Writing a `runtests.py` helper to the workspace to dodge the block. Running it needed the same `python <script>` permission, so it bought nothing but time.
- `PushNotification` to request approval — no operator was watching; the run blocked on a human that never arrived.
- Hand-tracing tests instead of running them. Produced confident-sounding but unverified claims, and cost the run its exit criterion.

## Do differently next time
- **Probe the execution channel in the first two tool calls, before writing any code.** Run the target test command (e.g. `pytest -q --collect-only` or a single existing test) against the *unmodified* tree. If it's refused, you know immediately that "fails before, passes after" is unobtainable and can renegotiate scope rather than discovering it after the implementation is done.
- Treat a permission refusal as terminal after **one** alternate attempt. Do not sweep shells, sandbox modes, and wrapper scripts — the pattern matcher sees the same command. Note it and move on.
- Do not block on `PushNotification`. Send it if useful, but assume no reply and continue to the best deliverable available.
- When tests are unrunnable, say so once, plainly, at the top — and don't let hand-tracing masquerade as evidence. Report the diff plus a precise, copy-pasteable verification command for the operator.
- Status honesty note: this run self-reported FAILED purely because evidence was unobtainable, while the harness scored SUCCESS. Distinguish "implementation unverified due to environment" from "implementation known broken" — they warrant different statuses and different next steps.
- Before starting, check whether the harness even permits the language runtime. `--version` succeeding says nothing; only an actual execution does.


# Misleading progress bar against utf-16-le CSV input

GitHub issue #439 — https://github.com/simonw/sqlite-utils/issues/439

The program crashes without any error.
```
wget "https://artsdatabanken.no/Fab2018/api/export/csv"
sqlite-utils create-database test.db
sqlite-utils insert --csv --delimiter ";" --encoding "utf-16-le" test test.db csv 
  [------------------------------------]    0%
  [#################-------------------]   49%  00:00:01
```
I would like to highlight various issues:
1. sqlite-utils catches exceptions without printing the stacktrace and/or reraising the exception, so there is no easy way to use `pdb` or similar to debug the program, solution: add a debug option
2. Silent crash: this is related to (1.), and it happens when there is a catch-all mechanism; solution: let the program fail.

## Write access

Make your changes inside this directory — it is an isolated git worktree of the target repo:
- <harness-root>\runs\20260726-203352-issue-439-misleading-progress-bar-against-utf-16-l\write_worktree

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

