"""Write flow: each write-repo run gets an isolated `git worktree` on its own
branch `linejudge/<run_id>`. The agent works there; the harness captures the
diff, commits it to the branch (a real, checkout-able record — an uncommitted
branch would die with the worktree), and leaves merging to a human.

Untracked runtime dirs (deps, data) are absent from worktrees, so goals can
declare `write_link_dirs` to link them in: junction on Windows (no admin
needed), symlink on POSIX, copy as last resort. Links are reparse points, not
real directories — teardown must unlink them, never recurse into them (a
recursive remove would destroy the live target), which is why cleanup is a
harness command, never a printed instruction.
"""

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

BRANCH_PREFIX = "linejudge/"


def _git(repo, *args, check=False):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=check,
    )


def is_dir_link(path):
    """True for POSIX symlinks and Windows junctions/reparse points."""
    path = Path(path)
    if path.is_symlink():
        return True
    if os.name == "nt":
        try:
            st = os.lstat(path)
        except OSError:
            return False
        return bool(st.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    return False


def link_dir(src, dst):
    """Link `src` into the worktree at `dst`; returns the method used."""
    if os.name == "nt":
        r = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            return "junction"
    else:
        try:
            os.symlink(src, dst, target_is_directory=True)
            return "symlink"
        except OSError:
            pass
    shutil.copytree(src, dst)
    return "copy"


def unlink_dir(dst):
    """Remove a linked dir: links are unlinked in place (never recursed into),
    copies removed recursively. Returns True when `dst` is gone."""
    dst = Path(dst)
    if not dst.exists() and not dst.is_symlink():
        return True
    if dst.is_symlink():
        dst.unlink()
        return not dst.exists()
    if is_dir_link(dst):  # Windows junction
        try:
            os.rmdir(dst)  # removes the junction itself, not its target
        except OSError:
            pass
        if is_dir_link(dst):
            # rmdir can report success yet leave the junction in place — fall
            # back to a .NET reparse-point delete, then re-verify.
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-Item -Force -LiteralPath '{dst}').Delete()"],
                capture_output=True, text=True,
            )
        return not is_dir_link(dst) and not dst.exists()
    shutil.rmtree(dst, ignore_errors=True)
    return not dst.exists()


def create(write_repo, run_id, run_dir, link_dirs=()):
    """Add the worktree + branch, link runtime dirs, record cleanup.json.
    Returns (worktree_path, branch)."""
    write_repo, run_dir = Path(write_repo), Path(run_dir)
    branch = BRANCH_PREFIX + run_id
    worktree = run_dir / "write_worktree"
    _git(write_repo, "worktree", "add", "-b", branch, str(worktree), check=True)
    for rel in link_dirs:
        src, dst = write_repo / rel, worktree / rel
        if src.exists() and not dst.exists():
            link_dir(src, dst)
    (run_dir / "cleanup.json").write_text(json.dumps({
        "write_repo": str(write_repo),
        "write_worktree": str(worktree),
        "write_link_dirs": list(link_dirs),
    }, indent=2), encoding="utf-8", newline="\n")
    return worktree, branch


def capture_and_commit(worktree, run_dir, goal_name, run_id):
    """Stage everything, snapshot the staged diff, commit if non-empty.
    Staging first means new files appear in the diff (an unstaged `git diff`
    silently omits every file the agent created).
    Returns (diff_text, committed)."""
    _git(worktree, "add", "-A")
    diff = _git(worktree, "diff", "--cached").stdout
    # newline="\n" or Windows write_text() CRLFs the diff, corrupting it for
    # later `git apply`.
    Path(run_dir, "write_diff.patch").write_text(diff, encoding="utf-8", newline="\n")
    committed = False
    if diff.strip():
        r = _git(
            worktree, "-c", "user.email=harness@linejudge", "-c", "user.name=linejudge",
            "commit", "-m", f"linejudge: {goal_name} ({run_id})",
        )
        committed = r.returncode == 0
    return diff, committed


def cleanup(write_repo, worktree, link_dirs):
    """Tear down a write run: unlink every linked dir (verified), remove the
    worktree, confirm live targets survived. Returns problem strings (empty =
    clean). The branch is deliberately kept — it is the record of the run."""
    write_repo, worktree = Path(write_repo), Path(worktree)
    problems = []
    for rel in link_dirs:
        if not unlink_dir(worktree / rel):
            problems.append(f"FAILED to unlink (still linked): {worktree / rel}")
    if problems:
        return problems  # never remove a worktree with a link still in place

    listed = _git(write_repo, "worktree", "list", "--porcelain").stdout
    git_error = None
    if worktree.as_posix() in listed:
        r = _git(write_repo, "worktree", "remove", "--force", str(worktree))
        if r.returncode != 0:
            git_error = r.stderr.strip()
    # `worktree remove` can deregister yet leave the dir behind on a transient
    # Windows file lock, wedging every retry with "not a working tree" — sweep
    # any leftover directly before treating the git error as fatal.
    if worktree.exists():
        try:
            shutil.rmtree(worktree)
        except OSError as exc:
            msg = f"leftover dir removal failed: {exc}"
            problems.append(f"git worktree remove failed: {git_error}; {msg}"
                            if git_error else msg)
    for rel in link_dirs:
        src = write_repo / rel
        if not src.exists() or not any(src.iterdir()):
            problems.append(f"POST-CLEANUP CHECK FAILED: live {src} is missing or empty")
    return problems


def cleanup_from_run_dir(run_dir):
    """Cleanup driven by the run's cleanup.json; returns (problems, note)."""
    meta_path = Path(run_dir) / "cleanup.json"
    if not meta_path.exists():
        return [], "no cleanup.json (not a write run, or already cleaned up)"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    problems = cleanup(meta["write_repo"], meta["write_worktree"], meta["write_link_dirs"])
    if not problems:
        meta_path.unlink()
    return problems, ""


def check_stale(write_repo, runs_dir):
    """Sweep every linejudge/* branch and check whether its captured diff still
    applies cleanly to the repo's current state. Returns (branch, state,
    detail) tuples, state OK / STALE / NO-DIFF. Read-only. Plain `git apply
    --check` (no --3way): a 3-way fallback can silently auto-merge drift via
    the object database — hiding exactly the conflicts this check exists to
    catch."""
    listed = _git(
        write_repo, "branch", "--list", BRANCH_PREFIX + "*",
        "--format=%(refname:short)",
    ).stdout
    results = []
    for branch in sorted(b.strip() for b in listed.splitlines() if b.strip()):
        run_id = branch.split(BRANCH_PREFIX, 1)[1]
        diff_path = Path(runs_dir) / run_id / "write_diff.patch"
        if not diff_path.exists() or not diff_path.read_text(encoding="utf-8").strip():
            results.append((branch, "NO-DIFF", f"missing or empty {diff_path}"))
            continue
        r = _git(write_repo, "apply", "--check", str(diff_path.resolve()))
        if r.returncode == 0:
            results.append((branch, "OK", ""))
        else:
            results.append((branch, "STALE", r.stderr.strip()[:300]))
    return results
