"""GUI entry point for Yellow Pages scraper."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def _prepare_sys_path() -> None:
    if getattr(sys, "frozen", False):
        return
    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_prepare_sys_path()

from config.settings import LOGS_DIR  # noqa: E402
from src.gui.app import YellowPagesGUI  # noqa: E402


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
