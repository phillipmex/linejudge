"""Local-path redaction for the committed run trail.

Run artifacts are committed and published, so absolute paths from the machine
that produced the run (harness root, home directory) have no business being in
them. Redaction happens once, over the run directory, after the run: doing it
at write time would mean threading `root` through every producer, and it would
still miss anything a verifier's captured output happened to print.

Placeholders are stable (`<harness-root>`, `<home>`) so the trail stays
diffable across machines.
"""

from pathlib import Path

# Artifacts deliberately left alone, and why:
#   cleanup.json      `linejudge cleanup` reads these paths back to tear the
#                     worktree down — redacting them would break teardown.
#                     Kept out of the trail via .gitignore instead.
#   session.json      gitignored raw transcript; the unedited evidence.
#   write_diff.patch  a patch has to apply verbatim; rewriting its content
#                     would silently diverge it from the committed branch.
EXCLUDE = {"cleanup.json", "session.json", "write_diff.patch"}

MIN_PATH_LEN = 4  # never substitute a path short enough to match incidentally


def substitutions(root):
    """(literal, placeholder) pairs, longest path first so a harness root
    nested under the home directory wins over the home directory itself."""
    paths = []
    for path, placeholder in ((root, "<harness-root>"), (Path.home(), "<home>")):
        if path is None:
            continue
        text = str(Path(path).resolve())
        if len(text) >= MIN_PATH_LEN:
            paths.append((text, placeholder))
    paths.sort(key=lambda p: len(p[0]), reverse=True)

    pairs = []
    for text, placeholder in paths:
        # The same path shows up in three forms: raw, backslash-escaped (JSON
        # serialization), and forward-slashed (git, Path.as_posix()).
        for variant in (text.replace("\\", "\\\\"), text, text.replace("\\", "/")):
            pairs.append((variant, placeholder))
    return pairs


def redact(text, root):
    for literal, placeholder in substitutions(root):
        text = text.replace(literal, placeholder)
    return text


def run_dir(path, root):
    """Redact every committed artifact in a run directory. Files only — the
    workspace and worktree subdirs are gitignored and left untouched. Returns
    the names of the files rewritten."""
    pairs = substitutions(root)
    changed = []
    for f in sorted(Path(path).iterdir()):
        if not f.is_file() or f.name in EXCLUDE:
            continue
        try:
            before = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable artifact: nothing to redact
        after = before
        for literal, placeholder in pairs:
            after = after.replace(literal, placeholder)
        if after != before:
            f.write_text(after, encoding="utf-8", newline="\n")
            changed.append(f.name)
    return changed
