<!-- Source draft for the launch post. Posts are kept under X's 280-char
     weighted limit (non-Premium): URLs count as 23, emoji as 2. -->

# X/Twitter thread draft

**1/**
Eight AI-written patches for eight real sqlite-utils issues.

All 8 passed the full test suite.
All 8 stayed inside their blast radius.
All 8 shipped a regression test that fails without the fix.

Two of them don't fix the bug. 🧵

**2/**
That's the whole argument.

Machine verification is necessary and not sufficient. Every automated check a diff can pass, these passed.

Someone still had to read the patch next to the issue it claimed to close. That read is where the two bad ones surfaced.

**3/**
So I built the harness that keeps those levels apart instead of collapsing them into one green checkmark.

linejudge runs your agent, then verifies the result itself — real commands, real file checks, real diff constraints — outside the session, after it ends.

**4/**
Reject #1 — issue 439, misleading progress bar on utf-16.

The patch counts bytes as utf-8-sig. It fixes utf-16 and regresses the default: a 708-byte plain utf-8 CSV now reports 1011. The old code was exact.

The added test covers utf-16-le only.

**5/**
Reject #2 — issue 762, transform drops CHECK constraints.

The parser masks string literals and quoted identifiers. Not SQL comments.

So a commented-out "-- CHECK (id > 0)" is re-emitted as an ACTIVE constraint. A table that accepted id = -1 now rejects it.

**6/**
Neither is catchable by a test suite that doesn't already know about the bug. Both cleared every machine gate I had.

The agent's own report on 762 openly defers the comment case — and the run still came back green.

The claim was honest. The verdict was wrong.

**7/**
So the scoreboard reports four numbers, not one:

• Runs succeeded: 7/8
• Independently verified: 8/8
• Regression test proven: 8/8 — fails with the fix reverted
• Diff reviewed against the issue: 6/8

That last line is the one nobody publishes.

**8/**
Built to be trusted, because a trust tool has to be:

• Python stdlib only — zero deps, no supply chain
• every file under 300 lines — read the engine in an afternoon
• writes land as a patch on an unmerged branch
• artifacts are plain text
• Apache-2.0

**9/**
There's also a zero-cost demo that ships with a liar: a mock agent that writes "Status: SUCCESS" and produces nothing.

The files_exist verifier checks the disk and fails the run.

Claim is not call. The call decides.

**10/**
Works with Claude Code headless today. The adapter contract is one method — wrapping any agent CLI is ~90 lines.

Full evidence trail for all 8 runs:
https://github.com/phillipmex/linejudge
