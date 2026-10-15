---
title: How Agent-12 works, runner, adapters, filesystem judges and the validation gate
description: Architecture of the Agent-12 local agent benchmark, read from the code. How a run creates sandboxes, calls an agent through an adapter, judges the files it leaves, validates every judge, and renders the leaderboard.
---

# How it works

## The pieces

```text
configs/models.json ──► runner.py ──► adapters/ (anvil | anvil_dflash | command)
                          │                  │
                          │                  ▼
                          │           the agent works in sandboxes/<run>/<task>/
                          ▼
                    tasks/easy.py, tasks/hard.py
                    setup() ─► agent ─► check()   (the judge reads the sandbox)
                          │
                          ▼
                    results/<run>.json, logs/<run>/<task>.log
                          │
          site/meta.json ─┴─► build_site.py ─► docs/index.html (the leaderboard)

validate_judges.py: runs every task's good, bad and good+BOM solutions
                    against its judge before any of the above counts
```

## A run, step by step

From `runner.py`:

1. Warn if the interpreter is below the Python floor (`envcheck.py`).
2. If `--model` is given, apply that entry's `env` block from the config.
3. Load the suite and apply its caps (`AGENT_MAX_TOKENS`, `AGENT_MAX_STEPS`,
   `AGENT_BASH_TIMEOUT`) plus `AGENT_TEMP=0.0`, without overriding values
   already set.
4. Load the adapter once and time it (`load_s`). Model load is not counted in
   task time.
5. For each task: delete and recreate `sandboxes/<run>/<task>/`, run the
   task's `setup()`, pin hashes if the task has a `pin()`, `chdir` into the
   sandbox, `reset()` the adapter, and run the agent on the prompt.
6. Return to the repo root and call the task's `check()` on the sandbox. A
   judge that crashes counts as a fail with detail `checker: <ExceptionType>`.
   An adapter exception is recorded in `error`, and the judge still runs.
7. Write `results/<run>.json` and exit with `os._exit(0)`, because MLX
   teardown can hang and the results are already on disk.

## Adapters

`adapters/__init__.py` defines the contract. The runner guarantees the
working directory is the task sandbox before `run()`, and calls `reset()`
between tasks.

| Method | Purpose |
|---|---|
| `load()` | Load the model or start the engine, once per run. |
| `reset()` | Wipe conversation state between tasks. |
| `run(prompt)` | Run one agent episode to completion in the current directory. |
| `info()` | Return `model`, `dialect`, `backend`, `prompt_file` for the result file. |
| `close()` | Release any seats or leases. |

- **`anvil`** imports Anvil's `agent.py` from `AGENT12_ENGINE_DIR`. If Anvil
  reports an `http` backend it uses `agent.HTTPEngine`, otherwise it takes a
  seat and uses `agent.MLXEngine`. Output is captured from stdout.
- **`anvil_dflash`** keeps the same Anvil prompt, tools, parser and loop but
  swaps generation for `dflash_generate` from mlx-dspark, with a drafter
  model. Its docstring explains that greedy speculative decoding verifies
  every token, so accuracy should match a plain greedy run and only speed
  changes. It caps the MLX buffer cache at 2 GB and clears it after each turn,
  because without the cap the process went past 100 GB on 2026-09-19. This
  path has no cross-turn KV prefix reuse, so every turn re-prefills the
  transcript.
- **`command`** runs `AGENT12_CMD` through the shell with `{prompt}`
  replaced, and stores stdout plus stderr as the log. It has nothing to load
  or reset; if your CLI reloads weights on every call, that time lands in
  every task.

## Tasks and judges

A task (`tasks/__init__.py`) is a `name`, a `prompt`, and five functions:
`setup(d)` builds the starting files, `check(d)` is the judge, `good(d)` and
`bad(d)` are reference solutions, and optional `pin(d)` runs after setup.

The judges inspect the filesystem. Where code has to run, they run it with
`sys.executable` in a subprocess with the sandbox as working directory. The
model's own description of its work is never read.

Judges read answer files through `tasks.answer_text()`, which opens them as
`utf-8-sig`. That drops a leading UTF-8 BOM and nothing else; code fences and
prefixes like `Answer:` are still content and still graded.

