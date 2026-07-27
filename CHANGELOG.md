# Changelog

All notable changes to linejudge are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] — 2026-07-27

The release that carries the sqlite-utils proof run. Minor rather than patch:
path redaction changes the contents of committed artifacts, and the artifacts
are the API.

### Added

- **Path redaction in the run trail** — absolute paths from the machine that
  produced a run (harness root, home directory) are replaced with
  `<harness-root>` / `<home>` across every committed artifact, so a published
  trail does not leak local filesystem layout. `cleanup.json` keeps real paths
  (teardown reads them back) and is now gitignored instead.
- **Human-adopted reviewer state** — `decision.json` distinguishes a review the
  project owner derived independently (`reviewer: human`) from one drafted by
  an assistant and adopted by the owner, so `PROOF.md` can state the provenance
  of its own verdicts instead of implying every call was human-made.
- **Published evidence** — `PROOF.md` now reports the eight-issue sqlite-utils
  run: 7/8 succeeded, 8/8 independently verified, 8/8 regression-test proven,
  6/8 diff-reviewed. The two rejects are walked through in full at
  <https://phillipmex.github.io/linejudge/>.

### Fixed

- **`--version` no longer lies.** It was a hardcoded string in
  `src/linejudge/__init__.py` that drifted from `pyproject.toml`; a 0.2.0
  install reported `linejudge 0.1.0`. It now reads the installed package
  metadata, and falls back to `0.0.0+source` when run from a source tree.

### Changed

- **README leads with the result** rather than the mock demo — three machine
  gates passed 8/8 and reading the diffs still found two patches that don't fix
  the bug. The zero-cost demo moved below it as the try-it-now path.
- **`pytest` works from the repo root.** Collection previously walked into
  `proofs/targets/` and died on a vendored suite's third-party imports;
  `testpaths`/`norecursedirs` now scope it to `tests/`.

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
