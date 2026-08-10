#!/bin/zsh
# sweep.sh <tag> — one full repeat sweep of all 5 local configs, both suites.
# Run names get suffix _<tag>. A failed run logs and the sweep continues.
TAG=$1
PY=$HOME/.local/mlx-server/bin/python
DS4="$HOME/Desktop/PROJECTS/Local AI Setup/ds4"
GG="$DS4/gguf"
cd "$HOME/bench-llm/agent12" || exit 1

run() {
  echo "=== $3 ($(date +%H:%M:%S)) ==="
  $PY runner.py --suite "$1" --model "$2" --run "$3" || echo "RUN-FAILED $3"
}

ds4_weights() {  # ds4_weights <gguf-file>
  kill $(lsof -ti :8000) 2>/dev/null; sleep 3
  ln -sf "$GG/$1" "$DS4/ds4flash.gguf"
  "$HOME/.local/bin/ds4-server-up" || echo "DS4-BOOT-FAILED $1"
  sleep 3
}

run easy qwen3-coder-30b  "qwen30_easy_$TAG"
run hard qwen3-coder-30b  "qwen30_hard_$TAG"
run easy qwen3.6-35b      "qwen36_easy_$TAG"
run hard qwen3.6-35b      "qwen36_hard_$TAG"
run easy gemma-4-31b      "gemma_easy_$TAG"
run hard gemma-4-31b      "gemma_hard_$TAG"

# ds4 configs dropped from repeat sweeps 2026-08-10 03:25 — the 81GB gguf
# remaps sent the box critical (21.7GB swap) mid-sweep-2. ds4-0731 already
# has two full clean passes (v1 + s2); orig is on death row with one.
echo "SWEEP $TAG COMPLETE ($(date +%H:%M:%S))"
