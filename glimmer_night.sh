#!/bin/zsh
# glimmer_night.sh — overnight Muse Glimmer 30B challenger gauntlet (2026-08-11).
# Waits for the HF download, smoke-tests the arch loads under mlx_lm, then
# 3 repeat runs of easy+hard. Launch with:
#   nohup caffeinate -ims zsh glimmer_night.sh > /dev/null 2>&1 &
PY=$HOME/.local/mlx-server/bin/python
LOG=$HOME/bench-llm/agent12/logs/glimmer_night_20260811.log
cd "$HOME/bench-llm/agent12" || exit 1
exec >> "$LOG" 2>&1

echo "=== glimmer night start $(date) ==="

# 1. Block until the weights are fully down (hf download resumes/verifies).
"$HOME/.local/mlx-server/bin/hf" download mlx-community/Muse-Glimmer-30B-bf16 \
  || { echo "DOWNLOAD-FAILED $(date)"; exit 1; }
echo "download complete $(date)"

# 2. Smoke test — day-1 model, mlx_lm 0.31.2 may not know the architecture.
$PY -c "
from mlx_lm import load, generate
m, t = load('mlx-community/Muse-Glimmer-30B-bf16')
print('SMOKE:', generate(m, t, prompt='Say OK.', max_tokens=8))
" || { echo "SMOKE-FAILED — mlx_lm likely too old for glimmer arch. NOT upgrading the shared mlx-server venv unattended."; exit 1; }
echo "smoke ok $(date)"

# 3. Three repeat runs, both suites, same convention as the 8/10 sweeps.
for i in 1 2 3; do
  echo "=== glimmer sweep g$i ($(date +%H:%M:%S)) ==="
  $PY runner.py --suite easy --model muse-glimmer-30b --run "glimmer_easy_g$i" \
    || echo "RUN-FAILED easy g$i"
  $PY runner.py --suite hard --model muse-glimmer-30b --run "glimmer_hard_g$i" \
    || echo "RUN-FAILED hard g$i"
done
echo "=== glimmer night complete $(date) ==="
