## Learnings from previous runs

### issue-586-transform-fails-to-drop-column-if-table — SUCCESS (20260726-205109-issue-586-transform-fails-to-drop-column-if-table)

## What worked
- Root-causing via SQLite semantics (view re-resolution during table drop/rename in `transform_sql`) before touching code — let the fix target the actual mechanism instead of symptom-patching.
- Implementing the fix as an opt-in flag (`recreate_views=False` default) that exactly matches the fix already proposed in the issue thread — low-risk, preserves existing behavior for all other callers, no need to invent a new design.
- Threading the new parameter through both layers that need it (`Table.transform()` → `transform_sql()` → CLI `--recreate-views` flag) in one pass, plus docs in all three doc files, rather than doing it piecemeal.
- Writing tests that assert the exact generated SQL statement list for the dry-run path (`transform_sql(..., recreate_views=True)`) in addition to an end-to-end behavioral test — catches both wiring bugs and behavioral regressions.
- Confirming no regression by checking that `recreate_views=False` leaves generated SQL byte-for-byte identical to before, across all existing parametrized `transform_sql` cases.
- Adding both a Python-API test and a CLI test for the same feature, since the CLI wiring (flag parsing, threading into `--sql` vs executing paths) is a separate failure surface from the underlying library logic.

## What failed
- Could not execute `pytest`/`python` in the sandbox — same execution block seen in prior runs against this repo. Verification was static/hand-trace only, not run.

## Do differently next time
- This repo's sandbox reliably blocks `pytest`/`python` execution — don't spend time retrying it; go straight to static/hand-trace verification and clearly flag the recommended verification command for the operator, as was done here.
- When a GitHub issue already proposes a concrete workaround/API shape (e.g. "maybe a `recreate_views=True` argument"), adopt that shape directly rather than designing a new one — it's already been discussed with maintainers and reduces review friction.
- For any fix touching a rebuild-via-copy/drop/rename pattern (common in SQLite wrapper libraries), check specifically for view/trigger/foreign-key references to the table being rebuilt — these are the recurring class of bug in that pattern.

### issue-488-sqlite-utils-transform-should-set-empty — SUCCESS (20260726-204559-issue-488-sqlite-utils-transform-should-set-empty)

## What worked
- Correct root-cause diagnosis of `Table.transform_sql()`: SQLite affinity conversion silently fails on `""` for INTEGER/FLOAT/REAL columns, leaving the empty string in place instead of nulling it. Fixing by wrapping the source column in `nullif(col, '')` in the copy `SELECT` is a minimal, targeted change.
- Scoped the fix precisely: only columns present in `types=` whose resolved SQL type is INTEGER/FLOAT/REAL get wrapped, leaving unrelated SQL generation byte-for-byte identical — verified by hand-tracing against existing test parametrizations (rename, drop, pk, column_order) to confirm no incidental breakage.
- Updated existing SQL-generation test expectations rather than just adding a new test, and added one precise regression test reproducing the exact issue scenario (mixed populated/empty rows, two converted columns).
- Wrote a concrete operator-facing verification command (pytest invocation + CLI repro steps with expected output) since the sandbox couldn't run it.

## What failed
- `python`/`pytest` are blocked in this sandbox with no operator response to approve — this is a recurring, repo-wide constraint (confirmed across multiple prior runs), not one-off flakiness.

## Do differently next time
- Don't attempt to run `python`/`pytest` at all in this repo's sandbox — it's confirmed blocked; go straight to hand-tracing the SQL/logic and documenting the verification command for the operator, saving a wasted tool-call round trip.
- When touching `transform_sql()`, always re-check all existing parametrized test cases (pk/no-pk, rename/no-rename, column_order, drop) by hand for SQL-string diffs, since this generator is shared across many transform test permutations.

### issue-479-operationalerror-cannot-vacuum-from-with — FAILED (20260726-204351-issue-479-operationalerror-cannot-vacuum-from-with)

