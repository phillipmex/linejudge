"""Dashboard HTTP layer. Read-only JSON views over runs/ plus one mutating
endpoint: the human approve/reject decision, written to runs/<id>/decision.json.
The dashboard never edits run artifacts — the decision file is the only thing
it owns, and it sits beside the evidence, not inside it.

Endpoints:
    GET  /                     -> static index.html
    GET  /api/runs             -> run list (newest first) + ledger aggregate
    GET  /api/runs/<id>        -> full artifact trail for one run
    POST /api/runs/<id>/decision  {"decision": "approve"|"reject", "note": ""}
"""

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from linejudge import ledger

RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")  # no separators — blocks traversal

# (json key, relative path) — every artifact the detail view exposes
TEXT_ARTIFACTS = [
    ("prompt", "prompt.md"),
    ("report", "workspace/REPORT.md"),
    ("diff", "write_diff.patch"),
    ("summary", "summary.md"),
]
JSON_ARTIFACTS = [
    ("outcome", "outcome.json"),
    ("verdict", "verdict.json"),
    ("cost", "run_cost.json"),
    ("decision", "decision.json"),
]


def _read_text(path):
    return path.read_text(encoding="utf-8") if path.exists() else None


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except json.JSONDecodeError:
        return {"error": f"unparseable: {path.name}"}


def list_runs(root):
    runs_dir = Path(root, "runs")
    if not runs_dir.is_dir():
        return []
    rows = []
    for d in sorted(runs_dir.iterdir(), reverse=True):
        outcome = _read_json(d / "outcome.json")
        if not d.is_dir() or outcome is None:
            continue  # ledger.jsonl, stale-check reports, half-written dirs
        cost = _read_json(d / "run_cost.json") or {}
        verdict = _read_json(d / "verdict.json") or {}
        decision = _read_json(d / "decision.json") or {}
        rows.append({
            "run_id": d.name,
            "status": outcome.get("status"),
            "failures": outcome.get("failures", []),
            "total_cost_usd": cost.get("total_cost_usd"),
            "verdict_passed": verdict.get("passed"),
            "verifier_count": len(verdict.get("verifiers", [])),
            "decision": decision.get("decision"),
            "has_diff": (d / "write_diff.patch").exists(),
        })
    return rows


def run_detail(root, run_id):
    run_dir = Path(root, "runs", run_id)
    if not RUN_ID_RE.match(run_id) or not run_dir.is_dir():
        return None
    detail = {"run_id": run_id}
    for key, rel in TEXT_ARTIFACTS:
        detail[key] = _read_text(run_dir / rel)
    for key, rel in JSON_ARTIFACTS:
        detail[key] = _read_json(run_dir / rel)
    detail["learning"] = _read_text(Path(root, "learnings", f"{run_id}.md"))
    return detail


def write_decision(root, run_id, payload):
    run_dir = Path(root, "runs", run_id)
    if not RUN_ID_RE.match(run_id) or not run_dir.is_dir():
        return None
    decision = payload.get("decision")
    if decision not in ("approve", "reject"):
        return {"error": "decision must be approve or reject"}
    from datetime import datetime
    record = {
        "decision": decision,
        "note": str(payload.get("note", ""))[:2000],
        "decided_at": datetime.now().isoformat(timespec="seconds"),
    }
    (run_dir / "decision.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8", newline="\n"
    )
    return record


class DashboardHandler(BaseHTTPRequestHandler):
    root = None  # set by make_server

    def _send(self, code, body, content_type="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass  # keep test output and the user's terminal quiet

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            page = Path(__file__).parent / "index.html"
            if page.exists():
                self._send(200, page.read_bytes(), "text/html; charset=utf-8")
            else:  # broken install (package data missing) — fail loudly, not with
                # an empty reply that curl reports as exit 52
                self._send(500, {"error": "index.html missing from install"})
        elif self.path == "/api/runs":
            self._send(200, {
                "runs": list_runs(self.root),
                "ledger": ledger.aggregate(self.root),
            })
        elif self.path.startswith("/api/runs/"):
            detail = run_detail(self.root, self.path[len("/api/runs/"):])
            if detail is None:
                self._send(404, {"error": "no such run"})
            else:
                self._send(200, detail)
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        m = re.match(r"^/api/runs/([^/]+)/decision$", self.path)
        if not m:
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid JSON body"})
            return
        record = write_decision(self.root, m.group(1), payload)
        if record is None:
            self._send(404, {"error": "no such run"})
        elif "error" in record:
            self._send(400, record)
        else:
            self._send(200, record)


def make_server(root, port=0, host="127.0.0.1"):
    """Bind and return the server (port 0 = ephemeral, for tests). Caller runs
    serve_forever()."""
    handler = type("Handler", (DashboardHandler,), {"root": Path(root)})
    return ThreadingHTTPServer((host, port), handler)


def serve(root, port=8765):
    server = make_server(root, port)
    print(f"linejudge dashboard: http://127.0.0.1:{server.server_address[1]}/")
    print("Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0
