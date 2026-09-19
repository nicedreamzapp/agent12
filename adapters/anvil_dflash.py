"""Anvil + DFlash adapter: the same Anvil engine (agent.py prompt, tools, dialect,
parser, loop), with generation swapped to mlx-dspark's lossless DFlash speculative
decoding. One variable moves versus the plain anvil adapter: the drafter.

Greedy DFlash output is exactly greedy target decoding (the target verifies every
token), so accuracy should match a greedy plain run; only speed should change.
Known difference: mlx-dspark's library path has no cross-turn KV prefix reuse
(its server prefix cache crashed on this model, see writeups/qwen38_dflash_rerun.md),
so every turn prefills the whole transcript. That costs DFlash time, never accuracy.

Env: AGENT_DFLASH_DRAFTER (default incoai/Qwen3.8-27B-DFlash2).
Runs in the ~/.local/qwen-fast venv (mlx-dspark 0.14, mlx 0.32).
"""
import contextlib
import io
import os
import sys
import time

ENGINE_DIR = os.path.expanduser(
    os.environ.get("AGENT12_ENGINE_DIR", "~/Desktop/PROJECTS/Local AI Setup/agent"))

STATS = {"tokens": 0, "seconds": 0.0, "rounds": 0, "calls": 0}


def make_engine(agent):
    from mlx_dspark.generate import dflash_generate
    from mlx_dspark.load import load_dflash_pair

    class DFlashEngine(agent.MLXEngine):
        def __init__(self, model_path):
            t0 = time.time()
            import mlx.core as mx
            # Without a cap MLX keeps every freed prefill buffer cached; re-prefilling the
            # whole transcript each turn took this process past 100GB on 2026-09-19 and put
            # the box into heavy swap. Cap the buffer cache and clear it after each turn.
            mx.set_cache_limit(2 * 1024 ** 3)
            self._mx = mx
            drafter = os.environ.get("AGENT_DFLASH_DRAFTER", "incoai/Qwen3.8-27B-DFlash2")
            self.target, self.tokenizer, self.drafter, _ = load_dflash_pair(model_path, drafter=drafter)
            self.model = self.target
            self.vision = False
            self.cache = None
            self.cache_tokens = []
            self.model_path = model_path
            self.messages = [{"role": "system", "content": agent.build_system(model_path)}]
            self.ctx_limit = int(os.environ.get("AGENT_CTX_LIMIT", "131072"))
            print(f"  loaded target + DFlash drafter in {time.time()-t0:.1f}s")

        def _new_cache(self):
            return None

        def reset(self):
            self.messages = self.messages[:1]
            self.cache_tokens = []

        def _generate(self, on_text):
            tokens = list(self._render())
            res = dflash_generate(
                self.target, self.tokenizer, self.drafter,
                prompt_ids=tokens, max_new_tokens=agent.MAX_TOKENS,
                temperature=0.0, stop=["</function>"], on_text=on_text)
            STATS["tokens"] += res.num_tokens
            STATS["seconds"] += res.seconds
            STATS["rounds"] += res.num_rounds
            STATS["calls"] += 1
            text = res.text
            # the stop string is cut from .text; the plain engine keeps it, and the
            # tool-call parser keys on it, so put it back exactly as the plain path has it
            if "</function>" not in text and "</function>" in self.tokenizer.decode(res.token_ids):
                text += "</function>"
                on_text("</function>")
            self.cache_tokens = tokens + list(res.token_ids)
            self._mx.clear_cache()
            return text

    return DFlashEngine


class AnvilDFlashAdapter:
    def __init__(self):
        self.agent = None
        self.engine = None
        self.last_output = ""

    def load(self):
        sys.path.insert(0, ENGINE_DIR)
        import agent
        self.agent = agent
        agent.acquire_seat()
        self.engine = make_engine(agent)(agent.MODEL_DEFAULT)

    def reset(self):
        self.engine.reset()

    def run(self, prompt):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.agent.agent_turn(self.engine, prompt, quiet=True)
        self.last_output = buf.getvalue()

    def info(self):
        s = STATS
        return {"model": self.agent.MODEL_DEFAULT,
                "dialect": self.agent.DIALECT,
                "backend": "mlx+dflash",
                "drafter": os.environ.get("AGENT_DFLASH_DRAFTER", "incoai/Qwen3.8-27B-DFlash2"),
                "prompt_file": self.agent.PROMPT_FILE}

    def stats(self):
        s = STATS
        return {"gen_tokens": s["tokens"], "gen_seconds": round(s["seconds"], 1),
                "tok_s_incl_prefill": round(s["tokens"] / s["seconds"], 1) if s["seconds"] else None,
                "mean_accept": round(s["tokens"] / s["rounds"], 2) if s["rounds"] else None,
                "generate_calls": s["calls"]}

    def close(self):
        with contextlib.suppress(Exception):
            self.agent.release_seat()
