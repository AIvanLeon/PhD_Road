# Academic Website

Personal academic website for Angel Ivan Rodriguez-León, built with [Quarto](https://quarto.org).

## Quick Start

### Prerequisites
```bash
# Install Quarto (macOS via Homebrew)
brew install quarto

# Verify installation
quarto --version
```

### Preview Locally
```bash
cd website/
quarto preview
```
The site will open in your browser with live reload on file changes.

### Build for Deployment
```bash
quarto render
```
Outputs to `_output/` — ready for GitHub Pages or other hosting.

## File Structure

```
website/
├── _quarto.yml           # Site configuration
├── index.qmd             # Homepage
├── about.qmd             # About + CV
├── projects.qmd          # Research projects
├── assets/
│   ├── Resume_AIRL.pdf   # Your CV (embedded on about page)
│   ├── style.css         # Custom styling
│   └── [photos, etc]
├── README.md             # This file
└── .gitignore            # Excludes build output
```

## Pages

- **Home** (`index.qmd`) — Intro, research focus, quick links
- **About** (`about.qmd`) — Background, education, experience, awards; CV embedded
- **Research** (`projects.qmd`) — Active projects, publications, technical skills

## Customization

**Update Social Links:**
Edit `_quarto.yml` navbar section:
- LinkedIn: ✓ www.linkedin.com/in/i-leon
- ORCID: ✓ https://orcid.org/0009-0001-0630-9370
- Google Scholar: Add your full Scholar ID
- GitHub: Add your GitHub URL

**Styling:**
Modify `assets/style.css` for colors, fonts, spacing.

**Content:**
Edit `.qmd` files using Markdown + HTML. Quarto docs: https://quarto.org

## Deployment

### GitHub Pages (Recommended)
1. Push this repo to GitHub
2. Enable GitHub Pages in repo settings → branch: `main`, folder: `/docs`
3. Move `_output` contents to `docs/` folder
4. Push again

### Netlify / Vercel / Other
1. Run `quarto render` locally
2. Push `_output/` to your hosting service

## Notes

- CV PDF is referenced in `about.qmd` — ensure `Resume_AIRL.pdf` is in `assets/`
- `.gitignore` excludes `_output/` to avoid committing build artifacts
- Quarto syntax: [Documentation](https://quarto.org/docs/)
