# Adapter authoring guide

An adapter is the only piece of linejudge that knows which agent it is
talking to. Everything else — guarding, verification, learning, cost ledger,
dashboard — is agent-agnostic. The whole contract is one method and one
dataclass, both in `src/linejudge/adapters/base.py`.

## The contract

```python
from linejudge.adapters.base import AgentAdapter, RunResult

class MyAdapter(AgentAdapter):
    name = "my-agent"

    def run(self, prompt, cwd, timeout, add_dirs=(), tools="", model=None):
        ...
        return RunResult(text=..., ...)
```

| argument | meaning |
|---|---|
| `prompt` | the fully composed prompt (goal body + output contract + learnings). Send it verbatim. |
| `cwd` | the run workspace. The agent must treat this as its working directory; `REPORT.md` is expected here. |
| `timeout` | seconds. A blown timeout must come back as a soft error, not an exception (see below). |
| `add_dirs` | extra directories the agent may access (read dirs; on write runs the **last** entry is the worktree). |
| `tools` | backend-specific tool allowlist string (e.g. `"Read,Glob,Grep,Write,Edit"`). Ignore if meaningless for your backend. |
| `model` | optional model override from the goal header. |

### RunResult

```python
RunResult(
    text=...,          # the agent's final message
    raw=...,           # raw backend output, saved verbatim to session.json
    is_error=False,    # soft failure the harness should record, not crash on
    error_kind="",     # "" | "api" | "timeout"
    cost_usd=...,      # optional — feeds run_cost.json + the ledger
    usage={...},       # optional token telemetry
)
```

## The three failure lanes

Getting these right is most of the work:

1. **Soft API error** (`is_error=True, error_kind="api"`): rate limits,
   overloaded backends — anything worth retrying. The runner retries **once**
   with backoff, then records a FAILED run with the error text preserved.
2. **Timeout** (`is_error=True, error_kind="timeout"`): catch your
   subprocess/HTTP timeout and return this. Timeouts are recorded and **never
   retried** (the next attempt would likely burn the same budget).
3. **Hard crash** (`raise AdapterError(...)`): binary missing, unparseable
   protocol failure. The harness stops — there is nothing meaningful to record.

Rule of thumb: if a human operator would say "run it again", it's soft; if
they'd say "fix the environment", it's hard.

## Invariants your adapter must keep

- **Side-effect-free outside `cwd`** (and the provided `add_dirs`). The guard
  will catch violations in guarded dirs and fail the run — don't make it.
- **Don't interpret the result.** Return what the agent said; the harness
  decides success via verifiers. An adapter that "helpfully" retries until the
  agent claims success defeats the entire point of the product.
- **Keep the telemetry.** If your backend reports cost/usage, put it on the
  RunResult instead of dropping it — the ledger and PROOF.md are built from it.
  `result_from_envelope()` in `base.py` does this for JSON-envelope CLIs.

## Reference implementations

- `adapters/claude_code.py` (~90 lines) — a real subprocess adapter: binary
  discovery, prompt on stdin, JSON envelope parsing, `.env.local` overlay,
  soft-error taxonomy, graceful timeout. If your agent has a headless CLI,
  start by copying this.
- `adapters/mock.py` — a scriptable fake used by the entire test suite and the
  demo. Each queued response can create files, simulate errors/timeouts, and
  report costs. Write your adapter's tests against the same patterns.

## Distillation calls

The runner uses the same adapter for the second, **tool-less** distillation
call (`tools=""`, no `add_dirs`). If your backend cannot disable tools, make
the distill call to a plain completion endpoint instead — the only requirement
is text in, text out, with soft errors flagged (a soft-errored distill is
deliberately discarded rather than written to the learning pool).

## Checklist

- [ ] `run()` returns `RunResult` for every soft failure; raises `AdapterError`
      only for environment problems
- [ ] timeout → `error_kind="timeout"`, retryable API errors → `"api"`
- [ ] `cost_usd`/`usage` populated when the backend provides them
- [ ] raw output preserved in `raw`
- [ ] unit tests: happy path, soft error, timeout (see `tests/test_adapters.py`)
