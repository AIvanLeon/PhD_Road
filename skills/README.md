# Skills: Conferences & Internships Reminder

A simple monthly Telegram reminder — not a scraper/scoring pipeline. Keeps things minimal.

## Files

- `conferences.json` — Curated list of conferences you follow (name + link only, no scraping — you check them yourself when reminded)
- `internships.json` — Job boards / career pages to check for postings matching your interests
- `config.json` — Your research keywords, used only to pull relevant snippets from internship pages
- `build_message.py` — Builds the message: conferences as a flat list, internships as a few keyword-matched snippets per site
- `data/message.txt` — Latest generated message (gitignored output)

## How it works

1. **Conferences**: no scraping at all. The message just lists name + link for every entry in `conferences.json`, so you can click through and check deadlines yourself.
2. **Internships**: fetches each page in `internships.json`, searches the text for your `config.json` keywords, and includes up to 3 short snippets per site as a hint of what's currently posted. No dates, no scoring — just "here's something that might be relevant, go look."

## Usage

```bash
python build_message.py     # builds data/message.txt
python send_telegram.py     # sends it to your Telegram bot
```

## Telegram setup

1. Copy `.env.example` to `.env`
2. Fill in `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (from @BotFather + your chat)
3. `.env` is gitignored — never commit real tokens

For GitHub Actions, store these as **repo secrets** instead (Settings → Secrets and variables → Actions), not in a committed file.

## Automation (GitHub Actions)

`.github/workflows/monthly-reminder.yml` runs `build_message.py` + `send_telegram.py` on the 1st of every month (also runnable manually from the Actions tab).

Requires these repo secrets (Settings → Secrets and variables → Actions):
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Never commit these — only the local `.env` (gitignored) or GitHub secrets should hold real values.

