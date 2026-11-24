#!/usr/bin/env python3
"""Side-by-side speed race for the demo video: Cerebras vs a GPU provider.

Streams the same prompt to two OpenAI-compatible endpoints at once and shows
live time-to-first-token, tokens/sec and total time. Stdlib only.

  export CEREBRAS_API_KEY=csk-...
  export GPU_BASE_URL=https://api.together.xyz/v1   # any OpenAI-compatible host
  export GPU_API_KEY=...
  export GPU_MODEL=moonshotai/Kimi-K2-Instruct      # closest Kimi they serve
  python3 demo/race.py
"""
import json
import os
import sys
import threading
import time
import urllib.request

PROMPT = os.environ.get("RACE_PROMPT", (
    "You are a Secret Santa shopping assistant. For each of these 4 friends, "
    "suggest 3 specific gift ideas under $40 with a one-line reason each: "
    "Priya (hiking, coffee), Arjun (retro gaming, lego), Meera (baking, plants), "
    "Sam (running, sci-fi books)."))

LANES = [
    {"label": "Kimi K3.1 Pro · Cerebras",
     "base": os.environ.get("CEREBRAS_BASE_URL","https://api.cerebras.ai/v1"),
     "key": os.environ.get("CEREBRAS_API_KEY", ""),
     "model": os.environ.get("CEREBRAS_MODEL", "moonshotai-kimi-k3.1-pro-trial")},
    {"label": os.environ.get("GPU_LABEL", "GPU provider"),
     "base": os.environ.get("GPU_BASE_URL", ""),
     "key": os.environ.get("GPU_API_KEY", ""),
     "model": os.environ.get("GPU_MODEL", "")},
]


def run(lane):
    lane.update(tokens=0, chars=0, ttft=None, done=False, err=None, t0=time.time())
    body = json.dumps({
        "model": lane["model"], "stream": True, "max_tokens": 1200,
        "stream_options": {"include_usage": True},
        "messages": [{"role": "user", "content": PROMPT}],
    }).encode()
    req = urllib.request.Request(
        lane["base"].rstrip("/") + "/chat/completions", data=body,
        headers={"Authorization": f"Bearer {lane['key']}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            for raw in r:
                line = raw.decode("utf-8", "ignore").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                if chunk.get("usage") and chunk["usage"].get("completion_tokens"):
                    lane["usage_tokens"] = chunk["usage"]["completion_tokens"]
                for ch in chunk.get("choices", []):
                    text = (ch.get("delta") or {}).get("content") or ""
                    if text:
                        if lane["ttft"] is None:
                            lane["ttft"] = time.time() - lane["t0"]
                        lane["chars"] += len(text)
                        lane["tokens"] += 1  # ~1 token per streamed chunk
    except Exception as e:  # noqa: BLE001
        lane["err"] = f"{type(e).__name__}: {e}"[:60]
    lane["elapsed"] = time.time() - lane["t0"]
    lane["done"] = True


def fmt(lane):
    now = lane.get("elapsed") if lane["done"] else time.time() - lane["t0"]
    toks = lane.get("usage_tokens") or max(lane["tokens"], lane["chars"] // 4)
    gen_time = max(now - (lane["ttft"] or now), 1e-3)
    tps = toks / gen_time if lane["ttft"] else 0
    bar = "█" * min(40, int(toks / 30))
    state = "✅ DONE" if lane["done"] and not lane["err"] else (lane["err"] or "…")
    ttft = f"{lane['ttft']:.2f}s" if lane["ttft"] else "—"
    return (f"\033[1m{lane['label']}\033[0m\n"
            f"  first token {ttft:>7} | {toks:>5} tok | {tps:>7.0f} tok/s | "
            f"{now:5.1f}s  {state}\n  {bar}\n")


def main():
    lanes = [l for l in LANES if l["base"] and l["key"] and l["model"]]
    if not lanes:
        sys.exit("Set CEREBRAS_API_KEY (and GPU_* vars for the comparison lane).")
    threads = [threading.Thread(target=run, args=(l,), daemon=True) for l in lanes]
    for l in lanes:
        l.update(done=False, t0=time.time(), tokens=0, chars=0, ttft=None, err=None)
    for t in threads:
        t.start()
    sys.stdout.write("\033[2J")
    while True:
        sys.stdout.write("\033[H🎅 Secret Santa speed race\n\n" +
                         "\n".join(fmt(l) for l in lanes))
        sys.stdout.flush()
        if all(l["done"] for l in lanes):
            break
        time.sleep(0.05)
    if len(lanes) == 2 and all(not l["err"] for l in lanes):
        a, b = lanes
        print(f"\n⚡ {a['label']} finished {b['elapsed'] / a['elapsed']:.1f}× faster")


if __name__ == "__main__":
    main()
