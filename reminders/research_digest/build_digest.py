#!/usr/bin/env python3
"""
Build the monthly research digest message from two sources:
  1. Papers similar to your own work (S2 Recommendations, seeded by research_profile.json)
  2. New papers from authors.json since the last run

Both pools are deduped against data/seen_papers.json, capped at
config.json's max_papers_per_digest, and everything considered (shown or
not) is recorded as seen so it never resurfaces. Authors whose new papers
didn't make the cut are named in a one-line pointer instead of dropped
silently.
"""

import html
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from fetch_papers import get_recommendations, recent_papers_for_author, load_anchors, load_authors

FALLBACK_LOOKBACK_DAYS = 35  # used only on the very first run, before last_run exists
RECOMMENDATION_POOL_SIZE = 15  # fetched pre-dedup, so 5 good ones usually survive


def load_config():
    with open('config.json') as f:
        return json.load(f)


def load_seen():
    path = Path('data/seen_papers.json')
    if not path.exists():
        return {"seen": [], "last_run": None}
    return json.loads(path.read_text())


def paper_key(paper):
    ext = paper.get('externalIds') or {}
    if ext.get('DOI'):
        return f"DOI:{ext['DOI']}"
    if ext.get('ArXiv'):
        return f"ARXIV:{ext['ArXiv']}"
    return f"S2:{paper.get('paperId')}"


def keyword_score(paper, keywords):
    text = ((paper.get('title') or '') + ' ' + (paper.get('abstract') or '')).lower()
    return sum(1 for kw in keywords if kw.lower() in text)


def lookback_days(seen):
    if not seen.get('last_run'):
        return FALLBACK_LOOKBACK_DAYS
    last_run = datetime.fromisoformat(seen['last_run'])
    days = (datetime.now(timezone.utc) - last_run).days + 1
    return max(days, 1)


def gather_similar(anchors, seen_ids):
    candidates = get_recommendations(anchors, limit=RECOMMENDATION_POOL_SIZE, verbose=False)
    fresh = [p for p in candidates if paper_key(p) not in seen_ids]
    return fresh


def gather_author_papers(authors, seen_ids, since_days):
    by_author = []
    for author in authors:
        if not author.get('semantic_scholar_id'):
            continue
        papers = recent_papers_for_author(author['semantic_scholar_id'], since_days=since_days, verbose=False)
        time.sleep(1)  # be polite to the unauthenticated rate limit
        for p in papers:
            if paper_key(p) not in seen_ids:
                by_author.append((author['name'], p))
    return by_author


def clean(text):
    return html.unescape(text or '')


def format_venue_year(p):
    venue = clean(p.get('venue')) or 'venue unknown'
    year = p.get('year') or ''
    return f"{venue} ({year})" if year else venue


def build_message(similar, spotlighted_authors, other_authors, month_label):
    lines = [f"📚 Research Digest — {month_label}"]

    if similar:
        lines.append("\n🔬 Similar to your work")
        for p in similar:
            lines.append(f"• {clean(p.get('title'))} — {format_venue_year(p)}")
            lines.append(f"  {p.get('url')}")

    if spotlighted_authors:
        lines.append("\n👤 New from authors you follow")
        for name, p in spotlighted_authors:
            lines.append(f"• {name} — {clean(p.get('title'))} ({p.get('publicationDate') or p.get('year')})")
            lines.append(f"  {p.get('url')}")

    if other_authors:
        lines.append(f"\nAlso new this month, not shown: {', '.join(other_authors)} — check semanticscholar.org")

    if not similar and not spotlighted_authors:
        lines.append("\nNo new relevant papers this month.")

    return "\n".join(lines)


def main():
    config = load_config()
    max_papers = config['output']['max_papers_per_digest']
    keywords = config['keywords']

    seen = load_seen()
    seen_ids = set(seen['seen'])
    since_days = lookback_days(seen)

    anchors = load_anchors()
    authors = load_authors()

    similar_pool = gather_similar(anchors, seen_ids)
    author_pool = gather_author_papers(authors, seen_ids, since_days)

    # Rank author papers by keyword relevance first, recency as tiebreaker
    author_pool.sort(key=lambda item: (keyword_score(item[1], keywords), item[1].get('publicationDate') or ''), reverse=True)

    similar_budget = min(5, max_papers)
    similar = similar_pool[:similar_budget]

    author_budget = max(max_papers - len(similar), 0)
    spotlighted_authors = author_pool[:author_budget]
    leftover_authors = author_pool[author_budget:]
    other_authors = sorted({name for name, _ in leftover_authors} - {name for name, _ in spotlighted_authors})

    month_label = datetime.now().strftime("%B %Y")
    message = build_message(similar, spotlighted_authors, other_authors, month_label)

    Path('data').mkdir(exist_ok=True)
    Path('data/message.txt').write_text(message)

    archive_month = datetime.now().strftime("%Y-%m")
    archive = {
        "similar": [{"title": p.get('title'), "url": p.get('url'), "key": paper_key(p)} for p in similar],
        "authors": [{"name": name, "title": p.get('title'), "url": p.get('url'), "key": paper_key(p)} for name, p in spotlighted_authors],
        "other_authors": other_authors,
    }
    Path(f'data/digest_{archive_month}.json').write_text(json.dumps(archive, indent=2))

    # Everything considered (shown or not) is marked seen so it never resurfaces
    considered_keys = {paper_key(p) for p in similar_pool} | {paper_key(p) for _, p in author_pool}
    seen['seen'] = sorted(seen_ids | considered_keys)
    seen['last_run'] = datetime.now(timezone.utc).isoformat()
    Path('data/seen_papers.json').write_text(json.dumps(seen, indent=2))

    print(message)
    print(f"\n\n✓ Saved to data/message.txt ({len(considered_keys)} new papers marked seen)")


if __name__ == '__main__':
    main()
