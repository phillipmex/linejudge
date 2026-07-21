"""Turn a repo's open GitHub issues into linejudge goal files.

Real mode (needs gh CLI, no Anthropic API spend):
    python proofs/generate.py --repo owner/name --limit 5 --out proofs/goals

Offline mode (canned gh JSON, used by tests and the mock demo):
    python proofs/generate.py --from-json proofs/fixtures/issues.json --out ...

Each issue becomes one goal file; labels become tags; verifiers are supplied
via --verifier (repeatable, "kind: spec" form) so every proof run is judged by
the harness, not by the agent's claim.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

GH_FIELDS = "number,title,body,labels,url"


def slugify(text, max_len=40):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "untitled"


def _clean_tag(label):
    """Header values are one-line and colon-free (the parser splits on ':')."""
    return re.sub(r"[:\r\n]+", "-", str(label)).strip()


def fetch_issues(repo, limit):
    out = subprocess.run(
        ["gh", "issue", "list", "--repo", repo, "--state", "open",
         "--limit", str(limit), "--json", GH_FIELDS],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def goal_text(issue, repo, verifiers=(), extra_tags=(), write_repo=None,
              timeout_secs=None, notes=()):
    number = issue["number"]
    name = f"issue-{number}-{slugify(issue.get('title', ''))}"
    tags = ["proof", _clean_tag(repo)] if repo else ["proof"]
    tags += [_clean_tag(t) for t in extra_tags]
    tags += [_clean_tag(lb["name"]) for lb in issue.get("labels", []) if lb.get("name")]

    lines = ["---", f"name: {name}", "tags:"]
    lines += [f"  - {t}" for t in dict.fromkeys(tags)]  # dedupe, keep order
    if verifiers:
        lines.append("verifiers:")
        lines += [f"  - {v}" for v in verifiers]
    if notes:
        lines.append("agent_notes:")
        lines += [f"  - {_clean_tag(n)}" for n in notes]
    if write_repo:
        lines.append(f"write_repo: {write_repo}")
    if timeout_secs:
        lines.append(f"timeout_secs: {timeout_secs}")
    lines.append("---")
    body = (issue.get("body") or "").strip()
    lines += [
        f"# {issue.get('title', name)}",
        "",
        f"GitHub issue #{number}" + (f" — {issue['url']}" if issue.get("url") else ""),
        "",
        body if body else "(no issue body)",
        "",
    ]
    return name, "\n".join(lines) + "\n"


def write_goals(issues, out_dir, repo, verifiers=(), extra_tags=(),
                write_repo=None, timeout_secs=None, notes=()):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for issue in issues:
        name, text = goal_text(issue, repo, verifiers, extra_tags,
                               write_repo, timeout_secs, notes)
        path = out_dir / f"{name}.md"
        path.write_text(text, encoding="utf-8", newline="\n")
        paths.append(path)
    return paths


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", help="owner/name to pull open issues from (gh CLI)")
    parser.add_argument("--from-json", help="canned gh JSON file instead of a live call")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out", default="proofs/goals", help="goal file output dir")
    parser.add_argument("--verifier", action="append", default=[],
                        help='repeatable "kind: spec", e.g. "command: python -m pytest -q"')
    parser.add_argument("--tag", action="append", default=[], help="extra tag (repeatable)")
    parser.add_argument("--write-repo", help="local clone the agent gets a write cycle on")
    parser.add_argument("--timeout", type=int, help="per-goal timeout_secs")
    parser.add_argument("--note", action="append", default=[],
                        help="agent_notes line (repeatable)")
    args = parser.parse_args(argv)

    if args.from_json:
        issues = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
    elif args.repo:
        issues = fetch_issues(args.repo, args.limit)
    else:
        parser.error("need --repo or --from-json")

    paths = write_goals(issues[:args.limit], args.out, args.repo or "",
                        args.verifier, args.tag, args.write_repo, args.timeout,
                        args.note)
    for p in paths:
        print(p)
    print(f"{len(paths)} goal files in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