## What worked
- Root cause approach: routing the OperationalError through an existing guard (`_ensure_no_open_transaction`) into a clearer `TransactionError` is a good pattern — reuse existing error-handling primitives rather than inventing new ones.
- Mirroring an existing test (`enable_wal` transaction test) for the new `test_vacuum_inside_transaction_raises` test is a reasonable way to keep test style consistent when authoring blind.

## What failed
- No REPORT.md was written — this is an output-contract violation and the run is marked FAILED regardless of code quality. The final chat message is not a substitute for the required file.
- Test execution was reportedly blocked in the sandbox, and the agent proceeded with only static/hand-traced verification instead of flagging this as a blocker requiring resolution or escalation.

## Do differently next time
- Always write REPORT.md before finishing, even if the fix seems complete and was explained in the final message — the report is the actual deliverable, not a courtesy summary.
- If REPORT.md is meant to document verification steps (as claimed here — "notes the recommended command to confirm"), write it as part of the fix, not as an afterthought that gets skipped.
- When test execution is blocked in this sandbox (a recurring issue on this repo per the agent's own note — "as in prior runs on this repo"), treat that as a known environment constraint to document explicitly in REPORT.md up front, and consider whether there's a workaround (different test runner invocation, subset of tests) before defaulting to static-only verification.
- Treat "wrote the fix and explained it in chat" as incomplete until REPORT.md exists on disk — verify the file was actually created before reporting the task done.


# `table.get(column=value)` option for retrieving things not by their primary key

GitHub issue #588 — https://github.com/simonw/sqlite-utils/issues/588

This came up working on this feature:
- https://github.com/simonw/llm/pull/186

I have a table with this schema:
```sql
CREATE TABLE [collections] (
   [id] INTEGER PRIMARY KEY,
   [name] TEXT,
   [model] TEXT
);
CREATE UNIQUE INDEX [idx_collections_name]
    ON [collections] ([name]);
```
So the primary key is an integer (because it's going to have a huge number of rows foreign key related to it, and I don't want to store a larger text value thousands of times), but there is a unique constraint on the `name` - that would be the primary key column if not for all of those foreign keys.

Problem is, fetching the collection by name is actually pretty inconvenient.

Fetch by numeric ID:

```python
try:
    table["collections"].get(1)
except NotFoundError:
    # It doesn't exist
```
Fetching by name:
```python
def get_collection(db, collection):
    rows = db["collections"].rows_where("name = ?", [collection])
    try:
        return next(rows)
    except StopIteration:
        raise NotFoundError("Collection not found: {}".format(collection))
```
It would be neat if, for columns where we know that we should always get 0 or one result, we could do this instead:
```python
try:
    collection = table["collections"].get(name="entries")
except NotFoundError:
    # It doesn't exist
```
The existing `.get()` method doesn't have any non-positional arguments, so using `**kwargs` like that should work:

https://github.com/simonw/sqlite-utils/blob/1260bdc7bfe31c36c272572c6389125f8de6ef71/sqlite_utils/db.py#L1495

## Write access

Make your changes inside this directory — it is an isolated git worktree of the target repo:
- <harness-root>\runs\20260726-205912-issue-588-table-get-column-value-option-for-retrie\write_worktree

Do not run git commit/branch/merge yourself; the harness captures and commits your diff after you finish. REPORT.md still goes in your working directory, NOT in the worktree — keep the diff clean of harness artifacts.


## Notes

- Add or update a test that fails before your fix and passes after it.
- Keep the change minimal and scoped to this issue; do not reformat unrelated code.

## Output contract (required)

When you are done, write a file named REPORT.md in your working directory with:
- `## Status` — exactly one of SUCCESS or FAILED on the next line
- `## What I did` — short factual list
- `## Evidence` — how you checked it works (commands run, files produced)

Your REPORT.md is a claim, not a verdict: the harness runs its own verifiers
after you finish. A missing REPORT.md fails the run regardless of your work.

