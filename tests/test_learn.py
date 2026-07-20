import tempfile
import types
import unittest
from pathlib import Path

from linejudge import learn
from linejudge.adapters.mock import MockAdapter


def make_report(learn_dir, run_id, tags, body="## What worked\n- thing\n",
                goal="demo", status="SUCCESS"):
    learn_dir.mkdir(parents=True, exist_ok=True)
    (learn_dir / f"{run_id}.md").write_text(
        f"---\ngoal: {goal}\nstatus: {status}\ntags: {tags}\nrun_id: {run_id}\n---\n\n"
        f"{body}",
        encoding="utf-8", newline="\n",
    )


class LearnTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.learn_dir = self.root / "learnings"


class SelectReportsTests(LearnTestCase):
    def test_tag_overlap_beats_recency(self):
        make_report(self.learn_dir, "20260101-000000-old", "python, api")
        make_report(self.learn_dir, "20260301-000000-new", "frontend")
        selected = learn.select_reports(self.root, ["python"], top_n=1)
        self.assertEqual(selected[0][1], "20260101-000000-old")

    def test_recency_breaks_ties(self):
        make_report(self.learn_dir, "20260101-000000-a", "python")
        make_report(self.learn_dir, "20260301-000000-b", "python")
        selected = learn.select_reports(self.root, ["python"], top_n=2)
        self.assertEqual([s[1] for s in selected],
                         ["20260301-000000-b", "20260101-000000-a"])

    def test_top_n_caps_the_pool(self):
        for i in range(5):
            make_report(self.learn_dir, f"2026010{i}-000000-r{i}", "python")
        self.assertEqual(len(learn.select_reports(self.root, ["python"], top_n=3)), 3)

    def test_untagged_goal_falls_back_to_recency(self):
        make_report(self.learn_dir, "20260101-000000-a", "python")
        make_report(self.learn_dir, "20260301-000000-b", "frontend")
        selected = learn.select_reports(self.root, [], top_n=1)
        self.assertEqual(selected[0][1], "20260301-000000-b")

    def test_latest_md_is_not_a_pool_member(self):
        self.learn_dir.mkdir()
        (self.learn_dir / "latest.md").write_text("seed", encoding="utf-8")
        self.assertEqual(learn.select_reports(self.root, []), [])

    def test_missing_dir_is_empty_pool(self):
        self.assertEqual(learn.select_reports(self.root, ["python"]), [])


class LoadPreambleTests(LearnTestCase):
    def goal(self, tags=()):
        return types.SimpleNamespace(tags=list(tags))

    def test_selected_bodies_without_frontmatter(self):
        make_report(self.learn_dir, "20260101-000000-a", "python",
                    body="USE THE FROBNICATOR\n")
        preamble = learn.load_preamble(self.root, self.goal(["python"]))
        self.assertIn("USE THE FROBNICATOR", preamble)
        self.assertIn("### demo — SUCCESS (20260101-000000-a)", preamble)
        self.assertNotIn("---", preamble)  # frontmatter stripped

    def test_falls_back_to_latest_md_when_pool_empty(self):
        self.learn_dir.mkdir()
        (self.learn_dir / "latest.md").write_text("HAND-WRITTEN SEED", encoding="utf-8")
        self.assertEqual(learn.load_preamble(self.root, self.goal()), "HAND-WRITTEN SEED")

    def test_empty_store_gives_empty_preamble(self):
        self.assertEqual(learn.load_preamble(self.root, self.goal(["python"])), "")


class PoisoningTests(LearnTestCase):
    def test_soft_errored_distill_never_enters_the_pool(self):
        goal = types.SimpleNamespace(name="demo", tags=["python"], model=None,
                                     agent_notes=[], read_dirs=[], body="x")
        adapter = MockAdapter([
            {"text": "API Error: overloaded", "is_error": True, "error_kind": "api"},
        ])
        result = learn.distill(adapter, self.root, "20260101-000000-demo", goal,
                               "SUCCESS", [], "report", "final")
        self.assertTrue(result.is_error)
        self.assertEqual(learn.select_reports(self.root, ["python"]), [])
        self.assertEqual(learn.load_preamble(self.root, goal), "")

    def test_clean_distill_is_retrievable_next_run(self):
        goal = types.SimpleNamespace(name="demo", tags=["python"], model=None,
                                     agent_notes=[], read_dirs=[], body="x")
        adapter = MockAdapter([{"text": "## What worked\n- everything\n"}])
        learn.distill(adapter, self.root, "20260101-000000-demo", goal,
                      "SUCCESS", [], "report", "final")
        selected = learn.select_reports(self.root, ["python"])
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0][0], 1)  # tag overlap counted
        self.assertIn("everything", selected[0][3])
        # back-compat copy still maintained
        self.assertTrue((self.learn_dir / "latest.md").exists())


if __name__ == "__main__":
    unittest.main()
