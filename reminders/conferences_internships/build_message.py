#!/usr/bin/env python3
"""
Build a simple monthly Telegram message:
  - Conferences: just name + link, no scraping (you check them yourself).
  - Internships/jobs: fetch each page, pull a few snippets that match your
    research keywords, so you get a hint of what's currently posted.
No dates, no scoring, no accessibility checks. Keep it simple.
"""

import json
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path

MAX_SNIPPETS_PER_SITE = 3
SNIPPET_PAD = 60  # characters of context around each keyword match

with open('conferences.json') as f:
    conferences = json.load(f)['conferences']

with open('internships.json') as f:
    internships = json.load(f)['internships']

with open('config.json') as f:
    config = json.load(f)

KEYWORDS = [kw.lower() for kw in config['user']['keywords']]


def find_snippets(text, url):
    """Find up to MAX_SNIPPETS_PER_SITE keyword matches with surrounding context."""
    text = re.sub(r'\s+', ' ', text)
    low = text.lower()

    snippets = []
    seen = set()
    for kw in KEYWORDS:
        start = 0
        while len(snippets) < MAX_SNIPPETS_PER_SITE:
            idx = low.find(kw, start)
            if idx == -1:
                break
            snippet = text[max(0, idx - SNIPPET_PAD): idx + len(kw) + SNIPPET_PAD].strip()
            if snippet not in seen:
                seen.add(snippet)
                snippets.append(snippet)
            start = idx + len(kw)
        if len(snippets) >= MAX_SNIPPETS_PER_SITE:
            break
    return snippets


def fetch_snippets(name, url):
    try:
        resp = requests.get(url, timeout=8)
        if not (200 <= resp.status_code < 400):
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        for tag in soup(['script', 'style']):
            tag.decompose()
        text = soup.get_text()
        return find_snippets(text, url)
    except Exception:
        return None


def build_conference_section():
    lines = ["📅 CONFERENCES — check for new deadlines:\n"]
    for conf in conferences:
        lines.append(f"• {conf['name']} — {conf['url']}")
    return "\n".join(lines)


def build_internship_section():
    lines = ["\n\n💼 INTERNSHIPS / JOBS — recent matches:\n"]
    for job in internships:
        snippets = fetch_snippets(job['name'], job['url'])
        lines.append(f"\n🔹 {job['name']} — {job['url']}")
        if snippets:
            for s in snippets:
                lines.append(f"   \"...{s}...\"")
        else:
            lines.append("   (no keyword matches found this time — check manually)")
    return "\n".join(lines)


message = build_conference_section() + build_internship_section()

Path('data').mkdir(exist_ok=True)
with open('data/message.txt', 'w') as f:
    f.write(message)

print(message)
print("\n\n✓ Saved to data/message.txt")
