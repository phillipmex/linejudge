"""linejudge CLI."""

import argparse
import sys
from pathlib import Path

from linejudge import __version__


def cmd_run(args):
    from linejudge.adapters.claude_code import ClaudeCodeAdapter
    from linejudge.runner import run_goal

    root = Path(args.root).resolve()
    adapter = ClaudeCodeAdapter(root=root)
    outcome = run_goal(args.goal, root, adapter, dry_run=args.dry_run)
    if outcome.status == "DRY-RUN":
        return 0
    print(f"{outcome.run_id}: {outcome.status}")
    for failure in outcome.failures:
        print(f"  - {failure}")
    print(f"  artifacts: {outcome.run_dir}")
    return 0 if outcome.status == "SUCCESS" else 1


def cmd_cleanup(args):
    from linejudge import worktree

    problems, note = worktree.cleanup_from_run_dir(Path(args.run_dir))
    if note:
        print(note)
        return 1
    if problems:
        print("CLEANUP FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"Cleaned up {args.run_dir} — links removed, worktree gone, live dirs intact.")
    return 0


def cmd_stale_check(args):
    from datetime import datetime

    from linejudge import worktree

    root = Path(args.root).resolve()
    results = worktree.check_stale(Path(args.write_repo), root / "runs")
    stale = [r for r in results if r[1] == "STALE"]
    lines = [f"# Write-diff staleness check — {args.write_repo}", ""]
    for branch, state, detail in results:
        lines.append(f"- **{state}** `{branch}`" + (f" — {detail}" if detail else ""))
    lines.append("")
    lines.append(f"**{len(stale)}/{len(results)} stale.**" if results
                 else "No linejudge/* branches found.")
    report = "\n".join(lines) + "\n"
    print(report)
    runs_dir = root / "runs"
    if runs_dir.exists():
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        (runs_dir / f"stale-check-{stamp}.md").write_text(
            report, encoding="utf-8", newline="\n"
        )
    return 1 if stale else 0


def cmd_dashboard(args):
    from linejudge.dashboard import server

    return server.serve(Path(args.root).resolve(), port=args.port)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="linejudge",
        description="The independent line judge for coding agents.",
    )
    parser.add_argument("--version", action="version", version=f"linejudge {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="run a goal file against an agent")
    p_run.add_argument("goal", help="path to a goal .md file")
    p_run.add_argument("--root", default=".", help="harness root (runs/, learnings/)")
    p_run.add_argument("--dry-run", action="store_true", help="print the composed prompt and exit")
    p_run.set_defaults(func=cmd_run)

    p_clean = sub.add_parser("cleanup", help="tear down a write run's worktree safely")
    p_clean.add_argument("run_dir", help="the run directory holding cleanup.json")
    p_clean.set_defaults(func=cmd_cleanup)

    p_stale = sub.add_parser(
        "stale-check", help="check whether captured write diffs still apply cleanly"
    )
    p_stale.add_argument("write_repo", help="the target repo with linejudge/* branches")
    p_stale.add_argument("--root", default=".", help="harness root (runs/)")
    p_stale.set_defaults(func=cmd_stale_check)

    p_dash = sub.add_parser("dashboard", help="serve the local review dashboard")
    p_dash.add_argument("--root", default=".", help="harness root (runs/, learnings/)")
    p_dash.add_argument("--port", type=int, default=8765, help="port (default 8765)")
    p_dash.set_defaults(func=cmd_dashboard)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
