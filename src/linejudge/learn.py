"""Cross-run learning. After each run, a second tool-less agent call distills
the run into a short LearningReport stored under learnings/. The next run's
prompt gets a preamble from the store.

Retrieval (Wave 4): top-N reports by tag overlap with the goal, recency as
tiebreak — no embeddings, no index, just frontmatter. Poisoned distillations
(soft-errored calls) are never written, so they can never enter the pool.
latest.md is still written for back-compat and serves as the fallback when no
per-run reports exist (e.g. a hand-written seed).
"""

from pathlib import Path

from linejudge import prompts

DISTILL_TIMEOUT = 300
TOP_N = 3


def _parse_report(path):
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            for line in text[4:end].splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip()
            body = text[end + 5:]
    return meta, body.strip()


def select_reports(root, tags, top_n=TOP_N):
    """Score every stored report by tag overlap with the goal; recency breaks
    ties (run_id filenames start with a timestamp, so the stem IS the recency
    key). Returns [(overlap, run_id, meta, body)], best first."""
    learn_dir = Path(root, "learnings")
    if not learn_dir.is_dir():
        return []
    scored = []
    for path in learn_dir.glob("*.md"):
        if path.name == "latest.md":
            continue
        meta, body = _parse_report(path)
        report_tags = {t.strip() for t in meta.get("tags", "").split(",") if t.strip()}
        scored.append((len(set(tags) & report_tags), path.stem, meta, body))
    scored.sort(key=lambda r: (r[0], r[1]), reverse=True)
    return scored[:top_n]


def load_preamble(root, goal=None):
    selected = select_reports(root, list(goal.tags) if goal else [])
    if selected:
        parts = [
            f"### {meta.get('goal', run_id)} — {meta.get('status', '?')} ({run_id})"
            f"\n\n{body}"
            for _overlap, run_id, meta, body in selected
        ]
        return "\n\n".join(parts) + "\n"
    latest = Path(root, "learnings", "latest.md")
    return latest.read_text(encoding="utf-8") if latest.exists() else ""


def distill(adapter, root, run_id, goal, status, failures, report_text, result_text):
    """Run the distillation call and store the report. Always returns the
    RunResult (the runner ledgers its cost either way), but when the distill
    call itself soft-errored NOTHING is written to latest.md — so an API error
    message can never poison the preamble every future run would inherit."""
    prompt = prompts.compose_distill(goal, status, failures, report_text, result_text)
    result = adapter.run(
        prompt, cwd=root, timeout=DISTILL_TIMEOUT, tools="", model=goal.model
    )
    if result.is_error:
        return result

    body = (
        f"---\ngoal: {goal.name}\nstatus: {status}\n"
        f"tags: {', '.join(goal.tags)}\nrun_id: {run_id}\n---\n\n"
        f"{result.text.strip()}\n"
    )
    learn_dir = Path(root, "learnings")
    learn_dir.mkdir(parents=True, exist_ok=True)
    (learn_dir / f"{run_id}.md").write_text(body, encoding="utf-8", newline="\n")
    (learn_dir / "latest.md").write_text(body, encoding="utf-8", newline="\n")
    return result
