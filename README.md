# Yellow Pages Scraper

Production-ready Python scraper for [Yellow Pages](https://www.yellowpages.com) with:

- **Undetected Chrome** (Selenium + `undetected-chromedriver`)
- **Pagination** across all listing pages (e.g. 1–3000)
- **Detail scraping** for each business (reviews, gallery, hours, more info, etc.)
- **CSV + JSON** export
- **Resume support** via `progress.json` (scraped / pending / failed tracking)
- **Professional Tkinter GUI**

## Quick Start (Windows)

```bat
setup.bat
run_gui.bat
```

## Quick Start (Ubuntu / Linux)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python gui.py
```

## Manual Setup

**Windows**

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python gui.py
```

**Ubuntu / Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python gui.py
```

> On Linux/macOS, use `source venv/bin/activate` (or `. venv/bin/activate`). Do not run `venv/bin/activate` directly.

## CLI Usage

```bash
python main.py --url "https://www.yellowpages.com/los-angeles-ca/restaurants"
python main.py --url "https://www.yellowpages.com/los-angeles-ca/restaurants" --max-pages 2 --headless
python main.py --output "output/data" --verbose
```

## Output Files

| File | Description |
|------|-------------|
| `output/data/businesses.csv` | Flattened business records (one row per business) |
| `output/data/businesses.json` | Full nested JSON (reviews, gallery, hours, etc.) |
| `output/data/progress.json` | Resume state: scraped, pending, failed URLs |
| `output/logs/scraper.log` | Runtime logs |

## Resume Behavior

If scraping stops midway (crash, stop button, close app):

1. Run again with the **same start URL**
2. The scraper reads `progress.json`
3. Already scraped URLs are **skipped**
4. Pending URLs and list pagination continue where they left off

## Project Structure

```
Yellow Pages/
├── config/settings.py       # Configuration
├── src/
│   ├── browser/             # Undetected Chrome driver
│   ├── parsers/             # Listing & detail HTML parsers
│   ├── scraper/             # Orchestrator (pagination + resume)
│   ├── storage/             # CSV, JSON, progress tracker
│   └── gui/                 # Tkinter application
├── main.py                  # CLI entry
├── gui.py                   # GUI entry
├── setup.bat                # One-click venv setup
├── run_gui.bat
└── run_cli.bat
```

## Requirements

- Python 3.10+
- Google Chrome installed
- Windows / macOS / Linux
