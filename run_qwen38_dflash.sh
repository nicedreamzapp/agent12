#!/bin/zsh
# 2026-09-19 rerun of Qwen3.8-27B 8-bit with the DFlash 2 drafter (see writeups/qwen38_dflash_rerun.md)
cd "$HOME/bench-llm/agent12" || exit 1
PY=$HOME/.local/qwen-fast/bin/python
wait_forge() { while curl -s -m 5 127.0.0.1:8767/api/status | grep -q '"jobs_running": [1-9]'; do echo "song forge busy, waiting"; sleep 30; done; }
wait_forge; echo "=== easy $(date +%T)"; $PY $HOME/bench-llm/agent12/runner.py --suite easy --model qwen3.8-27b-8bit-dflash --run qwen38_8bit_dflash_easy_v1
wait_forge; echo "=== hard $(date +%T)"; $PY $HOME/bench-llm/agent12/runner.py --suite hard --model qwen3.8-27b-8bit-dflash --run qwen38_8bit_dflash_hard_v1
wait_forge; echo "=== hard big budget $(date +%T)"; AGENT_MAX_TOKENS=8000 AGENT_MAX_STEPS=40 $PY $HOME/bench-llm/agent12/runner.py --suite hard --model qwen3.8-27b-8bit-dflash --run qwen38_8bit_dflash_hard_bigbudget
echo "=== done $(date +%T)"
