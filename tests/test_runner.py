import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from linejudge.adapters.mock import MockAdapter
from linejudge.runner import run_goal

REPORT = "## Status\nSUCCESS\n\n## What I did\n- the task\n"
OK_RUN = {"text": "done", "files": {"REPORT.md": REPORT}}
DISTILL = {"text": "## What worked\n- everything\n## What failed\n- nothing\n"}


class RunnerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write_goal(self, header_extra="", body="Do the task."):
        path = self.root / "goal.md"
        path.write_text(f"---\nname: demo\n{header_extra}---\n{body}\n", encoding="utf-8")
        return path

    def run_mock(self, responses, header_extra=""):
        adapter = MockAdapter(responses)
        outcome = run_goal(
            self.write_goal(header_extra), self.root, adapter, retry_delay=0
        )
        return outcome, adapter


class HappyPathTests(RunnerTestCase):
    def test_full_artifact_trail(self):
        outcome, adapter = self.run_mock([OK_RUN, DISTILL])
        self.assertEqual(outcome.status, "SUCCESS")
        self.assertEqual(outcome.failures, [])
        for artifact in ("prompt.md", "session.json", "verdict.json",
                         "run_cost.json", "summary.md", "outcome.json"):
            self.assertTrue((outcome.run_dir / artifact).exists(), artifact)
        self.assertTrue((self.root / "learnings" / "latest.md").exists())
        ledger_lines = (self.root / "runs" / "ledger.jsonl").read_text().splitlines()
        self.assertEqual(len(ledger_lines), 1)
        self.assertEqual(json.loads(ledger_lines[0])["status"], "SUCCESS")
        cost = json.loads((outcome.run_dir / "run_cost.json").read_text())
        self.assertEqual(len(cost["calls"]), 2)  # execute + distill
        self.assertAlmostEqual(cost["total_cost_usd"], 0.02)

    def test_preamble_from_previous_learning_reaches_prompt(self):
        learn_dir = self.root / "learnings"
        learn_dir.mkdir()
        (learn_dir / "latest.md").write_text("USE THE FROBNICATOR", encoding="utf-8")
        _, adapter = self.run_mock([OK_RUN, DISTILL])
        self.assertIn("USE THE FROBNICATOR", adapter.calls[0].prompt)

    def test_dry_run_touches_nothing(self):
        adapter = MockAdapter([])
        outcome = run_goal(self.write_goal(), self.root, adapter, dry_run=True)
        self.assertEqual(outcome.status, "DRY-RUN")
        self.assertFalse((self.root / "runs").exists())
        self.assertEqual(adapter.calls, [])


class MultiVerifierIntegrationTests(RunnerTestCase):
    HEADER = (
        "verifiers:\n"
        "  - files_exist: hello.txt, REPORT.md\n"
        '  - command: python -c "assert open(\'hello.txt\').read() == \'hi\'"\n'
        "  - diff_constraints: max_files=1\n"
    )

    def test_mixed_verdict_records_every_verifier(self):
        run = {"text": "done", "files": {"REPORT.md": REPORT, "hello.txt": "hi"}}
        outcome, _ = self.run_mock([run, DISTILL], header_extra=self.HEADER)
        # read-only run captures no write diff, so diff_constraints must fail
        # while the other two pass — and the run fails on the AND.
        self.assertEqual(outcome.status, "FAILED")
        verdict = json.loads((outcome.run_dir / "verdict.json").read_text())
        self.assertFalse(verdict["passed"])
        by_kind = {e["kind"]: e for e in verdict["verifiers"]}
        self.assertEqual(len(verdict["verifiers"]), 3)
        self.assertTrue(by_kind["files_exist"]["passed"])
        self.assertTrue(by_kind["command"]["passed"])
        self.assertFalse(by_kind["diff_constraints"]["passed"])
        self.assertIn("no write_diff.patch", by_kind["diff_constraints"]["evidence"])

    def test_all_green_multi_verifier_run_succeeds(self):
        run = {"text": "done", "files": {"REPORT.md": REPORT, "hello.txt": "hi"}}
        outcome, _ = self.run_mock(
            [run, DISTILL],
            header_extra=(
                "verifiers:\n"
                "  - files_exist: hello.txt\n"
                '  - command: python -c "pass"\n'
            ),
        )
        self.assertEqual(outcome.status, "SUCCESS")
        verdict = json.loads((outcome.run_dir / "verdict.json").read_text())
        self.assertTrue(verdict["passed"])
        self.assertEqual([e["passed"] for e in verdict["verifiers"]], [True, True])


