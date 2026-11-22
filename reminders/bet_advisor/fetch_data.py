#!/usr/bin/env python3
"""
Fetch the current tournament's match results from ESPN's public API (no key
needed) and compute the table plus last-N form per team.

Run directly for a printed table preview.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE = "https://site.api.espn.com/apis"
FINISHED = {"STATUS_FULL_TIME", "STATUS_FINAL", "STATUS_FINAL_AET", "STATUS_FINAL_PEN"}


def _get(url, **params):
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


LIGUILLA_STAGES = ("quarterfinals", "semifinals", "finals")


def _classify(season):
    """(tournament label, stage) for a season blob, e.g. ('Clausura 2026',
    'semifinals'); None for play-in games or anything unrecognized."""
    slug = season.get("slug", "")
    if slug.startswith("torneo-"):
        kind, stage = slug.split("-", 1)[1].capitalize(), "regular"
    else:
        kind = slug.split("-", 1)[0].capitalize()
        stage = slug.rsplit("---", 1)[-1]
        if kind not in ("Apertura", "Clausura") or stage not in LIGUILLA_STAGES:
            return None
    year = season["year"] + (1 if kind == "Clausura" else 0)
    return f"{kind} {year}", stage


def _month_events(league, month, now):
    """Raw scoreboard events for one month; past months cached on disk."""
    key = month.strftime("%Y%m")
    path = Path("data/scoreboard_cache") / f"{league}_{key}.json"
    done = (month.year, month.month) < (now.year, now.month)
    if done and path.exists():
        return json.loads(path.read_text())
    batch = _get(f"{BASE}/site/v2/sports/soccer/{league}/scoreboard", dates=key).get("events", [])
    if done:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(batch))
    return batch


def _normalized(raw_events, label):
    out = {}
    for e in raw_events:
        c = _classify(e.get("season", {}))
        if c and c[0] == label:
            out[e["id"]] = dict(_normalize(e), stage=c[1])
    return sorted(out.values(), key=lambda e: e["date"])


def fetch_current_tournament(league):
    """(label, regular-season events, Liguilla events) for the tournament
    being played now. ESPN's scoreboard only accepts a single month
    (YYYYMM), so walk back month by month from next month."""
    now = datetime.now(timezone.utc)
    month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
    raw, label = [], None
    for _ in range(9):
        batch = _month_events(league, month, now)
        if label is None:
            labels = [c[0] for c in (_classify(e.get("season", {})) for e in batch) if c]
            label = labels[-1] if labels else None
        mine = [e for e in batch if label and (_classify(e.get("season", {})) or ("",))[0] == label]
        if label and not mine and raw:
            break
        raw += mine
        month = (month - timedelta(days=1)).replace(day=1)
    events = _normalized(raw, label)
    return (label, [e for e in events if e["stage"] == "regular"],
            [e for e in events if e["stage"] != "regular"])


def fetch_season_events(league):
    return fetch_current_tournament(league)[1]


def fetch_past_tournaments(league, start="202401", liguilla=False):
    """Every tournament from `start` to now as {label: events}, regular
    season only, or with liguilla=True {label: (regular, liguilla)}."""
    now = datetime.now(timezone.utc)
    month = datetime.strptime(start, "%Y%m").replace(tzinfo=timezone.utc)
    raw = []
    while month <= now:
        raw += _month_events(league, month, now)
        month = (month + timedelta(days=32)).replace(day=1)
    labels = []
    for e in raw:
        c = _classify(e.get("season", {}))
        if c and c[0] not in labels:
            labels.append(c[0])
    out = {}
    for label in labels:
        events = _normalized(raw, label)
        regular = [e for e in events if e["stage"] == "regular"]
        lig = [e for e in events if e["stage"] != "regular"]
        out[label] = (regular, lig) if liguilla else regular
    return out


def _normalize(event):
    comp = event["competitions"][0]
    sides = {c["homeAway"]: c for c in comp["competitors"]}
    status = event["status"]["type"]["name"]
    return {
        "id": event["id"],
        "date": datetime.fromisoformat(event["date"].replace("Z", "+00:00")),
        "finished": status in FINISHED,
        "status": status,
        "home_id": sides["home"]["team"]["id"],
        "away_id": sides["away"]["team"]["id"],
        "home_name": sides["home"]["team"]["displayName"],
        "away_name": sides["away"]["team"]["displayName"],
        "home_score": int(sides["home"].get("score") or 0),
        "away_score": int(sides["away"].get("score") or 0),
        "venue": comp.get("venue", {}).get("fullName", ""),
    }


def _points(gf, ga):
    return 3 if gf > ga else 1 if gf == ga else 0


def build_table(events, form_games, total_rounds=None, details=None):
    """Compute the league table from finished regular-season matches (each
    team's first `total_rounds` games, so Liguilla games never leak in), plus
    last-N form in points and shots-on-target difference (when `details` is
    given). Ranked by points, goal diff, goals for."""
    details = details or {}
    names = {}
    for ev in events:
        names[ev["home_id"]] = ev["home_name"]
        names[ev["away_id"]] = ev["away_name"]
    total_rounds = total_rounds or len(names) - 1
    games = {tid: [] for tid in names}
    for ev in events:
        if not ev["finished"]:
            continue
        stats = details.get(ev["id"], {}).get("stats", {})
        for tid, opp, gf, ga in (
            (ev["home_id"], ev["away_id"], ev["home_score"], ev["away_score"]),
            (ev["away_id"], ev["home_id"], ev["away_score"], ev["home_score"]),
        ):
            if len(games[tid]) < total_rounds:
                has_sot = tid in stats and opp in stats
                games[tid].append({
                    "event_id": ev["id"], "gf": gf, "ga": ga, "pts": _points(gf, ga),
                    "sot_diff": stats[tid]["sot"] - stats[opp]["sot"] if has_sot else None,
                })

    table = {}
    for tid, g in games.items():
        recent = g[-form_games:]
        sot_recent = [x["sot_diff"] for x in recent if x["sot_diff"] is not None]
        table[tid] = {
            "id": tid,
            "name": names[tid],
            "played": len(g),
            "points": sum(x["pts"] for x in g),
            "gf": sum(x["gf"] for x in g),
            "ga": sum(x["ga"] for x in g),
            "remaining": total_rounds - len(g),
            "form": "".join("W" if x["pts"] == 3 else "D" if x["pts"] == 1 else "L" for x in recent),
            "form_ppg": sum(x["pts"] for x in recent) / (len(recent) or 1),
            "form_sot_diff": sum(sot_recent) / (len(sot_recent) or 1),
            "match_ids": [x["event_id"] for x in g],
        }

    ranked = sorted(table.values(), key=lambda t: (-t["points"], -(t["gf"] - t["ga"]), -t["gf"]))
    for i, t in enumerate(ranked, 1):
        t["rank"] = i
    return table, total_rounds


def upcoming_fixtures(events, days):
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=days)
    return [e for e in events if e["status"] == "STATUS_SCHEDULED" and now <= e["date"] <= horizon]


if __name__ == "__main__":
    events = fetch_season_events("mex.1")
    table, rounds = build_table(events, 4)
    print(f"{len(events)} matches, {rounds} rounds")
    for t in sorted(table.values(), key=lambda t: t["rank"]):
        print(f"{t['rank']:>2} {t['name']:<22} {t['points']:>3}pts  {t['gf']}-{t['ga']}  form {t['form']}")
