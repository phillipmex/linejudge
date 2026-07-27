---
title: "Eight patches passed every check I had. Two of them were wrong."
description: "Three machine gates said 8/8. Reading the diffs found two that don't fix the bug. Why machine verification is necessary and not sufficient."
---

# Eight patches passed every check I had. Two of them were wrong.

I ran an AI coding agent against eight real open issues in
[sqlite-utils](https://github.com/simonw/sqlite-utils) — a mature, well-tested
Python library — and put every patch it produced through three independent
machine gates.

All eight passed the project's full test suite. All eight stayed inside the
blast radius the task declared. All eight shipped a regression test that fails
with the fix reverted and passes with it applied — not a test the agent claimed
to write, a test re-run both ways to prove it discriminates.

Three gates, 8/8 on every one.

Then I read the diffs next to the issues they claimed to close, and two of them
don't fix the bug.

That gap is the entire thesis of this project, so let me put the receipts first
and the pitch second.

## Reject one: the fix that regressed the case it wasn't testing

sqlite-utils issue 439 reports a misleading progress bar when importing a
utf-16 CSV. The agent's patch changes how the importer measures bytes consumed,
defaulting the encoding to `utf-8-sig` and calling a byte-length helper once per
line.

It does fix utf-16. It also breaks the common path. `'a'.encode('utf-8-sig')` is
four bytes where `utf-8` is one, so a plain utf-8 CSV — the default, the one
almost everybody imports — now reports 1011 bytes for a 708-byte file. The
previous code was exact.

The added regression test covers utf-16-le only. It passes. The full suite
passes. Nothing in the automated evidence trail knows the default case got
worse.

There's a second problem, less subtle: the issue body asks for two things — a
silent crash with no stacktrace, and a `--debug` option — and the patch
addresses neither. The issue had been retitled at some point, and the agent
fixed the headline instead of the report.

## Reject two: the parser that reads comments as code

Issue 762 reports that `transform()` drops CHECK constraints. The agent's fix
parses the table's original SQL and re-emits the constraints, masking quoted
regions first so that string literals don't confuse the scan.

It masks string literals and quoted identifiers. It does not mask SQL comments —
the masking function's own docstring says as much, and nothing in the diff
mentions comments at all.

So a constraint someone deliberately commented out:

```sql
-- CHECK (id > 0)
```

is scanned as live text and re-emitted as an *active* constraint. Run
`transform()` on that table and it stops accepting `id = -1`. The migration
silently tightens the schema.

There's a second hole: with `drop={'a'}`, a compound `CHECK (a > 0 AND b > 0)`
is discarded whole, quietly losing the `b` half.

The fix is otherwise genuine — real work, real improvement. But `fixes #762`
would overclaim, and the failure mode it introduces is worse than the bug it
closes. Notably, the agent's own report *openly defers* the comment case. It
didn't lie. The run was still green.

## What this does and doesn't prove

It doesn't prove agents are useless. Six of eight patches were good, and the two
rejects both contain real work.

It proves something narrower and, I think, more useful: **machine verification
is necessary and it is not sufficient, and reporting them as one number destroys
the distinction.** A test suite cannot catch a bug it doesn't know about. A
diff-constraint checker cannot tell you the diff solves the wrong problem. The
only thing that caught either of these was a person reading the patch against
the issue.

Every agent benchmark I've seen collapses this. "Resolved 62% of issues" — by
whose call?

## The line judge

In tennis we solved this a century ago: the player doesn't call the lines.

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
executes the verifiers itself — real subprocesses, real filesystem checks, real
diff analysis — against what's actually on disk. Results land in `verdict.json`
with per-verifier evidence. Run status is derived from the verdict, the guard,
and the output contract. The agent's report is stored, displayed, and **never
consulted**.

Everything else is supporting structure:

- **Blast-radius guard.** Directories the agent may read are
  git-status-snapshotted before and after the run. Any unexpected mutation fails
  the run with diagnostics. "It shouldn't have touched that" becomes a recorded
  fact, not a suspicion.
- **Verified-diff-only writes.** Write access goes through a git worktree on an
  unmerged `linejudge/<run_id>` branch. The diff — including new files — is
  captured before verifiers run, so diff constraints judge the real change. Your
  working tree is never touched; a human merges, or doesn't.
- **Learning you can audit.** After each run, a second, tool-less call distills a
  short lesson into a markdown file; future runs retrieve relevant lessons by
  tag. It's a directory of files you can read and edit, not an opaque memory.
- **A ledger.** The agent's JSON envelope already contains the run's cost and
  token usage — most DIY scripts drop it. linejudge writes it to `run_cost.json`
  per run and an append-only `runs/ledger.jsonl`.
- **A review gate.** A local, stdlib-only dashboard renders each run's full
  evidence trail — prompt, claim, diff, verdict, cost, lesson — with
  approve/reject buttons. The decision is a file *beside* the evidence.

## The scoreboard

`PROOF.md` is generated from the artifacts, not the transcript, and it refuses to
blur the levels together:

> **Runs succeeded:** 7/8
>
> **Independently verified pass:** 8/8 — every task judged by verifiers, not by
> the agent's claim
>
> **Regression test proven:** 8/8 — the added test fails with the fix removed
>
> **Diff reviewed against the issue:** 6/8

Four numbers, four different strengths of evidence, in descending order of how
easy they are to automate and ascending order of how much they tell you.

It also records *who* made each review call. The two rejections above I derived
myself and will defend; the six approvals were drafted by an assistant and
adopted by me, and PROOF.md says so in those words. A tool whose pitch is "claims
aren't verdicts" doesn't get to be vague about the provenance of its own
verdicts.

I'm not publishing dollar costs: this run was billed to a subscription, not
per-token API credit, so any figure would be notional.

## Built to be read

Some deliberate constraints, because a trust tool must itself be trustable:

- **Zero runtime dependencies.** Python stdlib only — including the HTTP
  dashboard and the diff parser. No supply chain to audit.
- **≤300 lines per source file.** You can read the whole engine in an afternoon.
  Please do.
- **The artifacts are the API.** Everything is plain text in `runs/` — stable
  formats that scripts, CI, or a future hosted layer can build on.
- **No LLM-as-judge verifier — yet.** It reintroduces model-grades-model. If it
  ships, it'll be opt-in and labeled as the weaker evidence class it is.

It works with Claude Code headless today; the adapter contract is one method, so
wrapping another agent CLI takes about 90 lines.

If you'd rather not spend tokens to see it work, the repo ships a zero-cost
demo: three tasks against scripted mock agents, one of which writes a glowing
`REPORT.md` ("Status: SUCCESS") and produces nothing at all. The `files_exist`
verifier checks the disk, disagrees, and the run is FAILED — claim
notwithstanding.

The full evidence trail for all eight sqlite-utils runs is in the repo:
**[github.com/phillipmex/linejudge](https://github.com/phillipmex/linejudge)**
