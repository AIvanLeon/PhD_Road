# Research Digest: Monthly Research Paper Digest

A monthly Telegram digest of new papers relevant to your research — matched against your own published work and tracked researchers.

## Files

- `authors.json` — Researchers you follow (Semantic Scholar author IDs, resolved once by hand to avoid name collisions)
- `research_profile.json` — Anchor abstracts from your own papers/ongoing work, used as the comparison baseline
- `config.json` — Keywords, arXiv categories, output size
- `data/` — **Tracked in git** (not gitignored — this is persistent state, not throwaway output)
  - `seen_papers.json` — Dedupe log (arXiv ID / DOI) so nothing is repeated across months. Must survive between GitHub Actions runs, so the workflow commits it back after each run.
  - `digest_YYYY-MM.json` — Archive of what was sent each month

## Sources (planned)

- **arXiv API** — free, no key. Primary preprint source for `cond-mat.mtrl-sci`, `physics.chem-ph`, `physics.comp-ph`, `cs.LG`
- **Semantic Scholar API** — free. Two uses:
  1. **Recommendations endpoint** seeded with your own papers (from `research_profile.json`) — finds similar work
  2. **Author papers endpoint** for each entry in `authors.json` — catches new work from people you follow

## Matching approach (v1)

1. Semantic Scholar Recommendations (seeded by your papers) — zero cost, zero compute
2. Keyword boost on arXiv results (reusing `config.json` keywords) — zero cost, works well on clean abstract text
3. Author tracking — highest priority section, since it's people you already know are relevant

No embeddings or Claude API calls in v1 — add later only if relevance quality needs improvement.

## Setup TODO

1. Fill in `semantic_scholar_id` for each entry in `authors.json` (resolve once via Semantic Scholar's author search) — in progress, see prints from `fetch_papers.py`
2. Fill in `abstract` for each entry in `research_profile.json`
3. ~~Build `fetch_papers.py`~~ done (preliminary/prints-only); still need `score.py`, `build_digest.py`
4. Reuse `send_telegram.py` pattern from `../conferences_internships/` (same bot, same chat)
5. Add monthly GitHub Actions workflow
