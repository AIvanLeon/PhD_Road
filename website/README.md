# Academic Website

Personal academic website for Angel Ivan Rodriguez-León, built with [Quarto](https://quarto.org).

## Quick Start

### Prerequisites
```bash
brew install quarto
```

### Preview Locally
```bash
quarto preview
```
Opens at `http://localhost:4200` with live reload.

### Deploy to GitHub Pages
```bash
./deploy.sh "commit message"
```
From repo root. Script handles render, copy, commit, and push.

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

## Edit Content

- `.qmd` files: Markdown + Quarto syntax ([docs](https://quarto.org/docs/))
- `_quarto.yml`: navbar, title, social links
- `assets/style.css`: colors, fonts, spacing
