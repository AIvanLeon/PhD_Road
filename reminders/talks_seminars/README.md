# Talks & Seminars Reminder

A weekly Telegram reminder for talks, seminars, and symposia — pulled straight from two calendar sources instead of parsing forwarded "Recruiting and Networking Opportunities" emails.

## Files

- `config.json` — Feed URL + lookahead window for the Chemistry calendar, and the saved filter (category/audience/location) for PlanIt Purple
- `fetch_events.py` — Fetches and normalizes events from both sources; run directly for a prints-only preview
- `build_message.py` — Builds `data/message.txt`, deduped against `data/seen_events.json`
- `send_telegram.py` — Sends it to `@PhDork_bot` (same bot as the other two reminders)
- `data/` — **Tracked in git** (not gitignored except `message.txt`) — this is persistent dedup state
  - `seen_events.json` — Dedupe log keyed by event id/date+title, each entry expiring ~45 days after its event date so the file doesn't grow forever
  - `message.txt` — Latest generated message (gitignored output)

## Sources

1. **Chemistry Dept. calendar** — `https://chemistry.northwestern.edu/js/events-feed.xml?start=...&end=...`, a plain XML feed the department's own calendar page fetches under the hood. No filter — every event in the lookahead window is included, per your call.
2. **PlanIt Purple** (university-wide) — `https://planitpurple.northwestern.edu/refresh_events`, the internal endpoint the calendar page POSTs to when you apply filters. Uses the same filter you already had saved as a link (`https://planitpurple.northwestern.edu/#search=/5/1+20/1/` → Academic (general) + Sciences, Evanston, Graduate Students). No login/session token required. Response is an HTML fragment, parsed with BeautifulSoup — if Northwestern ever changes the markup and parsing breaks, the message falls back to just including the saved search link instead of silently showing nothing.

## Usage

```bash
python build_message.py     # builds data/message.txt, updates data/seen_events.json
python send_telegram.py     # sends it to your Telegram bot
```

## Telegram setup

Same bot/chat as the other two reminders:
1. Copy `.env.example` to `.env`
2. Fill in `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (from @BotFather + your chat)
3. `.env` is gitignored — never commit real tokens

For GitHub Actions, store these as **repo secrets** instead (Settings → Secrets and variables → Actions), not in a committed file.

## Automation (GitHub Actions)

`.github/workflows/weekly-talks-seminars.yml` runs `build_message.py` + `send_telegram.py` automatically every Monday, then commits the updated `data/seen_events.json` back so dedup persists.

Requires these repo secrets (Settings → Secrets and variables → Actions):
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Sending on a day other than Monday

**From GitHub (no code, no laptop needed):** Repo → **Actions** tab → "Weekly Talks & Seminars Reminder" → **Run workflow** button.

**From your terminal:**
```bash
cd reminders/talks_seminars
python build_message.py
python send_telegram.py
```

## If PlanIt Purple filters change

Go to https://planitpurple.northwestern.edu/, set your filters in the UI, copy the resulting `#search=/.../.../` hash from the address bar, and update `config.json`'s `planitpurple.filters` (`category`, `audience_type`, `location_type` — same three numbers in the hash) and `saved_link`.
