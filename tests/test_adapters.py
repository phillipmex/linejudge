import json
import tempfile
import unittest
from pathlib import Path

from linejudge.adapters.base import result_from_envelope
from linejudge.adapters.claude_code import load_env
from linejudge.adapters.mock import MockAdapter


class EnvelopeTests(unittest.TestCase):
    def test_valid_envelope_keeps_telemetry(self):
        raw = json.dumps({
            "result": "hello", "is_error": False, "total_cost_usd": 0.42,
            "usage": {"input_tokens": 10}, "num_turns": 3, "session_id": "s1",
        })
        r = result_from_envelope(raw)
        self.assertEqual(r.text, "hello")
        self.assertFalse(r.is_error)
        self.assertEqual(r.cost_usd, 0.42)
        self.assertEqual(r.usage, {"input_tokens": 10})
        self.assertEqual(r.num_turns, 3)

    def test_soft_error_envelope(self):
        raw = json.dumps({"result": "rate limited", "is_error": True})
        r = result_from_envelope(raw)
        self.assertTrue(r.is_error)
        self.assertEqual(r.error_kind, "api")

    def test_non_json_falls_back_to_text(self):
        r = result_from_envelope("plain text output")
        self.assertEqual(r.text, "plain text output")
        self.assertFalse(r.is_error)


class LoadEnvTests(unittest.TestCase):
    def test_env_local_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env.local").write_text(
                "# comment\nMY_TEST_KEY = my-value\nBADLINE\n", encoding="utf-8"
            )
            env = load_env(root)
            self.assertEqual(env["MY_TEST_KEY"], "my-value")
            self.assertNotIn("BADLINE", env)

    def test_no_root_returns_process_env(self):
        self.assertIn("PATH", load_env(None))


class MockAdapterTests(unittest.TestCase):
    def test_writes_files_and_records_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            mock = MockAdapter([{"text": "ok", "files": {"REPORT.md": "## Status\nSUCCESS\n"}}])
            r = mock.run("prompt", cwd=tmp, timeout=10, tools="Read")
            self.assertEqual(r.text, "ok")
            self.assertTrue((Path(tmp) / "REPORT.md").exists())
            self.assertEqual(mock.calls[0].tools, "Read")

    def test_script_exhaustion_raises(self):
        mock = MockAdapter([])
        with self.assertRaises(AssertionError):
            mock.run("p", cwd=".", timeout=1)

    def test_error_response(self):
        mock = MockAdapter([{"text": "boom", "is_error": True, "error_kind": "timeout"}])
        r = mock.run("p", cwd=".", timeout=1)
        self.assertTrue(r.is_error)
        self.assertEqual(r.error_kind, "timeout")


if __name__ == "__main__":
    unittest.main()
