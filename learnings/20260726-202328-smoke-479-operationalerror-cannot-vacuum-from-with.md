---
goal: smoke-479-operationalerror-cannot-vacuum-from-with
status: FAILED
tags: proof, sqlite-utils
run_id: 20260726-202328-smoke-479-operationalerror-cannot-vacuum-from-with
---

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
