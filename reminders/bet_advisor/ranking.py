#!/usr/bin/env python3
"""
Estimated hit probability for a pick, from how often the same kind of pick
(type + size of the rating gap) came true in that league's backtests.
`python ranking.py --league <name>` refreshes leagues/calibration/<name>.json
from every season since the league's `history_start`.
"""

import json
from collections import defaultdict
from pathlib import Path

WIN_BINS = (0.7, 1.0, 1.5)
SMOOTHING = 10  # pseudo-games pulled toward the pick type's overall rate


def bucket(pick_type, edge, rule):
    if pick_type == "close" and rule == "motivated":
        return "double_chance_motivated"
    if pick_type == "close":
        return "double_chance"
    if pick_type == "draw":
        return "draw"
    if pick_type == "win":
        lo = max(b for b in WIN_BINS if abs(edge) >= b)
        return f"win_gap_{lo}+"
    return None


def calibration_path(name):
    return Path("leagues/calibration") / f"{name}.json"


def load_calibration(name):
    path = calibration_path(name)
    return json.loads(path.read_text()) if path.exists() else {}


def estimate(cal, pick_type, edge, rule):
    """Smoothed hit rate for this kind of pick, or None if never seen."""
    key = bucket(pick_type, edge, rule)
    if key is None or key not in cal:
        return None
    b = cal[key]
    family = [v for k, v in cal.items() if k.split("_gap")[0] == key.split("_gap")[0]]
    prior = sum(v["hits"] for v in family) / max(sum(v["n"] for v in family), 1)
    return (b["hits"] + SMOOTHING * prior) / (b["n"] + SMOOTHING)


def build_calibration(name):
    from backtest import replay
    from build_message import load_config
    from fetch_data import fetch_past_tournaments
    from match_details import fetch_details

    cfg = load_config(name)
    counts = defaultdict(lambda: {"hits": 0, "n": 0})
    for events in fetch_past_tournaments(cfg["league"], cfg["history_start"]).values():
        details = fetch_details([e for e in events if e["finished"]], cfg["league"])
        for r in replay(events, cfg, details):
            key = bucket(r["pick_type"], r["edge"], r["rule"])
            if key:
                counts[key]["hits"] += r["correct"]
                counts[key]["n"] += 1
    path = calibration_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(sorted(counts.items())), indent=2) + "\n")
    return counts


if __name__ == "__main__":
    import sys
    from build_message import load_config
    name = sys.argv[sys.argv.index("--league") + 1] if "--league" in sys.argv else "liga_mx"
    for key, v in sorted(build_calibration(name).items()):
        print(f"  {key:<26} {v['hits']:>4}/{v['n']:<4} ({100 * v['hits'] / v['n']:.0f}%)")
