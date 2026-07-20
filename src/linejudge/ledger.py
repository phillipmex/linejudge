"""Cost accounting. The agent CLI's result envelope already reports cost and
token usage per call — this module is what keeps it instead of discarding it:
a per-run run_cost.json plus an append-only runs/ledger.jsonl for aggregation.
"""

import json
from pathlib import Path


def _call_entry(phase, result):
    return {
        "phase": phase,
        "cost_usd": result.cost_usd,
        "usage": result.usage,
        "num_turns": result.num_turns,
        "is_error": result.is_error,
        "error_kind": result.error_kind,
    }


def record(root, run_dir, run_id, goal, status, calls):
    """calls: list of (phase, RunResult). Writes run_cost.json in the run dir
    and appends one line to runs/ledger.jsonl."""
    entries = [_call_entry(phase, r) for phase, r in calls]
    total = sum(e["cost_usd"] for e in entries if e["cost_usd"] is not None)
    cost = {"run_id": run_id, "total_cost_usd": round(total, 6), "calls": entries}
    Path(run_dir, "run_cost.json").write_text(
        json.dumps(cost, indent=2), encoding="utf-8"
    )

    ledger_line = {
        "run_id": run_id,
        "goal": goal.name,
        "tags": goal.tags,
        "status": status,
        "total_cost_usd": round(total, 6),
        "num_calls": len(entries),
    }
    ledger_path = Path(root, "runs", "ledger.jsonl")
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(ledger_line) + "\n")
    return cost


def aggregate(root):
    ledger_path = Path(root, "runs", "ledger.jsonl")
    if not ledger_path.exists():
        return {"runs": 0, "total_cost_usd": 0.0, "by_status": {}}
    runs, total, by_status = 0, 0.0, {}
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        runs += 1
        total += rec.get("total_cost_usd") or 0.0
        by_status[rec.get("status", "?")] = by_status.get(rec.get("status", "?"), 0) + 1
    return {"runs": runs, "total_cost_usd": round(total, 6), "by_status": by_status}
