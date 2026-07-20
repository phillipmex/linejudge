<!-- Source draft for the launch post. -->

# Never trust the robot: why your coding agent needs a line judge

Ask any coding agent how the task went. It went great. It always went great.

I ran an autonomous agent loop for months — headless runs, batch tasks, the
works — and the single most reliable observation was this: **agents claim
success far more often than they achieve it.** Not maliciously; the model
genuinely believes its summary. But a claim is not evidence, and every
mainstream agent harness treats it as one. The agent runs the tests (or says
it did), reads the output (or misreads it), and reports "done". The harness
believes it. The agent is grading its own homework.

In tennis, we solved this problem a century ago: the player doesn't call the
lines. The line judge does. So that's what I built.

## The claim and the call

[linejudge](https://github.com/phillipmex/linejudge) is a verification harness
for any coding agent. A task is a **goal file** — a markdown prompt plus a
declarative list of verifiers:

```markdown
---
name: fix-config-crash
write_repo: /path/to/widget
verifiers:
  - command: python -m pytest -q
  - files_exist: done.txt
  - diff_constraints: max_files=5 deny=**/*.env
---
Fix the config loader crash on empty YAML files…
```

The harness sends the prompt to the agent, and when the session **ends**, it
executes the verifiers itself — real subprocesses, real filesystem checks,
real diff analysis — against what's actually on disk. The results land in
`verdict.json` with per-verifier evidence. Run status is derived from the
verdict, the guard, and the output contract. The agent's report is stored,
displayed, and **never consulted**.

That's the entire idea. Everything else is supporting structure:

- **Blast-radius guard.** Directories the agent may read are
  git-status-snapshotted before and after the run. Any unexpected mutation
  fails the run with diagnostics. "It shouldn't have touched that" becomes a
  recorded fact, not a suspicion.
- **Verified-diff-only writes.** Write access goes through a git worktree on
  an unmerged `linejudge/<run_id>` branch. The diff — including new files —
  is captured before verifiers run, so diff constraints judge the real
  change. Your working tree is never touched; a human merges, or doesn't.
- **Learning you can audit.** After each run, a second, tool-less call
  distills a short lesson into a markdown file; future runs retrieve relevant
  lessons by tag. It's a directory of files you can read and edit, not an
  opaque memory. A guard keeps rate-limit garbage from poisoning the pool.
- **A ledger.** The agent's JSON envelope already contains the run's cost and
  token usage — most DIY scripts just drop it. linejudge writes it to
  `run_cost.json` per run and an append-only `runs/ledger.jsonl`.
- **A review gate.** A local, stdlib-only dashboard renders each run's full
  evidence trail — prompt, claim, diff, verdict, cost, lesson — with
  approve/reject buttons. The decision is a file *beside* the evidence.

## The liar in the demo

The repo ships a zero-cost demo: three tasks generated from canned GitHub
issues, run through the full harness against scripted mock agents. Two do the
work. One writes a glowing REPORT.md ("Status: SUCCESS") and produces nothing.

The `files_exist` verifier checks the disk, disagrees, and the run is FAILED —
claim notwithstanding. The generated PROOF.md then reports two numbers that
every agent benchmark should be forced to separate:

> **Runs succeeded:** 2/3
> **Independently verified pass:** 2/3 — every task judged by verifiers, not
> by the agent's claim

When those numbers diverge on your own fleet, that divergence *is* the
information.

## Built to be read

Some deliberate constraints, because a trust tool must itself be trustable:

- **Zero runtime dependencies.** Python stdlib only — including the HTTP
  dashboard and the diff parser. No supply chain to audit.
- **≤300 lines per source file.** You can read the whole engine in an
  afternoon. Please do.
- **The artifacts are the API.** Everything is plain text in `runs/` — stable
  formats that scripts, CI, or a future hosted layer can build on.
- **No LLM-as-judge verifier — yet.** It reintroduces model-grades-model. If
  it ships, it'll be opt-in and labeled as the weaker evidence class it is.

It works with Claude Code headless today; the adapter contract is one method,
so wrapping another agent CLI takes about 90 lines.

`pip install`, run the demo, watch the liar get caught:
**https://github.com/phillipmex/linejudge**
