<!-- Source draft for the launch post. -->

# Show HN draft

**Title:**
Show HN: Linejudge – an independent verification harness for coding agents

**URL:** https://github.com/phillipmex/linejudge

**Text:**

Every coding-agent loop I've used has the same design flaw: the agent runs the
checks (or doesn't), then reports its own result, and the harness believes it.
The agent grades its own homework.

Linejudge splits the roles. Your agent plays the point; the harness calls the
lines. You declare verifiers in the goal file — shell commands, files that
must exist, diff constraints (max files/lines, path allow/deny), HTTP checks —
and the harness executes them *outside the agent session, after it ends*,
against the artifacts on disk. The agent can't see, influence, or spoof the
verdict. Run status comes from verdict.json, never from the agent's report.

Other things it does:

- Blast-radius guard: read-only dirs are git-status-snapshotted before/after
  every run; unexpected mutation fails the run with diagnostics.
- Verified-diff-only writes: agents edit in a git worktree on an unmerged
  branch; the terminal state is a reviewable patch, never a silent merge.
- Cross-run learning you can read: each run distills a short markdown lesson;
  future runs retrieve relevant ones by tag. It's files, not a vector DB.
- Cost ledger: per-run dollars/tokens (parsed from the agent's own telemetry,
  which most DIY scripts throw away) into an append-only JSONL.
- A local dashboard showing the full evidence trail per run — prompt, the
  agent's claim, the diff, the verdict with evidence, cost — with an
  approve/reject gate written beside the evidence.

It's Python stdlib only (zero dependencies, every file ≤300 lines — you can
read the whole engine in an afternoon), Apache-2.0, works with Claude Code
headless today, and the adapter contract is one method, so any agent CLI can
be wrapped in ~90 lines.

The demo is the pitch: `python proofs/demo.py` runs three mock-agent tasks,
one of which lies about success. The verifier catches it. The generated
PROOF.md reports "runs succeeded" and "independently verified pass %" as
separate numbers, because they're separate facts.

Happy to answer questions about the design — especially the deliberate
omissions (no LLM-as-judge verifier yet: it reintroduces model-grades-model,
so it's deferred until it can be labeled as the weaker evidence class it is).
