import http.server
import json
import tempfile
import threading
import unittest
from pathlib import Path

from linejudge.verify import run_verifiers

SAMPLE_DIFF = """\
diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,4 @@
 def main():
-    return 1
+    # fixed
+    return 2
diff --git a/secrets/key.pem b/secrets/key.pem
--- a/secrets/key.pem
+++ /dev/null
@@ -1,1 +0,0 @@
-PRIVATE
"""


class VerifierTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cwd = Path(self._tmp.name) / "ws"
        self.run_dir = Path(self._tmp.name) / "run"
        self.cwd.mkdir()
        self.run_dir.mkdir()

    def run_one(self, kind, spec):
        verdict = run_verifiers([(kind, spec)], cwd=self.cwd, run_dir=self.run_dir)
        return verdict["passed"], verdict["verifiers"][0]["evidence"]


class RunVerifiersTests(VerifierTestCase):
    def _run(self, verifiers):
        verdict = run_verifiers(verifiers, cwd=self.cwd, run_dir=self.run_dir)
        on_disk = json.loads((self.run_dir / "verdict.json").read_text(encoding="utf-8"))
        self.assertEqual(verdict, on_disk)
        return verdict

    def test_command_pass(self):
        verdict = self._run([("command", 'python -c "print(42)"')])
        self.assertTrue(verdict["passed"])
        self.assertIn("42", verdict["verifiers"][0]["evidence"])

    def test_command_fail_keeps_evidence(self):
        verdict = self._run([("command", 'python -c "import sys; sys.exit(3)"')])
        self.assertFalse(verdict["passed"])
        self.assertIn("exit 3", verdict["verifiers"][0]["evidence"])

    def test_unknown_kind_is_failed_entry_not_crash(self):
        verdict = self._run([("no_such_kind", "whatever")])
        self.assertFalse(verdict["passed"])
        self.assertIn("unknown verifier kind", verdict["verifiers"][0]["evidence"])

    def test_empty_verifier_list_passes(self):
        verdict = self._run([])
        self.assertTrue(verdict["passed"])
        self.assertEqual(verdict["verifiers"], [])

    def test_overall_verdict_is_and(self):
        verdict = self._run([
            ("command", 'python -c "pass"'),
            ("command", 'python -c "import sys; sys.exit(1)"'),
        ])
        self.assertFalse(verdict["passed"])
        self.assertTrue(verdict["verifiers"][0]["passed"])
        self.assertFalse(verdict["verifiers"][1]["passed"])


class FilesExistTests(VerifierTestCase):
    def test_all_present_passes(self):
        (self.cwd / "a.txt").write_text("x", encoding="utf-8")
        (self.cwd / "sub").mkdir()
        (self.cwd / "sub" / "b.txt").write_text("y", encoding="utf-8")
        passed, evidence = self.run_one("files_exist", "a.txt, sub/b.txt")
        self.assertTrue(passed)
        self.assertIn("OK", evidence)

    def test_missing_file_fails_and_names_it(self):
        (self.cwd / "a.txt").write_text("x", encoding="utf-8")
        passed, evidence = self.run_one("files_exist", "a.txt, nope.txt")
        self.assertFalse(passed)
        self.assertIn("MISSING nope.txt", evidence)

    def test_empty_spec_passes_with_note(self):
        passed, evidence = self.run_one("files_exist", "")
        self.assertTrue(passed)
        self.assertIn("no paths given", evidence)


class DiffConstraintsTests(VerifierTestCase):
    def write_diff(self, text=SAMPLE_DIFF):
        (self.run_dir / "write_diff.patch").write_text(text, encoding="utf-8", newline="\n")

    def test_no_diff_captured_fails(self):
        passed, evidence = self.run_one("diff_constraints", "max_files=5")
        self.assertFalse(passed)
        self.assertIn("no write_diff.patch", evidence)

    def test_within_limits_passes(self):
        self.write_diff()
        passed, evidence = self.run_one("diff_constraints", "max_files=2 max_lines=10")
        self.assertTrue(passed)
        self.assertIn("2 files / 4 changed lines", evidence)

    def test_max_files_exceeded_fails(self):
        self.write_diff()
        passed, evidence = self.run_one("diff_constraints", "max_files=1")
        self.assertFalse(passed)
        self.assertIn("max_files=1", evidence)

    def test_max_lines_exceeded_fails(self):
        self.write_diff()
        passed, evidence = self.run_one("diff_constraints", "max_lines=3")
        self.assertFalse(passed)
        self.assertIn("max_lines=3", evidence)

    def test_allowlist_flags_stray_file(self):
        self.write_diff()
        passed, evidence = self.run_one("diff_constraints", "allow=src/*")
        self.assertFalse(passed)
        self.assertIn("secrets/key.pem outside allowlist", evidence)

    def test_denylist_flags_deleted_secret(self):
        # key.pem only appears as a deletion (+++ /dev/null) — the parser must
        # still attribute it from the --- side.
        self.write_diff()
        passed, evidence = self.run_one("diff_constraints", "deny=secrets/*")
        self.assertFalse(passed)
        self.assertIn("secrets/key.pem matches denylist", evidence)

    def test_bad_limit_value_is_failed_entry_not_crash(self):
        self.write_diff()
        passed, evidence = self.run_one("diff_constraints", "max_files=lots")
        self.assertFalse(passed)
        self.assertIn("verifier raised", evidence)


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ok":
            body = b"hello linejudge"
            self.send_response(200)
        elif self.path == "/teapot":
            body = b"short and stout"
            self.send_response(418)
        else:
            body = b"gone"
            self.send_response(404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class HttpCheckTests(VerifierTestCase):
    def setUp(self):
        super().setUp()
        self.server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def test_status_and_substring_pass(self):
        passed, evidence = self.run_one(
            "http_check", f"{self.base}/ok expect=200 contains=linejudge"
        )
        self.assertTrue(passed)
        self.assertIn("-> 200", evidence)

    def test_wrong_status_fails(self):
        passed, evidence = self.run_one("http_check", f"{self.base}/teapot expect=200")
        self.assertFalse(passed)
        self.assertIn("expected 200", evidence)

    def test_non_2xx_can_be_expected(self):
        passed, _ = self.run_one("http_check", f"{self.base}/teapot expect=418")
        self.assertTrue(passed)

    def test_missing_substring_fails(self):
        passed, evidence = self.run_one(
            "http_check", f"{self.base}/ok contains=absent-string"
        )
        self.assertFalse(passed)
        self.assertIn("does not contain", evidence)

    def test_unreachable_server_fails_with_evidence(self):
        passed, evidence = self.run_one(
            "http_check", "http://127.0.0.1:9/nothing expect=200"
        )
        self.assertFalse(passed)
        self.assertIn("request failed", evidence)

    def test_empty_spec_fails(self):
        passed, evidence = self.run_one("http_check", "")
        self.assertFalse(passed)
        self.assertIn("no URL", evidence)


if __name__ == "__main__":
    unittest.main()