Anti-cheat details in the hard suite, from `tasks/hard.py`:

- `h2_fix_iteration_bug` and `h8_cache_collision` pin the SHA-256 of their
  test file. A changed test file fails with `test file was modified`.
- `h4_csv_no_csv` fails with `used the banned csv module` if the solution
  uses Python's `csv` module.
- `h8_cache_collision` fails with `memoization was removed` if the cache was
  deleted instead of fixed.

### The suites

**easy** (12): `t01_create_run`, `t02_fix_bug`, `t03_rename_across_files`,
`t04_extract_value`, `t05_find_marker`, `t06_precise_append`,
`t07_write_json`, `t08_tricky_escapes`, `t09_count_files`,
`t10_extract_constant`, `t11_csv_sum`, `t12_delete_right_file`.

**hard** (8): `h1_interval_merge`, `h2_fix_iteration_bug`,
`h3_lru_ttl_cache`, `h4_csv_no_csv`, `h5_topo_lex`, `h6_log_normalize`,
`h7_spec_gauntlet`, `h8_cache_collision`.

## The validation gate

`validate_judges.py` runs, for every task in both suites, in a temporary
directory:

- the known-good solution, which the judge must pass,
- the known-bad solution, which the judge must fail,
- the known-good solution again with a UTF-8 BOM prepended to every `.txt`
  or `.json` file it wrote (found by diffing the sandbox before and after),
  which the judge must still pass.

Any mismatch marks the judge `BROKEN` and the script exits 1. On this
branch, under Python 3.13, all 20 judges validate, and 7 of them (5 easy, 2
hard) get the BOM check because they write answer files.

The BOM check came from an outside report
([issue #3](https://github.com/nicedreamzapp/agent12/issues/3)): the
reference solutions were written in the same shape as the judges, so the
gate could not see a judge that graded form instead of meaning. Before the
fix, a BOM failed every correct answer on those 7 tasks.

## The interpreter is a grading condition

Because judges run the agent's code with `sys.executable`, the interpreter
that runs the harness decides which syntax a correct answer may use. This was
found when a correct `h5_topo_lex` solution annotated `list[str] | None`
failed on Python 3.9
([issue #1](https://github.com/nicedreamzapp/agent12/issues/1)). Since
harness 1.1.0, every result file records the interpreter, and
`validate_judges.py` refuses to run below 3.10.

## The harness is a variable

The scores on the board come from Anvil, which METHODOLOGY.md describes as a
~550-token-system-prompt terminal engine with per-model tool-call dialects.
A different harness gives different numbers for the same model. An
independent run in
[issue #1](https://github.com/nicedreamzapp/agent12/issues/1) measured
Qwen3.6-35B-A3B on an M5 Max at 12/12 in 72 s and 8/8 in 105 s through
Anvil, and 12/12 in 335 s and 6/8 in 310 s inside Claude Code as installed
with MCP servers connected. Other harnesses can be measured through the
`command` adapter and labeled as their own row.

## The leaderboard

`build_site.py` reads `site/meta.json`, loads each named result file, sums
the per-task seconds, and fills an HTML template with three tables: local
models, cloud reference, and vendor-reported numbers (credited and linked,
never mixed with Agent-12 scores). It writes `docs/index.html`.

## Contamination policy

CONTAMINATION.md describes three pools: the 20 public tasks in this repo, a
private held-out pool of matched tasks, and retired tasks. The held-out pool
is not in the repo, and `build_site.py` does not yet render the
contamination flag the policy describes, so board scores come from the 20
public tasks only.

## Visual benches

A separate set of tasks (`tasks/furball`, `tasks/spin`, `tasks/breakout`)
asks a model for one self-contained HTML file. `furball_bench.py` and
`showdown.py` load it in headless Brave over the Chrome DevTools Protocol,
install an error collector before the page's own script runs, take
screenshots, send synthetic mouse drags and key presses, and score the
result from pixel statistics computed through `ffmpeg`. The pass rules are on
the [Configuration](configuration.md#visual-bench-commands) page.
