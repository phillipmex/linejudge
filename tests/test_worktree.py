import subprocess
import tempfile
import unittest
from pathlib import Path

from linejudge import worktree


def make_repo(base, name="target"):
    repo = Path(base) / name
    repo.mkdir()
    (repo / "app.py").write_text("print('v1')\n", encoding="utf-8", newline="\n")
    (repo / ".gitignore").write_text("runtime/\n", encoding="utf-8", newline="\n")
    for cmd in (
        ["git", "init", "-q"],
        ["git", "add", "."],
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
    ):
        subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
    return repo


class WorktreeTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.repo = make_repo(self.base)
        self.run_dir = self.base / "runs" / "run1"
        self.run_dir.mkdir(parents=True)

    def branches(self):
        out = subprocess.run(
            ["git", "-C", str(self.repo), "branch", "--format=%(refname:short)"],
            capture_output=True, text=True,
        ).stdout
        return {b.strip() for b in out.splitlines() if b.strip()}


class CreateTests(WorktreeTestCase):
    def test_create_makes_branch_worktree_and_cleanup_json(self):
        wt, branch = worktree.create(self.repo, "run1", self.run_dir)
        self.assertEqual(branch, "linejudge/run1")
        self.assertIn("linejudge/run1", self.branches())
        self.assertTrue((wt / "app.py").exists())
        self.assertTrue((self.run_dir / "cleanup.json").exists())

    def test_link_dirs_bring_untracked_runtime_into_worktree(self):
        runtime = self.repo / "runtime"
        runtime.mkdir()
        (runtime / "data.bin").write_text("payload", encoding="utf-8")
        wt, _ = worktree.create(self.repo, "run1", self.run_dir, link_dirs=["runtime"])
        # worktrees only contain tracked files — the link is the only way in
        self.assertEqual((wt / "runtime" / "data.bin").read_text(encoding="utf-8"), "payload")


class CaptureAndCommitTests(WorktreeTestCase):
    def test_diff_includes_new_files_and_edits(self):
        wt, _ = worktree.create(self.repo, "run1", self.run_dir)
        (wt / "app.py").write_text("print('v2')\n", encoding="utf-8", newline="\n")
        (wt / "new.py").write_text("x = 1\n", encoding="utf-8", newline="\n")
        diff, committed = worktree.capture_and_commit(wt, self.run_dir, "demo", "run1")
        self.assertTrue(committed)
        # an unstaged `git diff` would miss created files entirely
        self.assertIn("new.py", diff)
        self.assertIn("v2", diff)
        patch = (self.run_dir / "write_diff.patch").read_bytes()
        self.assertNotIn(b"\r\n", patch)  # CRLF would corrupt `git apply`

    def test_no_changes_means_no_commit_and_empty_patch(self):
        wt, _ = worktree.create(self.repo, "run1", self.run_dir)
        diff, committed = worktree.capture_and_commit(wt, self.run_dir, "demo", "run1")
        self.assertFalse(committed)
        self.assertEqual(diff.strip(), "")

    def test_committed_branch_survives_cleanup_as_the_record(self):
        wt, branch = worktree.create(self.repo, "run1", self.run_dir)
        (wt / "app.py").write_text("print('v2')\n", encoding="utf-8", newline="\n")
        worktree.capture_and_commit(wt, self.run_dir, "demo", "run1")
        problems = worktree.cleanup(self.repo, wt, [])
        self.assertEqual(problems, [])
        self.assertFalse(wt.exists())
        self.assertIn(branch, self.branches())
        show = subprocess.run(
            ["git", "-C", str(self.repo), "show", f"{branch}:app.py"],
            capture_output=True, text=True,
        ).stdout
        self.assertIn("v2", show)


class CleanupTests(WorktreeTestCase):
    def test_cleanup_unlinks_without_touching_live_dir(self):
        runtime = self.repo / "runtime"
        runtime.mkdir()
        (runtime / "data.bin").write_text("payload", encoding="utf-8")
        wt, _ = worktree.create(self.repo, "run1", self.run_dir, link_dirs=["runtime"])
        problems, note = worktree.cleanup_from_run_dir(self.run_dir)
        self.assertEqual(problems, [])
        self.assertEqual(note, "")
        self.assertFalse(wt.exists())
        # B-005/B-006: the live target must survive the teardown intact
        self.assertEqual((runtime / "data.bin").read_text(encoding="utf-8"), "payload")
        self.assertFalse((self.run_dir / "cleanup.json").exists())

    def test_cleanup_without_metadata_reports_note(self):
        problems, note = worktree.cleanup_from_run_dir(self.run_dir)
        self.assertEqual(problems, [])
        self.assertIn("no cleanup.json", note)

    def test_unlink_dir_on_real_directory_removes_copy(self):
        d = self.base / "copydir"
        d.mkdir()
        (d / "f.txt").write_text("x", encoding="utf-8")
        self.assertTrue(worktree.unlink_dir(d))
        self.assertFalse(d.exists())


class StaleCheckTests(WorktreeTestCase):
    def _write_run(self, run_id):
        run_dir = self.base / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        wt, branch = worktree.create(self.repo, run_id, run_dir)
        (wt / "app.py").write_text("print('patched')\n", encoding="utf-8", newline="\n")
        worktree.capture_and_commit(wt, run_dir, "demo", run_id)
        worktree.cleanup(self.repo, wt, [])
        return branch

    def test_fresh_diff_is_ok(self):
        self._write_run("run1")
        results = worktree.check_stale(self.repo, self.base / "runs")
        self.assertEqual(results, [("linejudge/run1", "OK", "")])

    def test_drifted_repo_flags_stale(self):
        self._write_run("run1")
        (self.repo / "app.py").write_text("print('v3-drift')\n", encoding="utf-8", newline="\n")
        subprocess.run(
            ["git", "-C", str(self.repo), "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-qam", "drift"],
            check=True, capture_output=True,
        )
        results = worktree.check_stale(self.repo, self.base / "runs")
        self.assertEqual(results[0][:2], ("linejudge/run1", "STALE"))
        self.assertTrue(results[0][2])  # git's conflict text kept as detail

    def test_branch_without_diff_is_no_diff(self):
        run_dir = self.base / "runs" / "run2"
        run_dir.mkdir(parents=True)
        wt, _ = worktree.create(self.repo, "run2", run_dir)
        worktree.cleanup(self.repo, wt, [])
        (run_dir / "write_diff.patch").unlink(missing_ok=True)
        results = worktree.check_stale(self.repo, self.base / "runs")
        self.assertEqual(results[0][:2], ("linejudge/run2", "NO-DIFF"))


if __name__ == "__main__":
    unittest.main()
