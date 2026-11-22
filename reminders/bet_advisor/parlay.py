#!/usr/bin/env python3
"""
Combined European message: run the Premier League, LaLiga and Serie A models
on the next week's fixtures, keep each league's 3 picks with the highest
estimated hit probability (from leagues/calibration/), and show them as
3-pick parlays per league plus the 9-pick total. Writes data/message.txt.
"""

import json
from datetime import datetime
from pathlib import Path

from build_message import TZ, analyze, load_config
from fetch_data import build_table, fetch_current_tournament, upcoming_fixtures
from match_details import fetch_details
from ranking import estimate, load_calibration

LEAGUES = ("premier_league", "laliga", "serie_a")
PER_LEAGUE = 3
RECORD = Path("leagues/calibration/parlay_record.json")


def record_line(name):
    """Past weekly record for this league's 3-pick parlay (or the 9-pick)."""
    if not RECORD.exists():
        return ""
    rec = json.loads(RECORD.read_text())
    h, n, u, priced = rec["all"] if name == "all" else rec[name]["parlay"]
    money = f", {u:+.1f}u on {priced} with odds" if priced else ""
    return f" — since 2024-25 hit {h}/{n} weeks ({100 * h / max(n, 1):.0f}%{money})"


def league_picks(name):
    cfg = load_config(name)
    label, events, _ = fetch_current_tournament(cfg["league"])
    details = fetch_details(events, cfg["league"])
    table, _ = build_table(events, cfg["form_games"], cfg.get("rounds_per_team"), details)
    cal = load_calibration(name)
    picks = []
    for fx in upcoming_fixtures(events, cfg["lookahead_days"], cfg.get("kickoff_grace_minutes", 0)):
        if table[fx["home_id"]]["remaining"] <= 0 or table[fx["away_id"]]["remaining"] <= 0:
            continue
        a = analyze(fx, table, cfg, details.get(fx["id"], {}).get("odds"))
        if a["pick_type"] == "skip":
            continue
        prob = estimate(cal, a["pick_type"], a["edge"], a["rule"])
        if prob is None:
            continue
        picks.append(dict(a, fx=fx, prob=prob))
    return cfg, top_picks(picks)


def top_picks(picks, n=PER_LEAGUE):
    """Highest estimated probability first; one pick per team."""
    chosen, teams = [], set()
    for p in sorted(picks, key=lambda p: (-p["prob"], -abs(p["edge"]))):
        ids = {p["home"]["id"], p["away"]["id"]}
        if ids & teams:
            continue
        chosen.append(p)
        teams |= ids
        if len(chosen) == n:
            break
    return chosen


def _parlay(picks):
    prob, odds, priced = 1.0, 1.0, True
    for p in picks:
        prob *= p["prob"]
        if p["pick_odds"]:
            odds *= p["pick_odds"]
        else:
            priced = False
    return prob, (odds if priced else None)


def format_pick(i, p):
    fx = p["fx"]
    when = fx["date"].astimezone(TZ).strftime("%a %b %d, %-I:%M %p")
    odds = f" @ {p['pick_odds']:.2f}" if p["pick_odds"] else " (no odds yet)"
    pick = p["pick"].split(" — ")[0]
    why = " · motivated side" if p["rule"] == "motivated" else ""
    return (f"  {i}. {pick}{odds} · est. {100 * p['prob']:.0f}%{why}\n"
            f"     {fx['home_name']} vs {fx['away_name']} — {when}")


