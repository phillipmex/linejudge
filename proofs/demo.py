"""End-to-end proof demo on the MockAdapter — zero API spend.

    python proofs/demo.py [--root <dir>]

Generates goals from the canned issue fixture, runs each through the full
harness with a scripted fake agent, then renders PROOF.md. One of the three
scripted runs LIES (claims success, does nothing) — the verifier catches it,
which is exactly the point.

Real mode is the same pipeline with a real adapter:
    python proofs/generate.py --repo owner/name --limit 5 --out proofs/goals
    linejudge run proofs/goals/<goal>.md --root proofs/root   # needs API key
    python proofs/stats.py --root proofs/root
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate  # noqa: E402
import stats  # noqa: E402
from linejudge.adapters.mock import MockAdapter  # noqa: E402
from linejudge.runner import run_goal  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "issues.json"
REPORT = "## Status\nSUCCESS\n\n## What I did\n- resolved the issue\n"
DISTILL = {"text": "- verify before claiming\n", "cost_usd": 0.001}

# scripted agent behaviour per issue: two honest runs, one liar (#102 claims
# success but never writes done.txt — the files_exist verifier fails it)
SCRIPTS = {
    "issue-101": [{"files": {"REPORT.md": REPORT, "done.txt": "fixed\n"},
                   "cost_usd": 0.041}, DISTILL],
    "issue-102": [{"files": {"REPORT.md": REPORT}, "cost_usd": 0.029}, DISTILL],
    "issue-103": [{"files": {"REPORT.md": REPORT, "done.txt": "docs updated\n"},
                   "cost_usd": 0.018}, DISTILL],
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=None,
                        help="harness root for the demo runs (default: temp dir)")
    args = parser.parse_args(argv)

    root = Path(args.root) if args.root else Path(tempfile.mkdtemp(prefix="linejudge-demo-"))
    root.mkdir(parents=True, exist_ok=True)

    issues = json.loads(FIXTURE.read_text(encoding="utf-8"))
    goal_paths = generate.write_goals(
        issues, root / "goals", "example/widget",
        verifiers=["files_exist: done.txt"],
    )

    for goal_path in goal_paths:
        key = next(k for k in SCRIPTS if goal_path.stem.startswith(k))
        adapter = MockAdapter(list(SCRIPTS[key]))
        outcome = run_goal(goal_path, root, adapter)
        print(f"{outcome.run_id}: {outcome.status}")

    out = root / "PROOF.md"
    out.write_text(stats.render(stats.collect(root)), encoding="utf-8", newline="\n")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
