"""Goal files: a `---` fenced header of simple `key: value` / `- item` lines,
then the prompt body.

    ---
    name: my-goal
    tags:
      - my-project
    read_dirs:
      - /path/to/guarded-repo
    write_repo: /path/to/repo-getting-a-write-cycle  # optional
    write_link_dirs:  # optional, only with write_repo
      - node_modules
    model: claude-sonnet-5  # optional adapter model override
    verifiers:
      - command: python -m pytest -q
      - files_exist: REPORT.md
    verify: <shell command>  # legacy sugar for a single command verifier
    timeout_secs: 1800
    agent_notes:
      - <extra per-goal reminder injected into the prompt>
    ---
    <prompt body>

The header is deliberately not YAML — no nesting, no quoting rules, nothing to
mis-parse. Verifier list items are `kind: spec` where `spec` is an opaque string
each verifier parses itself.
"""

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TIMEOUT = 1800


def parse_header(text):
    """Split the `---` fenced header into a config dict + prompt body."""
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("goal file needs a --- fenced header")
    cfg, key = {}, None
    for line in parts[1].splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and key:
            cfg.setdefault(key, []).append(stripped[2:].strip())
        elif ":" in stripped:
            key, _, val = stripped.partition(":")
            key, val = key.strip(), val.strip()
            if val:
                cfg[key] = val
    return cfg, parts[2].strip()


@dataclass
class Goal:
    name: str
    body: str
    read_dirs: list = field(default_factory=list)
    write_repo: Path | None = None
    write_link_dirs: list = field(default_factory=list)
    verifiers: list = field(default_factory=list)  # (kind, spec) tuples
    tags: list = field(default_factory=list)
    model: str | None = None
    agent_notes: list = field(default_factory=list)
    timeout_secs: int = DEFAULT_TIMEOUT


def _as_list(cfg, key):
    val = cfg.get(key, [])
    return [val] if isinstance(val, str) else list(val)


def load_goal(path):
    path = Path(path)
    cfg, body = parse_header(path.read_text(encoding="utf-8"))

    verifiers = []
    if cfg.get("verify"):  # legacy single-command form
        verifiers.append(("command", cfg["verify"]))
    for item in _as_list(cfg, "verifiers"):
        kind, _, spec = item.partition(":")
        verifiers.append((kind.strip(), spec.strip()))

    return Goal(
        name=cfg.get("name", path.stem),
        body=body,
        read_dirs=[Path(d) for d in _as_list(cfg, "read_dirs")],
        write_repo=Path(cfg["write_repo"]) if cfg.get("write_repo") else None,
        write_link_dirs=_as_list(cfg, "write_link_dirs"),
        verifiers=verifiers,
        tags=_as_list(cfg, "tags"),
        model=cfg.get("model"),
        agent_notes=_as_list(cfg, "agent_notes"),
        timeout_secs=int(cfg.get("timeout_secs", DEFAULT_TIMEOUT)),
    )
