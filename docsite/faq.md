---
title: Agent-12 FAQ, local LLM agent benchmark questions
description: Answers about Agent-12, the local LLM agent benchmark. Which local model is best as an agent, why scores differ from Claude Code, how judging works, what hardware was used, and how to submit a result.
---

# FAQ

## Which local model does best?

Two local rows on the current board have a full score on both suites.
Qwen3.6-35B-A3B (MLX 8-bit) does it fastest: 12/12 easy in 64.2 s and 8/8
hard in 125.2 s. DeepSeek V4 Flash (2-bit) also scores 12/12 and 8/8, in
203.2 s and 550.8 s. See the [Home](index.md#current-scores) table and
the full leaderboard.

## Is this a Claude Code benchmark?

No. The local rows were measured in Agent-12's own reference harness, Anvil.
The same model inside Claude Code scores and times differently (measured in
[issue #1](https://github.com/nicedreamzapp/agent12/issues/1)). The
leaderboard links to
[Claude Code Local](https://github.com/nicedreamzapp/claude-code-local) as a
way to run these models, but the numbers are not Claude Code numbers.

## How is a task judged?

By the files the agent leaves in its sandbox. The judge reads them and runs
the code in a fresh subprocess. Nothing the model says about its own work is
used. See [How it works](how-it-works.md#tasks-and-judges).

## How do I know the judges are right?

Every judge is run against a known-good solution that must pass and a known
bad one that must fail, plus a BOM-prefixed copy of the good answer, by
`validate_judges.py`. The gate has caught real problems: a private version of
the `h3_lru_ttl_cache` probe demanded an eviction order that contradicted the
task's own spec (METHODOLOGY.md), and an outside report found 7 judges that
rejected correct answers with a BOM (issue #3).

## What hardware produced the numbers?

One Apple-silicon Mac with 128 GB of unified memory. `site/meta.json` says
"Apple M5, 128 GB unified memory"; the writeups say "M5 Max".
**TODO-VERIFY** the exact chip. The cloud reference row ran against the
Anthropic API.

## Can I run it on Linux or an NVIDIA GPU?

Judge validation and the `command` adapter are plain Python and should run
anywhere with Python 3.10+. They were run on Linux with Python 3.13 while
writing these docs. The board rows need the Anvil engine and MLX, which is
Apple silicon only. The visual benches hard-code the macOS Brave path.

## Why temperature 0?

To measure the deterministic path and move one variable at a time.
METHODOLOGY.md notes that a temp-0 single run does not measure the
distribution, and that some serving stacks are not bit-stable, so repeat runs
are kept (`_s2` to `_s4` result files).

## Why are some runs slow even when they pass?

Reasoning models can need many more tokens. Qwen3.8-27B 8-bit passes 8/8 hard
at an 8000-token, 40-step budget but took 2065.3 s against 122.3 s for
Qwen3.6-35B-A3B at the same budget (`results/qwen38_8bit_hard_bigbudget.json`,
`results/qwen36_hard_bigbudget.json`).

## Aren't 20 public tasks easy to train on?

Yes, and the repo says so. CONTAMINATION.md describes a private held-out
pool and task rotation. The held-out pool is not in the repo and its
contamination flag is not shown on the board yet.

## What about the vendor-reported section?

Those are numbers the model publishers report on their own benchmarks,
credited and linked. They are not Agent-12 scores and are not compared with
them. A model moves into the local table when it gets a real Agent-12 run.

## How do I submit a result?

Run it on your hardware and open an
[issue](https://github.com/nicedreamzapp/agent12/issues/new) with chip, RAM,
serving stack, model, quant and the score from your result file
([issue #5](https://github.com/nicedreamzapp/agent12/issues/5) asks for
exactly this). Contributors are credited in the README.

## What license is it under?

MIT. See `LICENSE`.
