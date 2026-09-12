"""JSON export for scraped business records."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.models.business import BusinessDetail

logger = logging.getLogger(__name__)


class JSONStorage:
    """Maintains a JSON array of all scraped business records."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records: list[dict] = self._load_existing()

    def _load_existing(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def append(self, detail: BusinessDetail) -> None:
        record = detail.to_dict()
        existing_urls = {r.get("url") for r in self.records}
        if detail.url in existing_urls:
            self.records = [r for r in self.records if r.get("url") != detail.url]
        self.records.append(record)
        self._save()
        logger.debug("Appended JSON record: %s", detail.name)

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=2, ensure_ascii=False)
