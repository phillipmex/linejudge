# OperationalError: cannot VACUUM from within a transaction

GitHub issue #479 — https://github.com/simonw/sqlite-utils/issues/479

Maybe when calling `.vacuum()` and other DB-level write-lock operations `sqlite_utils` could guard against this error message by automatically committing first?

```
     46 db["media"].optimize()  # type: ignore
---> 47 db.vacuum()

File ~/.local/lib/python3.10/site-packages/sqlite_utils/db.py:1047, in Database.vacuum(self)
   1045 def vacuum(self):
   1046     "Run a SQLite ``VACUUM`` against the database."
-> 1047     self.execute("VACUUM;")

File ~/.local/lib/python3.10/site-packages/sqlite_utils/db.py:470, in Database.execute(self, sql, parameters)
    468     return self.conn.execute(sql, parameters)
    469 else:
--> 470     return self.conn.execute(sql)

OperationalError: cannot VACUUM from within a transaction
```

It might also be nice to add a sentence or two about how transactions are committed on the [docs page](https://sqlite-utils.datasette.io/en/latest/python-api.html#detect-fts). When I was swapping out my sqlite3 code for this library it was nice that everything was pretty much drop-in but I was/am unsure what to do about the places I explicitly call `.commit()` in my code

Related to https://github.com/simonw/sqlite-utils/issues/121

## Write access

Make your changes inside this directory — it is an isolated git worktree of the target repo:
- <harness-root>\runs\20260720-235940-issue-479-operationalerror-cannot-vacuum-from-with\write_worktree

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

