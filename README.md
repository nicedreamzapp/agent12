# Agent-12 — the local agent leaderboard

**Which model can actually be your agent on your own hardware?**

Not "which model scores highest on trivia" — which model, running locally on a
machine you can buy, will reliably create the file, fix the bug, rename the
function, and delete the *right* backup. Agent-12 measures that by making
models DO real agent tasks in a sandbox, judged by the filesystem, never by
their prose.

**Run the winner:** every model on this board plugs straight into
[Claude Code Local](https://github.com/nicedreamzapp/claude-code-local) — Claude Code,
100% on-device on Apple Silicon. Live board: [nicedreamzapp.github.io/agent12](https://nicedreamzapp.github.io/agent12/).
MLX builds of the fighters: [huggingface.co/divinetribe](https://huggingface.co/divinetribe).

## What makes this benchmark different

1. **It runs on consumer hardware.** Every local row on the scoreboard was
   produced on a single Apple-silicon machine you can put on a desk. Rows
   report score, wall-clock seconds, and the hardware that produced them.
2. **The harness is part of the experiment.** The same model can score 12/12
   in a lean, per-model-tuned harness and spiral for an hour inside a heavy
   one (7,800-token system prompt, 66 tools). Most benchmarks hide this
   variable; Agent-12 controls it. The reference harness is a ~550-token
   native terminal engine with per-model tool-call dialects; any other
   harness can be plugged in through the `command` adapter and labeled as
   its own row.
3. **Every judge is validated before it judges.** `validate_judges.py` runs a
   known-good reference solution (must pass) and a plausible known-bad
   attempt (must fail) against every task's judge. A judge that fails either
   direction blocks the run. This gate has already caught one of our own
   judges demanding behavior that contradicted its own task spec.

## The suites

- **easy (12 tasks)** — everyday agent work: create/run a file, fix a failing
  test, rename across files, extract a config value, precise edits, tricky
  escapes, counting, CSV summing, deleting exactly the right file.
- **hard (8 tasks)** — reasoning under spec pressure: interval merging with
  edge cases, multi-bug debugging with a hash-pinned test file, an LRU+TTL
  cache, CSV parsing with the csv module banned, lexicographic toposort,
  timestamp normalization, a 10-rule validation gauntlet, and a cache-key
  collision hidden behind a red herring.

Anti-cheat: tasks that ship a test file pin its hash — editing the test
scores zero. Judges run the model's artifacts in a fresh subprocess.

## Running it

```bash
# 1. validate the judges (required — the runner assumes this passed)
python3 validate_judges.py

# 2. run a configured model through the reference engine
python3 runner.py --suite easy --model qwen3-coder-30b --run qwen30_easy
python3 runner.py --suite hard --model qwen3-coder-30b --run qwen30_hard

# 3. or plug in ANY agent CLI (it gets the same sandboxes and judges)
AGENT12_CMD='your-agent --print {prompt}' AGENT12_MODEL_LABEL='your-model' \
  python3 runner.py --suite easy --adapter command --run yours_easy
```

Discipline: temperature 0, fixed step/token caps per suite, fresh sandbox and
fresh conversation per task, one variable moved per comparison.

## Docs

- [METHODOLOGY.md](METHODOLOGY.md) — how scoring, judging, and validation work
- [CONTAMINATION.md](CONTAMINATION.md) — public vs held-out tasks, rotation policy

## License

MIT.
