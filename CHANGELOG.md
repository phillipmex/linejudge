# Changelog

All notable changes to linejudge are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-07-21

First release. The independent line judge for coding agents: runs your agent
on a goal file, then verifies the result itself — the agent's own claim of
success is never consulted.

### Added

- **Core engine** — goal-file parser (`---` fenced header: name, tags,
  read_dirs, write_repo, write_link_dirs, model, verifiers, timeout_secs,
  agent_notes; legacy `verify:` sugar), run orchestration with per-run
  artifact directories (`runs/<run_id>/`), graceful timeout handling, and a
  single retry on soft API errors.
- **Adapters** — `AgentAdapter` contract with `RunResult` telemetry (cost,
  usage, duration, turns, session id); `ClaudeCodeAdapter` for `claude -p`
  headless runs; `MockAdapter` for $0 development, demos, and tests.
- **Verifier registry** — `command`, `files_exist`, `diff_constraints`,
  `http_check`; every verifier runs outside the agent session; structured
  evidence in `verdict.json`; overall verdict is AND of all verifiers,
  fail-closed.
- **Guard** — git-status blast-radius check over read_dirs and write_repo
  before/after each run, with a diagnostic artifact on trip.
- **Write flow** — isolated `git worktree` per run on branch
  `linejudge/<run_id>`, LF-safe diff capture, auto-commit of non-empty diffs,
  `cleanup` and `stale-check` subcommands; junction/symlink/copy linking for
  untracked runtime dirs.
- **Learning store** — tool-less distillation call after each run, tagged
  learning reports with frontmatter, tag-overlap + recency retrieval
  (poisoning guard: soft-errored distills are discarded).
- **Cost ledger** — per-run `run_cost.json` plus append-only
  `runs/ledger.jsonl` with aggregation.
- **Dashboard** — stdlib-only web UI (`linejudge dashboard`): run list,
  full artifact detail (prompt, report, verdict, diff, cost, learning), and
  a human approve/reject gate written to `runs/<id>/decision.json`.
- **Proof harness** — `proofs/` goal generation from GitHub issues, mock
  end-to-end demo, and `PROOF.md` stats (verified-pass rate vs claimed).
- **Docs** — quickstart, verifier spec, adapter authoring guide, comparison,
  governance templates, ADR-0001.
- **CI** — GitHub Actions matrix: Windows + Ubuntu × Python 3.10/3.12.

### Notes

- Zero runtime dependencies — Python stdlib only, by design.
- Requires Python ≥ 3.10 and git; the Claude Code CLI only for real
  (non-mock) runs.
