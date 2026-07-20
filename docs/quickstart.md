# Quickstart

From zero to a reviewed, independently-verified agent run. Steps 1–3 cost
nothing and need no API key; step 4 runs a real agent.

## 0. Requirements

- Python 3.10+
- git (for write-mode goals and the guard)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI — only for
  real runs (step 4)

## 1. Install

```console
git clone https://github.com/phillipmex/linejudge
cd linejudge
pip install .
linejudge --version
```

Zero runtime dependencies — the install is the package itself and a `linejudge`
console script.

## 2. Dry-run a goal ($0)

```console
linejudge run goals/examples/hello.md --dry-run
```

Prints the exact composed prompt — goal body, output contract, retrieved
learnings preamble — and exits. Nothing is called, nothing is written. This is
the fastest way to sanity-check a new goal file.

## 3. The mock demo ($0)

```console
python proofs/demo.py --root demo
linejudge dashboard --root demo
```

Then open <http://127.0.0.1:8765>.

The demo generates three goals from a canned GitHub-issue fixture and runs each
through the **full harness** (workspace, guard, verifiers, distillation,
ledger) against scripted mock agents. Two agents do the work; one **lies** —
it writes a REPORT.md claiming success but never produces the required file.
The `files_exist` verifier fails it, and the run is FAILED regardless of the
claim.

In the dashboard you can see, per run: the prompt, the agent's report (the
claim), the verdict with per-verifier evidence (the call), the cost, and the
distilled lesson — plus an approve/reject gate. Your decision is written to
`runs/<id>/decision.json`, beside the evidence, never into it.

`demo/PROOF.md` holds the scoreboard; a committed sample lives at
[PROOF-sample.md](PROOF-sample.md).

## 4. A real run

Pick a billing mode:

- **API key** — put `ANTHROPIC_API_KEY=sk-…` in the environment or in a
  gitignored `.env.local` at your harness root.
- **Config dir** — set `CLAUDE_CONFIG_DIR` to a separately-logged-in Claude
  Code config directory (interactive/personal use).

Then:

```console
mkdir myruns && cd myruns
linejudge run ../goals/examples/hello.md
```

The agent gets a fresh workspace, writes `hello.txt` and its `REPORT.md`; the
harness runs the goal's `command` verifier and prints the verdict. All
artifacts land in `runs/<run_id>/`:

```
runs/<run_id>/
├── prompt.md          # exactly what the agent was sent
├── session.json       # raw agent envelope
├── workspace/         # the agent's sandbox, incl. REPORT.md (the claim)
├── verdict.json       # per-verifier pass/fail + evidence (the call)
├── outcome.json       # final status + failure reasons
├── run_cost.json      # dollars + tokens for this run
└── summary.md         # human-readable recap
```

## 5. Write-mode goals

To let the agent modify a real repo, add `write_repo:` to the goal header:

```markdown
---
name: fix-widget-crash
write_repo: /path/to/widget
verifiers:
  - command: python -m pytest -q
  - diff_constraints: max_files=5 deny=**/*.env
---
Fix the crash described in …
```

The harness creates a **git worktree** on branch `linejudge/<run_id>`; the
agent edits there, never in your checkout. After the run:

- the full diff (including new files) is captured to
  `runs/<id>/write_diff.patch` **before** verifiers run, so
  `diff_constraints` judges the real change;
- non-empty changes are committed to the branch, which survives as the record;
- your working tree is untouched.

Housekeeping:

```console
linejudge cleanup runs/<run_id>       # tear down worktree + links safely
linejudge stale-check /path/to/widget # do captured diffs still apply?
```

## 6. Scale it: the proof harness

```console
python proofs/generate.py --repo owner/name --limit 5 \
    --verifier "command: python -m pytest -q" --tag mylabel
# … linejudge run each generated goal …
python proofs/stats.py --root proofs/root     # → PROOF.md scoreboard
```

## Where next

- [Verifier spec](verifier-spec.md) — all built-ins and custom authoring
- [Adapter guide](adapter-guide.md) — run agents other than Claude Code
- [Governance templates](governance-templates.md) — policies for agent fleets
