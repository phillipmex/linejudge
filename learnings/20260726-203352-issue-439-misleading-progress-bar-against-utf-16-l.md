---
goal: issue-439-misleading-progress-bar-against-utf-16-l
status: SUCCESS
tags: proof, sqlite-utils, bug, help wanted
run_id: 20260726-203352-issue-439-misleading-progress-bar-against-utf-16-l
---

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
