---
title: Agent-12 quickstart, validate the judges and score your own agent
description: Run the Agent-12 judge gate in seconds, then score any agent CLI on the 12 easy and 8 hard tasks with the command adapter, and read the result JSON.
---

# Quickstart

Three steps. The first two work from a fresh clone with Python 3.10+.

## 1. Validate the judges

Always do this first. The runner does not check it for you.

```bash
python3 validate_judges.py
```

Each task is run three ways: the known-good solution (must pass), a
plausible known-bad one (must fail), and, for tasks that write a `.txt` or
`.json` answer, the known-good answer with a UTF-8 BOM in front (must still
pass). A healthy run ends with:

```text
All judges validated: every known-good passes (with or without a BOM), every known-bad fails.
```

If any judge is wrong it prints `BROKEN` on that row, then
`N BROKEN judge(s) — do not run the benchmark.` and exits with status 1.

## 2. Score your own agent CLI

The `command` adapter runs any shell command once per task, with the task's
sandbox as the working directory. `{prompt}` is replaced by the shell-quoted
task prompt.

```bash
AGENT12_CMD='your-agent --print {prompt}' \
AGENT12_MODEL_LABEL='your-model' \
  python3 runner.py --suite easy --adapter command --run yours_easy
```

Then the hard suite:

```bash
AGENT12_CMD='your-agent --print {prompt}' \
AGENT12_MODEL_LABEL='your-model' \
  python3 runner.py --suite hard --adapter command --run yours_hard
```

The command must exit when the agent is done. It is killed after
`AGENT12_CMD_TIMEOUT` seconds (default 600). The adapter's docstring gives
`claude -p {prompt} --dangerously-skip-permissions` as an example of a
comparison lane; that flag lets the agent act without asking, so only use it
inside the throwaway sandboxes.

While it runs you see one line per task:

```text
  PASS  t01_create_run  (3.2s)
  FAIL  t02_fix_bug  (12.9s)  [some judge detail]
SCORE 11/12 -> /path/to/agent12/results/yours_easy.json
```

(Timings above are illustrative, not a real run.)

## 3. Read the result

`results/<run>.json` holds the score, per-task pass/fail, seconds, judge
detail, any adapter error, the harness version and the interpreter that
judged it. The agent's output for each task is in `logs/<run>/<task>.log`,
and the sandbox it worked in is kept in `sandboxes/<run>/<task>/` until the
next run with the same name. `logs/` and `sandboxes/` are in `.gitignore`.

## Running a configured model (needs Anvil)

The board rows come from entries in `configs/models.json`, run through the
Anvil engine:

```bash
python3 runner.py --suite easy --model qwen3-coder-30b --run qwen30_easy
python3 runner.py --suite hard --model qwen3-coder-30b --run qwen30_hard
```

This needs the Anvil engine, MLX on Apple silicon and the weights; see
[Install](install.md#about-the-anvil-engine).

## Report your result

If you ran it on your own hardware, open an
[issue](https://github.com/nicedreamzapp/agent12/issues/new) with your chip,
RAM, serving stack, model, quant and score. Reports of a judge failing a
correct answer are especially useful.
