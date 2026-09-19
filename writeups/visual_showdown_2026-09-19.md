# Visual showdown: Qwen 3.8 27B vs Gemma 4 31B (2026-09-19)

*Run on the M5 Max (128 GB). Three builds you can watch, each written in one try from the
same prompt and judged by a script in headless Brave, not by eye.*

## Setup

| | Qwen 3.8 27B | Gemma 4 31B |
|---|---|---|
| Weights | `lmstudio-community/Qwen3.8-27B-MLX-8bit` (8-bit) | `gemma-4-31b-it-abliterated-VL-mlx-bf16` (bf16, full precision) |
| Engine | mlx-dspark 0.14, DFlash 2 drafter `incoai/Qwen3.8-27B-DFlash2` | mlx-vlm 0.6.15, text only |
| Reasoning | **medium** (see "the first Qwen attempt") | model default |
| Budget | temperature 0, 32,768 new tokens, one shot, no retries | same |

Prompts: `tasks/furball/prompt.md`, `tasks/spin/prompt.md`, `tasks/breakout/prompt.md`
(new today, taken from the August game-off prompt). Generator: `showdown_gen.py`.
Judges: `furball_bench.py` (fur ball, spin) and `showdown.py judge-breakout`.

Precision differs (Qwen 8-bit, Gemma bf16), so compare the speed row with that in mind.

## Results

| Build | Qwen 3.8 27B | Gemma 4 31B |
|---|---|---|
| **Fur ball** | fail · 311.4 s, 9,968 tokens | fail · 435.7 s, 3,582 tokens |
| **Spinning ball** | fail · 61.6 s, 3,262 tokens | **PASS** · 218.5 s, 1,792 tokens |
| **Breakout** | **PASS** · 145.5 s, 6,467 tokens | **PASS** · 397.7 s, 3,276 tokens |
| Passed | 1 of 3 | 2 of 3 |
| Time for all three | 518.5 s | 1,051.9 s |
| Generation speed | 32.0-53.0 tok/s | 8.2 tok/s |

### What each model built

**Fur ball.** Nobody has passed this task yet, including every model from August.
- Qwen drew a strand-by-strand brown fur ball that runs at 60 fps. Stroking it bends the fur
  under the cursor: the stroke band changed 97.9% of its pixels, against 0.4% in an untouched
  band (ratio 244.8). It failed only the texture check. Its strand detail score was 1.98, where
  the pass line is 6.0 and the reference build scores 7.63. The fur reads as too smooth and
  dark at this camera distance.
- Gemma's page threw `attachShader: parameter 2 is not of type 'WebGLShader'` on line 122. A
  shader failed to compile and the code never checked, so the canvas stayed black. This is the
  same failure mode recorded in August.

**Spinning ball.**
- Gemma passed: a shaded sphere, framed in view, 60 fps. Its sphere is dark blue on black, so
  it passes the shading check (22.5) but is dim on video.
- Qwen's page ran at 60 fps with no errors and drew nothing. The cause is one line: it builds
  the view-projection matrix as `mul4(lookAt(...), perspective(...))`, which is the wrong
  order, so the ball lands outside the view.

**Breakout.** Both games are playable. The paddle follows the mouse across the field (Qwen
814 px of travel, Gemma 836 px), the ball keeps moving after space (Qwen 100% of sampled
frames moving, Gemma 80%, since its ball waits on the paddle after a lost life until space
is pressed), and neither page threw an error. Qwen's version has a starfield, glossy bricks
and a level counter. Gemma's has neon bricks and a ball trail.

### The first Qwen attempt, at its default reasoning (xhigh)

Qwen 3.8's stock chat template sets reasoning effort to `xhigh` unless told otherwise. At that
setting, with the same 32,768-token budget:
- spin: spent all 32,770 tokens thinking (1,008.5 s) and never wrote the file.
- breakout: spent all 32,769 tokens thinking (1,399.6 s) and output a 381-character stub.
- fur ball: not generated. forge_guard terminated the process at 05:11:55 as an unregistered
  memory user while the machine was swapping.

So the scored run uses `reasoning_effort="medium"`, which is what a person building
something would pick. The xhigh outputs are kept as `*-dflash.gen.json` / `.raw.txt`.

## Judge changes made today

- `furball_bench.py score()` overwrote the task-specific pass rule with the fur-ball rule on
  every task, so spin was being judged as fur. It now calls `verdict()`.
- Breakout judge validated against the August game-off builds before use: Qwen3-Coder and
  DeepSeek builds pass, and Qwen 3.6's "ball never launches" build fails.

## Files

- Builds and scores: `results/{furball,spin,breakout}/{qwen3.8-27b-dflash-medium,gemma-4-31b-bf16}.*`
- Screenshots: `results/<task>/<label>_shots/`
- Clips: `~/bench-llm/showdown-0919/clips/`
- Video: `~/bench-llm/showdown-0919/showdown_FINAL.mp4`

Thanks to the Qwen team, Google's Gemma team, Apple's MLX team, the mlx-vlm and mlx-dspark
maintainers, and the DFlash drafter authors.
