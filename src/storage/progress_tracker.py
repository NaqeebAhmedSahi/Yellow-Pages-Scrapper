"""Persistent progress tracking for resume-capable scraping."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks scraped, pending, and failed URLs across sessions."""

    def __init__(self, path: Path, start_url: str) -> None:
        self.path = path
        self.start_url = start_url
        self.data: dict[str, Any] = self._default_state(start_url)
        self.load()

    @staticmethod
    def _default_state(start_url: str) -> dict[str, Any]:
        return {
            "start_url": start_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": None,
            "status": "idle",
            "current_list_page": 1,
            "total_list_pages": None,
            "total_results": None,
            "scraped_urls": [],
            "pending_urls": [],
            "failed_urls": [],
            "in_progress_url": None,
            "stats": {
                "scraped_count": 0,
                "failed_count": 0,
                "pending_count": 0,
            },
        }

    def load(self) -> None:
        if not self.path.exists():
            self.save()
            return

        with open(self.path, encoding="utf-8") as f:
            loaded = json.load(f)

        if loaded.get("start_url") == self.start_url:
            self.data = loaded
            logger.info(
                "Resumed progress: %d scraped, %d pending, %d failed",
                len(self.data.get("scraped_urls", [])),
                len(self.data.get("pending_urls", [])),
                len(self.data.get("failed_urls", [])),
            )
        else:
            logger.info("Different start URL detected; starting fresh progress file")
            self.data = self._default_state(self.start_url)
            self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.data["stats"] = {
            "scraped_count": len(self.data.get("scraped_urls", [])),
            "failed_count": len(self.data.get("failed_urls", [])),
            "pending_count": len(self.data.get("pending_urls", [])),
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def is_scraped(self, url: str) -> bool:
        return url in set(self.data.get("scraped_urls", []))

    def mark_scraped(self, url: str) -> None:
        scraped = set(self.data.setdefault("scraped_urls", []))
        scraped.add(url)
        self.data["scraped_urls"] = sorted(scraped)

        pending = [u for u in self.data.get("pending_urls", []) if u != url]
        self.data["pending_urls"] = pending

        if self.data.get("in_progress_url") == url:
            self.data["in_progress_url"] = None

        failed = [item for item in self.data.get("failed_urls", []) if item.get("url") != url]
        self.data["failed_urls"] = failed
        self.save()

    def mark_failed(self, url: str, error: str) -> None:
        failed = self.data.setdefault("failed_urls", [])
        failed = [item for item in failed if item.get("url") != url]
        failed.append(
            {
                "url": url,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.data["failed_urls"] = failed

        pending = [u for u in self.data.get("pending_urls", []) if u != url]
        self.data["pending_urls"] = pending

        if self.data.get("in_progress_url") == url:
            self.data["in_progress_url"] = None
        self.save()

    def set_pending_urls(self, urls: list[str]) -> None:
        scraped = set(self.data.get("scraped_urls", []))
        unique_pending = []
        seen: set[str] = set()
        for url in urls:
            if url not in scraped and url not in seen:
                seen.add(url)
                unique_pending.append(url)
        self.data["pending_urls"] = unique_pending
        self.save()

    def add_pending_urls(self, urls: list[str]) -> None:
        existing = set(self.data.get("pending_urls", []))
        scraped = set(self.data.get("scraped_urls", []))
        for url in urls:
            if url not in existing and url not in scraped:
                existing.add(url)
        self.data["pending_urls"] = sorted(existing)
        self.save()

    def pop_next_pending(self) -> str | None:
        pending = self.data.get("pending_urls", [])
        if not pending:
            return None
        url = pending.pop(0)
        self.data["pending_urls"] = pending
        self.data["in_progress_url"] = url
        self.save()
        return url

    def set_list_page(self, page: int) -> None:
        self.data["current_list_page"] = page
        self.save()

    def set_pagination_info(self, total_pages: int | None, total_results: int | None) -> None:
        self.data["total_list_pages"] = total_pages
        self.data["total_results"] = total_results
        self.save()

    def set_status(self, status: str) -> None:
        self.data["status"] = status
        self.save()

    def get_resume_list_page(self) -> int:
        if self.data.get("pending_urls"):
            return self.data.get("current_list_page", 1)
        return self.data.get("current_list_page", 1)
