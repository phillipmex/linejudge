"""Scriptable fake adapter for tests and demos — no network, no billing.

Each scripted response is a dict:
    text          -> RunResult.text (default "done")
    is_error      -> soft error flag
    error_kind    -> "api" / "timeout"
    cost_usd, usage, num_turns -> telemetry passthrough
    files         -> {relpath: content} written into the call's cwd BEFORE
                     returning (how a fake agent "does work" — or lies by
                     claiming success while writing nothing)
    add_dir_files -> {relpath: content} written into the call's LAST add_dir
                     (the write worktree on write runs) — how a fake agent
                     edits the target repo
Responses are consumed in order; running past the script raises. Every call is
recorded on .calls for assertions.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from linejudge.adapters.base import AgentAdapter, RunResult


@dataclass
class MockCall:
    prompt: str
    cwd: str
    timeout: int
    add_dirs: tuple
    tools: str
    model: str | None = None


class MockAdapter(AgentAdapter):
    name = "mock"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def run(self, prompt, cwd, timeout, add_dirs=(), tools="", model=None):
        self.calls.append(MockCall(prompt, str(cwd), timeout, tuple(add_dirs), tools, model))
        if not self.responses:
            raise AssertionError("MockAdapter ran out of scripted responses")
        spec = self.responses.pop(0)

        for rel, content in (spec.get("files") or {}).items():
            path = Path(cwd) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        if spec.get("add_dir_files"):
            base = Path(add_dirs[-1]) if add_dirs else Path(cwd)
            for rel, content in spec["add_dir_files"].items():
                path = base / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

        usage = spec.get("usage", {"input_tokens": 100, "output_tokens": 50})
        cost = spec.get("cost_usd", 0.01)
        is_error = spec.get("is_error", False)
        raw = json.dumps({
            "type": "result", "is_error": is_error,
            "result": spec.get("text", "done"),
            "total_cost_usd": cost, "usage": usage,
            "num_turns": spec.get("num_turns", 1), "session_id": "mock-session",
        })
        return RunResult(
            text=spec.get("text", "done"), raw=raw,
            is_error=is_error, error_kind=spec.get("error_kind", "api" if is_error else ""),
            cost_usd=cost, usage=usage,
            num_turns=spec.get("num_turns", 1), session_id="mock-session",
        )
