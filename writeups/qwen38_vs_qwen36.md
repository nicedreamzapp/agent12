# Qwen3.8-27B vs Qwen3.6-35B-A3B — the challenger loses, but not for the reason we first thought

*Run 2026-08-18 on the M5. Two builds tested: an obscure 4-bit quant, then the
community-standard 8-bit for a fair rematch. Same harness (anvil), same tasks,
same judges as every other row on the board.*

## Headline (FINAL — settled by the equal-budget run)

**Qwen3.6-35B-A3B keeps the crown, and it is not close.** At an equal, generous
reasoning budget (`AGENT_MAX_TOKENS=8000`, `AGENT_MAX_STEPS=40`) both models
score a **perfect 8/8** on the hard suite. The entire difference is wall-clock:

| model | hard suite | total time | per task |
|---|---|---|---|
| **Qwen3.6-35B-A3B (8-bit)** | **8/8** | **122.3s** | 15.3s |
| Qwen3.8-27B (8-bit) | 8/8 | 2065.3s | 258.2s |
| | | | **16.9x slower** |

Identical accuracy, **16.9x the wall-clock**. Qwen3.8 buys nothing. It earns no
launcher and no place on this machine.

### The important correction

Under the suite's standard discipline (3000 tokens) Qwen3.8 scored 89.3% and
looked less capable. **It is not less capable.** Both of its apparent failures
were the token cap cutting off a `<think>`-block reasoning model mid-thought —
`h3_lru_ttl_cache` needed 613s and `h7_spec_gauntlet` needed 754s to finish, and
both then passed cleanly. The public reception of Qwen3.8-27B as a strong
agentic coder is **not wrong**. It is simply far too slow to be the daily driver
on this hardware, and its capability advantage evaporates once Qwen3.6 is given
the same room (3.6 goes from 31/32 to 8/8).

| model | total | speed (avg/hard task) |
|---|---|---|
| Claude (cloud reference) | 20/20 (100%) | — |
| **Qwen3.6-35B-A3B (8-bit)** | **91/92 (98.8%)** | **17.6s** |
| DeepSeek V4 Flash (2-bit) | 71/72 (98.6%) | — |
| Gemma 4 31B (4-bit) | 69/72 (95.8%) | — |
| Qwen3-Coder-30B (8-bit) | 69/72 (95.8%) | — |
| Qwen3.8-27B (**8-bit**, fair build) | 25/28 (89.3%) | 136.7s |
| Qwen3.8-27B (4-bit, EigenLabs) | 23/28 (82.1%) | 91.3s |

## The naming traps (read the configs, not the model cards)

**1. Qwen3.8-27B is not the successor to Qwen3.6-35B-A3B.**

| model | architecture class | shape |
|---|---|---|
| Qwen3.6-35B-A3B | `Qwen3_5MoeForConditionalGeneration` | MoE, ~3B active/token |
| Qwen3.6-27B | `Qwen3_5ForConditionalGeneration` | dense |
| **Qwen3.8-27B** | `Qwen3_5ForConditionalGeneration` | **dense** |
| Qwen3.8-2.4T-A95B | `Qwen3_5MoeForCausalLM` | MoE, 512 experts, 10 active |

The 3.8 line ships 2B, 4B, 9B, 27B, then jumps to 2.4T. There is **no mid-size
3.8 MoE**. The like-for-like successor to our champion is the 2.4T model, which
is datacenter-only. The 27B we can run succeeds Qwen3.6-**27B**, the dense
sibling we never benched.

**2. Parameter count is backwards here.** A dense 27B does all 27B of work per
token; the 35B-A3B does ~3B. The "smaller" model does roughly 9x the computation
per token — which is exactly the wall-clock above.

## The quantization question, answered properly

The first run used `EigenLabs/Qwen3.8-27B-4bit` — **515 downloads, 0 likes,
uploaded the same day the model launched**. Our Qwen3.6 is `lmstudio-community`
8-bit (161k downloads). That was not a fair fight, so we downloaded
`lmstudio-community/Qwen3.8-27B-MLX-8bit` (same packager, same bit depth) and
re-ran everything.

**Quantization mattered, but not enough to change the verdict:** 82.1% → 89.3%.
Still 9.5 points behind Qwen3.6, and the better build is *slower* (136.7s vs
91.3s per hard task) because there is twice as much weight data to move.

## The two failures, and why they are different

| task | 4-bit v1 | 4-bit s2 | 8-bit v1 | 8-bit s2 |
|---|---|---|---|---|
| h1_interval_merge | PASS 116.5s | PASS 86.6s | PASS 196.0s | PASS 141.3s |
| h2_fix_iteration_bug | PASS 50.3s | PASS 41.0s | PASS 47.3s | PASS 92.2s |
| **h3_lru_ttl_cache** | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| h4_csv_no_csv | PASS 87.3s | **FAIL** | PASS 77.7s | PASS 130.7s |
| h5_topo_lex | PASS 94.0s | PASS 61.6s | PASS 133.6s | PASS 84.6s |
| h6_log_normalize | PASS 77.5s | PASS 105.3s | PASS 116.4s | PASS 119.2s |
| **h7_spec_gauntlet** | FAIL `0/10` | FAIL `0/10` | FAIL `0/10` | **PASS `10/10`** 310.1s |
| h8_cache_collision | PASS 60.1s | PASS 181.0s | PASS 124.2s | PASS 112.9s |
| | 6/8 | 5/8 | 6/8 | **7/8** |

**h3_lru_ttl_cache is the real failure** — 4 for 4 across both builds. Qwen3.6
passes it 4 for 4. This is a genuine capability gap, not noise.

**h7_spec_gauntlet is a budget problem, not a capability gap.** Note that
`h7_check` returns the literal string `"0/10"` when `validators.py` *was never
created* — so the three failures were "never produced the file," not "got every
rule wrong." On the one sweep where it did finish, it scored a **perfect 10/10**
— after 310 seconds, the longest single task time in the whole board's history.
Qwen3.8 is a `<think>`-block reasoning model and h7 is the most complex spec in
the suite (10 ordered rules). The harness caps responses at `AGENT_MAX_TOKENS`
(4096); the model appears to deliberate past that ceiling and never emit the
tool call. The cap applies equally to Qwen3.6, but a reasoning-heavy model is
punished more by it.

**Open question worth a follow-up:** re-run h7 with `AGENT_MAX_TOKENS` raised.
If Qwen3.8 passes it reliably at a larger budget, its accuracy number here is
understated — though at 310s/task the speed verdict only gets worse.

## What was NOT ruled out

Tool-call format was checked and cleared: both models' chat templates use the
same `<tool_call>` / `</tool_call>` markers, so `AGENT_DIALECT=native` is correct
for 3.8 and the losses are not a dialect mismatch.

## The lesson for this board

Neither *newer version number* nor *bigger parameter count* predicted anything.
The 35B that fires 3B per token beat the dense 27B that fires all of it; the
older generation beat the newer one. The public reception of Qwen3.8-27B (strong
Terminal-Bench and SWE-bench Pro numbers, "most anticipated local coder") is not
obviously wrong — it simply did not reproduce on **our** tasks, at **our**
settings, on **our** hardware. That is the entire point of running the bench
ourselves.
