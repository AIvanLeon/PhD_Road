#!/usr/bin/env python3
"""
Build the weekly Liga MX bet-advisor message: for each fixture in the
lookahead window, rate both teams on current-season form (last-N points per
game + shots-on-target difference), adjust for stakes in the final rounds,
and pick draw / double chance / win (strong edges only) with DraftKings odds.
Lists each team's top scorers/assisters and flags any who looked unavailable
in the last match. Writes data/message.txt.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


from fetch_data import build_table, fetch_current_tournament, upcoming_fixtures
from match_details import fetch_details
from players import format_players, key_players

TZ = ZoneInfo("America/Mexico_City")


def load_config(name=None):
    """leagues/<name>.json; name from `--league <name>` (default liga_mx)."""
    if name is None:
        args = sys.argv[1:]
        name = args[args.index("--league") + 1] if "--league" in args else "liga_mx"
    return json.loads(Path(f"leagues/{name}.json").read_text())


def zone_undecided(team, table, k):
    """Can this team still finish on the other side of the top-`k` line?"""
    others = [t for t in table.values() if t["id"] != team["id"]]
    if team["rank"] <= k:
        return any(t["rank"] > k and t["points"] + 3 * t["remaining"] >= team["points"] for t in others)
    kth = sorted(table.values(), key=lambda t: t["rank"])[k - 1]
    return team["points"] + 3 * team["remaining"] >= kth["points"]


def live_zones(team, table, cfg):
    """Table targets (title, top 8, Champions League, survival, …) still open for this team."""
    return [z for z in cfg["stakes"]["zones"] if zone_undecided(team, table, z["top"])]


def stakes_adjustment(team, zones, cfg):
    st = cfg["stakes"]
    if team["remaining"] > st["final_rounds"]:
        return 0.0
    lateness = (st["final_rounds"] - team["remaining"] + 1) / st["final_rounds"]
    if zones:
        return max(z["bonus"] for z in zones) * lateness
    return -st["nothing_to_play_penalty"] * lateness


def stakes_label(zones):
    return "🔥 fighting for " + " / ".join(z["name"] for z in zones) if zones else "😴 nothing left to play for"


def rating(team, cfg):
    w = cfg["weights"]
    return w["form_ppg"] * team["form_ppg"] + w["form_sot_diff"] * team["form_sot_diff"]


def pick_odds(pick_type, fav_side, odds):
    if not odds or not odds.get(fav_side):
        return None
    if pick_type in ("win", "skip"):
        return odds[fav_side]
    if not odds.get("draw"):
        return None
    if pick_type == "draw":
        return odds["draw"]
    return 1 / (1 / odds[fav_side] + 1 / odds["draw"])  # double chance from 1X2 prices


def ordinal(n):
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def choose_pick(edge, home, away, cfg):
    """(pick_type, text, favoured team) from the home-minus-away rating gap."""
    fav = home if edge >= 0 else away
    th = cfg["thresholds"]
    if abs(edge) <= th["draw"]:
        return "draw", "Draw", fav
    if abs(edge) <= th["double_chance"]:
        return "close", f"Double chance {fav['name']} (win or draw)", fav
    if abs(edge) > th["win"]:
        return "win", f"{fav['name']} win", fav
    return "skip", f"No bet — leans {fav['name']}, edge too small to back", fav


def analyze(fx, table, cfg, odds=None):
    home, away = table[fx["home_id"]], table[fx["away_id"]]
    statuses = {t["id"]: live_zones(t, table, cfg) for t in (home, away)}
    r_home = rating(home, cfg) + stakes_adjustment(home, statuses[home["id"]], cfg)
    r_away = rating(away, cfg) + stakes_adjustment(away, statuses[away["id"]], cfg)
    edge = r_home - r_away + cfg.get("home_advantage", 0)
    pick_type, pick, fav = choose_pick(edge, home, away, cfg)
    late = max(home["remaining"], away["remaining"]) <= cfg["stakes"]["final_rounds"]
    motivated = [t for t in (home, away) if statuses[t["id"]]]
    if late and cfg["stakes"].get("motivated_double_chance") and len(motivated) == 1:
        fav = motivated[0]
        pick_type, pick = "close", f"Double chance {fav['name']} (win or draw) — still playing for something, rival isn't"

    fav_side = "home" if fav["id"] == home["id"] else "away"
    return {
        "home": home, "away": away, "statuses": statuses, "late": late,
        "edge": edge, "pick": pick, "pick_type": pick_type, "fav_id": fav["id"],
        "odds": odds, "pick_odds": pick_odds(pick_type, fav_side, odds),
        "round": max(home["played"], away["played"]) + 1,
    }


def team_line(team, label):
    return (f"   {label} {team['name']}: form {team['form'] or '—'} ({team['form_ppg']:.1f} pts/g) · "
            f"shots on target {team['form_sot_diff']:+.1f}/g")


def format_match(a, players):
    h, w = a["home"], a["away"]
    when = a["date"].astimezone(TZ).strftime("%a %b %d, %-I:%M %p")
    lines = [
        f"\n⚽ {h['name']} ({ordinal(h['rank'])}, {h['points']} pts) vs "
        f"{w['name']} ({ordinal(w['rank'])}, {w['points']} pts)",
        f"   🗓 {when} (CDMX)",
        team_line(h, "🏠"),
        format_players(players[h["id"]]),
        team_line(w, "✈️"),
        format_players(players[w["id"]]),
    ]
    if a["late"]:
        lines.append(f"   Stakes: {h['name']} {stakes_label(a['statuses'][h['id']])} · "
                     f"{w['name']} {stakes_label(a['statuses'][w['id']])}")
    odds = f" @ {a['pick_odds']:.2f}" if a["pick_odds"] and a["pick_type"] != "skip" else ""
    lines.append(f"   👉 {a['pick']}{odds}")
    return "\n".join(line for line in lines if line)


def season_record(events, cfg, details):
    from backtest import replay
    rs = replay(events, cfg, details)

    def rec(t):
        rows = [r for r in rs if r["pick_type"] == t]
        if not rows:
            return "—"
        units = sum(r["profit"] for r in rows if r["profit"] is not None)
        return f"{sum(r['correct'] for r in rows)}/{len(rows)} ({units:+.1f}u)"

    return (f"\n\n📊 This season, replayed at DraftKings odds (1u per pick): "
            f"draws {rec('draw')} · double chance {rec('close')} · wins {rec('win')}")


def regular_section(events, table, total_rounds, fixtures, details, cfg):
    analyses = []
    for fx in fixtures:
        a = analyze(fx, table, cfg, details.get(fx["id"], {}).get("odds"))
        a["date"] = fx["date"]
        analyses.append(a)
    round_txt = ", ".join(str(r) for r in sorted({a["round"] for a in analyses}))
    parts = [f"{cfg['round_name']} {round_txt} of {total_rounds} · {cfg['table_note']}"]
    parts += [
        format_match(a, {t["id"]: key_players(t, details, cfg["key_players"]) for t in (a["home"], a["away"])})
        for a in analyses
    ]
    parts.append(season_record(events, cfg, details))
    parts.append(f"\nModel: current season only — pts/game + shots-on-target difference over the last {cfg['form_games']} games, "
                 "⭐ = top goals+assists (⚠️ = looked unavailable last match), "
                 f"stakes in the last {cfg['stakes']['final_rounds']} rounds.")
    return "\n".join(parts)


def main():
    """`--liguilla-only` (used by the extra Monday run) writes an empty
    message unless there are Liguilla matches in the window."""
    from liguilla import liguilla_section

    cfg = load_config()
    label, events, lig = fetch_current_tournament(cfg["league"])
    if not cfg.get("liguilla"):
        lig = []
    wanted = events + lig
    details = fetch_details(wanted, cfg["league"])
    table, total_rounds = build_table(events, cfg["form_games"], cfg.get("rounds_per_team"), details)
    fixtures = [
        fx for fx in upcoming_fixtures(events, cfg["lookahead_days"], cfg.get("kickoff_grace_minutes", 0))
        if table[fx["home_id"]]["remaining"] > 0 and table[fx["away_id"]]["remaining"] > 0
    ]
    sections = []
    if fixtures and "--liguilla-only" not in sys.argv:
        sections.append(regular_section(events, table, total_rounds, fixtures, details, cfg))
    lig_text = liguilla_section(events, lig, cfg, details, cfg["lookahead_days"]) if lig else ""
    if lig_text:
        sections.append(lig_text)

    header = f"🎲 {cfg['league_name']} Bet Advisor — {label} — {datetime.now(TZ).strftime('%B %d, %Y')}"
    if sections:
        message = header + "\n" + "\n\n".join(sections) + "\n\nOdds: DraftKings via ESPN. Just a lean, not a sure thing."
    elif "--liguilla-only" in sys.argv:
        message = ""
    else:
        message = f"{header}\n\nNo matches in the next {cfg['lookahead_days']} days."

    Path("data").mkdir(exist_ok=True)
    Path("data/message.txt").write_text(message)
    print(message or "(nothing to send)")


if __name__ == "__main__":
    main()
