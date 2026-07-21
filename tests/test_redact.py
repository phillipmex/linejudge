import json
import tempfile
import unittest
from pathlib import Path

from linejudge import redact
from linejudge.adapters.mock import MockAdapter
from linejudge.runner import run_goal

REPORT = "## Status\nSUCCESS\n\n## What I did\n- the task\n"
DISTILL = {"text": "## What worked\n- everything\n## What failed\n- nothing\n"}


class SubstitutionTests(unittest.TestCase):
    def test_all_three_path_forms(self):
        root = Path.cwd()
        raw = str(root.resolve())
        for form in (raw, raw.replace("\\", "\\\\"), raw.replace("\\", "/")):
            out = redact.redact(f"see {form} for details", root)
            self.assertNotIn(form, out)
            self.assertIn("<harness-root>", out)

    def test_nested_root_wins_over_home(self):
        # home is a prefix of root, so root must be substituted first or the
        # trail ends up with "<home>/repos/..." still leaking the layout
        out = redact.redact(str(Path.cwd().resolve()), Path.cwd())
        self.assertEqual(out, "<harness-root>")


class RunTrailTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_no_absolute_paths_survive_into_the_trail(self):
        goal = self.root / "goal.md"
        # a read_dir is echoed into the prompt, and the guard reports it by
        # absolute path — both land in committed artifacts
        goal.write_text(
            f"---\nname: demo\nread_dirs:\n  - {self.root}\n---\nDo the task.\n",
            encoding="utf-8",
        )
        adapter = MockAdapter([{"text": "done", "files": {"REPORT.md": REPORT}}, DISTILL])
        outcome = run_goal(goal, self.root, adapter, retry_delay=0)

        leaked = str(self.root.resolve())
        for artifact in sorted(outcome.run_dir.iterdir()):
            if not artifact.is_file() or artifact.name in redact.EXCLUDE:
                continue
            text = artifact.read_text(encoding="utf-8")
            self.assertNotIn(leaked, text, artifact.name)
            self.assertNotIn(leaked.replace("\\", "\\\\"), text, artifact.name)
            self.assertNotIn(leaked.replace("\\", "/"), text, artifact.name)

    def test_redacted_json_artifacts_still_parse(self):
        goal = self.root / "goal.md"
        goal.write_text(
            f"---\nname: demo\nread_dirs:\n  - {self.root}\n---\nDo the task.\n",
            encoding="utf-8",
        )
        adapter = MockAdapter([{"text": "done", "files": {"REPORT.md": REPORT}}, DISTILL])
        outcome = run_goal(goal, self.root, adapter, retry_delay=0)
        for name in ("verdict.json", "outcome.json", "run_cost.json"):
            json.loads((outcome.run_dir / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
