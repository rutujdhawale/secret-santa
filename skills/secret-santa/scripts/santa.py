#!/usr/bin/env python3
"""Secret Santa state + link checker for the OpenClaw skill. Stdlib only.

State lives in $SANTA_DATA (default ~/.secret-santa/<group>.json).
Every command prints JSON so the agent can read it reliably.
"""
import argparse
import concurrent.futures as cf
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DATA_DIR = Path(os.environ.get("SANTA_DATA", Path.home() / ".secret-santa"))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(code)


def safe_group(g):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", g)[:80] or "default"


def path_for(group):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{safe_group(group)}.json"


def load(group):
    p = path_for(group)
    if p.exists():
        return json.loads(p.read_text())
    return {"group": group, "budget": None, "currency": "USD",
            "members": {}, "pairs": [], "gifts": {}}


def save(state):
    p = path_for(state["group"])
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    tmp.replace(p)


def split_likes(s):
    return [x.strip() for x in re.split(r"[,;/]| and ", s or "") if x.strip()]


def member(state, name):
    key = name.strip().lower()
    m = state["members"].setdefault(key, {"name": name.strip(), "likes": []})
    return m


# ---- commands -------------------------------------------------------------

def cmd_setup(a):
    s = load(a.group)
    s["budget"] = a.budget
    s["currency"] = a.currency.upper()
    save(s)
    out({"ok": True, "budget": s["budget"], "currency": s["currency"]})


def cmd_join(a):
    s = load(a.group)
    m = member(s, a.name)
    for like in split_likes(a.likes):
        if like.lower() not in (x.lower() for x in m["likes"]):
            m["likes"].append(like)
    s["pairs"] = []  # membership changed -> old draw is invalid
    save(s)
    out({"ok": True, "member": m, "count": len(s["members"])})


def cmd_wish(a):
    s = load(a.group)
    m = member(s, a.name)
    for like in split_likes(a.likes):
        if like.lower() not in (x.lower() for x in m["likes"]):
            m["likes"].append(like)
    save(s)
    out({"ok": True, "member": m})


def cmd_leave(a):
    s = load(a.group)
    removed = s["members"].pop(a.name.strip().lower(), None)
    s["pairs"] = []
    save(s)
    out({"ok": removed is not None, "count": len(s["members"])})


def cmd_status(a):
    s = load(a.group)
    out({
        "budget": s["budget"], "currency": s["currency"],
        "members": list(s["members"].values()),
        "drawn": bool(s["pairs"]),
        "gifts_found_for": list(s["gifts"].keys()),
    })


def cmd_draw(a):
    s = load(a.group)
    names = [m["name"] for m in s["members"].values()]
    if len(names) < 2:
        out({"ok": False, "error": "Need at least 2 people to draw names."}, 1)
    rng = random.Random(a.seed)
    order = names[:]
    # Sattolo's algorithm: one single loop, nobody draws themselves.
    for i in range(len(order) - 1, 0, -1):
        j = rng.randrange(i)
        order[i], order[j] = order[j], order[i]
    pairs = [{"giver": names[i], "receiver": order[i]} for i in range(len(names))]
    assert all(p["giver"] != p["receiver"] for p in pairs)
    for p in pairs:
        p["receiver_likes"] = s["members"][p["receiver"].lower()]["likes"]
    s["pairs"] = pairs
    save(s)
    out({"ok": True, "pairs": pairs, "note": "Do not post these in the group."})


def cmd_save_gifts(a):
    s = load(a.group)
    try:
        gifts = json.loads(a.json)
        assert isinstance(gifts, list)
    except Exception as e:  # noqa: BLE001
        out({"ok": False, "error": f"--json must be a JSON list: {e}"}, 1)
    s["gifts"][a.name.strip()] = gifts
    save(s)
    out({"ok": True, "saved": len(gifts)})


def check_one(url):
    if not re.match(r"^https?://", url):
        return {"url": url, "status": "dead", "reason": "not a URL"}
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            body = r.read(200_000).decode("utf-8", "ignore")
            title = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
            return {"url": url, "final_url": r.geturl(), "code": r.status,
                    "status": "ok",
                    "title": re.sub(r"\s+", " ", title.group(1)).strip()[:140]
                    if title else None}
    except urllib.error.HTTPError as e:
        # 404/410 = gone. 403/429/503 = usually bot protection (Amazon etc).
        status = "dead" if e.code in (404, 410) else "unverified"
        return {"url": url, "code": e.code, "status": status}
    except Exception as e:  # noqa: BLE001
        return {"url": url, "status": "unverified", "reason": type(e).__name__}


def cmd_check_links(a):
    with cf.ThreadPoolExecutor(max_workers=min(16, len(a.urls) or 1)) as ex:
        results = list(ex.map(check_one, a.urls))
    out({"results": results,
         "ok": sum(r["status"] == "ok" for r in results),
         "dead": sum(r["status"] == "dead" for r in results)})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def g(sp):
        sp.add_argument("--group", required=True)
        return sp

    sp = g(sub.add_parser("setup"))
    sp.add_argument("--budget", type=float, required=True)
    sp.add_argument("--currency", default="USD")
    sp.set_defaults(fn=cmd_setup)

    for name, fn in (("join", cmd_join), ("wish", cmd_wish)):
        sp = g(sub.add_parser(name))
        sp.add_argument("--name", required=True)
        sp.add_argument("--likes", default="")
        sp.set_defaults(fn=fn)

    sp = g(sub.add_parser("leave"))
    sp.add_argument("--name", required=True)
    sp.set_defaults(fn=cmd_leave)

    g(sub.add_parser("status")).set_defaults(fn=cmd_status)

    sp = g(sub.add_parser("draw"))
    sp.add_argument("--seed", type=int, default=None)
    sp.set_defaults(fn=cmd_draw)

    sp = g(sub.add_parser("save-gifts"))
    sp.add_argument("--name", required=True)
    sp.add_argument("--json", required=True)
    sp.set_defaults(fn=cmd_save_gifts)

    sp = sub.add_parser("check-links")
    sp.add_argument("urls", nargs="+")
    sp.set_defaults(fn=cmd_check_links)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
