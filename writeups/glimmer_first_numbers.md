# Meta Muse Glimmer 30B — First Independent Agent Numbers

*Draft — architecture and methodology are final and verified. Benchmark
numbers land the day the MLX runtime adds Glimmer support; the run is
automated and will fill the table below.*

## What it is (verified, not marketing)

Meta released Muse Glimmer on 2026-08-10 under Apache 2.0 — a genuinely open,
30-billion-parameter agentic model built to run on one consumer machine. These
specs are read straight from the model's own config, not the press release:

**Language model**
- 52 transformer layers, hidden size 6,656, intermediate size 19,968
- 32 attention heads over just 2 key/value heads (aggressive grouped-query
  attention — cheap KV cache, which is how it fits agent-length context on a
  laptop)
- 202,048-token vocabulary
- 131,072-token context window
- 2,048-token sliding-window attention on local layers

**Vision encoder** (bolted to the language model — Glimmer is multimodal)
- 50 layers, hidden size 1,536

## Why bother benchmarking it ourselves

Meta's own chart says Glimmer beats Qwen3.6-27B and Gemma-4-31B on agent
suites. Every model launch claims this. Nobody had run it on an independent,
harness-controlled agentic benchmark as of launch day. That's the gap this
fills — and the harness matters more than the model, which is the whole thesis
of this leaderboard.

## Method

Same harness every model on this board runs through:

- **Suites:** the Agent-12 easy (12 tasks) and hard (8 tasks) sets — real
  end-to-end terminal-agent work (file edits, multi-step tool use, verified
  outputs), not multiple-choice trivia.
- **Engine:** the lean native agent (Anvil), identical system prompt and tool
  set every model gets — a benchmark run is the exact code path a user types
  into.
- **Settings:** temperature 0, 3 repeat sweeps, scored by the fixed
  `validate_judges.py` gate (the one whose broken h3 probe was fixed 2026-08-10,
  so these numbers are clean).
- **Quant:** Glimmer runs at **full precision (bf16)** — the true, uncompressed
  model, no quantization loss. Note this is a deliberate handicap in Glimmer's
  favor: the other local models on the board ran quantized (Qwen at 8-bit,
  Gemma at 4-bit), so if anything Glimmer gets the more forgiving setup here.
  Called out plainly so the comparison is honest.

## Results

| Model | Easy | Hard | tok/s | Notes |
|---|---|---|---|---|
| Qwen3.6-35B *(current champ)* | 12/12 | 8/8 | 46 | clean sweep every run |
| Qwen3-Coder-30B | 12/12 | 7/8 | 84 | fastest; fails h4 banned-csv |
| Gemma-4-31B | 11–12/12 | 7–8/8 | 26 | flaky on t03 rename |
| Claude (cloud reference) | 12/12 | 8/8 | — | 20/20 but slower wall-clock than champ |
| **Muse Glimmer 30B** | **pending** | **pending** | **pending** | run auto-fires on MLX support |

Wall-clock reference from the champ run: Qwen3.6-35B did easy in 64s vs cloud
Claude's 122s, hard in 125s vs 131s — the local champ's headline was beating
cloud on latency, not just scoring.

## Status note

Glimmer's architecture is one day old. As of 2026-08-11 the MLX runtime
(`mlx_lm` 0.31.3, latest on PyPI) does not yet recognize `model_type:
muse_glimmer` — confirmed by direct test. The model loads and runs correctly
under PyTorch/transformers 5.15, but that path is too slow on Apple Silicon for
a reliable full agentic sweep. A watcher checks daily for MLX support and runs
the full 3-sweep gauntlet automatically the moment it lands, so these numbers
are apples-to-apples with the rest of the board rather than run on a different
engine.
