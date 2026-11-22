#!/usr/bin/env python3
"""
Liguilla (playoff) model. Two-legged ties, no away goals; the higher seed
(better regular-season rank) hosts the second leg and, in quarterfinals and
semifinals, goes through if the aggregate is level. The final has no seed
advantage (extra time + penalties).

Picks:
- First legs: double chance for the lower seed at home (they must win
  somewhere and the higher seed is happy with a draw away; 28/35 since 2024).
- Second leg of the final: the regular-season rating (last-N form + shots on
  target, end of regular season) with home advantage.
- Second legs of quarterfinals/semifinals, from the higher seed's first-leg
  goal difference d:
    d >= big_lead   -> higher seed win (rival needs a 3+ goal win, a draw is useless to them)
    0 <= d < big_lead -> double chance higher seed (a draw is enough for them)
    d < 0           -> higher seed win (they must win at home; levelling the aggregate is enough)

Run `python liguilla.py` to replay every past Liguilla since Clausura 2024.
"""

from collections import defaultdict

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from build_message import choose_pick, load_config, ordinal, pick_odds, rating
from players import format_players, key_players
from fetch_data import build_table, fetch_past_tournaments
from match_details import fetch_details

SETTLED = {"STATUS_FULL_TIME", "STATUS_FINAL"}  # extra-time/penalty games have no clean 90' result


def build_series(regular, liguilla, cfg, details):
    """One entry per Liguilla match: stage, leg, seeds, and (for second legs)
    the higher seed's first-leg goal difference."""
    table, _ = build_table(regular, cfg["form_games"], details=details)
    ties = defaultdict(list)
    for ev in liguilla:
        ties[(ev["stage"], frozenset((ev["home_id"], ev["away_id"])))].append(ev)
    matches = []
    for (stage, _), legs in ties.items():
        legs.sort(key=lambda e: e["date"])
        a, b = legs[0]["home_id"], legs[0]["away_id"]
        if a not in table or b not in table:
            continue
        higher, lower = (a, b) if table[a]["rank"] < table[b]["rank"] else (b, a)
        first_diff = None
        for leg_no, ev in enumerate(legs[:2], 1):
            matches.append({
                "event": ev, "stage": stage, "leg": leg_no,
                "higher": table[higher], "lower": table[lower],
                "first_diff": first_diff,
            })
            if ev["finished"]:
                hg = ev["home_score"] if ev["home_id"] == higher else ev["away_score"]
                lg = ev["away_score"] if ev["home_id"] == higher else ev["home_score"]
                first_diff = hg - lg
    return table, matches


def liguilla_pick(m, cfg, odds=None):
    ev, higher, lower = m["event"], m["higher"], m["lower"]
    home = higher if ev["home_id"] == higher["id"] else lower
    away = lower if home is higher else higher
    d = m["first_diff"]
    big = cfg["liguilla"]["big_lead"]

    if m["leg"] == 1:
        pick_type, pick, reason = "close", f"Double chance {lower['name']} (win or draw)", \
            "first leg at home — they need a result, a draw away suits the higher seed"
        fav = lower
    elif m["stage"] != "finals" and d is not None:
        if 0 <= d < big:
            pick_type, pick, reason = "close", f"Double chance {higher['name']} (win or draw)", \
                (f"up {d} after leg 1" if d else "level after leg 1") + " — a draw takes them through"
        elif d >= big:
            pick_type, pick, reason = "win", f"{higher['name']} win", \
                f"up {d} after leg 1 — rival needs a {d + 1}+ goal win"
        else:
            pick_type, pick, reason = "win", f"{higher['name']} win", \
                f"down {-d} after leg 1 — must win at home, levelling the tie is enough"
        fav = higher
    else:
        edge = rating(home, cfg) - rating(away, cfg) + cfg.get("home_advantage", 0)
        pick_type, pick, fav = choose_pick(edge, home, away, cfg)
        reason = "form model — no tie advantage in the final"

    fav_side = "home" if fav["id"] == ev["home_id"] else "away"
    return {"pick_type": pick_type, "pick": pick, "fav_id": fav["id"], "reason": reason,
            "pick_odds": pick_odds(pick_type, fav_side, odds)}


def _winner(ev):
    if ev["home_score"] == ev["away_score"]:
        return None
    return ev["home_id"] if ev["home_score"] > ev["away_score"] else ev["away_id"]


def _correct(pick_type, fav_id, winner):
    return {"win": winner == fav_id, "skip": winner == fav_id,
            "close": winner in (fav_id, None), "draw": winner is None}[pick_type]


