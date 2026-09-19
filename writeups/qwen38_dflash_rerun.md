# Qwen3.8-27B with the DFlash 2 drafter: the rerun

*Run 2026-09-19 on the M5 (Apple M5 Max, 128 GB). Same lmstudio-community 8-bit weights,
same Anvil engine, same tasks and judges as the 2026-08-18 runs in
`qwen38_vs_qwen36.md`. The only thing that moved: generation goes through mlx-dspark 0.14's
DFlash speculative decoding with `incoai/Qwen3.8-27B-DFlash2` as the drafter.*

## Headline

**The drafter makes Qwen3.8 about 3x faster on this benchmark. It is still about 3x slower
than Qwen3.6-35B-A3B.**

| run | Qwen3.8 8-bit, no drafter (08-18) | Qwen3.8 8-bit + DFlash 2 (09-19) | Qwen3.6-35B-A3B 8-bit (08-18) |
|---|---|---|---|
| easy (12 tasks) | 12/12, 350.7s | **12/12, 122.0s** | 12/12, 64.2s |
| hard, standard budget | 6/8 1031.0s · 7/8 1155.9s | **7/8, 401.4s** | 8/8, 125.2s |
| hard, big budget, tasks h1-h6 | 6/6, 1197.8s | **6/6, 243.5s** | 6/6, 96.1s |
| hard, big budget, h7-h8 | 2/2 (h7 took 754s) | **not finished** (see below) | 2/2, 26.2s |

Speed-ups against the plain 3.8 runs: easy 2.9x, hard standard 2.6-2.9x, big-budget h1-h6 4.9x.
Against Qwen3.6: easy 1.9x slower, hard standard 3.2x slower, big-budget h1-h6 2.5x slower.

Accuracy did not change in any way that matters: 12/12 easy both ways, 7/8 hard (the same
score as the 08-18 s2 sweep). The one hard failure this time was `h1_interval_merge`: the
model wrote its own 30-case test file, passed it, and still failed the judge, because its
own tests merged touching integer intervals like [1,2] and [3,4], which the spec does not
ask for. That is a model mistake, not an infrastructure one. With the big budget it passed h1.

Generation speed inside the benchmark, prefill included (see the limitation below):
20.2 tok/s on easy and 28.7 tok/s on hard, mean acceptance 6.4-6.8 tokens per target
forward. The standalone number from 2026-08-20 (`project_qwen38_fast_on_m5`) was
17.9 -> 39.9 tok/s for pure generation on a short prompt.

## What did not finish, and why

The big-budget hard run passed h1 through h6 in 243.5s, then spent 14 minutes on
`h7_spec_gauntlet` without finishing. At 03:32 a LatentSync render started on the same
machine, the box went into heavy swap (up to 10 GB/min), the benchmark process was swapped
out, and the run was stopped at 03:45 so it would not keep starving that render.
The 08-18 no-drafter run needed 754s for h7 at this budget, so h7 being long is expected;
an h7/h8 result at the big budget still needs a run on a quiet machine.

## Two things that went wrong on the way (kept in `results/archive/`)

1. **mlx-dspark's server prefix cache crashes on this model.** The first attempt served the
   model with `mlx-dspark serve` and pointed Anvil's http backend at it. Mid-run the drafter's
   rotating KV cache raised `ValueError: [full] Negative dimensions not allowed` on a
   prefix-cache restore, and the server died. Those runs are archived as `*_prefixcache.json`
   and are not comparable. The runs above use an in-process adapter
   (`adapters/anvil_dflash.py`) that calls `dflash_generate` with no cross-turn cache.
2. **Without a cache limit MLX kept every freed prefill buffer**, and the first in-process
   run grew past 100 GB, put the box into swap and was paused twice by forge_guard. Those
   runs are archived as `*_swapcontaminated.json`. The adapter now caps the MLX buffer cache
   at 2 GB and clears it after every turn; the final runs had no pauses or overruns.

## Limitation of this comparison

The plain Anvil engine reuses the KV cache across turns and only prefills what is new. The
DFlash adapter re-prefills the whole transcript every turn, because mlx-dspark's reusable
cache is the path that crashed. That costs the DFlash runs time and never accuracy. The
speed-ups above are therefore a floor: a DFlash path with working prefix reuse would be
faster, especially on long multi-turn tasks like h7.

## Bottom line

On this machine the drafter closes a lot of the gap but not all of it. Qwen3.6-35B-A3B is
still about 3x faster with a perfect hard score. Qwen3.8 + DFlash is now a
reasonable choice (12/12 and 7/8 at roughly 3x the old speed), not a 17x penalty.

Files: `results/qwen38_8bit_dflash_easy_v1.json`, `results/qwen38_8bit_dflash_hard_v1.json`,
adapter `adapters/anvil_dflash.py`, runner script `run_qwen38_dflash.sh`, config
`qwen3.8-27b-8bit-dflash` in `configs/models.json`.
