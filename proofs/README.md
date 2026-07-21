# Proof harness

Turns a real repo's open GitHub issues into linejudge goals, runs them through
the harness, and renders the results as `PROOF.md`. The point is not that an
agent can write code — it is that every result carries an *independent* verdict
the agent had no hand in.

Nothing here calls a model API until you run `linejudge run`. Generating goals
and inspecting them costs nothing.

## 1. Prepare a target

Clone the repo the agent will work on, and build an environment its test suite
runs in. Both live outside version control (see `.gitignore`).

```
git clone https://github.com/OWNER/NAME proofs/targets/NAME
python -m venv proofs/targets/venv
proofs/targets/venv/Scripts/python -m pip install -e proofs/targets/NAME
proofs/targets/venv/Scripts/python -m pip install pytest      # plus test deps
```

Run the suite once before generating anything. **A target whose baseline is not
green cannot produce a meaningful verdict** — you would be scoring the agent
against failures it did not cause.

## 2. Generate goals

```
python proofs/generate.py \
  --repo OWNER/NAME --limit 8 --out proofs/goals-NAME \
  --write-repo /abs/path/to/proofs/targets/NAME \
  --timeout 900 \
  --verifier "command: /abs/path/to/proofs/targets/venv/Scripts/python.exe -m pytest -q" \
  --verifier "diff_constraints: max_files=10 max_lines=800 deny=.github/*" \
  --note "Add or update a test that fails before your fix and passes after it."
```

Use `--from-json issues.json` instead of `--repo` to curate the issue list by
hand (recommended — see below).

**Curate before you spend.** `gh issue list` returns whatever is open, which
includes issues already fixed since they were filed, design debates with no
correct answer, and requests needing project context no agent has. Check each
candidate against the current source and drop the stale ones; a bogus task
teaches you nothing and still costs a full run.

## 3. Run and render

```
linejudge run proofs/goals-NAME/<goal>.md      # one run per goal
python proofs/stats.py --root . > PROOF.md
```

## Rehearse before you spend

With neither `ANTHROPIC_API_KEY` nor `CLAUDE_CONFIG_DIR` set, `claude -p` bills
whatever account is logged in — a Pro/Max subscription, if you have one. Running
one or two goals that way costs nothing and exercises the whole chain against a
real agent: worktree creation, diff capture, verifier execution, ledger write.

The catch is the ledger. `total_cost_usd` in the JSON envelope is what the tokens
*would* have cost at API rates; on a subscription no such money is spent, so those
figures are notional and must not be published as costs. Move `runs/ledger.jsonl`
aside after a rehearsal so the paid run starts from an empty ledger.

Note that `.env.local` is overlaid onto the agent subprocess's environment. Keep
release credentials and anything else the agent has no business reading somewhere
else.

`demo.py` performs this whole loop against `fixtures/issues.json` with the
MockAdapter, including an agent that lies about success — useful for checking
the pipeline end to end without an API key.

## What the verdict does and does not prove

The default verifier pair asserts two things: the target's full suite is green
in the agent's worktree, and the change stayed inside its blast radius. That is
strictly stronger than the agent's own claim, and it catches the common failure
modes — a broken build, a fix that regresses something else, a run that touched
files it had no business touching, an agent that changed nothing at all.

It is *not* proof the reported bug is fixed. A pre-existing suite passes on
unfixed code too. Requiring a regression test (the `--note` above) shifts the
odds, but nothing here verifies that the new test genuinely failed beforehand.
Read the diffs — `linejudge dashboard` exists for exactly that, and the
approve/reject decision it records is the human half of the verdict.

Claiming more than this would be the sort of thing linejudge was built to catch.
