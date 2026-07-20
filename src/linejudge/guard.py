"""Blast-radius guard: snapshot guarded directories before a run and fail the
run on any unexpected mutation. Directories are read-only by *instruction* only
(the agent gets real filesystem access), so the guard is the enforcement.
"""

import subprocess
from pathlib import Path


def git_status(repo):
    # Pathspec "-- ." scopes the check to `repo` itself; without it, `-C <subdir>`
    # still reports status for the WHOLE enclosing repo, which false-trips the
    # guard on any unrelated change elsewhere in that repo.
    r = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--", "."],
        capture_output=True, text=True, timeout=60,
    )
    return r.stdout if r.returncode == 0 else f"<git status failed: {r.stderr.strip()}>"


def git_diff(repo):
    # Tracked-file changes only — untracked additions won't show here, but their
    # paths are already listed by the porcelain status captured alongside this.
    r = subprocess.run(
        ["git", "-C", str(repo), "diff", "--", "."],
        capture_output=True, text=True, timeout=60,
    )
    return r.stdout if r.returncode == 0 else f"<git diff failed: {r.stderr.strip()}>"


def snapshot(dirs):
    return {str(d): git_status(d) for d in dirs}


def check(before, run_dir):
    """Compare a fresh snapshot against `before`. For each tripped dir, write a
    diagnostic artifact and return a failure string. A trip is not proof of
    agent misbehavior (concurrent processes touch repos too) — the diagnostic
    exists so investigating is a Read, not a manual git session."""
    failures = []
    after = snapshot(before.keys())
    for d, was in before.items():
        if after[d] == was:
            continue
        diag_path = Path(run_dir) / f"readonly_guard_diag_{Path(d).name}.txt"
        diag_path.write_text(
            f"# READ-ONLY GUARD diagnostic for {d}\n\n"
            f"## git status --porcelain (before -> after)\n"
            f"--- before ---\n{was}\n--- after ---\n{after[d]}\n\n"
            f"## git diff (tracked-file changes only)\n{git_diff(d)}",
            encoding="utf-8",
        )
        failures.append(
            f"READ-ONLY GUARD TRIPPED: {d} changed during the run (diagnostic: {diag_path})"
        )
    return failures