def main():
    lines = [f"🎲 European Picks — {datetime.now(TZ).strftime('%B %d, %Y')}",
             f"Top {PER_LEAGUE} most likely picks per league this week (times CDMX)"]
    everything = []
    for name in LEAGUES:
        cfg, picks = league_picks(name)
        lines.append(f"\n⚽ {cfg['league_name']}")
        if not picks:
            lines.append("  No bettable picks in the next 7 days.")
            continue
        lines += [format_pick(i, p) for i, p in enumerate(picks, 1)]
        prob, odds = _parlay(picks)
        odds_txt = f"@ {odds:.2f}" if odds else "(odds incomplete)"
        lines.append(f"  🔗 {len(picks)}-pick parlay {odds_txt} · est. {100 * prob:.0f}%{record_line(name)}")
        everything += picks

    if everything:
        prob, odds = _parlay(everything)
        odds_txt = f"@ {odds:.2f}" if odds else "(odds incomplete)"
        lines.append(f"\n🎯 All {len(everything)} together {odds_txt} · est. {100 * prob:.1f}%{record_line('all')}")
    lines.append("\nest. = how often that kind of pick (type + size of the form gap) came true in "
                 "the league's backtests since 2024-25; parlays multiply them, assuming independent games. "
                 "Odds: DraftKings via ESPN. Just a lean, not a sure thing.")
    message = "\n".join(lines)
    Path("data").mkdir(exist_ok=True)
    Path("data/message.txt").write_text(message)
    print(message)


def backtest():
    """Replay every past week (Thursday→Wednesday): pick each league's top 3
    by estimated probability among that week's matches, and score the
    3-pick parlays and the combined parlay at the stored odds."""
    from collections import defaultdict
    from datetime import timedelta

    from backtest import replay
    from fetch_data import fetch_past_tournaments

    weeks = defaultdict(dict)
    for name in LEAGUES:
        cfg = load_config(name)
        cal = load_calibration(name)
        for events in fetch_past_tournaments(cfg["league"], cfg["history_start"]).values():
            details = fetch_details([e for e in events if e["finished"]], cfg["league"])
            by_id = {e["id"]: e for e in events}
            for r in replay(events, cfg, details):
                if r["pick_type"] == "skip":
                    continue
                prob = estimate(cal, r["pick_type"], r["edge"], r["rule"])
                ev = by_id[r["id"]]
                d = ev["date"].astimezone(TZ).date()
                week = d - timedelta(days=(d.weekday() - 3) % 7)  # Thursday on/before
                weeks[week].setdefault(name, []).append(dict(
                    r, prob=prob, home={"id": ev["home_id"]}, away={"id": ev["away_id"]}))

    leg = defaultdict(lambda: [0, 0])
    league_parlays = defaultdict(lambda: [0, 0, 0.0, 0])  # hits, n, profit, n priced
    full = [0, 0, 0.0, 0]
    for week, by_league in sorted(weeks.items()):
        combined = []
        for name in LEAGUES:
            picks = top_picks(by_league.get(name, []))
            if len(picks) < PER_LEAGUE:
                combined = None
                continue
            for p in picks:
                leg[name][0] += p["correct"]
                leg[name][1] += 1
            hit = all(p["correct"] for p in picks)
            lp = league_parlays[name]
            lp[0] += hit
            lp[1] += 1
            if all(p["pick_odds"] for p in picks):
                odds = 1.0
                for p in picks:
                    odds *= p["pick_odds"]
                lp[2] += (odds - 1) if hit else -1
                lp[3] += 1
            if combined is not None:
                combined += picks
        if combined and len(combined) == PER_LEAGUE * len(LEAGUES):
            hit = all(p["correct"] for p in combined)
            full[0] += hit
            full[1] += 1
            if all(p["pick_odds"] for p in combined):
                odds = 1.0
                for p in combined:
                    odds *= p["pick_odds"]
                full[2] += (odds - 1) if hit else -1
                full[3] += 1

    record = {name: {"singles": leg[name], "parlay": league_parlays[name]} for name in LEAGUES}
    record["all"] = full
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(record, indent=2) + "\n")

    print("Weekly top-3 picks, replayed since 2024-25 (1 unit per parlay; profit only where odds exist):")
    for name in LEAGUES:
        h, n = leg[name]
        ph, pn, pu, pp = league_parlays[name]
        print(f"  {load_config(name)['league_name']:<15} single picks {h}/{n} ({100*h/max(n,1):.0f}%) · "
              f"3-pick parlay {ph}/{pn} weeks ({100*ph/max(pn,1):.0f}%) · {pu:+.1f}u on {pp}")
    h, n, u, pn = full
    print(f"  {'All 9':<15} parlay {h}/{n} weeks ({100*h/max(n,1):.1f}%) · {u:+.1f}u on {pn}")


if __name__ == "__main__":
    import sys
    backtest() if "--backtest" in sys.argv else main()
