"""Prompt composition. The agent's only obligations beyond the goal body are
the output contract (REPORT.md = the agent's *claim*, which the harness never
trusts — verifiers produce the verdict) and the read-only rules."""

OUTPUT_CONTRACT = """\
## Output contract (required)

When you are done, write a file named REPORT.md in your working directory with:
- `## Status` — exactly one of SUCCESS or FAILED on the next line
- `## What I did` — short factual list
- `## Evidence` — how you checked it works (commands run, files produced)

Your REPORT.md is a claim, not a verdict: the harness runs its own verifiers
after you finish. A missing REPORT.md fails the run regardless of your work.
"""


def read_only_note(read_dirs):
    dirs = "\n".join(f"- {d}" for d in read_dirs)
    return (
        "## Read-only reference directories\n\n"
        "These directories are reference material. Do NOT create, modify, or "
        "delete anything inside them — any change there fails the run:\n"
        f"{dirs}\n"
    )


def write_note(worktree_path):
    return (
        "## Write access\n\n"
        "Make your changes inside this directory — it is an isolated git "
        f"worktree of the target repo:\n- {worktree_path}\n\n"
        "Do not run git commit/branch/merge yourself; the harness captures and "
        "commits your diff after you finish. REPORT.md still goes in your "
        "working directory, NOT in the worktree — keep the diff clean of "
        "harness artifacts.\n"
    )


def compose(goal, preamble="", worktree_path=None):
    parts = []
    if preamble:
        parts.append("## Learnings from previous runs\n\n" + preamble)
    parts.append(goal.body)
    if worktree_path:
        parts.append(write_note(worktree_path))
    if goal.read_dirs:
        parts.append(read_only_note(goal.read_dirs))
    if goal.agent_notes:
        parts.append("## Notes\n\n" + "\n".join(f"- {n}" for n in goal.agent_notes))
    parts.append(OUTPUT_CONTRACT)
    return "\n\n".join(parts) + "\n"


DISTILL_PROMPT = """\
You are distilling one autonomous agent run into a short LearningReport that
future runs will read before starting. Be concrete and reusable; skip anything
specific to this one run that cannot transfer.

## Run facts
- goal: {name}
- status: {status}
- failures: {failures}

## Agent's report (its own claim)
{report}

## Agent's final message
{result}

Write ONLY the LearningReport, max 40 lines, markdown, with sections:
`## What worked`, `## What failed`, `## Do differently next time`.
"""


def compose_distill(goal, status, failures, report_text, result_text):
    return DISTILL_PROMPT.format(
        name=goal.name,
        status=status,
        failures="; ".join(failures) if failures else "(none)",
        report=report_text or "(no REPORT.md was written)",
        result=result_text[:4000],
    )