def replay_all(cfg):
    rows = []
    for label, (regular, lig) in fetch_past_tournaments(cfg["league"], cfg["history_start"], liguilla=True).items():
        if not lig:
            continue
        details = fetch_details([e for e in regular + lig if e["finished"]], cfg["league"])
        _, matches = build_series(regular, lig, cfg, details)
        for m in matches:
            ev = m["event"]
            if ev["status"] not in SETTLED:
                continue
            odds = details.get(ev["id"], {}).get("odds")
            p = liguilla_pick(m, cfg, odds)
            winner = _winner(ev)
            correct = _correct(p["pick_type"], p["fav_id"], winner)
            hw = winner == m["higher"]["id"]
            hl = winner == m["lower"]["id"]
            alt = {}
            if odds and odds.get("home") and odds.get("away") and odds.get("draw"):
                h_side = "home" if ev["home_id"] == m["higher"]["id"] else "away"
                alt = {
                    "higher_win_profit": (odds[h_side] - 1) if hw else -1.0,
                    "higher_dc_profit": (1 / (1 / odds[h_side] + 1 / odds["draw"]) - 1) if not hl else -1.0,
                    "draw_profit": (odds["draw"] - 1) if winner is None else -1.0,
                }
            rows.append({
                "tournament": label, "stage": m["stage"], "leg": m["leg"], "first_diff": m["first_diff"],
                "match": f"{ev['home_name']} {ev['home_score']}-{ev['away_score']} {ev['away_name']}",
                "pick": p["pick"], "pick_type": p["pick_type"], "correct": correct,
                "profit": None if p["pick_odds"] is None else (p["pick_odds"] - 1 if correct else -1.0),
                "higher_result": "W" if hw else "L" if hl else "D", **alt,
            })
    return rows


def _rec(rows):
    if not rows:
        return "—"
    w = sum(r["higher_result"] == "W" for r in rows)
    d = sum(r["higher_result"] == "D" for r in rows)
    l = sum(r["higher_result"] == "L" for r in rows)
    n = len(rows)
    return f"{n:>3} games  higher seed W {w} ({100*w/n:.0f}%)  D {d} ({100*d/n:.0f}%)  L {l} ({100*l/n:.0f}%)"


def _hits(rows, key=None):
    if not rows:
        return "—"
    if key:
        vals = [r[key] for r in rows if r.get(key) is not None]
        return f"{sum(vals):+.1f}u on {len(vals)}" if vals else "no odds"
    vals = [r["profit"] for r in rows if r["profit"] is not None]
    money = f"   {sum(vals):+.1f}u on {len(vals)} with odds" if vals else ""
    return f"{sum(r['correct'] for r in rows)}/{len(rows)} ({100*sum(r['correct'] for r in rows)/len(rows):.0f}%){money}"


def summarize(rows):
    qs = [r for r in rows if r["stage"] != "finals"]
    leg1 = [r for r in rows if r["leg"] == 1]
    leg2 = [r for r in qs if r["leg"] == 2]
    lines = ["What actually happens (higher seed's result):"]
    lines.append(f"  {'Leg 1 (higher seed away)':<34} {_rec(leg1)}")
    lines.append(f"  {'Leg 2, QF/SF (higher seed home)':<34} {_rec(leg2)}")
    for label, cond in (("  …higher seed up ≥2 after leg 1", lambda d: d >= 2),
                        ("  …up 1", lambda d: d == 1),
                        ("  …level", lambda d: d == 0),
                        ("  …down 1", lambda d: d == -1),
                        ("  …down ≥2", lambda d: d <= -2)):
        lines.append(f"  {label:<34} {_rec([r for r in leg2 if cond(r['first_diff'])])}")
    lines.append(f"  {'Finals (both legs)':<34} {_rec([r for r in rows if r['stage'] == 'finals'])}")

    lines.append("\nModel picks (hit rate; profit only where ESPN has odds, i.e. Clausura 2026):")
    lines.append(f"  {'All':<34} {_hits([r for r in rows if r['pick_type'] != 'skip'])}")
    lines.append(f"  {'Leg 1 → double chance lower seed':<34} {_hits(leg1)}")
    lines.append(f"  {'Leg 2 QF/SF (first-leg rule)':<34} {_hits(leg2)}")
    for label, cond in (("  …up ≥2 → higher seed win", lambda d: d >= 2),
                        ("  …up 0–1 → double chance", lambda d: 0 <= d < 2),
                        ("  …down → higher seed win", lambda d: d < 0)):
        lines.append(f"  {label:<34} {_hits([r for r in leg2 if cond(r['first_diff'])])}")
    lines.append(f"  {'Finals leg 2 (form model)':<34} {_hits([r for r in rows if r['stage'] == 'finals' and r['leg'] == 2 and r['pick_type'] != 'skip'])}")

    lines.append("\nFlat strategies on Clausura 2026 Liguilla (only one with odds):")
    for label, key in (("Always higher seed win", "higher_win_profit"),
                       ("Always higher seed double chance", "higher_dc_profit"),
                       ("Always draw", "draw_profit")):
        lines.append(f"  {label:<34} leg 1 {_hits(leg1, key):<16} leg 2 {_hits(leg2, key)}")
    return "\n".join(lines)


