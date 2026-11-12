# FLC & Associates LLP: Case Law Database

A searchable database of the firm's case law notes, published with GitHub Pages.
The Google Sheet is the master copy. This repository holds the website and a
snapshot of the data, refreshed from the sheet every 6 hours.

Copyright (c) FLC & Associates LLP. All rights reserved. See `LICENSE`.

## How it fits together

```
Google Sheet ("Cases" tab, published as CSV)
        |  every 6 hours, or "Run workflow"
        v
GitHub Action: scripts/sync_sheet.py  ->  data/cases.json  ->  GitHub Pages
```

| Path | Purpose |
|---|---|
| `index.html`, `assets/` | The website (no external services; works on phones) |
| `data/cases.json` | Snapshot of the database built from the sheet |
| `scripts/sync_sheet.py` | Converts the sheet CSV into `data/cases.json` |
| `scripts/citations.py` | Reads and normalises PLD, SCMR, CLC, YLR, MLD, PCrLJ, PLJ and older report citations |
| `scripts/extract.py` | Fills blank columns (court, outcome, provisions, reliance) from the entry text |
| `.github/workflows/sync-and-deploy.yml` | Scheduled sync and publication |
| `robots.txt` + `noindex` meta tags | Keep the site out of search engines |

## One-time setup

1. **Pages**: Settings > Pages > Build and deployment > Source: **GitHub Actions**.
2. **Sheet link**: in the Google Sheet, File > Share > Publish to web > choose the
   **Cases** sheet and **Comma-separated values (.csv)** > Publish. Copy the link.
3. **Repository secret**: Settings > Secrets and variables > Actions > Secrets >
   New repository secret. Name: `SHEET_CSV_URL`. Value: the link from step 2.
   (A secret, not a variable, so the link never appears in the public Actions logs.)
4. Actions > "Sync from Google Sheet and publish" > **Run workflow**.

The site address is shown under Settings > Pages once the first run finishes.

## Updating the database

Edit the Google Sheet. The website updates at the next scheduled run, or at once
via Actions > Run workflow. See the "How to use" tab in the sheet for the column rules.

Safety checks in the sync: it stops without changing the site if the sheet link
returns a web page instead of CSV, if required columns are missing, or if fewer
than 10 usable rows are found.

## Running locally

```
python3 -m http.server 8000      # then open http://localhost:8000
python3 scripts/sync_sheet.py path/or/url/to/sheet.csv data/cases.json
```

## Hosting and access (from November 2026)

The database is served by Cloudflare Pages at https://caselawdatabase.flcassociates.com, behind one shared username and password.

- `functions/_middleware.js` checks the username and password on Cloudflare's server before any page or data file is sent. The credentials are the encrypted variables `DB_USER` and `DB_PASSWORD` in the Cloudflare Pages project; to change the password, edit `DB_PASSWORD` there and redeploy.
- Cloudflare deploys every push to `main`, including the data commits made by the "Sync from Google Sheet and publish" workflow every 6 hours.
- The repository is private and GitHub Pages is switched off, so the data cannot be read on GitHub either.
