"""Main scraping orchestrator with pagination and resume support."""

from __future__ import annotations

import logging
import re
import threading
import time
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from config.settings import (
    DATA_DIR,
    MAX_GALLERY_SCROLLS,
    MAX_REVIEW_SCROLLS,
    REQUEST_DELAY_SECONDS,
)
from src.browser.driver_factory import BrowserManager
from src.models.business import BusinessListing
from src.parsers.detail_parser import DetailPageParser
from src.parsers.listing_parser import ListingPageParser
from src.storage.csv_writer import CSVStorage
from src.storage.image_downloader import download_gallery_images
from src.storage.json_writer import JSONStorage
from src.storage.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

StatusCallback = Callable[[str], None]
ProgressCallback = Callable[[dict], None]


class ScraperOrchestrator:
    """Coordinates listing discovery, detail scraping, and persistence."""

    def __init__(
        self,
        start_url: str,
        output_dir: Path | None = None,
        headless: bool = False,
        max_pages: int | None = None,
        download_images: bool = True,
        on_status: StatusCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        self.start_url = self._normalize_url(start_url)
        self.output_dir = output_dir or DATA_DIR
        self.headless = headless
        self.max_pages = max_pages
        self.download_images = download_images
        self.on_status = on_status or (lambda msg: None)
        self.on_progress = on_progress or (lambda data: None)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.csv_storage = CSVStorage(self.output_dir / "businesses.csv")
        self.json_storage = JSONStorage(self.output_dir / "businesses.json")
        self.progress = ProgressTracker(self.output_dir / "progress.json", self.start_url)

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()

        self.listing_cache: dict[str, BusinessListing] = {}

    @staticmethod
    def _normalize_url(url: str) -> str:
        url = url.strip()
        if not url.startswith("http"):
            url = f"https://www.yellowpages.com/{url.lstrip('/')}"
        return url

    @staticmethod
    def _page_url(base_url: str, page: int) -> str:
        if page <= 1:
            parsed = urlparse(base_url)
            query = parse_qs(parsed.query)
            query.pop("page", None)
            new_query = urlencode({k: v[0] for k, v in query.items()})
            return urlunparse(parsed._replace(query=new_query))

        parsed = urlparse(base_url)
        query = parse_qs(parsed.query)
        query["page"] = [str(page)]
        new_query = urlencode({k: v[0] for k, v in query.items()})
        return urlunparse(parsed._replace(query=new_query))

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.set()
        self.on_status("Stop requested...")

    def pause(self) -> None:
        self._pause_event.clear()
        self.on_status("Paused")

    def resume(self) -> None:
        self._pause_event.set()
        self.on_status("Resumed")

    def _wait_if_paused(self) -> bool:
        while not self._pause_event.is_set():
            if self._stop_event.is_set():
                return False
            time.sleep(0.2)
        return not self._stop_event.is_set()

    def run(self) -> None:
        self._stop_event.clear()
        self.progress.set_status("running")
        self.on_status("Starting scraper...")

        with BrowserManager(headless=self.headless) as browser:
            if not self._process_pending_details(browser):
                return

            start_page = self.progress.get_resume_list_page()
            current_page = start_page

            while not self._stop_event.is_set():
                if not self._wait_if_paused():
                    break

                page_url = self._page_url(self.start_url, current_page)
                self.on_status(f"Loading listing page {current_page}: {page_url}")
                html = browser.safe_get(page_url)
                if not html:
                    self.on_status(f"Failed to load page {current_page}")
                    break

                parser = ListingPageParser(html, page_number=current_page)
                pagination = parser.parse_pagination()
                self.progress.set_pagination_info(
                    pagination.get("total_pages"),
                    pagination.get("total_results"),
                )
                self.progress.set_list_page(current_page)

                listings = parser.parse_listings()
                for listing in listings:
                    self.listing_cache[listing.url] = listing

                urls = parser.parse_detail_urls()
                new_urls = [u for u in urls if not self.progress.is_scraped(u)]
                self.progress.add_pending_urls(new_urls)

                self._emit_progress(
                    current_page=current_page,
                    total_pages=pagination.get("total_pages"),
                    message=f"Found {len(urls)} listings on page {current_page}",
                )

                if not self._process_pending_details(browser):
                    break

                total_pages = pagination.get("total_pages", current_page)
                if self.max_pages and current_page >= self.max_pages:
                    self.on_status(f"Reached max pages limit ({self.max_pages})")
                    break

                if current_page >= total_pages:
                    self.on_status("All listing pages processed")
                    break

                current_page += 1
                time.sleep(REQUEST_DELAY_SECONDS)

        if self._stop_event.is_set():
            self.progress.set_status("stopped")
            self.on_status("Scraper stopped")
        elif self.progress.data.get("pending_urls"):
            self.progress.set_status("paused")
            self.on_status("Scraper paused with pending items")
        else:
            self.progress.set_status("completed")
            self.on_status("Scraping completed successfully")

        self._emit_progress(message="Finished")

    def _process_pending_details(self, browser: BrowserManager) -> bool:
        while self.progress.data.get("pending_urls") and not self._stop_event.is_set():
            if not self._wait_if_paused():
                return False

            url = self.progress.pop_next_pending()
            if not url:
                break

            if self.progress.is_scraped(url):
                continue

            listing = self.listing_cache.get(url)
            self.on_status(f"Scraping detail: {listing.name if listing else url}")

            detail = self._scrape_detail(browser, url, listing)
            if detail:
                if self.download_images and detail.gallery_images:
                    listing_key = detail.listing_id or re.sub(r"[^\w.\-]+", "_", detail.name) or "unknown"
                    self.on_status(
                        f"Downloading {len(detail.gallery_images)} gallery image(s): {detail.name}"
                    )
                    download_gallery_images(
                        detail.gallery_images,
                        self.output_dir,
                        listing_key,
                        driver=browser.driver,
                        referer=url,
                    )
                self.csv_storage.append(detail)
                self.json_storage.append(detail)
                self.progress.mark_scraped(url)
                self._emit_progress(
                    scraped=True,
                    current_url=url,
                    business_name=detail.name,
                    message=f"Saved: {detail.name}",
                )
            else:
                self.progress.mark_failed(url, "Failed to load or parse detail page")
                self._emit_progress(failed=True, current_url=url, message=f"Failed: {url}")

            time.sleep(REQUEST_DELAY_SECONDS)

        return not self._stop_event.is_set()

    def _scrape_detail(
        self,
        browser: BrowserManager,
        url: str,
        listing: BusinessListing | None,
    ):
        html = browser.safe_get(url)
        if not html:
            return None

        browser.scroll_to_bottom()
        browser.scroll_element_into_view("#gallery")
        browser.scroll_carousel("#gallery .collage .next:not(.disabled)", MAX_GALLERY_SCROLLS)
        browser.scroll_element_into_view("#reviews")
        browser.scroll_to_bottom()

        html = browser.driver.page_source if browser.driver else html
        parser = DetailPageParser(html, url, listing)
        return parser.parse()

    def _emit_progress(self, **kwargs) -> None:
        payload = {
            "scraped_count": len(self.progress.data.get("scraped_urls", [])),
            "pending_count": len(self.progress.data.get("pending_urls", [])),
            "failed_count": len(self.progress.data.get("failed_urls", [])),
            "current_list_page": self.progress.data.get("current_list_page", 1),
            "total_list_pages": self.progress.data.get("total_list_pages"),
            "total_results": self.progress.data.get("total_results"),
            "status": self.progress.data.get("status", "idle"),
        }
        payload.update(kwargs)
        self.on_progress(payload)
