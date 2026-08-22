#!/bin/bash
# one model at a time: generate, then score. never two sets of weights at once.
cd "$HOME/bench-llm/agent12"
for m in gemma-4-31b qwen3.6-35b qwen3-vl-32b muse-glimmer-mm; do
  echo "=== $m  $(date +%H:%M:%S) ==="
  python3 furball_bench.py generate "$m" || { echo "$m GENERATE FAILED"; continue; }
  python3 furball_bench.py score "results/furball/$m.html" --label "$m" --port 9350 \
    || echo "$m SCORE FAILED"
done
echo "=== board  $(date +%H:%M:%S) ==="
python3 furball_bench.py board
