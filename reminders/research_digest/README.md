# Research Digest: Monthly Research Paper Digest

A monthly Telegram digest of new papers relevant to your research — matched against your own published work and tracked researchers, via the free Semantic Scholar API. No embeddings, no Claude API calls — keyword/recommendation matching only.

## Files

- `authors.json` — Researchers you follow (Semantic Scholar author IDs, resolved once by hand to avoid name collisions)
- `research_profile.json` — Anchor papers (with DOI where possible) from your own work, used to seed "similar to your work"
- `config.json` — Keywords, arXiv categories, `output.max_papers_per_digest`, and `field_watch` (keywords + count for the field-watch section)
- `fetch_papers.py` — Semantic Scholar fetch helpers (recommendations, author papers, keyword search); run directly for a prints-only preview
- `build_digest.py` — builds `data/message.txt` from the three sections below
- `send_telegram.py` — sends it to `@PhDork_bot`
- `data/` — **Tracked in git** (not gitignored — this is persistent state, not throwaway output)
  - `seen_papers.json` — Dedupe log (DOI/arXiv/S2 paper id) plus `last_run` timestamp, so nothing repeats across months. The GitHub Actions workflow commits it back after each run.
  - `digest_YYYY-MM.json` — Archive of what was sent each month
  - `message.txt` — Latest generated message (gitignored output)

## How it works

The message has three sections, each capped so it stays short:

1. **🔬 Similar to your work** — S2 Recommendations, seeded by every anchor in `research_profile.json` that has a DOI (or resolves to an S2 paper by title). Top 5.
2. **👤 New from authors you follow** — new papers since the last run from everyone in `authors.json`, ranked by keyword overlap with `config.json` then recency. Up to 3 shown; authors with new papers that didn't make the cut are named in a one-line pointer instead of dropped.
3. **🧭 Field watch** — for each keyword in `config.json`'s `field_watch.keywords`, the first `papers_per_keyword` not-yet-seen matches from a plain S2 search. General field awareness, independent of your own papers/authors.

Everything considered (shown or not) is recorded in `data/seen_papers.json` so it never resurfaces.

## Usage

```bash
python build_digest.py     # builds data/message.txt (and updates data/seen_papers.json + the monthly archive)
python send_telegram.py    # sends it to your Telegram bot
```

## Telegram setup

Same bot/chat as `../conferences_internships/`:
1. Copy `.env.example` to `.env`
2. Fill in `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (from @BotFather + your chat)
3. Optionally fill in `S2_API_KEY` (free, from [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api#api-key-form)) — moves requests off the shared unauthenticated rate limit, which is easy to hit during local testing
4. `.env` is gitignored — never commit real tokens

For GitHub Actions, store these as **repo secrets** instead (Settings → Secrets and variables → Actions), not in a committed file.

## Automation (GitHub Actions)

`.github/workflows/monthly-digest.yml` runs `build_digest.py` + `send_telegram.py` automatically on the 1st of every month (30 min after the conferences/internships reminder), then commits the updated `data/` state back to the repo so dedup persists across runs.

Requires these repo secrets (Settings → Secrets and variables → Actions):
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `S2_API_KEY` (optional, but recommended)

## Sending on a day other than the 1st

**From GitHub (no code, no laptop needed):** Repo → **Actions** tab → "Monthly Research Digest" → **Run workflow** button.

**From your terminal:**
```bash
cd reminders/research_digest
python build_digest.py
python send_telegram.py
```

## Remaining TODO

- Fill in `semantic_scholar_id` for the few `authors.json` entries still blank (ambiguous name-search results — see `fetch_papers.py` prints)
- Fill in `abstract` for any `research_profile.json` anchors missing one
