<!-- Source draft for the launch post. -->

# X/Twitter thread draft

**1/**
Eight AI-generated patches for eight real sqlite-utils issues.

All 8 passed the full test suite.
All 8 stayed inside their declared blast radius.
All 8 shipped a regression test that provably fails without the fix.

Two of them do not fix the bug. 🧵

**2/**
That's the whole argument.

Machine verification is necessary and it is not sufficient. Every automated
check a diff can pass, these passed. Somebody still had to read the patch next
to the issue it claimed to close — and that read is where the two bad ones
surfaced.

**3/**
So I built the harness that keeps those levels of evidence apart instead of
collapsing them into one green checkmark.

linejudge runs your agent, then verifies the result ITSELF — real commands,
real file checks, real diff constraints — outside the agent session, after it
ends. The agent can't see, influence, or spoof the verdict.

**4/**
Reject #1 — issue 439, "misleading progress bar against utf-16".

The agent switched the byte-counting path to utf-8-sig. It fixes utf-16.
It also regresses the default: a plain utf-8 CSV that's 708 bytes on disk now
reports 1011, where the old code was exact.

The added test only covers utf-16-le.

**5/**
Reject #2 — issue 762, "transform drops CHECK constraints".

The constraint parser masks string literals and quoted identifiers. It does not
mask SQL comments.

So `-- CHECK (id > 0)`, commented out, gets scanned as live text and re-emitted
as an ACTIVE constraint. A table that accepted id = -1 starts rejecting it.

**6/**
Neither is catchable by a test suite that doesn't already know about the bug.
Both cleared every machine gate I had.

The agent's own report on 762 openly defers the comment case — and the run
still came back green. The claim was honest. The verdict was still wrong.

**7/**
So the scoreboard reports four numbers instead of one:

• Runs succeeded: 7/8
• Independently verified pass: 8/8 — judged by verifiers, not by the claim
• Regression test proven: 8/8 — fails with the fix removed
• Diff reviewed against the issue: 6/8

That last line is the one nobody publishes.

**8/**
Built to be trusted, because a trust tool has to be:
• Python stdlib ONLY — zero dependencies, no supply chain
• every file ≤300 lines — read the whole engine in an afternoon
• writes only via git worktree → a reviewable patch on an unmerged branch
• artifacts are plain text; the formats are the API
• Apache-2.0

**9/**
There's also a zero-cost demo that ships with a liar: a mock agent that writes
"Status: SUCCESS" and produces nothing. The files_exist verifier checks the
disk and fails the run.

Claim ≠ call. The call decides.

**10/**
Works with Claude Code headless today. The adapter contract is one method —
wrapping any agent CLI is ~90 lines.

Full evidence trail for all 8 runs is in the repo:
https://github.com/phillipmex/linejudge
