# Verifier specification

Verifiers are the core of linejudge. They run **outside** the agent session,
after it has ended, in a process the agent never sees. The agent's REPORT.md is
a *claim*; the verdict is what the verifiers say. The two are never mixed.

## Declaring verifiers in a goal file

```
---
name: fix-timeout-bug
verifiers:
  - command: python -m unittest discover -s tests
  - files_exist: CHANGELOG.md
  - diff_constraints: max_files=3 max_lines=120 deny=secrets/*
  - http_check: http://127.0.0.1:8000/health expect=200 contains=ok
---
Fix the request timeout bug described below...
```

Each list item is `kind: spec`. The `kind` selects a verifier from the
registry; everything after the first colon is the `spec`, an opaque string
whose format is defined per verifier. The legacy single `verify: <shell
command>` key still works — it is sugar for a `command` verifier prepended to
the list.

## Semantics

- Every declared verifier runs, in order, even after one fails — the verdict
  should tell you *everything* that is wrong, not just the first thing.
- The overall verdict is the **AND** of all entries. An empty list passes
  (you declared no requirements; declare some).
- A verifier that crashes, or an unknown `kind`, becomes a **failed entry with
  evidence**, never a crashed run. The harness always delivers a recorded
  verdict.
- Each entry records `kind`, `spec`, `passed`, `evidence` (capped at the last
  8000 characters), and `duration_secs`.
- The verdict is written to `runs/<run_id>/verdict.json`:

```json
{
  "passed": false,
  "verifiers": [
    {"kind": "command", "spec": "python -m unittest ...",
     "passed": true, "evidence": "exit 0\n--- stdout ---\n...", "duration_secs": 4.1},
    {"kind": "diff_constraints", "spec": "max_files=3",
     "passed": false, "evidence": "5 files / 212 changed lines: ...", "duration_secs": 0.0}
  ]
}
```

## Built-in verifiers

### `command` — run a shell command, pass on exit 0

```
- command: python -m unittest discover -s tests
```

Runs with `shell=True` in the run's workspace, 600 s timeout. Evidence is the
exit code plus captured stdout/stderr. This is the workhorse: test suites,
linters, `make check`, anything scriptable.

### `files_exist` — comma-separated relative paths

```
- files_exist: dist/app.whl, CHANGELOG.md, docs/api.md
```

Every path (relative to the workspace) must exist. Evidence lists each path
with `OK` or `MISSING`, so a failure names exactly what the agent didn't
deliver. Directories count as existing.

### `diff_constraints` — blast-radius limits on the captured write diff

```
- diff_constraints: max_files=3 max_lines=150 allow=src/*,tests/* deny=**/secrets*
```

Space-separated `key=value` tokens, all optional, all enforced together:

| token | meaning |
|---|---|
| `max_files=N` | at most N files may appear in the diff |
| `max_lines=N` | at most N changed lines (added + removed) total |
| `allow=glob,glob` | every changed file must match at least one glob |
| `deny=glob,glob` | no changed file may match any glob |

Globs use `fnmatch` against repo-relative paths. Applies to the unified diff
the write flow captures at `runs/<run_id>/write_diff.patch`; **when no diff was
captured (read-only run, or the agent changed nothing) this verifier fails** —
declaring diff constraints on a goal asserts that a diff should exist. Deleted
files count as changed files. This is how you turn "the agent shouldn't have
touched that" from a code-review groan into an automatic FAILED verdict.

> Until the write flow lands (Wave 3), read-only runs never produce
> `write_diff.patch`, so this verifier only makes sense on `write_repo` goals.

### `http_check` — probe an endpoint

```
- http_check: http://127.0.0.1:8000/health expect=200 contains=ok
```

First token is the URL; optional `expect=STATUS` (default 200) and
`contains=SUBSTR`. A non-2xx response is still a checkable answer (`expect=418`
passes on a 418). The substring cannot contain spaces — spec tokens are
space-separated; use a `command` verifier with `curl`/python for anything
fancier. 30 s timeout; connection failures fail with the error as evidence.

## Authoring a custom verifier

A verifier is a function `fn(spec, cwd, run_dir) -> (passed, evidence)`:

- `spec` — the opaque string from the goal header. Parse it however you like;
  document the format.
- `cwd` — the run's workspace (where the agent worked).
- `run_dir` — the run's artifact directory (`verdict.json`, `write_diff.patch`,
  `REPORT.md` live here or in the workspace).
- Return a bool and a human-readable evidence string. Raising is safe — the
  registry converts exceptions into failed entries — but a caught failure with
  good evidence beats a traceback.

Register it:

```python
from linejudge import verify

def verify_coverage(spec, cwd, run_dir):
    minimum = float(spec)
    ...
    return pct >= minimum, f"coverage {pct:.1f}% (minimum {minimum}%)"

verify.REGISTRY["coverage"] = verify_coverage
```

Design rules for good verifiers:

1. **Independent** — never trust anything the agent wrote as proof; re-derive
   it. REPORT.md is input to humans, not to verifiers.
2. **Evidence-first** — the evidence string must let a reviewer confirm the
   verdict without re-running anything.
3. **Deterministic** — same workspace, same verdict. Push flaky checks into
   `command` scripts where retries are explicit.
4. **Fail closed** — when the thing you need is missing (no diff, no server,
   no file), that is a FAILED verdict with a clear message, not a skip.

## Deliberately not included (yet)

- **LLM-as-judge** — a rubric-scored model call is a natural verifier, but it
  costs money and reintroduces trust in a model's opinion. It will land as an
  optional verifier that records model, prompt, and raw response as evidence.
- **Regex/AST assertions on code** — expressible today via `command` with a
  short python one-liner; a dedicated kind may come later if patterns emerge.
