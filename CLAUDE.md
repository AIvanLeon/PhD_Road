# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

**PhD_Road** is Angel Ivan Rodriguez-León's academic hub combining:
1. **Website** — Personal academic portfolio (Quarto-based static site)
2. **Skills** — APIs and tools for discovering internships, conferences, and sharing research interests (planned)

The repository is structured as a monorepo with independent components that can be deployed separately.

## Repository Structure

```
PhD_Road/
├── website/                    # Quarto-based academic website
│   ├── _quarto.yml            # Site config (navbar, title, theme)
│   ├── index.qmd              # Homepage
│   ├── about.qmd              # Bio + CV embed
│   ├── projects.qmd           # Research projects + publications
│   ├── assets/
│   │   ├── Resume_AIRL.pdf    # CV (downloadable/embeddable)
│   │   └── style.css          # Custom styling
│   ├── README.md              # Website-specific setup
│   ├── .gitignore             # Excludes _output/
│   └── _output/               # (gitignored) Built HTML
│
└── [skills/]                  # (TODO) Internship/conference discovery APIs
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

### Future: Skills & APIs

Planned component for:
- Fetching internship opportunities (APIs: job boards, company sites)
- Aggregating conference/workshop info (academic calendars, societies)
- Sharing research interests via structured data or feeds

**Suggested tech stack** (when built):
- **Language**: Python (fits with computational background) or Node.js
- **API integrations**: BeautifulSoup/Selenium for scraping; requests/axios for APIs
- **Scheduling**: APScheduler (Python) or node-cron for periodic fetches
- **Data storage**: JSON files, SQLite, or lightweight database
- **Deployment**: GitHub Actions for scheduling; static outputs for easy sharing

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
- `_output/` and `.quarto/` are gitignored — rebuild after clone
- Consider adding a `/admin` or private notes section for internship/conference tracking (not in website)


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