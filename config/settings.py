"""Application-wide configuration."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = OUTPUT_DIR / "data"
LOGS_DIR = OUTPUT_DIR / "logs"

DEFAULT_START_URL = "https://www.yellowpages.com/los-angeles-ca/restaurants"
BASE_URL = "https://www.yellowpages.com"

PAGE_LOAD_TIMEOUT = 30
IMPLICIT_WAIT = 5
REQUEST_DELAY_SECONDS = 1.5
SCROLL_PAUSE_SECONDS = 0.8
MAX_GALLERY_SCROLLS = 20
MAX_REVIEW_SCROLLS = 10

HEADLESS_DEFAULT = False
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

CSV_FILENAME = "businesses.csv"
JSON_FILENAME = "businesses.json"
PROGRESS_FILENAME = "progress.json"
