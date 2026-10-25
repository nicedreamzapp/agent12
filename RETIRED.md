# Retired models

Every model we downloaded, tested, and then deleted because something else beat it or no tool ever used it.
One line each: what it was, what replaced it, why. Kept so we never download and re-test a loser again.

The model janitor adds rows here on its own: when a model has sat on a machine for 7+ days and no tool,
launcher or project loads it, it deletes the model and writes it down. When a head-to-head test picks a
winner, the loser is retired the same day with the reason.

| Retired | Model | Kind | Size | Lost to / replaced by | Why |
|---|---|---|---|---|---|
| 2026-10-24 | Wan 2.2 14B (t2v + i2v, fp16) | video | 116 GB | LTX-2.5 | Same quality check pass, LTX-2.5 ~70 s per clip vs Wan 13-16 min (test 2026-08-29) |
| 2026-10-24 | umt5-xxl text encoder | video helper | 11 GB | (Wan retired) | Only Wan used it |
| 2026-10-25 | LTX-Video 0.9.8 13B distilled | video | 29 GB | LTX-2.5 | Older generation; LTX-2.5 is faster and makes synced audio |
| 2026-10-25 | T5-XXL + CLIP-L encoders | video/picture helper | 10 GB | (LTXV 0.9.8 + FLUX retired) | Only the retired models used them |
| 2026-10-24 | Ideogram 4 (fp8) + abliterated encoder | picture | 42 GB | Qwen-Image 2.1 | Refused 5 of 10 harmless prompts, ~104 s/image vs ~62 s, Qwen spelled poster text perfectly (bake-off 2026-09-20) |
| 2026-10-25 | FLUX.1-dev (fp8) | picture | 17 GB | Qwen-Image 2.1 | Story Forge stills moved to Qwen-Image 2.1 after the 2026-09-20 bake-off |
| 2026-10-24 | LatentSync 1.6 (MPS branch) | lip-sync | 13 GB | none | Failed on cartoon characters; CUDA-first, experimental on Mac |
| 2026-10-24 | Nemotron-3.5 Bolt 74B base (bf16) | LLM | 150 GB | our 8-bit MLX build | Source checkpoint only; conversion done and published |
| 2026-10-25 | Bolt 74B MLX 8-bit (stock) | LLM | 81 GB | Bolt 74B abliterated 8-bit | The Moonstone Bolt button loads the abliterated build; stock copy is on Hugging Face |
| 2026-10-25 | Muse-Glimmer 30B (bf16) | vision LLM | 60 GB | Qwen 3.8 27B Heretic VL | Only an unused vision-chat script loaded it; last used 2026-08-22 |
| 2026-10-24 | Nimble 9B (bf16, Ollama) | LLM | 17 GB | none | Email keep/toss sorting test (2026-10-04) never went into a tool |
| 2026-10-25 | Gemma 4 E2B-it | LLM | 10 GB | none | Small-model scout 2026-09-30; never wired into a tool |
| 2026-10-25 | SmolVLM2 2.2B + 500M Video | vision | 11 GB | none | Small-model scout 2026-09-30; never wired into a tool |
| 2026-10-25 | moondream2 | vision | 4 GB | none | Small-model scout 2026-09-30; never wired into a tool |
| 2026-10-25 | MiniCPM-V 4.6 | vision | 3 GB | none | Small-model scout 2026-09-30; never wired into a tool |
| 2026-10-25 | OCR scouts: TeleOCR, PaddleOCR-VL 1.5 + 1.6, Xiaomi-OCR-0, OvisOCR2 | OCR | 8 GB | none | OCR scout 2026-09-30; never wired into a tool |
| 2026-10-25 | Small LLM scouts: OneJev 0.8B, Intern-Decision 0.8B, Supertron3 0.8B | LLM | 6 GB | none | Scout 2026-09-30; never wired into a tool |
| 2026-10-25 | whisper-large-v3 (MLX) | speech | 3 GB | whisper-large-v3-turbo | Tools use the turbo build |
| 2026-10-25 | mlx-community/LFM2.5-VL-1.6B-bf16 | model | 3 GB | none | no tool loads it; last used 2026-10-01 (Matts-MacBook-Pro) |
| 2026-10-25 | mlx-community/LFM2.5-VL-1.6B-bf16 | model | 3 GB | none | no tool loads it; last used 2026-10-01 (M5) |
| 2026-10-25 | ACE-Step 1.5 XL-turbo (fp32 + bf16) | music | 30 GB | ACE-Step 1.5 turbo | Song Forge renders every song on the regular turbo; XL never wired in, last opened 2026-09-10 |
| 2026-10-25 | iPhone15,3 27.0 (24A5390f) | Xcode iPhone support files | 7 GB | none | no tool loads it; last used 2026-08-21 (Matts-MacBook-Pro) |
