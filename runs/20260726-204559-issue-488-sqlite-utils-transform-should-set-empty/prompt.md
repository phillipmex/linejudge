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

### issue-479-operationalerror-cannot-vacuum-from-with — FAILED (20260726-204351-issue-479-operationalerror-cannot-vacuum-from-with)

## What worked
- Root cause approach: routing the OperationalError through an existing guard (`_ensure_no_open_transaction`) into a clearer `TransactionError` is a good pattern — reuse existing error-handling primitives rather than inventing new ones.
- Mirroring an existing test (`enable_wal` transaction test) for the new `test_vacuum_inside_transaction_raises` test is a reasonable way to keep test style consistent when authoring blind.

## What failed
- No REPORT.md was written — this is an output-contract violation and the run is marked FAILED regardless of code quality. The final chat message is not a substitute for the required file.
- Test execution was reportedly blocked in the sandbox, and the agent proceeded with only static/hand-traced verification instead of flagging this as a blocker requiring resolution or escalation.

## Do differently next time
- Always write REPORT.md before finishing, even if the fix seems complete and was explained in the final message — the report is the actual deliverable, not a courtesy summary.
- If REPORT.md is meant to document verification steps (as claimed here — "notes the recommended command to confirm"), write it as part of the fix, not as an afterthought that gets skipped.
- When test execution is blocked in this sandbox (a recurring issue on this repo per the agent's own note — "as in prior runs on this repo"), treat that as a known environment constraint to document explicitly in REPORT.md up front, and consider whether there's a workaround (different test runner invocation, subset of tests) before defaulting to static-only verification.
- Treat "wrote the fix and explained it in chat" as incomplete until REPORT.md exists on disk — verify the file was actually created before reporting the task done.


# `sqlite-utils transform` should set empty strings to null when converting text columns to integer/float

GitHub issue #488 — https://github.com/simonw/sqlite-utils/issues/488

```
/tmp % echo "id,age,weight\n1,3,2.5\n2,," | sqlite-utils insert test.db test - --csv
/tmp % sqlite-utils schema test.db                                                  
CREATE TABLE [test] (
   [id] TEXT,
   [age] TEXT,
   [weight] TEXT
);
/tmp % sqlite-utils transform test.db test --type age integer --type weight float   
/tmp % sqlite-utils schema test.db                                               
CREATE TABLE "test" (
   [id] TEXT,
   [age] INTEGER,
   [weight] FLOAT
);
/tmp % sqlite-utils rows test.db test
[{"id": "1", "age": 3, "weight": 2.5},
 {"id": "2", "age": "", "weight": ""}]
```
It would be neat if this resulted in the following instead:
```
 {"id": "2", "age": null, "weight": null}
```
Related Discord discussion: https://discord.com/channels/823971286308356157/823971286941302908/1019635490833567794

## Write access

Make your changes inside this directory — it is an isolated git worktree of the target repo:
- <harness-root>\runs\20260726-204559-issue-488-sqlite-utils-transform-should-set-empty\write_worktree

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

