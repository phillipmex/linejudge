<!-- Paste-ready. HN renders no markdown: asterisks and backticks appear
     literally, so this file deliberately contains neither. Blank lines are
     paragraph breaks. The form takes a URL *or* text, not both -- submit the
     URL, then post the comment below as your own first reply. -->

# Show HN

## Title (74 chars, HN max is 80)

Show HN: Linejudge – an independent verification harness for coding agents

## URL

https://github.com/phillipmex/linejudge

## First comment — post this yourself immediately after submitting

Every coding-agent loop I've used has the same design flaw: the agent runs the
checks (or doesn't), then reports its own result, and the harness believes it.
The agent grades its own homework.

Linejudge splits the roles. You declare verifiers in the goal file — shell
commands, files that must exist, diff constraints (max files/lines, path
allow/deny), HTTP checks — and the harness executes them outside the agent
session, after it ends, against the artifacts on disk. The agent can't see,
influence, or spoof the verdict. Run status comes from verdict.json, never from
the agent's report.

To find out what that's actually worth, I ran it against eight real open issues
from sqlite-utils. The result is the reason I'm posting.

All eight patches passed the project's full test suite. All eight stayed inside
their declared blast radius. All eight shipped a regression test that provably
fails with the fix reverted and passes with it applied. Three independent
machine gates, 8/8 on every one.

Then I read the diffs next to the issues they claimed to close, and two of them
don't fix the bug:

- Issue 439 (misleading progress bar on utf-16): the patch moves byte counting
  to utf-8-sig. It fixes utf-16 and regresses the default path — a plain utf-8
  CSV that is 708 bytes on disk reports 1011, where the previous code was exact.
  The added regression test covers utf-16-le only.

- Issue 762 (transform drops CHECK constraints): the constraint parser masks
  string literals and quoted identifiers but not SQL comments, so a
  commented-out "-- CHECK (id > 0)" is scanned as live text and re-emitted as an
  active constraint. A table that accepted id = -1 starts rejecting it. The
  agent's own report openly defers the comment case; the run was still green.

Neither is reachable by a test suite that doesn't already know about the bug.
That's the honest shape of the problem: machine verification is necessary, it is
not sufficient, and the two should never be reported as one number. So PROOF.md
reports them separately — runs succeeded 7/8, independently verified pass 8/8,
regression test proven 8/8, diff reviewed against the issue 6/8 — and it
distinguishes which review decisions I derived myself from which were drafted by
an assistant and adopted.

Other things it does:

- Blast-radius guard: read-only dirs are git-status-snapshotted before/after
  every run; unexpected mutation fails the run with diagnostics.

- Verified-diff-only writes: agents edit in a git worktree on an unmerged
  branch; the terminal state is a reviewable patch, never a silent merge.

- Cross-run learning you can read: each run distills a short markdown lesson;
  future runs retrieve relevant ones by tag. It's files, not a vector DB.

- Cost ledger: per-run dollars/tokens, parsed from the agent's own telemetry,
  which most DIY scripts throw away.

- A local dashboard showing the full evidence trail per run — prompt, the
  agent's claim, the diff, the verdict with evidence, cost — with an
  approve/reject gate written beside the evidence.

It's Python stdlib only (zero dependencies, every file under 300 lines — you can
read the whole engine in an afternoon), Apache-2.0, works with Claude Code
headless today, and the adapter contract is one method, so any agent CLI can be
wrapped in about 90 lines.

If you'd rather not spend tokens to see it work: python proofs/demo.py runs
three mock-agent tasks, one of which lies about success and produces nothing.
The verifier checks the disk and fails the run.

Longer write-up of the two rejects:
https://phillipmex.github.io/linejudge/

Happy to answer questions about the design — especially the deliberate omissions
(no LLM-as-judge verifier yet: it reintroduces model-grades-model, so it's
deferred until it can be labeled as the weaker evidence class it is).
