"""Fail-before / pass-after check for a proof run's regression tests.

    python proofs/recheck.py --root . --repo proofs/targets/sqlite-utils \
        --python proofs/targets/venv/Scripts/python.exe

The default verifier pair proves the suite is green and the diff stayed inside
its blast radius. Neither proves the reported bug was fixed — a pre-existing
suite passes on unfixed code too. This closes that gap for the one claim the
goals actually asked for: "a test that fails before your fix and passes after".

For each run it replays the diff twice against a clean baseline worktree:

    tests only  -> the changed test files MUST fail (they need the fix)
    full diff   -> the same files MUST pass

A test file that passes with the fix removed is not testing the fix. That run
gets NOT-PROVEN: the harness verdict still stands, but the regression test
carries no evidence about the bug.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TEST_PATH_RE = re.compile(r"^\+\+\+ b/(tests/.+)$", re.MULTILINE)


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def test_files(patch_text):
    """Test files the diff touches — the only ones whose before/after matters."""
    return sorted(set(TEST_PATH_RE.findall(patch_text)))


def reset(worktree):
    run(["git", "checkout", "-f", "--", "."], worktree)
    run(["git", "clean", "-fdq"], worktree)


def pytest_on(python, worktree, files):
    r = run([python, "-m", "pytest", "-q", "--no-header", "-p", "no:randomly",
             *files], worktree)
    tail = [ln for ln in r.stdout.strip().splitlines() if ln.strip()]
    return r.returncode, (tail[-1] if tail else "(no output)")


def check_run(run_dir, worktree, python):
    # absolute: git apply runs with cwd set to the worktree, not the harness root
    patch = (run_dir / "write_diff.patch").resolve()
    if not patch.exists():
        return {"run": run_dir.name, "result": "NO-DIFF"}
    text = patch.read_text(encoding="utf-8")
    files = test_files(text)
    if not files:
        return {"run": run_dir.name, "result": "NO-TESTS",
                "note": "diff touches no test file"}

    reset(worktree)
    applied = run(["git", "apply", "--include=tests/*", str(patch)], worktree)
    if applied.returncode != 0:
        return {"run": run_dir.name, "result": "APPLY-FAILED",
                "note": applied.stderr.strip()[:200]}
    before_code, before = pytest_on(python, worktree, files)

    reset(worktree)
    applied = run(["git", "apply", str(patch)], worktree)
    if applied.returncode != 0:
        return {"run": run_dir.name, "result": "APPLY-FAILED",
                "note": applied.stderr.strip()[:200]}
    after_code, after = pytest_on(python, worktree, files)

    if before_code != 0 and after_code == 0:
        result = "PROVEN"          # failed without the fix, passes with it
    elif before_code == 0:
        result = "NOT-PROVEN"      # test passes on unfixed code
    else:
        result = "STILL-FAILING"   # broken even with the fix
    return {"run": run_dir.name, "result": result, "files": files,
            "before": before, "after": after}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="harness root (runs/)")
    parser.add_argument("--repo", required=True, help="the target repo clone")
    parser.add_argument("--python", required=True, help="interpreter with the suite's deps")
    parser.add_argument("--worktree", required=True, help="scratch worktree path (created)")
    parser.add_argument("--base", default="main", help="baseline ref to replay against")
    args = parser.parse_args(argv)

    repo, worktree = Path(args.repo).resolve(), Path(args.worktree).resolve()
    if not worktree.exists():
        r = run(["git", "worktree", "add", "--detach", str(worktree), args.base], repo)
        if r.returncode != 0:
            print(f"worktree add failed: {r.stderr.strip()}", file=sys.stderr)
            return 1

    ledger = Path(args.root) / "runs" / "ledger.jsonl"
    ids = [json.loads(ln)["run_id"] for ln in
           ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]

    rows = []
    for rid in ids:
        run_dir = Path(args.root) / "runs" / rid
        row = check_run(run_dir, worktree, args.python)
        # stats.py joins this back in, so the finding lands in PROOF.md rather
        # than staying in whatever terminal happened to run the check
        if run_dir.exists():
            Path(run_dir, "recheck.json").write_text(
                json.dumps(row, indent=2), encoding="utf-8"
            )
        rows.append(row)
    for row in rows:
        print(f"{row['result']:14} {row['run'][:58]}")
        if row.get("before"):
            print(f"               without fix: {row['before']}")
            print(f"               with fix:    {row['after']}")
        if row.get("note"):
            print(f"               {row['note']}")
    proven = sum(1 for r in rows if r["result"] == "PROVEN")
    print(f"\n{proven}/{len(rows)} runs have a regression test that fails without the fix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
