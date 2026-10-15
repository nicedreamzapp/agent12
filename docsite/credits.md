---
title: Agent-12 credits, contributors and upstream projects
description: Who built Agent-12 and the upstream projects it depends on or measures, including MLX, mlx-lm, mlx-vlm, mlx-dspark, ds4.c, Brave and the model publishers.
---

# Credits

## Built in this repo

Agent-12 is by Matt Macosko ([@nicedreamzapp](https://github.com/nicedreamzapp)):
the runner, the adapters, the 20 tasks with their judges and reference
solutions, the validation gate, the leaderboard builder, the visual benches,
and the methodology and contamination documents.

## Contributors

- **Sergey Galashko** ([@galashko](https://github.com/galashko)) reproduced
  the Qwen3.6-35B numbers on an M5 Max with a different serving stack, found
  that the judges failed correct code on Python 3.9, and wrote the fix that
  records the interpreter and gates validation at 3.10
  ([issue #1](https://github.com/nicedreamzapp/agent12/issues/1),
  [#2](https://github.com/nicedreamzapp/agent12/pull/2)). He also reported
  the BOM problem in the judges
  ([issue #3](https://github.com/nicedreamzapp/agent12/issues/3)). The Python
  floor in `envcheck.py` is his.

## Upstream projects

Not built here. Agent-12 depends on them, runs them, or measures them.

- **[MLX](https://github.com/ml-explore/mlx)** from Apple, the array framework
  the local models run on.
- **[mlx-lm](https://github.com/ml-explore/mlx-lm)**, used to load and serve
  text models (`mlx_lm.server`).
- **[mlx-vlm](https://github.com/Blaizzy/mlx-vlm)**, used to serve and run the
  vision-language models in the visual benches.
- **mlx-dspark** and the **DFlash 2** drafter
  (`incoai/Qwen3.8-27B-DFlash2`), used for speculative decoding in the
  `anvil_dflash` adapter. **TODO-VERIFY** the upstream link for mlx-dspark.
- **ds4.c**, the engine that served DeepSeek V4 Flash. **TODO-VERIFY** the
  upstream link.
- **[Brave](https://brave.com/)**, run headless to judge the visual benches.
- **[FFmpeg](https://ffmpeg.org/)**, used to read screenshots and make clips.
- **[websocket-client](https://github.com/websocket-client/websocket-client)**,
  used to talk to the browser over the DevTools protocol.
- **[MkDocs](https://www.mkdocs.org/)** and
  **[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)**,
  which build this documentation site.

## Models

The models are the work of their publishers: Qwen (Alibaba), Gemma (Google),
DeepSeek, Claude (Anthropic), Muse Glimmer (Meta) and Nemotron (NVIDIA).
Quantized and converted builds come from
[lmstudio-community](https://huggingface.co/lmstudio-community),
[mlx-community](https://huggingface.co/mlx-community), EigenLabs and
[divinetribe](https://huggingface.co/divinetribe), as named in
`configs/models.json`.

## Related

- [Claude Code Local](https://github.com/nicedreamzapp/claude-code-local)
  runs Anthropic's Claude Code against local models on Apple silicon. Claude
  Code is Anthropic's product. The Agent-12 board scores were not measured
  inside it.
