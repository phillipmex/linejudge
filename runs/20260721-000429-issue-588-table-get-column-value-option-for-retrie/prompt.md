## Learnings from previous runs

### issue-479-operationalerror-cannot-vacuum-from-with — SUCCESS (20260720-235940-issue-479-operationalerror-cannot-vacuum-from-with)

## What worked
- Following the repo's own documented policy instead of inventing behavior: the codebase states "the library will never commit a transaction you opened", so raising `TransactionError` (mirroring the existing `enable_wal()`/`disable_wal()` guards) was the defensible fix over auto-committing. Look for an existing analogous guard in the same file and copy its shape.
- Auditing every internal caller of the changed function before changing its contract (`db.py`, three `cli.py` commands) and checking whether any existing test exercises the old path. This caught that a migrations test uses raw `db.execute("VACUUM")` and is unaffected.
- Parametrizing the new test over both entry points (`db.begin()` and `db.atomic()`) and asserting the transaction is still usable afterward — the guard's whole point is that it doesn't destroy caller state.
- Honestly reporting FAILED when verification was impossible rather than claiming an unverified fix works.

## What failed
- Every Python invocation was blocked by the permission layer — `pytest`, `python -c "print(1)"`, even `python -V` — via both Bash and PowerShell, sandbox on and off. This was discovered only at the end, after all code was written, so the run produced an unverifiable change.
- Repeatedly retrying the same blocked capability in slightly different forms (different runners, different shells, sandbox toggled) burned effort without changing the outcome. A denied call means the capability is denied, not that the invocation was malformed.

## Do differently next time
- **Probe the toolchain in the first two tool calls.** Run the cheapest possible smoke test (`python -V`, `pytest --version`, or whatever the project's runner is) *before* writing any code. If it's blocked, you know immediately that "fails before, passes after" is unreachable and can plan around it.
- **If execution is blocked, say so up front and ask** — use PushNotification to surface the block rather than writing the whole change and discovering it's unverifiable at report time. The user may be able to approve the command in seconds.
- **Budget at most one retry per blocked capability**, ideally in a different mechanism (e.g. Bash vs PowerShell) — then stop and treat it as a hard constraint.
- **When tests can't run, maximize static evidence**: hand-trace the new code path against the test's assertions, confirm imports/symbols actually exist (`TransactionError` is really exported), and grep for every call site of the changed function. State explicitly in the report which assertions were traced by hand vs executed.
- Keep the FAILED-on-unverified convention. A green-sounding report on an unrun test is worse than an honest failure.


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
- <harness-root>\runs\20260721-000429-issue-588-table-get-column-value-option-for-retrie\write_worktree

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

