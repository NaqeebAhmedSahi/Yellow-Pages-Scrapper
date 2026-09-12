# Yellow Pages Scraper

Production-ready Python scraper for [Yellow Pages](https://www.yellowpages.com) with:

- **Undetected Chrome** (Selenium + `undetected-chromedriver`)
- **Pagination** across all listing pages (e.g. 1–3000)
- **Detail scraping** for each business (reviews, gallery, hours, more info, etc.)
- **CSV + JSON** export and **local gallery image storage**
- **Resume support** via `progress.json` (scraped / pending / failed tracking)
- **Full desktop GUI**: Scraper, History, Settings, Export/Import, Help
- **Presets** and persistent app settings

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
python main.py --no-download-images
```

## Output Files

| File | Description |
|------|-------------|
| `output/data/businesses.csv` | Flattened business records (one row per business) |
| `output/data/businesses.json` | Full nested JSON (reviews, gallery, hours, etc.) |
| `output/data/images/{listing_id}/` | Local gallery images (when enabled; default on) |
| `output/data/progress.json` | Resume state: scraped, pending, failed URLs |
| `output/app/settings.json` | GUI defaults and timing |
| `output/app/presets.json` | Saved scraper presets |
| `output/app/history.json` | Scrape session history |
| `output/logs/scraper.log` | Runtime logs |

Gallery JSON entries keep the remote `url` and add a relative `local_path` (e.g. `images/123/abc.jpg`) when downloads are enabled. CSV includes `gallery_local_paths`.
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
│   ├── storage/             # CSV, JSON, images, progress, app store
│   └── gui/                 # Multi-page Tkinter application
├── main.py                  # CLI entry
├── gui.py                   # GUI entry
├── setup.bat                # One-click venv setup
├── run_gui.bat
└── run_cli.bat
```

## Requirements

- Python 3.10+ (on Python 3.12+, `setuptools` is required because `distutils` was removed)
- Google Chrome installed
- Windows / macOS / Linux
