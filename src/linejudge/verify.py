"""Verifier registry. A verifier is `fn(spec, cwd, run_dir) -> (passed, evidence)`
where `spec` is the opaque string from the goal header. Verifiers run OUTSIDE
the agent session, after it ends — the agent cannot see, game, or re-run them.

Spec formats are documented in docs/verifier-spec.md (the authoritative doc).
"""

import fnmatch
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

VERIFY_TIMEOUT = 600
HTTP_TIMEOUT = 30


def verify_command(spec, cwd, run_dir):
    r = subprocess.run(
        spec, shell=True, capture_output=True, text=True,
        cwd=str(cwd), timeout=VERIFY_TIMEOUT,
    )
    evidence = f"exit {r.returncode}\n--- stdout ---\n{r.stdout}--- stderr ---\n{r.stderr}"
    return r.returncode == 0, evidence


def verify_files_exist(spec, cwd, run_dir):
    lines, ok = [], True
    for rel in [p.strip() for p in spec.split(",") if p.strip()]:
        exists = (Path(cwd) / rel).exists()
        ok = ok and exists
        lines.append(f"{'OK   ' if exists else 'MISSING'} {rel}")
    return ok, "\n".join(lines) or "no paths given"


def _parse_unified_diff(text):
    """Return (changed file paths, changed line count) from a unified diff."""
    files, changed, minus_path = set(), 0, None
    for line in text.splitlines():
        if line.startswith("--- "):
            minus_path = line[4:].split("\t")[0].strip()
        elif line.startswith("+++ "):
            path = line[4:].split("\t")[0].strip()
            if path == "/dev/null":  # deletion: name it from the --- side
                path = minus_path or ""
            path = path[2:] if path[:2] in ("a/", "b/") else path
            if path and path != "/dev/null":
                files.add(path)
        elif line.startswith("+") and not line.startswith("+++"):
            changed += 1
        elif line.startswith("-") and not line.startswith("---"):
            changed += 1
    return sorted(files), changed


def verify_diff_constraints(spec, cwd, run_dir):
    """Constrain the run's captured write diff (blast-radius as a verdict).
    spec tokens: max_files=N max_lines=N allow=glob,glob deny=glob,glob.
    Only meaningful for write-repo goals — fails when no diff was captured."""
    diff_path = Path(run_dir) / "write_diff.patch"
    if not diff_path.exists():
        return False, "no write_diff.patch captured (not a write run, or agent changed nothing)"
    limits = dict(tok.split("=", 1) for tok in spec.split() if "=" in tok)
    files, changed = _parse_unified_diff(diff_path.read_text(encoding="utf-8"))

    violations = []
    if "max_files" in limits and len(files) > int(limits["max_files"]):
        violations.append(f"{len(files)} files changed > max_files={limits['max_files']}")
    if "max_lines" in limits and changed > int(limits["max_lines"]):
        violations.append(f"{changed} lines changed > max_lines={limits['max_lines']}")
    allow = [g for g in limits.get("allow", "").split(",") if g]
    deny = [g for g in limits.get("deny", "").split(",") if g]
    for f in files:
        if allow and not any(fnmatch.fnmatch(f, g) for g in allow):
            violations.append(f"{f} outside allowlist {allow}")
        if any(fnmatch.fnmatch(f, g) for g in deny):
            violations.append(f"{f} matches denylist {deny}")

    evidence = (
        f"{len(files)} files / {changed} changed lines: {', '.join(files)}\n"
        + ("\n".join(violations) if violations else "all constraints satisfied")
    )
    return not violations, evidence


def verify_http_check(spec, cwd, run_dir):
    """spec: URL [expect=STATUS] [contains=SUBSTR]. SUBSTR cannot contain
    spaces (spec tokens are space-separated)."""
    tokens = spec.split()
    if not tokens:
        return False, "no URL given"
    url, opts = tokens[0], dict(t.split("=", 1) for t in tokens[1:] if "=" in t)
    expect = int(opts.get("expect", 200))
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:
            status, body = resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:  # non-2xx is still a checkable answer
        status, body = exc.code, exc.read().decode("utf-8", "replace")
    except OSError as exc:
        return False, f"request failed: {exc}"
    evidence = f"GET {url} -> {status} ({len(body)} bytes)"
    if status != expect:
        return False, f"{evidence}; expected {expect}"
    if "contains" in opts and opts["contains"] not in body:
        return False, f"{evidence}; body does not contain {opts['contains']!r}"
    return True, evidence


REGISTRY = {
    "command": verify_command,
    "files_exist": verify_files_exist,
    "diff_constraints": verify_diff_constraints,
    "http_check": verify_http_check,
}


def run_verifiers(verifiers, cwd, run_dir):
    """Run every (kind, spec) pair, write verdict.json, return the verdict dict.
    A verifier that crashes or an unknown kind is a FAILED verdict entry, never
    a crashed run — the harness must always deliver a recorded verdict."""
    entries = []
    for kind, spec in verifiers:
        fn = REGISTRY.get(kind)
        started = time.monotonic()
        if fn is None:
            passed, evidence = False, f"unknown verifier kind: {kind!r}"
        else:
            try:
                passed, evidence = fn(spec, cwd, run_dir)
            except Exception as exc:
                passed, evidence = False, f"verifier raised: {exc!r}"
        entries.append({
            "kind": kind,
            "spec": spec,
            "passed": passed,
            "evidence": evidence[-8000:],
            "duration_secs": round(time.monotonic() - started, 1),
        })
    verdict = {
        "passed": all(e["passed"] for e in entries),
        "verifiers": entries,
    }
    Path(run_dir, "verdict.json").write_text(
        json.dumps(verdict, indent=2), encoding="utf-8"
    )
    return verdict
