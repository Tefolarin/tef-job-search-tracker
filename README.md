# TEF: a personal job search command centre

A local web app I designed and built to run my own product and strategy job search as an international MBA candidate. It answers three questions every morning: who should I follow up with, which roles are worth my time, and which companies are likely to sponsor a work visa.

I designed it, wrote the requirements, made the product decisions and tested every release; the code was written with an AI coding assistant (Claude). It runs entirely on my laptop, reads one Excel workbook as its source of truth, and makes no calls to paid AI services.

## The problem

Recruiting from abroad means juggling LinkedIn outreach, coffee chats, applications and visa questions across hundreds of companies. Spreadsheets don't tell you what to do next, job boards don't tell you who sponsors, and generic CVs don't get past screening.

## What it does

**Follow-ups.** Reads my outreach log and tells me each day who to message, thank or nudge, based on simple timing rules (request sent, accepted, message sent, chat done and so on).

**Sponsorship evidence.** Analyses about 495,000 certified H-1B filings from the US Department of Labor (July 2025 to June 2026) to rank employers by how often they sponsor the kinds of roles I target. The filings are treated as evidence of intent, never as a promise: a person's answer always outranks a number.

**Job watcher.** Checks more than 100 employers' careers sites on Greenhouse, Lever, Ashby and Workday, plus Amazon and Google, for product, strategy and MBA leadership programme roles. It reads each description and removes roles that state they won't sponsor a visa (while respecting each site's robots.txt).

**Matching.** Scores every role against my CVs two ways: a keyword match (what screening software looks for) and a meaning match using a small local embedding model (bge-base), so "drive alignment across teams" counts as a match for "aligned bank partners across five markets". It lists the stated requirements my bullets cover least.

**Tailored CVs.** Builds a one-page Word CV for any role from a bank of pre-written, fact-checked bullets, choosing the version written for that role type, covering the job's stated requirements first, and using a local re-ranker (bge-reranker) to pick the strongest bullets. It never rewrites a sentence, so every line stays true.

**Applications.** Tracks status, the CV used and match level, and asks "did you apply?" when I come back from a posting.

## How it's built

- Python and Flask, served locally; one Excel workbook (openpyxl) as the database, with backups and lock-safe writes
- fastembed (ONNX) for local embeddings and re-ranking; models download once and stay on the machine
- python-docx for CV generation; pypdf for reading CVs
- Plain HTML and CSS, with dark mode

| File | What it does |
|---|---|
| `app.py` | The site: pages, forms and the follow-up rules |
| `templates_html.py` | Page templates and styling |
| `jobwatch.py` | The job watcher and description analysis |
| `cvmatch.py`, `jdtext.py` | Keyword matching and job description parsing |
| `meaning.py` | Local meaning matching and re-ranking |
| `cvbuild.py`, `cvlib.py`, `rewrites.py` | CV generation from the bullet bank |
| `h1b.py`, `h1b_names.json` | H-1B filing analysis and employer grouping |
| `digest.py` | Optional daily email summary |
| `clicks.py` | The "did you apply?" prompts |
| `make_tracker.py` | Builds an empty tracker workbook from a company list |
| `start.bat` | Installs what's needed and starts the site on Windows |

## Running it

Windows with Python 3.12 to 3.14. Double-click `start.bat`. It installs the packages and opens the site at http://127.0.0.1:5000.

Your own data isn't part of this repository: you need a `tracker.xlsx` (Companies, People and Applications sheets; `make_tracker.py` builds one from a company list), your CVs in a `CV` folder, and, for the sponsorship analysis, the Department of Labor's LCA disclosure files.

## Privacy

Personal data stays out of this repository: the tracker, CVs, outreach notes, saved job descriptions and email settings are all excluded (see `.gitignore`). The email password, if used, is kept in Windows Credential Manager.

## Licence

Fonts: Manrope, under the SIL Open Font License (see `static/fonts`).
