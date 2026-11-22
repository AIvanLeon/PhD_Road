#!/usr/bin/env python3
"""
Replay the current season: for every finished regular-season match, rebuild
the table from only the matches played before kickoff, make the pick the
model would have made, and score it against the real result and the
DraftKings odds (1 unit flat stake per pick). Prints hit rates, profit/ROI,
and naive/bookmaker baselines. "No bet" leans are tracked but not staked.
"""

import json
from collections import defaultdict
from pathlib import Path

from build_message import analyze, load_config
import sys

from fetch_data import build_table, fetch_past_tournaments, fetch_season_events
from match_details import fetch_details


def outcome(ev):
    if ev["home_score"] > ev["away_score"]:
        return ev["home_id"]
    if ev["away_score"] > ev["home_score"]:
        return ev["away_id"]
    return None


def profit(correct, odds):
    if odds is None:
        return None
    return odds - 1 if correct else -1.0


def replay(events, cfg, details=None):
    details = details or {}
    _, total_rounds = build_table(events, cfg["form_games"], cfg.get("rounds_per_team"))
    finished = [e for e in events if e["finished"]]
    played_count = defaultdict(int)
    results = []
    for ev in finished:
        round_no = max(played_count[ev["home_id"]], played_count[ev["away_id"]]) + 1
        played_count[ev["home_id"]] += 1
        played_count[ev["away_id"]] += 1
        if round_no > total_rounds:
            continue  # Liguilla
        before = [e for e in finished if e["date"] < ev["date"]]
        table, _ = build_table(before, cfg["form_games"], total_rounds, details)
        home, away = table.get(ev["home_id"]), table.get(ev["away_id"])
        if not home or not away or min(home["played"], away["played"]) < cfg["backtest_min_played"]:
            continue
        odds = details.get(ev["id"], {}).get("odds")
        a = analyze(ev, table, cfg, odds)
        winner = outcome(ev)
        fav = a["fav_id"]
        correct = {"win": winner == fav, "skip": winner == fav,
                   "close": winner in (fav, None), "draw": winner is None}[a["pick_type"]]
        higher = home if home["rank"] < away["rank"] else away

        book = {}
        if odds and odds.get("home") and odds.get("away") and odds.get("draw"):
            book_fav = ev["home_id"] if odds["home"] <= odds["away"] else ev["away_id"]
            book = {
                "book_fav_won": winner == book_fav,
                "book_fav_profit": profit(winner == book_fav, odds["home"] if book_fav == ev["home_id"] else odds["away"]),
                "draw_profit": profit(winner is None, odds["draw"]),
                "home_profit": profit(winner == ev["home_id"], odds["home"]),
            }

        results.append({
            "id": ev["id"], "round": round_no, "match": f"{ev['home_name']} {ev['home_score']}-{ev['away_score']} {ev['away_name']}",
            "pick": a["pick"], "pick_type": a["pick_type"], "edge": a["edge"], "rule": a["rule"],
            "correct": correct, "pick_odds": a["pick_odds"], "profit": profit(correct, a["pick_odds"]),
            "draw": winner is None, "home_won": winner == ev["home_id"], "higher_won": winner == higher["id"],
            "late": a["late"], **book,
        })
    return results


def pct(hits, n):
    return f"{hits}/{n} ({100 * hits / n:.0f}%)" if n else "—"


def money(rows, key="profit"):
    vals = [r[key] for r in rows if r.get(key) is not None]
    if not vals:
        return "—"
    total = sum(vals)
    return f"{total:+.1f}u on {len(vals)} bets (ROI {100 * total / len(vals):+.0f}%)"


def summarize(results):
    lines = []

    def block(label, rs):
        lines.append(f"  {label:<26} {pct(sum(r['correct'] for r in rs), len(rs)):<14} {money(rs)}")

    bets = [r for r in results if r["pick_type"] != "skip"]
    lines.append("Picks (hit rate, then flat 1-unit stake at DraftKings odds):")
    block("All bets", bets)
    block("Draw", [r for r in results if r["pick_type"] == "draw"])
    block("Double chance", [r for r in results if r["pick_type"] == "close"])
    block("Win (strong edge)", [r for r in results if r["pick_type"] == "win"])
    block("Final rounds (stakes on)", [r for r in bets if r["late"]])
    block("No bet (if we had bet)", [r for r in results if r["pick_type"] == "skip"])

    n = len(results)
    b = [r for r in results if "book_fav_won" in r]
    lines.append("\nBaselines (same matches):")
    lines.append(f"  {'Bookmaker favourite wins':<26} {pct(sum(r['book_fav_won'] for r in b), len(b)):<14} {money(b, 'book_fav_profit')}")
    lines.append(f"  {'Always bet the draw':<26} {pct(sum(r['draw'] for r in results), n):<14} {money(b, 'draw_profit')}")
    lines.append(f"  {'Always bet home win':<26} {pct(sum(r['home_won'] for r in results), n):<14} {money(b, 'home_profit')}")
    lines.append(f"  {'Higher-ranked team wins':<26} {pct(sum(r['higher_won'] for r in results), n)}")

    return "\n".join(lines)


def main():
    cfg = load_config()
    if "--all" not in sys.argv:
        events = fetch_season_events(cfg["league"])
        details = fetch_details([e for e in events if e["finished"]], cfg["league"])
        results = replay(events, cfg, details)
        print(summarize(results))
        Path("data").mkdir(exist_ok=True)
        Path("data/backtest.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
        return

    every = []
    for label, events in fetch_past_tournaments(cfg["league"], cfg["history_start"]).items():
        details = fetch_details([e for e in events if e["finished"]], cfg["league"])
        results = replay(events, cfg, details)
        for r in results:
            r["tournament"] = label
        every += results
        print(f"\n===== {label} ({len(results)} matches) =====")
        print(summarize(results))
    print(f"\n===== ALL TOURNAMENTS ({len(every)} matches) =====")
    print(summarize(every))
    Path("data").mkdir(exist_ok=True)
    Path("data/backtest_all.json").write_text(json.dumps(every, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
