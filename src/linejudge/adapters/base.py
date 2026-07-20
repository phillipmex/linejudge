"""Agent adapter contract.

An adapter runs one prompt against one agent backend and returns a RunResult.
Hard crashes (backend missing, unparseable failure) raise AdapterError; soft
failures the harness should record rather than die on (API rate limits,
timeouts) come back as RunResult(is_error=True, error_kind=...).
"""

import json
from dataclasses import dataclass, field


class AdapterError(RuntimeError):
    """Unrecoverable adapter failure — the run cannot be recorded normally."""


@dataclass
class RunResult:
    text: str
    raw: str = ""
    is_error: bool = False
    error_kind: str = ""  # "" | "api" | "timeout"
    cost_usd: float | None = None
    usage: dict = field(default_factory=dict)
    duration_ms: int | None = None
    num_turns: int | None = None
    session_id: str | None = None


class AgentAdapter:
    """Protocol. Implementations must be side-effect-free outside `cwd`."""

    name = "base"

    def run(self, prompt, cwd, timeout, add_dirs=(), tools="", model=None):
        raise NotImplementedError


def result_from_envelope(raw_stdout, is_error=False):
    """Build a RunResult from an agent CLI's JSON result envelope, keeping the
    telemetry (cost, tokens, turns) that a plain text read would discard. Falls
    back to treating non-JSON stdout as the result text."""
    try:
        env = json.loads(raw_stdout)
    except json.JSONDecodeError:
        return RunResult(text=raw_stdout, raw=raw_stdout, is_error=is_error)
    return RunResult(
        text=env.get("result", ""),
        raw=raw_stdout,
        is_error=bool(env.get("is_error", is_error)),
        error_kind="api" if env.get("is_error", is_error) else "",
        cost_usd=env.get("total_cost_usd"),
        usage=env.get("usage") or {},
        duration_ms=env.get("duration_ms"),
        num_turns=env.get("num_turns"),
        session_id=env.get("session_id"),
    )
