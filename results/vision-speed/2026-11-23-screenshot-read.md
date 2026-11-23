# Vision speed: one phone screenshot, local vs Claude (2026-11-23, M5 128 GB)

Same image (1320x2868 iPhone screenshot of a chat app), same question:
"What app is this screenshot from, and what does the gray line near the bottom say? Quote it exactly."

| Model | Where / how | Total time | Prefill | Decode | Exact quote right? | App named right? |
|---|---|---|---|---|---|---|
| DaisyRose 27B bf16 | M5, mlx_vlm 0.7.10, full-size image, temp 0, thinking off | 28.5 s answer (+7.3 s load) | 3,726 tok @ 720 tok/s | 200 tok @ 8.7 tok/s | yes | no (guessed "Claude app") |
| Claude Sonnet | cloud, `claude -p`, Read tool | 6.8 s end to end | n/a (cloud) | n/a | yes | yes |
| Claude Opus | cloud, `claude -p`, Read tool | 9.3 s end to end | n/a (cloud) | n/a | yes | yes |

Notes on fairness:
- The quote test is fair: all three read the exact text off the image.
- "App named" is NOT fair: the Claude runs carried the owner's project notes, which name the app; the local model had only the image.
- Claude times include CLI start-up and the tool call; local time is model-only after load. Peak local memory 58.1 GB.
- Local decode was capped at 400 tokens and ran 200; most of its 28.5 s was the long answer at 8.7 tok/s.
