"""Data models for scraped business records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class BusinessListing:
    """Summary data from search results page."""

    listing_id: str = ""
    name: str = ""
    url: str = ""
    categories: list[str] = field(default_factory=list)
    phone: str = ""
    street_address: str = ""
    locality: str = ""
    full_address: str = ""
    website: str = ""
    yp_rating: str = ""
    yp_review_count: str = ""
    ta_rating: str = ""
    ta_review_count: str = ""
    open_status: str = ""
    years_in_business: str = ""
    amenities: list[str] = field(default_factory=list)
    snippet: str = ""
    source_page: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BusinessDetail:
    """Full detail page data merged with listing summary."""

    listing_id: str = ""
    name: str = ""
    url: str = ""
    phone: str = ""
    extra_phones: list[str] = field(default_factory=list)
    website: str = ""
    street_address: str = ""
    locality: str = ""
    full_address: str = ""
    latitude: str = ""
    longitude: str = ""
    directions_url: str = ""
    categories: list[str] = field(default_factory=list)
    yp_rating: str = ""
    yp_review_count: str = ""
    ta_rating: str = ""
    ta_review_count: str = ""
    open_status: str = ""
    today_hours: str = ""
    tomorrow_hours: str = ""
    regular_hours: dict[str, str] = field(default_factory=dict)
    years_in_business: str = ""
    amenities: list[str] = field(default_factory=list)
    gallery_images: list[dict[str, str]] = field(default_factory=list)
    gallery_count: int = 0
    reviews_yp: list[dict[str, Any]] = field(default_factory=list)
    reviews_ta: list[dict[str, Any]] = field(default_factory=list)
    places_near: list[dict[str, str]] = field(default_factory=list)
    similar_businesses: list[dict[str, str]] = field(default_factory=list)
    payment_methods: str = ""
    neighborhoods: list[str] = field(default_factory=list)
    aka: list[str] = field(default_factory=list)
    other_links: list[str] = field(default_factory=list)
    other_information: dict[str, str] = field(default_factory=dict)
    snippet: str = ""
    source_page: int = 0
    scraped_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_flat_dict(self) -> dict[str, Any]:
        """Flatten nested structures for CSV export."""
        data = self.to_dict()
        data["categories"] = " | ".join(self.categories)
        data["amenities"] = " | ".join(self.amenities)
        data["extra_phones"] = " | ".join(self.extra_phones)
        data["neighborhoods"] = " | ".join(self.neighborhoods)
        data["aka"] = " | ".join(self.aka)
        data["other_links"] = " | ".join(self.other_links)
        data["regular_hours"] = "; ".join(
            f"{day}: {hours}" for day, hours in self.regular_hours.items()
        )
        data["other_information"] = "; ".join(
            f"{key}: {value}" for key, value in self.other_information.items()
        )
        data["gallery_images"] = " | ".join(
            img.get("url", "") for img in self.gallery_images if img.get("url")
        )
        data["places_near"] = " | ".join(
            f"{p.get('name', '')} ({p.get('url', '')})" for p in self.places_near
        )
        data["similar_businesses"] = " | ".join(
            b.get("name", "") for b in self.similar_businesses
        )
        data["reviews_yp"] = str(len(self.reviews_yp))
        data["reviews_ta"] = str(len(self.reviews_ta))
        return data
