"""Dashboard endpoint tests: a real ThreadingHTTPServer on an ephemeral port
over a fabricated runs/ directory — no network beyond loopback, no mocks of
http.server itself."""

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from linejudge.dashboard import server as dash


def make_run(root, run_id, status="SUCCESS", passed=True, cost=0.12,
             diff=True, decision=None):
    d = Path(root, "runs", run_id)
    (d / "workspace").mkdir(parents=True)
    (d / "outcome.json").write_text(json.dumps(
        {"status": status, "failures": [] if status == "SUCCESS" else ["verifier failed"]}
    ), encoding="utf-8")
    (d / "verdict.json").write_text(json.dumps({
        "passed": passed,
        "verifiers": [{"kind": "command", "spec": "echo ok",
                       "passed": passed, "evidence": "exit 0"}],
    }), encoding="utf-8")
    (d / "run_cost.json").write_text(
        json.dumps({"run_id": run_id, "total_cost_usd": cost, "calls": []}),
        encoding="utf-8")
    (d / "prompt.md").write_text("# Goal\ndo the thing\n", encoding="utf-8")
    (d / "workspace" / "REPORT.md").write_text("STATUS: SUCCESS\n", encoding="utf-8")
    (d / "summary.md").write_text(f"# {run_id}\n", encoding="utf-8")
    if diff:
        (d / "write_diff.patch").write_text("--- a/x\n+++ b/x\n", encoding="utf-8")
    if decision:
        (d / "decision.json").write_text(json.dumps(decision), encoding="utf-8")
    learn = Path(root, "learnings")
    learn.mkdir(exist_ok=True)
    (learn / f"{run_id}.md").write_text("learned something\n", encoding="utf-8")
    with open(Path(root, "runs", "ledger.jsonl"), "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"run_id": run_id, "goal": "demo", "tags": [],
                            "status": status, "total_cost_usd": cost,
                            "num_calls": 2}) + "\n")


class DashboardTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        make_run(self.root, "20260101-000000-aaaa")
        make_run(self.root, "20260102-000000-bbbb", status="FAILED",
                 passed=False, cost=0.05, diff=False)
        self.server = dash.make_server(self.root, port=0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as resp:
            return resp.status, json.loads(resp.read())

    def post(self, path, body):
        req = urllib.request.Request(
            self.base + path, data=body, method="POST",
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())


class ListTests(DashboardTestCase):
    def test_list_newest_first_with_fields(self):
        status, data = self.get("/api/runs")
        self.assertEqual(status, 200)
        ids = [r["run_id"] for r in data["runs"]]
        self.assertEqual(ids, ["20260102-000000-bbbb", "20260101-000000-aaaa"])
        newest, oldest = data["runs"]
        self.assertEqual(newest["status"], "FAILED")
        self.assertFalse(newest["verdict_passed"])
        self.assertFalse(newest["has_diff"])
        self.assertTrue(oldest["has_diff"])
        self.assertEqual(oldest["total_cost_usd"], 0.12)
        self.assertEqual(oldest["verifier_count"], 1)
        self.assertIsNone(oldest["decision"])

    def test_ledger_aggregate_included(self):
        _, data = self.get("/api/runs")
        self.assertEqual(data["ledger"]["runs"], 2)
        self.assertAlmostEqual(data["ledger"]["total_cost_usd"], 0.17)
        self.assertEqual(data["ledger"]["by_status"],
                         {"SUCCESS": 1, "FAILED": 1})

    def test_ledger_file_not_listed_as_run(self):
        _, data = self.get("/api/runs")
        self.assertNotIn("ledger.jsonl", [r["run_id"] for r in data["runs"]])


class DetailTests(DashboardTestCase):
    def test_detail_has_full_trail(self):
        status, d = self.get("/api/runs/20260101-000000-aaaa")
        self.assertEqual(status, 200)
        self.assertIn("do the thing", d["prompt"])
        self.assertIn("STATUS: SUCCESS", d["report"])
        self.assertIn("+++ b/x", d["diff"])
        self.assertTrue(d["verdict"]["passed"])
        self.assertEqual(d["cost"]["total_cost_usd"], 0.12)
        self.assertIn("learned something", d["learning"])
        self.assertIsNone(d["decision"])

    def test_missing_run_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/api/runs/nope")
        self.assertEqual(ctx.exception.code, 404)

    def test_traversal_run_id_404(self):
        # ..%2f..%2f stays one path segment; the id regex must reject it
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/api/runs/..%2f..%2fsecrets")
        self.assertEqual(ctx.exception.code, 404)


class DecisionTests(DashboardTestCase):
    def test_approve_round_trip(self):
        status, rec = self.post(
            "/api/runs/20260101-000000-aaaa/decision",
            json.dumps({"decision": "approve", "note": "looks good"}).encode())
        self.assertEqual(status, 200)
        self.assertEqual(rec["decision"], "approve")
        self.assertEqual(rec["note"], "looks good")
        self.assertIn("decided_at", rec)
        on_disk = json.loads(Path(
            self.root, "runs", "20260101-000000-aaaa", "decision.json"
        ).read_text(encoding="utf-8"))
        self.assertEqual(on_disk["decision"], "approve")
        _, data = self.get("/api/runs")
        row = [r for r in data["runs"] if r["run_id"] == "20260101-000000-aaaa"][0]
        self.assertEqual(row["decision"], "approve")

    def test_reject_round_trip(self):
        status, rec = self.post(
            "/api/runs/20260102-000000-bbbb/decision",
            json.dumps({"decision": "reject"}).encode())
        self.assertEqual(status, 200)
        self.assertEqual(rec["decision"], "reject")
        self.assertEqual(rec["note"], "")

    def test_invalid_decision_400(self):
        status, body = self.post(
            "/api/runs/20260101-000000-aaaa/decision",
            json.dumps({"decision": "maybe"}).encode())
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_invalid_json_400(self):
        status, body = self.post(
            "/api/runs/20260101-000000-aaaa/decision", b"not json")
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_decision_for_missing_run_404(self):
        status, _ = self.post(
            "/api/runs/nope/decision",
            json.dumps({"decision": "approve"}).encode())
        self.assertEqual(status, 404)


class StaticTests(DashboardTestCase):
    def test_index_served(self):
        with urllib.request.urlopen(self.base + "/") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/html", resp.headers["Content-Type"])
            body = resp.read().decode("utf-8")
        self.assertIn("linejudge", body)
        self.assertIn("/api/runs", body)

    def test_unknown_path_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/etc/passwd")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
