#!/usr/bin/env python3
"""
Semantic Scholar fetch helpers, shared by build_digest.py.

  1. Similar to your work: seed Semantic Scholar's Recommendations API with the
     anchors in research_profile.json. Anchors with a DOI are used directly;
     anchors without one (in-prep manuscripts) are matched to an S2 paper by
     title, since some preprints/venues get indexed before a DOI exists.
     Anchors that don't correspond to a real paper (e.g. "Qualifying Exams")
     or that don't match anything on S2 are skipped.
  2. From authors you follow: for entries in authors.json missing a
     semantic_scholar_id, search by name and print candidates to hand-verify
     and paste in (avoids name collisions — see README). For entries that
     already have an id, fetch their recent papers.

Run directly (`python fetch_papers.py`) for a preliminary, prints-only look
at what these two sources currently return.
"""

import json
import os
import time
import requests
from pathlib import Path

GRAPH_API = "https://api.semanticscholar.org/graph/v1"
RECS_API = "https://api.semanticscholar.org/recommendations/v1"
RECENT_DAYS = 90
TOP_N_RECOMMENDATIONS = 3
MAX_RETRIES = 5
TITLE_OVERLAP_THRESHOLD = 0.6  # fraction of query words that must appear in the matched title
NOT_A_PAPER_TITLES = {"qualifying exams"}  # anchors that are notes, not real paper titles


def load_env_file(path='.env'):
    """Minimal .env loader — no extra dependency needed."""
    if not Path(path).exists():
        return
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file()
S2_API_KEY = os.environ.get('S2_API_KEY')  # optional — moves off the shared unauthenticated rate limit


def request_with_retry(method, url, **kwargs):
    headers = kwargs.pop('headers', {})
    if S2_API_KEY:
        headers['x-api-key'] = S2_API_KEY
    for attempt in range(MAX_RETRIES):
        resp = requests.request(method, url, timeout=15, headers=headers, **kwargs)
        if resp.status_code != 429:
            return resp
        time.sleep(10 * (attempt + 1))
    return resp


def load_anchors():
    with open('research_profile.json') as f:
        return json.load(f)['anchors']


def load_authors():
    with open('authors.json') as f:
        return json.load(f)['authors']


def word_overlap(query_title, matched_title):
    query_words = {w for w in query_title.lower().split() if len(w) > 2}
    matched_words = {w for w in matched_title.lower().split() if len(w) > 2}
    if not query_words:
        return 0
    return len(query_words & matched_words) / len(query_words)


def find_seed_id_by_title(title, verbose=True):
    resp = request_with_retry(
        "GET", f"{GRAPH_API}/paper/search/match",
        params={"query": title, "fields": "title"},
    )
    if resp.status_code != 200:
        if verbose:
            print(f"   (no S2 match for \"{title}\" — likely not indexed yet)")
        return None

    match = resp.json().get('data', [{}])[0]
    matched_title = match.get('title', '')
    if word_overlap(title, matched_title) < TITLE_OVERLAP_THRESHOLD:
        if verbose:
            print(f"   (skipping weak title match for \"{title}\": got \"{matched_title}\")")
        return None

    if verbose:
        print(f"   (matched \"{title}\" -> \"{matched_title}\")")
    return match.get('paperId')


def build_seed_ids(anchors, verbose=True):
    seed_ids = []
    for a in anchors:
        if a['title'].strip().lower() in NOT_A_PAPER_TITLES:
            continue
        if a.get('doi'):
            seed_ids.append(f"DOI:{a['doi']}")
            continue
        seed_id = find_seed_id_by_title(a['title'], verbose=verbose)
        time.sleep(1)
        if seed_id:
            seed_ids.append(seed_id)
    return seed_ids


def get_recommendations(anchors, limit=TOP_N_RECOMMENDATIONS, verbose=True):
    """Returns a list of paper dicts (title, year, venue, url, externalIds, paperId)."""
    seed_ids = build_seed_ids(anchors, verbose=verbose)
    if not seed_ids:
        if verbose:
            print("(no anchors resolved to a seed paper — nothing to seed recommendations with)")
        return []

    resp = request_with_retry(
        "POST", f"{RECS_API}/papers/",
        params={"fields": "title,year,venue,url,externalIds", "limit": limit},
        json={"positivePaperIds": seed_ids, "negativePaperIds": []},
    )
    if resp.status_code != 200:
        if verbose:
            print(f"(recommendations request failed: {resp.status_code} {resp.text[:200]})")
        return []

    return resp.json().get('recommendedPapers', [])


def search_author_candidates(name, verbose=True):
    resp = request_with_retry(
        "GET", f"{GRAPH_API}/author/search",
        params={"query": name, "fields": "name,affiliations,paperCount,hIndex,url"},
    )
    if resp.status_code != 200:
        if verbose:
            print(f"   (search failed: {resp.status_code})")
        return []

    candidates = resp.json().get('data', [])[:3]
    if verbose:
        if not candidates:
            print("   (no candidates found)")
        for c in candidates:
            affil = ", ".join(c.get('affiliations') or []) or "affiliation unknown"
            print(f"   candidate id={c['authorId']} — {c['name']} — {affil} — {c['paperCount']} papers, h-index {c['hIndex']}")
            print(f"   {c['url']}")
    return candidates


def recent_papers_for_author(author_id, since_days=RECENT_DAYS, verbose=True):
    """Returns a list of paper dicts published in the last `since_days` days."""
    resp = request_with_retry(
        "GET", f"{GRAPH_API}/author/{author_id}/papers",
        params={"fields": "title,year,venue,externalIds,url,publicationDate,abstract", "limit": 20},
    )
    if resp.status_code != 200:
        if verbose:
            print(f"   (papers request failed: {resp.status_code})")
        return []

    papers = resp.json().get('data', [])
    cutoff = time.time() - since_days * 86400
    recent = []
    for p in papers:
        pub_date = p.get('publicationDate')
        if not pub_date:
            continue
        pub_ts = time.mktime(time.strptime(pub_date, "%Y-%m-%d"))
        if pub_ts >= cutoff:
            recent.append(p)

    if verbose:
        if not recent:
            print(f"   (nothing in the last {since_days} days)")
        for p in recent:
            print(f"   • {p.get('title')} ({p.get('publicationDate')}) — {p.get('venue') or 'venue unknown'}")
            print(f"     {p.get('url')}")
    return recent


def search_papers_by_keyword(keyword, limit=10, verbose=True):
    """Plain relevance-ranked S2 search for a keyword — used for the field-watch section."""
    resp = request_with_retry(
        "GET", f"{GRAPH_API}/paper/search",
        params={"query": keyword, "fields": "title,year,venue,url,externalIds,abstract", "limit": limit},
    )
    if resp.status_code != 200:
        if verbose:
            print(f"   (search failed for \"{keyword}\": {resp.status_code})")
        return []
    return resp.json().get('data', [])


if __name__ == '__main__':
    anchors = load_anchors()
    authors = load_authors()

    print("=== Similar to your work ===\n")
    recs = get_recommendations(anchors)
    for p in recs:
        print(f"• {p.get('title')} ({p.get('year')}) — {p.get('venue') or 'venue unknown'}")
        print(f"   {p.get('url')}")

    print("\n=== From authors you follow ===\n")
    for author in authors:
        print(f"\n{author['name']} ({author.get('note') or 'no note'})")
        if author.get('semantic_scholar_id'):
            recent_papers_for_author(author['semantic_scholar_id'])
        else:
            search_author_candidates(author['name'])
        time.sleep(3)  # be polite to the unauthenticated rate limit
