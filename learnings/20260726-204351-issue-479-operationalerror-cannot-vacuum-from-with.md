---
goal: issue-479-operationalerror-cannot-vacuum-from-with
status: FAILED
tags: proof, sqlite-utils
run_id: 20260726-204351-issue-479-operationalerror-cannot-vacuum-from-with
---

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
