# How linejudge compares

linejudge is **not** another coding agent. It is the layer that decides whether
an agent's work is actually done — for any agent. That makes most comparisons
"complement, not competitor", but the differences matter when you're deciding
what to trust.

| | verification of results | who decides success | blast-radius control | cross-run memory | cost ledger | audit trail | deps |
|---|---|---|---|---|---|---|---|
| **linejudge** | declarative verifiers run by the harness | the harness (verdict.json) | git-status guard + worktree-only writes | versioned markdown lessons, tag retrieval | per-run + append-only ledger | full per-run artifact dir + review gate | **0** (stdlib) |
| bare `claude -p` loop (DIY script) | whatever you script | the agent's final message | none unless you build it | none | discarded (it's in the envelope — most scripts drop it) | stdout, if you saved it | 0 |
| Aider | optional auto-test after edit, same process | agent + your eyeballs | edits your working tree directly (git commits as undo) | repo map, chat history | token report per session | git history | Python deps |
| OpenHands | agent may run tests *itself* inside its sandbox | the agent | container sandbox (strong) | per-conversation | usage metrics | event stream | heavy (Docker + service) |
| hosted agents (Devin, Copilot coding agent, …) | agent-run tests, platform-defined | the platform/agent | vendor sandbox | vendor-managed, opaque | vendor billing | PR + vendor UI | SaaS |

## The one distinction that matters

Everyone in this table except linejudge lets the **agent** run (or skip) the
checks and then report its own result. An agent that runs the tests *inside
its own session* can also mis-run them, misread them, or claim it ran them.
linejudge executes verifiers **outside the agent session, after it ends**,
against the artifacts on disk. The agent cannot see, influence, or spoof the
verdict.

Corollary: linejudge composes with all of the above. An Aider or OpenHands
session driven through an [adapter](adapter-guide.md) gets the same
independent verdict, guard, ledger, and review gate as Claude Code does today.

## When *not* to use linejudge

- Interactive pair-programming — you're watching every edit; you *are* the
  verifier. Aider-style tools fit better.
- Tasks with no checkable definition of done — if success can't be expressed
  as commands/files/diff constraints/HTTP checks (or a custom verifier), the
  harness can only tell you the run finished, not that it's right.
- One-off throwaway scripts — the artifact trail is overhead when nothing
  needs to be trusted later.

## When it earns its keep

- Unattended/batch agent runs, where nobody reads transcripts
- Anything feeding a **PROOF-style scoreboard** — claims are marketing,
  verdicts are evidence
- Agents touching repos you care about (guard + worktree-only writes)
- Teams that need an approval gate with the evidence attached
