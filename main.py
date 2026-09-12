"""CLI entry point for Yellow Pages scraper."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import DATA_DIR, DEFAULT_START_URL, LOGS_DIR
from src.scraper.orchestrator import ScraperOrchestrator


def setup_logging(verbose: bool = False) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOGS_DIR / "scraper.log", encoding="utf-8"),
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Yellow Pages Scraper")
    parser.add_argument("--url", default=DEFAULT_START_URL, help="Category/search URL to scrape")
    parser.add_argument("--output", default=str(DATA_DIR), help="Output directory")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument("--max-pages", type=int, default=0, help="Max listing pages (0 = all)")
    parser.add_argument(
        "--no-download-images",
        action="store_true",
        help="Do not save gallery images to local disk",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    setup_logging(args.verbose)
    max_pages = args.max_pages if args.max_pages > 0 else None

    def on_status(msg: str) -> None:
        print(msg)

    def on_progress(data: dict) -> None:
        if data.get("message"):
            print(f"  -> {data['message']}")

    orchestrator = ScraperOrchestrator(
        start_url=args.url,
        output_dir=Path(args.output),
        headless=args.headless,
        max_pages=max_pages,
        download_images=not args.no_download_images,
        on_status=on_status,
        on_progress=on_progress,
    )
    orchestrator.run()


if __name__ == "__main__":
    main()
