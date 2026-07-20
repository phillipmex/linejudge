# ADR-0001 — Lineage, scope, and the open-core bet

- **Status**: accepted
- **Date**: 2026-07-21

## Context

linejudge began as a private experiment: a governance-and-verification wrapper
around a headless coding agent used as an autonomous task runner. Living with
that system produced one durable observation:

> The execution loop is a commodity. Every vendor ships one, and they all
> share a flaw: **the agent grades its own homework.** The valuable, missing
> layer is independent verification — harness-run verifiers, blast-radius
> guarding, verified-diff-only writes, auditable learning, honest cost
> accounting.

linejudge is a clean-room-style productization of that trust layer. The
private predecessor was used as a read-only design reference; no history,
paths, or account-specific configuration were carried over. Several known
weaknesses were fixed rather than ported: ungraceful main-run timeouts,
no retry on soft API errors, discarded cost telemetry, new files missing from
captured diffs, flat un-retrieved learning memory, and zero test coverage on
orchestration (now the most-tested part of the codebase).

## Decision

1. **Product = the judge, not the player.** linejudge never competes on agent
   capability. The agent backend is a pluggable adapter; the product is the
   verdict, the guardrails, and the audit trail.
2. **Open-core.** The harness — engine, verifiers, guard, worktree writes,
   learning store, local dashboard, proof tooling — is Apache-2.0 OSS. A
   possible future commercial layer is a hosted control plane (team review
   queues, fleet dashboards, org policy) built *on top of* the same artifact
   formats. The OSS tool must remain complete and self-sufficient; nothing in
   this repo is crippled to upsell.
3. **Python stdlib only, ≤300 lines per source file.** Zero runtime
   dependencies is a trust feature (auditable in an afternoon, no supply
   chain) and a differentiator. `unittest` for tests, GitHub Actions
   (Windows + Ubuntu) for CI.
4. **Artifacts are the API.** `runs/<id>/` (prompt, session, verdict.json,
   write_diff.patch, outcome, cost, decision) and `runs/ledger.jsonl` are
   stable, documented, plain-text formats. Anything — including a future
   hosted product — builds on the files, not on internal Python APIs.
5. **Claim/verdict separation is inviolable.** Run status derives from
   harness-observed facts (verifiers, guard, contract, errors) only. No code
   path may promote an agent claim into a success signal.

## Consequences

- Anyone can wrap any agent CLI in ~90 lines (see the adapter guide) and get
  the full trust stack — adoption surface is every agent, not one vendor.
- Stdlib-only means hand-rolling things dependencies would give us (HTTP
  serving, diff parsing). Accepted: each piece so far fits the 300-line cap.
- The LLM-as-judge verifier is deliberately deferred — it reintroduces "model
  grades model" and costs money to test honestly. If added, it will be opt-in
  and clearly labeled as a *weaker* evidence class than command/file/diff
  verifiers.
- Open-core discipline (complete OSS tool) forfeits some monetization levers;
  the bet is that trust products cannot be trusted if the trust parts are
  paywalled.
