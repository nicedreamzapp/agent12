#!/bin/bash
# usage: TASK=spin ./run_task.sh
cd "$HOME/bench-llm/agent12"
for m in gemma-4-31b qwen3.6-35b qwen3-vl-32b muse-glimmer-mm; do
  echo "=== $m  $(date +%H:%M:%S) ==="
  python3 furball_bench.py generate "$m" || { echo "$m GENERATE FAILED"; continue; }
  F="results/$TASK/$m.html"
  [ -f "$F" ] && python3 furball_bench.py score "$F" --label "$m" --port 9350 || echo "$m no file to score"
done
echo "=== board $TASK  $(date +%H:%M:%S) ==="
python3 furball_bench.py board
echo "=== restoring Song Forge $(date +%H:%M:%S) ==="
launchctl bootstrap gui/501 "$HOME/Library/LaunchAgents/com.nicedreamz.songforge-m5-stack.plist" 2>&1
for i in $(seq 1 45); do
  sleep 10
  S=$(curl -s --max-time 5 http://127.0.0.1:8767/api/status)
  case "$S" in *'"warm": true'*) echo "$(date +%H:%M) SONGFORGE WARM"; break;; esac
done
curl -s --max-time 5 http://127.0.0.1:8767/api/status | head -c 200; echo
