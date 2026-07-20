"""Claude Code headless adapter (`claude -p`).

Billing modes, chosen by environment:
- API key: set ANTHROPIC_API_KEY (directly or via <root>/.env.local) — required
  for any commercial/automated use.
- Config dir: set CLAUDE_CONFIG_DIR to a separately-logged-in config directory
  to bill a specific account for interactive/personal use.
"""

import json
import os
import shutil
import subprocess

from linejudge.adapters.base import AdapterError, AgentAdapter, RunResult, result_from_envelope


def find_binary():
    for name in ("claude", "claude.cmd"):
        path = shutil.which(name)
        if path:
            return path
    raise AdapterError("claude CLI not found on PATH")


def load_env(root=None):
    """Process env overlaid with <root>/.env.local (KEY=VALUE lines, gitignored)."""
    env = dict(os.environ)
    if root is None:
        return env
    env_file = root / ".env.local"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip()
    return env


class ClaudeCodeAdapter(AgentAdapter):
    name = "claude-code"

    def __init__(self, root=None, binary=None):
        self.root = root
        self._binary = binary

    @property
    def binary(self):
        if self._binary is None:
            self._binary = find_binary()
        return self._binary

    def run(self, prompt, cwd, timeout, add_dirs=(), tools="", model=None):
        cmd = [self.binary, "-p", "--output-format", "json"]
        if model:
            cmd += ["--model", model]
        if tools:
            cmd += ["--allowedTools", tools]
        for d in add_dirs:
            cmd += ["--add-dir", str(d)]
        try:
            r = subprocess.run(
                cmd, input=prompt, capture_output=True, text=True,
                encoding="utf-8", cwd=str(cwd), timeout=timeout,
                env=load_env(self.root),
            )
        except subprocess.TimeoutExpired:
            # A too-long run is a recordable failure, not a harness crash — the
            # run dir keeps its prompt and partial artifacts for diagnosis.
            return RunResult(
                text=f"(agent run timed out after {timeout}s)",
                is_error=True, error_kind="timeout",
            )
        if r.returncode != 0:
            # claude -p can exit non-zero yet still emit a valid JSON envelope
            # describing a soft API-level error (e.g. rate limit) rather than a
            # hard crash. Record it instead of raising so diagnostics survive.
            try:
                env = json.loads(r.stdout)
                if env.get("is_error"):
                    return result_from_envelope(r.stdout, is_error=True)
            except json.JSONDecodeError:
                pass
            raise AdapterError(f"claude exited {r.returncode}: {r.stderr.strip()[:2000]}")
        return result_from_envelope(r.stdout)