STAGE_NAME = {"quarterfinals": "Quarterfinals", "semifinals": "Semifinals", "finals": "Final"}
TZ = ZoneInfo("America/Mexico_City")


def _conditional_leg2(m):
    h = m["higher"]["name"]
    return (f"Depends on leg 1 — if {h} win or draw it → Double chance {h}; "
            f"if they lose it → {h} win (must win at home, levelling is enough)")


def liguilla_section(regular, lig, cfg, details, days, now=None):
    """Message text for Liguilla matches kicking off in the next `days`
    (`now` overridable to preview a past Liguilla)."""
    now = now or datetime.now(timezone.utc)
    horizon = now + timedelta(days=days)
    _, matches = build_series(regular, lig, cfg, details)
    upcoming = sorted((m for m in matches if now <= m["event"]["date"] <= horizon
                       and (m["event"]["status"] == "STATUS_SCHEDULED" or now < datetime.now(timezone.utc))),
                      key=lambda m: m["event"]["date"])
    if not upcoming:
        return ""
    parts = []
    stage = None
    for m in upcoming:
        ev, hi, lo = m["event"], m["higher"], m["lower"]
        if m["stage"] != stage:
            stage = m["stage"]
            parts.append(f"\n🏆 Liguilla — {STAGE_NAME[stage]}")
        home, away = (hi, lo) if ev["home_id"] == hi["id"] else (lo, hi)
        when = ev["date"].astimezone(TZ).strftime("%a %b %d, %-I:%M %p")
        lines = [
            f"\n⚽ {home['name']} ({ordinal(home['rank'])}) vs {away['name']} ({ordinal(away['rank'])}) — leg {m['leg']}",
            f"   🗓 {when} (CDMX)",
            f"   🏠 {home['name']}: form {home['form']} · shots on target {home['form_sot_diff']:+.1f}/g",
            format_players(key_players(home, details, cfg["key_players"])),
            f"   ✈️ {away['name']}: form {away['form']} · shots on target {away['form_sot_diff']:+.1f}/g",
            format_players(key_players(away, details, cfg["key_players"])),
        ]
        if m["leg"] == 2 and m["first_diff"] is not None:
            d = m["first_diff"]
            state = f"up {d}" if d > 0 else f"down {-d}" if d < 0 else "level"
            lines.append(f"   Leg 1: {hi['name']} (higher seed) {state} on aggregate")
        if m["leg"] == 2 and m["first_diff"] is None and stage != "finals":
            lines.append(f"   👉 {_conditional_leg2(m)}")
        else:
            p = liguilla_pick(m, cfg, details.get(ev["id"], {}).get("odds"))
            at = f" @ {p['pick_odds']:.2f}" if p["pick_odds"] and p["pick_type"] != "skip" else ""
            lines.append(f"   👉 {p['pick']}{at} — {p['reason']}")
        parts.append("\n".join(line for line in lines if line))

    rows = replay_all(cfg)
    bets = [r for r in rows if r["pick_type"] != "skip"]
    parts.append(f"\n📊 Liguillas since 2024, replayed: {sum(r['correct'] for r in bets)}/{len(bets)} picks right "
                 f"(leg 1 {sum(r['correct'] for r in bets if r['leg'] == 1)}/{sum(1 for r in bets if r['leg'] == 1)} · "
                 f"leg 2 {sum(r['correct'] for r in bets if r['leg'] == 2)}/{sum(1 for r in bets if r['leg'] == 2)})")
    parts.append("Rules: no away goals; the higher seed hosts leg 2 and goes through on a tied aggregate "
                 "(not in the final, which goes to extra time + penalties).")
    return "\n".join(parts)


if __name__ == "__main__":
    cfg = load_config()
    rows = replay_all(cfg)
    print(summarize(rows))
