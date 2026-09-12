"""Application-wide configuration."""

from __future__ import annotations

import sys
from pathlib import Path


def _app_base_dir() -> Path:
    """Project root in source mode; folder containing the EXE when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _app_base_dir()
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = OUTPUT_DIR / "data"
LOGS_DIR = OUTPUT_DIR / "logs"
APP_CONFIG_DIR = OUTPUT_DIR / "app"
SETTINGS_FILE = APP_CONFIG_DIR / "settings.json"
PRESETS_FILE = APP_CONFIG_DIR / "presets.json"
HISTORY_FILE = APP_CONFIG_DIR / "history.json"

DEFAULT_START_URL = "https://www.yellowpages.com/los-angeles-ca/restaurants"
BASE_URL = "https://www.yellowpages.com"

PAGE_LOAD_TIMEOUT = 30
IMPLICIT_WAIT = 5
REQUEST_DELAY_SECONDS = 1.5
SCROLL_PAUSE_SECONDS = 0.8
MAX_GALLERY_SCROLLS = 20
MAX_REVIEW_SCROLLS = 10

HEADLESS_DEFAULT = False
DOWNLOAD_IMAGES_DEFAULT = True
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

CSV_FILENAME = "businesses.csv"
JSON_FILENAME = "businesses.json"
PROGRESS_FILENAME = "progress.json"
APP_VERSION = "1.0.0"
