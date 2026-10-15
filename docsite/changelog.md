---
title: Agent-12 changelog, from the git history
description: Dated history of the Agent-12 local LLM agent benchmark, built from the repository's git log. Harness versions, judge fixes, new model rows and writeups.
---

# Changelog

The repo has no release tags. This page is built from the git history on
`main`, grouped by date. `harness_version` is the value `runner.py` writes
into every result file.

## 2026-09-27

- README rewritten with a one-line summary, the results table, a list of what
  was built in this repo, and setup notes on what will not run from a fresh
  clone (`db0d4c8`, merged in #6).

## 2026-09-19

- Qwen3.8-27B 8-bit rerun with the DFlash 2 drafter through the new
  `anvil_dflash` adapter: 12/12 easy, 7/8 hard. About 3x faster than without
  the drafter and still about 3x slower than Qwen3.6-35B-A3B
  (`777e73e`, `writeups/qwen38_dflash_rerun.md`).
- Visual showdown, Qwen3.8-27B (DFlash 2) against Gemma 4 31B on fur ball,
  spin and breakout, with the new `showdown.py` breakout judge. Fixed
  `furball_bench.py` so spin is judged by its own rule instead of the fur
  ball rule (`20a5ad4`, `writeups/visual_showdown_2026-09-19.md`).
- README: credit for the reproduction in #1 and the Python 3.10 gate in #2
  (`a7f891a`), and how to report a result or a judge problem (`8a91fc4`).

## 2026-09-10

- Judges read answer files past a UTF-8 BOM through `tasks.answer_text()`,
  and `validate_judges.py` re-runs every known-good answer with a BOM so the
  gate can see this class of defect (`9b8144e`, merged in #4, reported in
  issue #3).
- Merged #2 from @galashko.

## 2026-09-09

- **harness 1.1.0.** Every result file records the interpreter (version,
  implementation, executable, floor, whether the floor was met), and
  `validate_judges.py` refuses to run below Python 3.10, with
  `AGENT12_MIN_PYTHON` to change the floor. Authored by Sergey Galashko
  (`e74a98b`).
- Leaderboard names the harness next to the local scores: Anvil, not Claude
  Code (`88991bf`).

## 2026-08-22

- Board: Qwen3.8-27B 8-bit row from its own runs, and a separate
  vendor-reported section for Muse Glimmer and Nemotron Omni, credited
  (`03462e0`).
- Board and README link to Claude Code Local and the MLX builds on Hugging
  Face (`82b0ba4`).

## 2026-08-10

- **harness 1.0.0.** First commit: easy and hard task suites, validated
  judges, adapter-based runner, methodology and contamination policy, and the
  leaderboard builder (`00cee6c`).
- Day-one scoreboard with 5 local configs on both suites, an HTTP engine
  adapter fix, and a lease name that works with the author's memory guard
  (`31be2ee`).
- Overnight repeat sweeps (3 to 4 runs per config), a tokens-per-second
  column, and the original DeepSeek V4 Flash quant retired (`e34cd30`).
- Claude cloud reference row: 20/20 (`4ac7bbc`).
- Leaderboard published on GitHub Pages from `docs/` (`9aa4fb4`).
