#!/usr/bin/env python3
"""
Build the biweekly-ish (actually weekly) Telegram message: upcoming talks,
seminars, and symposia from the Chemistry dept. calendar (no filter) and
PlanIt Purple (filtered to your saved academic/sciences/grad-student search).

Dedup against data/seen_events.json so the same event isn't re-sent every
week while the lookahead windows overlap. Entries expire out of the seen
log once their event date has passed.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fetch_events import fetch_chemistry_events, fetch_planitpurple_events

SEEN_TTL_DAYS = 45  # safety margin past an event's date before pruning it from seen log


def load_config():
    with open('config.json') as f:
        return json.load(f)


def load_seen():
    path = Path('data/seen_events.json')
    if not path.exists():
        return {"seen": {}}
    return json.loads(path.read_text())


def prune_seen(seen):
    now = datetime.now(timezone.utc)
    seen['seen'] = {
        key: expiry for key, expiry in seen['seen'].items()
        if datetime.fromisoformat(expiry) > now
    }
    return seen


def event_expiry(event):
    """Best-effort parse of the event's date for seen-log pruning; falls back
    to a flat TTL from now if the date string can't be parsed."""
    for fmt in ('%B %d, %Y', '%b %d %Y'):
        try:
            dt = datetime.strptime(event['date'], fmt).replace(tzinfo=timezone.utc)
            return (dt + timedelta(days=SEEN_TTL_DAYS)).isoformat()
        except ValueError:
            continue
    return (datetime.now(timezone.utc) + timedelta(days=SEEN_TTL_DAYS)).isoformat()


def build_section(header, events):
    if not events:
        return ""
    lines = [f"\n\n{header}"]
    for ev in events:
        lines.append(f"\n🔹 {ev['title']}")
        when = f"{ev['date']}" + (f", {ev['time']}" if ev['time'] else "")
        lines.append(f"   {when}")
        if ev['location']:
            lines.append(f"   📍 {ev['location']}")
        if ev['link']:
            lines.append(f"   {ev['link']}")
    return "\n".join(lines)


def main():
    config = load_config()
    seen = prune_seen(load_seen())
    seen_keys = set(seen['seen'].keys())

    chem_events = fetch_chemistry_events(config)
    pip_events, pip_ok = fetch_planitpurple_events(config)

    chem_new = [e for e in chem_events if e['key'] not in seen_keys]
    pip_new = [e for e in pip_events if e['key'] not in seen_keys]

    lines = [f"🎤 Talks & Seminars — {datetime.now().strftime('%B %d, %Y')}"]

    chem_section = build_section("🧪 Chemistry Department", chem_new)
    pip_section = build_section("🏛️ University-wide (PlanIt Purple)", pip_new)

    if not pip_ok:
        pip_section += (
            f"\n\n(Couldn't parse PlanIt Purple this time — check manually: "
            f"{config['planitpurple']['saved_link']})"
        )

    message = "".join([lines[0], chem_section, pip_section])
    if not chem_new and not pip_new:
        message += "\n\nNo new events since last week."

    Path('data').mkdir(exist_ok=True)
    Path('data/message.txt').write_text(message)

    for ev in chem_new + pip_new:
        seen['seen'][ev['key']] = event_expiry(ev)
    Path('data/seen_events.json').write_text(json.dumps(seen, indent=2))

    print(message)
    print(f"\n\n✓ Saved to data/message.txt ({len(chem_new) + len(pip_new)} new events marked seen)")


if __name__ == '__main__':
    main()
