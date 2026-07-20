"""Proof harness tests: goal generation from canned issue JSON, PROOF.md
rendering, and the full mock demo pipeline. No gh calls, no API spend."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROOFS = Path(__file__).resolve().parent.parent / "proofs"
sys.path.insert(0, str(PROOFS))

import demo  # noqa: E402
import generate  # noqa: E402
import stats  # noqa: E402

from linejudge.goal import load_goal  # noqa: E402

FIXTURE = PROOFS / "fixtures" / "issues.json"


class TmpDirTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)


class GenerateTests(TmpDirTestCase):
    def test_fixture_issues_become_loadable_goals(self):
        issues = json.loads(FIXTURE.read_text(encoding="utf-8"))
        paths = generate.write_goals(
            issues, self.tmp, "example/widget",
            verifiers=["files_exist: done.txt", "command: echo ok"],
        )
        self.assertEqual(len(paths), 3)
        goal = load_goal(paths[0])
        self.assertEqual(goal.name, "issue-101-config-loader-crashes-on-empty-yaml-file")
        self.assertIn("proof", goal.tags)
        self.assertIn("example/widget", goal.tags)
        self.assertIn("bug", goal.tags)
        self.assertEqual(goal.verifiers,
                         [("files_exist", "done.txt"), ("command", "echo ok")])
        self.assertIn("Config loader crashes", goal.body)
        self.assertIn("issues/101", goal.body)

    def test_body_with_dashes_does_not_break_header(self):
        # fixture issue 101 contains a literal "---" in its markdown body
        issues = json.loads(FIXTURE.read_text(encoding="utf-8"))
        goal = load_goal(generate.write_goals([issues[0]], self.tmp, "r")[0])
        self.assertIn("Expected: defaults applied", goal.body)

    def test_hostile_title_and_labels_sanitized(self):
        issue = {"number": 7, "title": "Fix: the thing!! (URGENT)  ",
                 "labels": [{"name": "bad: label"}, {"name": "ok"}],
                 "body": ""}
        goal = load_goal(generate.write_goals([issue], self.tmp, "o/r")[0])
        self.assertEqual(goal.name, "issue-7-fix-the-thing-urgent")
        self.assertIn("bad- label", goal.tags)
        self.assertIn("ok", goal.tags)

    def test_empty_body_placeholder(self):
        issue = {"number": 8, "title": "empty", "labels": [], "body": None}
        goal = load_goal(generate.write_goals([issue], self.tmp, "o/r")[0])
        self.assertIn("(no issue body)", goal.body)


class StatsTests(TmpDirTestCase):
    def _seed_run(self, run_id, goal, status, cost, passed=None, verifiers=0):
        d = self.tmp / "runs" / run_id
        d.mkdir(parents=True)
        (d / "outcome.json").write_text(json.dumps(
            {"run_id": run_id, "status": status, "failures": []}), encoding="utf-8")
        if verifiers:
            (d / "verdict.json").write_text(json.dumps({
                "passed": passed,
                "verifiers": [{"kind": "command", "spec": "x",
                               "passed": passed, "evidence": ""}] * verifiers,
            }), encoding="utf-8")
        with open(self.tmp / "runs" / "ledger.jsonl", "a",
                  encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"run_id": run_id, "goal": goal, "tags": [],
                                "status": status, "total_cost_usd": cost,
                                "num_calls": 2}) + "\n")

    def test_render_totals_and_claim_vs_verdict(self):
        self._seed_run("r1", "g1", "SUCCESS", 0.04, passed=True, verifiers=1)
        self._seed_run("r2", "g2", "FAILED", 0.03, passed=False, verifiers=2)
        self._seed_run("r3", "g3", "SUCCESS", 0.02)  # no verifiers
        text = stats.render(stats.collect(self.tmp))
        self.assertIn("**Tasks run:** 3", text)
        self.assertIn("**Runs succeeded:** 2/3", text)
        self.assertIn("**Independently verified pass:** 1/2 (50%)", text)
        self.assertIn("**Total cost:** $0.0900 ($0.0300/task)", text)
        self.assertIn("| r1 | g1 | SUCCESS | PASS (1) | $0.0400 |", text)
        self.assertIn("| r2 | g2 | FAILED | FAIL (2) | $0.0300 |", text)
        self.assertIn("| r3 | g3 | SUCCESS | no verifiers (0) | $0.0200 |", text)

    def test_empty_root_renders_gracefully(self):
        self.assertIn("No runs recorded", stats.render(stats.collect(self.tmp)))

    def test_main_writes_proof_md(self):
        self._seed_run("r1", "g1", "SUCCESS", 0.01, passed=True, verifiers=1)
        stats.main(["--root", str(self.tmp)])
        self.assertTrue((self.tmp / "PROOF.md").exists())


class DemoTests(TmpDirTestCase):
    def test_demo_end_to_end_liar_caught(self):
        demo.main(["--root", str(self.tmp)])
        proof = (self.tmp / "PROOF.md").read_text(encoding="utf-8")
        self.assertIn("**Tasks run:** 3", proof)
        # issue-102's agent claimed success but wrote no done.txt: the run is
        # FAILED because the harness verdict, not the claim, decides status
        self.assertIn("**Runs succeeded:** 2/3", proof)
        self.assertIn("**Independently verified pass:** 2/3 (67%)", proof)
        self.assertEqual(proof.count("| FAIL (1)"), 1)
        run_dirs = [d for d in (self.tmp / "runs").iterdir() if d.is_dir()]
        self.assertEqual(len(run_dirs), 3)
        liar = [d for d in run_dirs if "issue-102" in d.name][0]
        outcome = json.loads((liar / "outcome.json").read_text(encoding="utf-8"))
        self.assertEqual(outcome["status"], "FAILED")
        self.assertIn("verifier failed: files_exist: done.txt", outcome["failures"])


if __name__ == "__main__":
    unittest.main()
