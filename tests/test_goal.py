import tempfile
import unittest
from pathlib import Path

from linejudge.goal import DEFAULT_TIMEOUT, load_goal, parse_header

HEADER = """\
---
name: demo
tags:
  - alpha
  - beta
read_dirs:
  - /some/repo
model: claude-sonnet-5
verifiers:
  - command: python -m pytest -q
  - files_exist: REPORT.md
verify: echo legacy
timeout_secs: 60
agent_notes:
  - remember the thing
---
Do the task.
"""


class ParseHeaderTests(unittest.TestCase):
    def test_missing_fence_raises(self):
        with self.assertRaises(ValueError):
            parse_header("no fence here")

    def test_comments_and_blanks_skipped(self):
        cfg, body = parse_header("---\n# comment\n\nname: x\n---\nbody")
        self.assertEqual(cfg, {"name": "x"})
        self.assertEqual(body, "body")

    def test_list_items_attach_to_last_key(self):
        cfg, _ = parse_header("---\ntags:\n  - a\n  - b\n---\nbody")
        self.assertEqual(cfg["tags"], ["a", "b"])


class LoadGoalTests(unittest.TestCase):
    def _load(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "goal.md"
            path.write_text(text, encoding="utf-8")
            return load_goal(path)

    def test_full_header(self):
        goal = self._load(HEADER)
        self.assertEqual(goal.name, "demo")
        self.assertEqual(goal.tags, ["alpha", "beta"])
        self.assertEqual(goal.read_dirs, [Path("/some/repo")])
        self.assertEqual(goal.model, "claude-sonnet-5")
        self.assertEqual(goal.timeout_secs, 60)
        self.assertEqual(goal.agent_notes, ["remember the thing"])
        self.assertEqual(goal.body, "Do the task.")

    def test_verify_is_sugar_for_command_verifier(self):
        goal = self._load(HEADER)
        self.assertEqual(goal.verifiers[0], ("command", "echo legacy"))
        self.assertIn(("command", "python -m pytest -q"), goal.verifiers)
        self.assertIn(("files_exist", "REPORT.md"), goal.verifiers)

    def test_defaults(self):
        goal = self._load("---\nname: bare\n---\nbody")
        self.assertEqual(goal.timeout_secs, DEFAULT_TIMEOUT)
        self.assertEqual(goal.verifiers, [])
        self.assertIsNone(goal.write_repo)
        self.assertIsNone(goal.model)

    def test_name_defaults_to_filename(self):
        goal = self._load("---\ntimeout_secs: 5\n---\nbody")
        self.assertEqual(goal.name, "goal")


if __name__ == "__main__":
    unittest.main()
