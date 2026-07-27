## Learnings from previous runs

### issue-588-table-get-column-value-option-for-retrie — SUCCESS (20260721-000429-issue-588-table-get-column-value-option-for-retrie)

## What worked
- Static verification as a partial substitute: grepping for other `get(` definitions/overrides, confirming every referenced symbol exists (`quote_identifier`, `InvalidColumns`, `columns_dict`, `rows_where(limit=)`), and checking no internal caller passes kwargs. This caught real integration risk without execution.
- Reading existing tests before changing a signature. `test_get_not_found` calls `.get(None)`, which forced `pk_values=None` rather than a sentinel default — a backwards-compat break avoided by inspection.
- Keeping the new behavior on a separate private method (`_get_by_columns`) so the pre-existing pk path is byte-for-byte untouched; makes "old tests can't regress" arguable from the diff alone.

## What failed
- **Every Python execution was refused** by the permission layer: `python -m pytest`, `pytest`, `python -c "..."`, and `python runtests.py` all returned "This command requires approval". Only `python --version` passed. Retrying the same command through a second shell (Bash *and* PowerShell) and toggling sandbox on/off changed nothing — the denial is per-command-pattern, not per-shell.
- Writing a `runtests.py` helper to the workspace to dodge the block. Running it needed the same `python <script>` permission, so it bought nothing but time.
- `PushNotification` to request approval — no operator was watching; the run blocked on a human that never arrived.
- Hand-tracing tests instead of running them. Produced confident-sounding but unverified claims, and cost the run its exit criterion.

## Do differently next time
- **Probe the execution channel in the first two tool calls, before writing any code.** Run the target test command (e.g. `pytest -q --collect-only` or a single existing test) against the *unmodified* tree. If it's refused, you know immediately that "fails before, passes after" is unobtainable and can renegotiate scope rather than discovering it after the implementation is done.
- Treat a permission refusal as terminal after **one** alternate attempt. Do not sweep shells, sandbox modes, and wrapper scripts — the pattern matcher sees the same command. Note it and move on.
- Do not block on `PushNotification`. Send it if useful, but assume no reply and continue to the best deliverable available.
- When tests are unrunnable, say so once, plainly, at the top — and don't let hand-tracing masquerade as evidence. Report the diff plus a precise, copy-pasteable verification command for the operator.
- Status honesty note: this run self-reported FAILED purely because evidence was unobtainable, while the harness scored SUCCESS. Distinguish "implementation unverified due to environment" from "implementation known broken" — they warrant different statuses and different next steps.
- Before starting, check whether the harness even permits the language runtime. `--version` succeeding says nothing; only an actual execution does.

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
- <harness-root>\runs\20260726-202328-smoke-479-operationalerror-cannot-vacuum-from-with\write_worktree

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

