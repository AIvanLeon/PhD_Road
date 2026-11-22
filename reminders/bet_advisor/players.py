#!/usr/bin/env python3
"""
Key players per team: season goals + assists from per-match player stats,
and whether each one looked unavailable in the team's last match (red card,
not in the squad, or an unused sub). Lineups are only published ~1 h before
kickoff, so last-match availability is the best pre-match signal we have.
"""

from collections import defaultdict


def key_players(team, details, top_n):
    totals = defaultdict(lambda: {"name": "", "goals": 0, "assists": 0, "apps": 0})
    for mid in team["match_ids"]:
        for p in details.get(mid, {}).get("players", []):
            if p["team_id"] != team["id"]:
                continue
            t = totals[p["id"]]
            t["name"] = p["name"]
            t["goals"] += p["goals"]
            t["assists"] += p["assists"]
            t["apps"] += p.get("played", True)

    ranked = sorted(
        (dict(id=pid, **t) for pid, t in totals.items() if t["goals"] + t["assists"] > 0),
        key=lambda p: (-(p["goals"] + p["assists"]), -p["goals"]),
    )[:top_n]

    last = details.get(team["match_ids"][-1], {}).get("players", []) if team["match_ids"] else []
    last_by_id = {p["id"]: p for p in last if p["team_id"] == team["id"]}
    for p in ranked:
        lp = last_by_id.get(p["id"])
        if not last_by_id:
            p["flag"] = None
        elif lp is None:
            p["flag"] = "not in last squad"
        elif lp["red"]:
            p["flag"] = "red card last match"
        elif not lp.get("played", True):
            p["flag"] = "unused sub last match"
        else:
            p["flag"] = None
    return ranked


def format_players(players):
    if not players:
        return ""
    parts = []
    for p in players:
        txt = f"{p['name']} {p['goals']:.0f}G {p['assists']:.0f}A"
        if p["flag"]:
            txt += f" ⚠️ {p['flag']}"
        parts.append(txt)
    return "      ⭐ " + " · ".join(parts)
