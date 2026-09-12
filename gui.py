"""GUI entry point for Yellow Pages scraper."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import LOGS_DIR
from src.gui.app import YellowPagesGUI


def setup_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(LOGS_DIR / "gui.log", encoding="utf-8"),
        ],
    )


def main() -> None:
    setup_logging()
    app = YellowPagesGUI()
    app.run()


if __name__ == "__main__":
    main()
