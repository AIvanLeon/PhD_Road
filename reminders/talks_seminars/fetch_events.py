#!/usr/bin/env python3
"""
Fetch upcoming talks/seminars/symposia from two Northwestern sources:
  1. Chemistry department calendar (events-feed.xml) — no filter, everything included.
  2. PlanIt Purple, university-wide calendar — filtered to the categories/audience/
     location saved in config.json (Academic (general) + Sciences, Evanston, Grad Students).

Both return a common event dict shape so build_message.py doesn't care which
source an event came from:
  {"source", "title", "date", "time", "location", "link", "key"}
"""

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup


def fetch_chemistry_events(config):
    """The feed ignores the start/end query params server-side (it always
    returns its full cached event list, past and future) — so the lookahead
    window is applied client-side against each event's start_datetime."""
    cfg = config['chemistry_calendar']
    now = datetime.now(timezone.utc)
    start = int(now.timestamp())
    end = int((now + timedelta(days=cfg['lookahead_days'])).timestamp())

    resp = requests.get(cfg['feed_url'], params={'start': start, 'end': end}, timeout=15)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    events = []
    for e in root.findall('.//event'):
        title = (e.findtext('title') or '').strip()
        if not title:
            continue

        start_dt_raw = e.findtext('start_datetime') or ''
        if not start_dt_raw.isdigit() or not (start <= int(start_dt_raw) <= end):
            continue

        building = e.findtext('.//address/building_name') or ''
        room = e.findtext('.//address/address_2') or ''
        location = ', '.join(part for part in [building, room] if part) or (e.findtext('location') or '')

        events.append({
            'source': 'Chemistry Dept.',
            'title': title,
            'date': e.findtext('date') or '',
            'time': e.findtext('time') or '',
            'location': location,
            'link': e.findtext('ppurl') or None,
            'key': f"chem:{start_dt_raw}:{title}",
        })
    return events


def fetch_planitpurple_events(config, max_retries=2):
    """Returns (events, ok). ok=False means parsing failed — caller should
    fall back to just linking the saved search instead of showing nothing."""
    cfg = config['planitpurple']
    today = datetime.now().strftime('%Y-%m-%d')
    payload = {
        'calendar_id': '0',
        'feed_id': '0',
        'eventdate': today,
        'search_terms': '',
        'prev_link': '0',
        'url_token': '',
        **cfg['filters'],
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(cfg['refresh_endpoint'], data=payload, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            articles = soup.select('article.event')
            if not articles:
                return [], False

            events = []
            for art in articles:
                link_tag = art.select_one('.event-content h3 a')
                if not link_tag:
                    continue
                title = link_tag.get_text(strip=True)
                href = link_tag.get('href', '')
                link = href if href.startswith('http') else f"{cfg['base_url']}{href}"

                month = art.select_one('.event-date .month')
                day = art.select_one('.event-date .day')
                year = art.select_one('.event-date .year')
                date = ' '.join(t.get_text(strip=True) for t in [month, day, year] if t)

                time_loc = art.select_one('.time-location')
                time_str = ''
                location = ''
                if time_loc:
                    strong = time_loc.select_one('strong')
                    time_str = strong.get_text(strip=True) if strong else ''
                    full_text = re.sub(r'\s+', ' ', time_loc.get_text(' ', strip=True))
                    location = full_text.replace(time_str, '', 1).strip()

                events.append({
                    'source': 'PlanIt Purple',
                    'title': title,
                    'date': date,
                    'time': time_str,
                    'location': location,
                    'link': link,
                    'key': f"pip:{href}",
                })
            return events, True
        except Exception:
            if attempt + 1 < max_retries:
                time.sleep(2)
                continue
            return [], False


if __name__ == '__main__':
    import json
    with open('config.json') as f:
        cfg = json.load(f)

    print("=== Chemistry Dept. ===")
    for ev in fetch_chemistry_events(cfg):
        print(f"- {ev['title']} | {ev['date']} {ev['time']} | {ev['location']}")

    print("\n=== PlanIt Purple ===")
    pip_events, ok = fetch_planitpurple_events(cfg)
    if not ok:
        print(f"(parsing failed — fall back to {cfg['planitpurple']['saved_link']})")
    for ev in pip_events:
        print(f"- {ev['title']} | {ev['date']} {ev['time']} | {ev['location']}")
