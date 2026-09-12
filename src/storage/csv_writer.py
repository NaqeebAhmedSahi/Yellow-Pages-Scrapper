"""CSV export for scraped business records."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from src.models.business import BusinessDetail

logger = logging.getLogger(__name__)


class CSVStorage:
    """Append-only CSV writer with automatic header creation."""

    FLAT_FIELDS = [
        "listing_id",
        "name",
        "url",
        "phone",
        "extra_phones",
        "website",
        "street_address",
        "locality",
        "full_address",
        "latitude",
        "longitude",
        "directions_url",
        "categories",
        "yp_rating",
        "yp_review_count",
        "ta_rating",
        "ta_review_count",
        "open_status",
        "today_hours",
        "tomorrow_hours",
        "regular_hours",
        "years_in_business",
        "amenities",
        "gallery_count",
        "gallery_images",
        "gallery_local_paths",
        "reviews_yp",
        "reviews_ta",
        "places_near",
        "similar_businesses",
        "payment_methods",
        "neighborhoods",
        "aka",
        "other_links",
        "other_information",
        "snippet",
        "source_page",
        "scraped_at",
    ]

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_header()

    def _ensure_header(self) -> None:
        if not self.path.exists() or self.path.stat().st_size == 0:
            with open(self.path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=self.FLAT_FIELDS)
                writer.writeheader()

    def append(self, detail: BusinessDetail) -> None:
        row = detail.to_flat_dict()
        filtered = {key: row.get(key, "") for key in self.FLAT_FIELDS}
        with open(self.path, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=self.FLAT_FIELDS)
            writer.writerow(filtered)
        logger.debug("Appended CSV row: %s", detail.name)
