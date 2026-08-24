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

**Preview locally** (from repo root or `website/` folder):
```bash
cd website
quarto preview
```
Opens live-reload server at `http://localhost:4200`. Changes to `.qmd` or `.css` auto-refresh.

**Build for deployment**:
```bash
quarto render
```
Generates `website/_output/` — ready for GitHub Pages or static hosting.

**Edit content**:
- `.qmd` files use Markdown + Quarto syntax (see [quarto.org/docs](https://quarto.org/docs/))
- `_quarto.yml` controls navbar, title, theme, CSS
- `assets/style.css` for custom styling (uses CSS variables for light/dark compatibility)

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
Edit `website/_quarto.yml` under `website: navbar: right:`:
```yaml
- icon: linkedin
  href: https://www.linkedin.com/in/i-leon
- icon: google
  href: https://scholar.google.com/citations?user=SCHOLAR_ID
```

### Add a Publication
Edit `website/projects.qmd`, add to Publications section:
```markdown
**"Paper Title"**
*Authors*
**Journal Name** Year, Vol(Issue), Pages
[DOI: link](url)
```

### Update CV
Replace `website/assets/Resume_AIRL.pdf` with new version. The about page auto-embeds it.

### Deploy to GitHub Pages
1. Ensure `website/_output/` is built: `cd website && quarto render`
2. Commit everything except `_output/` (see `.gitignore`)
3. Configure GitHub Pages in repo settings: source = `main`, folder = `/docs`
4. Rename `_output/` to `docs/` and push
5. Site live at `https://<username>.github.io/PhD_Road`

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