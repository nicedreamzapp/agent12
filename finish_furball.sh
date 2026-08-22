#!/bin/bash
# give Glimmer until 23:15, then call it a DNF, let the board print, and put
# Song Forge back exactly as it was.
HTML="$HOME/bench-llm/agent12/results/furball/muse-glimmer-mm.html"
while [ "$(date +%H%M)" -lt 2315 ]; do
  [ -f "$HTML" ] && break
  sleep 20
done
if [ ! -f "$HTML" ]; then
  echo "$(date +%H:%M) glimmer DNF — killing generation"
  pkill -f "mlx_vlm.server" ; pkill -f "furball_bench.py generate muse-glimmer-mm"
fi
# wait for the bench driver to finish on its own
while pgrep -f "run_furball_bench.sh" >/dev/null; do sleep 10; done
echo "$(date +%H:%M) bench done — restarting Song Forge"
launchctl bootstrap gui/501 "$HOME/Library/LaunchAgents/com.nicedreamz.songforge-m5-stack.plist" 2>&1
for i in $(seq 1 60); do
  sleep 10
  S=$(curl -s --max-time 5 http://127.0.0.1:8767/api/status)
  echo "$(date +%H:%M) $S" | head -c 200; echo
  case "$S" in *'"warm": true'*) echo "SONGFORGE WARM"; break;; esac
done
