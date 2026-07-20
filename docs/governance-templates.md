# Governance templates

Copy-paste starting points for running coding agents unattended. These are the
policies the harness mechanically enforces (guard, verifiers, worktree writes)
plus the human-side rules it can't. Adapt freely; delete what you don't need.

---

## Template 1 — Agent constitution

Put this (adapted) in your harness root as `CONSTITUTION.md` and reference it
from goal `agent_notes:` where relevant. Rules marked ⚙ are enforced by
linejudge itself; the rest are instructions to the agent and policy for
operators.

### Boundaries

1. ⚙ Work only in the provided workspace and the write worktree. Guarded
   read-dirs are snapshotted; any mutation fails the run.
2. ⚙ Never merge your own work. Changes end life as a diff on an unmerged
   `linejudge/<run_id>` branch; a human (or an approve decision in the
   dashboard) promotes them.
3. Do not install dependencies, alter CI config, or touch secrets/credential
   files unless the goal explicitly says so. (Back this with
   `diff_constraints: deny=**/*.env deny=.github/**` on write goals.)
4. Never delete files outside the workspace. Prefer additive changes.

### Honesty

5. Report failure as failure. A run that says FAILED with a good diagnosis is
   worth more than a false SUCCESS — ⚙ verifiers will catch the lie anyway,
   and the ledger remembers.
6. The REPORT.md contract is mandatory: status, what was done, what was not
   done, how to verify. ⚙ A missing report fails the run.

### Economy

7. Stay within `timeout_secs`. If the task is clearly bigger than the budget,
   stop early, report partial progress, and say what the next run should do.
8. ⚙ Every run's cost is recorded to the ledger. Operators: review
   `runs/ledger.jsonl` totals weekly; set per-goal `model:` overrides where a
   cheaper model passes the same verifiers.

### Learning

9. Distilled lessons must be durable and general ("verify X before claiming
   Y"), never run-specific trivia or transcript quotes. ⚙ Soft-errored
   distillations are discarded, not stored.

---

## Template 2 — Definition of Done (per-goal)

A goal is **done** when all of the following hold — encode as much as possible
in the goal header so the harness, not the agent, checks it:

```markdown
---
name: <goal>
verifiers:
  - command: <the test suite, run headless>       # behaviour is proven
  - files_exist: <deliverables, comma-separated>  # artifacts exist
  - diff_constraints: max_files=<N> deny=<globs>  # change is proportionate
timeout_secs: <budget>
---
```

- [ ] All verifiers pass (⚙ `verdict.json.passed == true`)
- [ ] Guard clean (⚙ no unexpected mutation of read dirs)
- [ ] REPORT.md present and honest (⚙ presence; honesty via spot-checks)
- [ ] Diff reviewed and **approved in the dashboard** — the decision file is
      the sign-off record
- [ ] Branch merged by a human, then `linejudge cleanup` run

**Not** part of done: the agent saying it's done.

---

## Template 3 — Unattended-fleet runbook

- **Before enabling unattended runs**: every goal has ≥1 command verifier;
  write goals have `diff_constraints`; `.env.local` is gitignored; a dry-run
  of each goal has been eyeballed.
- **Daily**: skim the dashboard run list; approve/reject anything with a diff;
  `linejudge stale-check <repo>` before merging old branches.
- **Weekly**: ledger review (cost per goal, failure rate per tag);
  prune/curate `learnings/` — the pool is plain markdown, edit it like docs.
- **On a guard trip**: treat as an incident, not noise. The diagnostics in the
  run dir show exactly what mutated; tighten tools/allowlists before rerunning.
- **On repeated verifier failures for one goal**: the goal is under-specified
  or over-budgeted. Fix the goal, don't loosen the verifier.
