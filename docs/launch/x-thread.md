<!-- Source draft for the launch post. -->

# X/Twitter thread draft

**1/**
Your coding agent is grading its own homework.

It runs the tests (or says it did), reads the output (or misreads it), and
reports "done". Your harness believes it.

I built the line judge instead. 🧵

**2/**
linejudge runs your agent on a task, then verifies the result ITSELF — real
commands, real file checks, real diff constraints — outside the agent
session, after it ends.

The agent can't see, influence, or spoof the verdict.

**3/**
The demo ships with a liar.

3 mock-agent tasks. One writes "Status: SUCCESS" in its report and produces
nothing. The files_exist verifier checks the disk and fails the run.

Claim ≠ call. The call decides.

**4/**
The scoreboard it generates separates two numbers every agent benchmark
blurs together:

• Runs succeeded: 2/3
• Independently verified pass: 2/3 — judged by verifiers, not by the
agent's claim

When these diverge on your fleet, that divergence IS the information.

**5/**
Also in the box:
• git-status guard — agent touches a read-only dir, run fails with evidence
• writes only via git worktree → reviewable patch on an unmerged branch
• cost ledger from the agent's own telemetry
• learning as readable markdown, not a vector DB
• local review dashboard w/ approve/reject

**6/**
Built to be trusted:
• Python stdlib ONLY — zero dependencies, no supply chain
• every file ≤300 lines — read the whole engine in an afternoon
• Apache-2.0
• artifacts are plain text; the formats are the API

**7/**
Works with Claude Code headless today. The adapter contract is one method —
wrapping any agent CLI is ~90 lines.

pip install, run the demo, watch the liar get caught:
https://github.com/phillipmex/linejudge
