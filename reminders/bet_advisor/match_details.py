#!/usr/bin/env python3
"""
Per-match details from ESPN's summary endpoint: DraftKings odds (1X2 and
Over/Under), team shots/shots on target/red cards, and per-player stats.
Finished matches are cached in data/match_cache/ since they never change;
upcoming matches are always re-fetched (odds move).
"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary"
CACHE = Path("data/match_cache")


def american_to_decimal(ml):
    if ml is None:
        return None
    ml = float(ml)
    return 1 + ml / 100 if ml > 0 else 1 + 100 / abs(ml)


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse(data, event):
    odds = None
    pc = (data.get("pickcenter") or [None])[0]
    if pc and pc.get("homeTeamOdds", {}).get("moneyLine") is not None:
        odds = {
            "home": american_to_decimal(pc["homeTeamOdds"].get("moneyLine")),
            "away": american_to_decimal(pc["awayTeamOdds"].get("moneyLine")),
            "draw": american_to_decimal((pc.get("drawOdds") or {}).get("moneyLine")),
            "line": pc.get("overUnder"),
            "over": american_to_decimal(pc.get("overOdds")),
            "under": american_to_decimal(pc.get("underOdds")),
        }

    stats = {}
    for team in data.get("boxscore", {}).get("teams", []):
        s = {x["name"]: x.get("displayValue") for x in team.get("statistics", [])}
        stats[team["team"]["id"]] = {
            "shots": _num(s.get("totalShots")),
            "sot": _num(s.get("shotsOnTarget")),
            "red": _num(s.get("redCards")),
            "possession": _num(s.get("possessionPct")),
        }

    players = []
    for roster in data.get("rosters", []):
        tid = roster["team"]["id"]
        for p in roster.get("roster", []):
            s = {x["name"]: x.get("displayValue") for x in p.get("stats", [])}
            players.append({
                "team_id": tid,
                "id": p["athlete"]["id"],
                "name": p["athlete"]["displayName"],
                "position": p.get("position", {}).get("abbreviation", ""),
                "starter": p.get("starter", False),
                "played": bool(p.get("starter") or p.get("subbedIn")),
                "goals": _num(s.get("totalGoals")),
                "assists": _num(s.get("goalAssists")),
                "sot": _num(s.get("shotsOnTarget")),
                "yellow": _num(s.get("yellowCards")),
                "red": _num(s.get("redCards")),
            })
    return {"id": event["id"], "odds": odds, "stats": stats, "players": players}


def fetch_detail(event, league):
    path = CACHE / f"{event['id']}.json"
    if event["finished"] and path.exists():
        return json.loads(path.read_text())
    try:
        resp = requests.get(SUMMARY.format(league=league), params={"event": event["id"]}, timeout=30)
        resp.raise_for_status()
        detail = _parse(resp.json(), event)
    except (requests.RequestException, KeyError, ValueError):
        return {"id": event["id"], "odds": None, "stats": {}, "players": []}
    if event["finished"] and detail["stats"]:
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(detail, ensure_ascii=False))
    return detail


def fetch_details(events, league, workers=8):
    """event id -> detail, for every finished or upcoming event given."""
    with ThreadPoolExecutor(workers) as pool:
        details = list(pool.map(lambda e: fetch_detail(e, league), events))
    return {d["id"]: d for d in details}