class FailureModeTests(RunnerTestCase):
    def test_lying_agent_missing_report_fails(self):
        outcome, _ = self.run_mock([{"text": "all done, definitely wrote it"}, DISTILL])
        self.assertEqual(outcome.status, "FAILED")
        self.assertTrue(any("REPORT.md" in f for f in outcome.failures))

    def test_soft_api_error_retries_once_then_succeeds(self):
        outcome, adapter = self.run_mock([
            {"text": "rate limited", "is_error": True, "error_kind": "api"},
            OK_RUN, DISTILL,
        ])
        self.assertEqual(outcome.status, "SUCCESS")
        self.assertEqual(len(adapter.calls), 3)
        cost = json.loads((outcome.run_dir / "run_cost.json").read_text())
        phases = [c["phase"] for c in cost["calls"]]
        self.assertEqual(phases, ["execute", "execute-retry", "distill"])

    def test_timeout_is_recorded_failure_without_retry(self):
        outcome, adapter = self.run_mock([
            {"text": "(timed out)", "is_error": True, "error_kind": "timeout"},
            DISTILL,
        ])
        self.assertEqual(outcome.status, "FAILED")
        self.assertEqual(len(adapter.calls), 2)  # no retry, distill still runs
        self.assertTrue(any("timeout" in f for f in outcome.failures))

    def test_verifier_failure_overrides_agent_claim(self):
        outcome, _ = self.run_mock(
            [OK_RUN, DISTILL],
            header_extra='verifiers:\n  - command: python -c "import sys; sys.exit(1)"\n',
        )
        self.assertEqual(outcome.status, "FAILED")
        verdict = json.loads((outcome.run_dir / "verdict.json").read_text())
        self.assertFalse(verdict["passed"])

    def test_poisoned_distill_never_reaches_latest(self):
        outcome, _ = self.run_mock([
            OK_RUN,
            {"text": "API Error: overloaded", "is_error": True, "error_kind": "api"},
        ])
        self.assertEqual(outcome.status, "SUCCESS")  # run itself was fine
        self.assertFalse((self.root / "learnings" / "latest.md").exists())
        cost = json.loads((outcome.run_dir / "run_cost.json").read_text())
        self.assertTrue(cost["calls"][-1]["is_error"])  # distill cost still ledgered

class GitRepoMixin:
    def _make_git_repo(self, name="guarded"):
        repo = self.root / name
        repo.mkdir()
        (repo / "keep.txt").write_text("original\n", encoding="utf-8")
        for cmd in (
            ["git", "init", "-q"],
            ["git", "add", "."],
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        ):
            subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
        return repo


class WriteFlowTests(RunnerTestCase, GitRepoMixin):
    def test_write_run_full_trail(self):
        repo = self._make_git_repo("target")
        run = {"text": "done", "files": {"REPORT.md": REPORT},
               "add_dir_files": {"keep.txt": "edited by agent\n"}}
        outcome, adapter = self.run_mock(
            [run, DISTILL],
            header_extra=(
                f"write_repo: {repo}\n"
                "verifiers:\n"
                "  - diff_constraints: max_files=1 allow=keep.txt\n"
            ),
        )
        self.assertEqual(outcome.status, "SUCCESS")
        # agent got Edit and the worktree as its last add_dir
        self.assertIn("Edit", adapter.calls[0].tools)
        wt = outcome.run_dir / "write_worktree"
        self.assertEqual(adapter.calls[0].add_dirs[-1], wt)
        self.assertIn(str(wt), adapter.calls[0].prompt)
        # diff captured (with the agent's edit), branch committed, cleanup armed
        diff = (outcome.run_dir / "write_diff.patch").read_text(encoding="utf-8")
        self.assertIn("edited by agent", diff)
        self.assertTrue((outcome.run_dir / "cleanup.json").exists())
        branches = subprocess.run(
            ["git", "-C", str(repo), "branch", "--format=%(refname:short)"],
            capture_output=True, text=True,
        ).stdout
        self.assertIn(f"linejudge/{outcome.run_id}", branches)
        # diff_constraints saw the patch end-to-end
        verdict = json.loads((outcome.run_dir / "verdict.json").read_text())
        self.assertTrue(verdict["passed"])
        # the change stayed in the worktree — live repo untouched
        self.assertEqual((repo / "keep.txt").read_text(encoding="utf-8"), "original\n")
        self.assertIn("linejudge cleanup", (outcome.run_dir / "summary.md").read_text())
        # REPORT.md must be in the workspace, not polluting the diff
        self.assertNotIn("REPORT.md", diff)

    def test_write_run_deny_verifier_catches_forbidden_edit(self):
        repo = self._make_git_repo("target")
        run = {"text": "done", "files": {"REPORT.md": REPORT},
               "add_dir_files": {"keep.txt": "edited\n"}}
        outcome, _ = self.run_mock(
            [run, DISTILL],
            header_extra=(
                f"write_repo: {repo}\n"
                "verifiers:\n  - diff_constraints: deny=keep.txt\n"
            ),
        )
        self.assertEqual(outcome.status, "FAILED")
        verdict = json.loads((outcome.run_dir / "verdict.json").read_text())
        self.assertFalse(verdict["passed"])


class GuardTests(RunnerTestCase, GitRepoMixin):

    def test_mutating_a_read_dir_trips_the_guard(self):
        repo = self._make_git_repo()
        # MockAdapter joins file keys onto cwd; an absolute path wins the join,
        # simulating an agent that escaped its workspace.
        naughty = {"text": "done", "files": {
            "REPORT.md": REPORT,
            str(repo / "keep.txt"): "tampered\n",
        }}
        outcome, _ = self.run_mock(
            [naughty, DISTILL], header_extra=f"read_dirs:\n  - {repo}\n"
        )
        self.assertEqual(outcome.status, "FAILED")
        self.assertTrue(any("READ-ONLY GUARD" in f for f in outcome.failures))
        diags = list(outcome.run_dir.glob("readonly_guard_diag_*.txt"))
        self.assertEqual(len(diags), 1)
        self.assertIn("keep.txt", diags[0].read_text(encoding="utf-8"))

    def test_untouched_read_dir_passes(self):
        repo = self._make_git_repo()
        outcome, _ = self.run_mock(
            [OK_RUN, DISTILL], header_extra=f"read_dirs:\n  - {repo}\n"
        )
        self.assertEqual(outcome.status, "SUCCESS")


if __name__ == "__main__":
    unittest.main()
