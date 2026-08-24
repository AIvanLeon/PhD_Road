# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

**PhD_Road** is Angel Ivan Rodriguez-León's academic hub combining:
1. **Website** — Personal academic portfolio (Quarto-based static site), live at **https://aivanleon.github.io/PhD_Road**
2. **Skills** — Monthly Telegram reminder for conferences and internships (`skills/`)

The repository is structured as a monorepo with independent components that can be deployed separately.

## Repository Structure

```
PhD_Road/
├── website/                    # Quarto-based academic website
│   ├── _quarto.yml            # Site config (navbar, title, theme)
│   ├── index.qmd              # Homepage
│   ├── about.qmd              # Bio + CV embed
│   ├── projects.qmd           # Research projects + publications
│   ├── assets/                # CV, photos, figures, style.css
│   └── README.md              # Website-specific setup
├── docs/                       # Built site (GitHub Pages source — root /docs)
├── deploy.sh                   # Render + copy to docs/ + commit + push
│
├── skills/                     # Conferences & internships Telegram reminder
│   ├── conferences.json       # Name + link list (no scraping)
│   ├── internships.json       # Job boards to check for keyword matches
│   ├── config.json            # Research keywords
│   ├── build_message.py       # Builds the monthly message
│   ├── send_telegram.py       # Sends it via @PhDork_bot
│   └── .env                   # (gitignored) bot token + chat id
│
└── .github/workflows/
    └── monthly-reminder.yml    # Cron: runs build+send on the 1st of each month
```

## Development

### Website (Quarto)

**Install Quarto** (one-time setup):
```bash
brew install quarto
```

**Preview locally**:
```bash
cd website && quarto preview
```
Opens at `http://localhost:4200` with live reload.

**Deploy to GitHub Pages**:
```bash
./deploy.sh "commit message"
```
This renders, copies to root `docs/`, commits, and pushes in one command.

**Edit content**:
- `.qmd` files: Markdown + Quarto syntax ([quarto.org/docs](https://quarto.org/docs/))
- `_quarto.yml`: navbar, title, theme, social links
- `assets/style.css`: custom styling (CSS variables for light/dark mode)

### Skills (Conferences & Internships Reminder)

```bash
cd skills
python build_message.py     # builds data/message.txt
python send_telegram.py     # sends it to @PhDork_bot
```

Runs automatically monthly via `.github/workflows/monthly-reminder.yml`, or trigger manually from the repo's **Actions** tab ("Run workflow"). Requires `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as GitHub repo secrets (Settings → Secrets and variables → Actions) for the Action to run, or a local `skills/.env` for manual runs. See `skills/README.md`.

Design is deliberately minimal: conferences are just a static name+link list (no scraping/scoring); internships are scraped for keyword snippets only (no dates, no accessibility checks) — kept simple after testing showed date-scraping was unreliable/noisy.

## Key Files & What They Do

| File | Purpose |
|------|---------|
| `website/_quarto.yml` | Navigation, title, color theme, social links |
| `website/index.qmd` | Homepage with research summary and quick links |
| `website/about.qmd` | Bio, education, experience, awards; CV embedded |
| `website/projects.qmd` | Active research, publications, skills breakdown |
| `website/assets/style.css` | Color palette, typography, responsive layout |
| `website/assets/Resume_AIRL.pdf` | CV (referenced, not generated) |

## Common Tasks

### Update Social Links
Edit `website/_quarto.yml` navbar section:
```yaml
- icon: linkedin
  href: https://www.linkedin.com/in/i-leon
```

### Add a Publication
Edit `website/projects.qmd` Publications section:
```markdown
**"Paper Title"**
Authors
**Journal** Year, Vol, Pages
[DOI](url)
```

### Update CV
Replace `website/assets/Resume_AIRL.pdf` with new version. Auto-embedded in about page.

### Deploy Changes
```bash
./deploy.sh "Added new publication"
```
That's it. Script handles render, copy, commit, and push.

## Style & Tone

- **Website**: Professional, academic; highlights ML/materials science focus
- **Code**: Minimal comments; self-documenting names; focus on computational clarity
- **Future skills component**: Practical, modular; prioritize robustness over feature creep



- The website uses Quarto's `cosmo` theme with custom CSS overrides (dark/light aware)
- CV is embedded via `{{< pdf assets/Resume_AIRL.pdf >}}` — ensure PDF exists
- Social links in navbar are SVG icons from Quarto's built-in set; add custom icons in `style.css` if needed
- GitHub Pages serves from root `/docs` (not `website/_output/`) — `deploy.sh` handles building and copying there
- `.quarto/` is gitignored — rebuild after clone


## Response style
- Be concise. Answer directly, no preamble or summary of what you just did.
- Don't explain code back to me unless I ask.
- No "Great question!" or similar filler.
- When editing files, just make the edit — don't paste the full file back.
- If something is ambiguous, ask one short question instead of guessing.


## Git workflow
- One logical change per commit; don't bundle unrelated edits.
- Never `git push --force` to main.
- Ask before pushing; don't push automatically after committing.