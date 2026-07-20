"""Run orchestration.

One run = fresh workspace -> composed prompt -> agent call (via adapter) ->
independent checks the agent cannot influence: read-only guard, REPORT.md
presence, verifiers -> distill learning -> cost ledger -> summary.

Every failure mode ends in a *recorded* run directory, never a bare crash:
timeouts and soft API errors come back as RunResult(is_error=True) from the
adapter and turn into FAILED runs with a full artifact trail.

Write-repo goals get an isolated worktree (see worktree.py); the agent's claim
(REPORT.md, in the workspace) stays fully separated from its change (the
captured diff, from the worktree).
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from linejudge import guard, learn, ledger, prompts, verify, worktree
from linejudge.goal import load_goal

READ_TOOLS = "Read,Glob,Grep,Write"
RETRY_DELAY_SECS = 30


@dataclass
class RunOutcome:
    run_id: str
    status: str  # SUCCESS | FAILED
    failures: list = field(default_factory=list)
    run_dir: Path | None = None


def _agent_call(adapter, prompt, workspace, goal, add_dirs, tools, retry_delay):
    """Main agent call with one retry on a soft API error (rate limits are
    transient; timeouts are not, so they never retry). Returns the list of
    (phase, RunResult) attempts — all of them get ledgered."""
    calls = []
    result = adapter.run(
        prompt, cwd=workspace, timeout=goal.timeout_secs,
        add_dirs=add_dirs, tools=tools, model=goal.model,
    )
    calls.append(("execute", result))
    if result.is_error and result.error_kind == "api":
        time.sleep(retry_delay)
        result = adapter.run(
            prompt, cwd=workspace, timeout=goal.timeout_secs,
            add_dirs=add_dirs, tools=tools, model=goal.model,
        )
        calls.append(("execute-retry", result))
    return calls, result


def run_goal(goal_path, root, adapter, dry_run=False, retry_delay=RETRY_DELAY_SECS):
    root = Path(root)
    goal = load_goal(goal_path)

    run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{goal.name}"
    run_dir = root / "runs" / run_id
    wt_path = run_dir / "write_worktree" if goal.write_repo else None
    prompt = prompts.compose(
        goal, preamble=learn.load_preamble(root, goal), worktree_path=wt_path
    )
    if dry_run:
        print(f"[dry-run] {run_id}\n\n{prompt}")
        return RunOutcome(run_id, "DRY-RUN")

    workspace = run_dir / "workspace"
    workspace.mkdir(parents=True)
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8", newline="\n")

    guard_dirs = list(goal.read_dirs) + ([goal.write_repo] if goal.write_repo else [])
    before = guard.snapshot(guard_dirs)
    if goal.write_repo:
        wt_path, _branch = worktree.create(
            goal.write_repo, run_id, run_dir, goal.write_link_dirs
        )
    tools = READ_TOOLS + (",Edit" if goal.write_repo else "")
    add_dirs = list(goal.read_dirs) + ([wt_path] if wt_path else [])
    calls, result = _agent_call(
        adapter, prompt, workspace, goal, add_dirs, tools, retry_delay
    )
    (run_dir / "session.json").write_text(result.raw or "", encoding="utf-8", newline="\n")

    failures = []
    if result.is_error:
        failures.append(f"agent call failed ({result.error_kind}): {result.text[:500]}")
    failures += guard.check(before, run_dir)

    report_path = workspace / "REPORT.md"
    report_text = ""
    if report_path.exists():
        report_text = report_path.read_text(encoding="utf-8")
    elif not result.is_error:
        failures.append("agent wrote no REPORT.md (output contract violated)")

    committed = False
    if wt_path:
        # capture BEFORE the verifiers so diff_constraints can see the diff
        _diff, committed = worktree.capture_and_commit(wt_path, run_dir, goal.name, run_id)

    verdict = verify.run_verifiers(goal.verifiers, wt_path or workspace, run_dir)
    failures += [
        f"verifier failed: {e['kind']}: {e['spec']}"
        for e in verdict["verifiers"] if not e["passed"]
    ]

    status = "SUCCESS" if not failures else "FAILED"

    distill_result = learn.distill(
        adapter, root, run_id, goal, status, failures, report_text, result.text
    )
    calls.append(("distill", distill_result))
    cost = ledger.record(root, run_dir, run_id, goal, status, calls)

    write_note = ""
    if wt_path:
        branch_state = "committed, not merged" if committed else "EMPTY — no diff"
        write_note = (
            f"- write branch: `{worktree.BRANCH_PREFIX}{run_id}` ({branch_state})\n"
            f"- write diff: write_diff.patch — review before merging into {goal.write_repo}\n"
            f"- cleanup when done: `linejudge cleanup {run_dir}` (never remove by hand)\n"
        )
    (run_dir / "summary.md").write_text(
        f"# {run_id}\n\n"
        f"- status: {status}\n"
        f"- goal: {goal.name}\n"
        f"- cost: ${cost['total_cost_usd']}\n"
        f"- verdict: {'PASS' if verdict['passed'] else 'FAIL'}"
        f" ({len(verdict['verifiers'])} verifiers)\n"
        + write_note + "\n"
        + ("## Failures\n\n" + "\n".join(f"- {f}" for f in failures) + "\n"
           if failures else "No failures.\n"),
        encoding="utf-8", newline="\n",
    )
    (run_dir / "outcome.json").write_text(
        json.dumps({"run_id": run_id, "status": status, "failures": failures}, indent=2),
        encoding="utf-8", newline="\n",
    )
    return RunOutcome(run_id, status, failures, run_dir)
