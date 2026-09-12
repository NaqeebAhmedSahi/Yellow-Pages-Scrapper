"""Parser for Yellow Pages search results (listing) pages."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config.settings import BASE_URL
from src.models.business import BusinessListing


class ListingPageParser:
    """Extract listing links and summary data from SRP HTML."""

    def __init__(self, html: str, page_number: int = 1) -> None:
        self.soup = BeautifulSoup(html, "lxml")
        self.page_number = page_number

    def parse_pagination(self) -> dict:
        pagination = self.soup.select_one(".pagination")
        info = {"current_page": self.page_number, "total_results": 0, "total_pages": 1}

        showing = self.soup.select_one(".pagination .showing-count")
        if showing:
            match = re.search(r"of\s+([\d,]+)", showing.get_text(strip=True))
            if match:
                info["total_results"] = int(match.group(1).replace(",", ""))

        if pagination:
            page_links = pagination.select("a[data-page]")
            pages = []
            for link in page_links:
                page_attr = link.get("data-page")
                if page_attr and page_attr.isdigit():
                    pages.append(int(page_attr))
            if pages:
                info["total_pages"] = max(pages)
            elif info["total_results"]:
                info["total_pages"] = max(1, (info["total_results"] + 29) // 30)

        return info

    def parse_listings(self) -> list[BusinessListing]:
        listings: list[BusinessListing] = []
        for result in self.soup.select(".search-results.organic .result"):
            listing = self._parse_single_result(result)
            if listing and listing.url:
                listings.append(listing)
        return listings

    def parse_detail_urls(self) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        for link in self.soup.select(".search-results.organic a.business-name"):
            href = link.get("href", "").strip()
            if not href:
                continue
            full_url = urljoin(BASE_URL, href.split("#")[0])
            if full_url not in seen:
                seen.add(full_url)
                urls.append(full_url)
        return urls

    def _parse_single_result(self, result) -> BusinessListing | None:
        listing_id = result.get("data-ypid") or result.get("id", "").replace("lid-", "")
        name_el = result.select_one("a.business-name span") or result.select_one("a.business-name")
        name = name_el.get_text(strip=True) if name_el else ""

        link_el = result.select_one("a.business-name")
        url = urljoin(BASE_URL, link_el["href"].split("#")[0]) if link_el and link_el.get("href") else ""

        categories = [a.get_text(strip=True) for a in result.select(".categories a")]

        yp_rating_el = result.select_one(".rating .result-rating")
        yp_rating = self._rating_from_class(yp_rating_el.get("class", []) if yp_rating_el else [])
        yp_count_el = result.select_one(".rating .count")
        yp_review_count = self._extract_count(yp_count_el.get_text() if yp_count_el else "")

        ta_rating_el = result.select_one(".ta-rating")
        ta_rating = self._ta_rating_from_class(ta_rating_el.get("class", []) if ta_rating_el else [])
        ta_count_el = result.select_one(".ta-count")
        ta_review_count = self._extract_count(ta_count_el.get_text() if ta_count_el else "")

        website_el = result.select_one("a.track-visit-website")
        website = website_el.get("href", "").strip() if website_el else ""

        phone_el = result.select_one(".phones.phone.primary")
        phone = phone_el.get_text(strip=True) if phone_el else ""

        street = result.select_one(".street-address")
        locality = result.select_one(".locality")
        street_text = street.get_text(strip=True) if street else ""
        locality_text = locality.get_text(strip=True) if locality else ""
        full_address = ", ".join(part for part in [street_text, locality_text] if part)

        open_status_el = result.select_one(".open-status")
        open_status = open_status_el.get_text(strip=True) if open_status_el else ""

        years_el = result.select_one(".years-in-business .count strong")
        years_in_business = years_el.get_text(strip=True) if years_el else ""

        amenities = [
            span.get_text(strip=True)
            for span in result.select(".amenities-info span")
            if span.get_text(strip=True)
        ]

        snippet_el = result.select_one(".snippet p.body")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        return BusinessListing(
            listing_id=listing_id,
            name=name,
            url=url,
            categories=categories,
            phone=phone,
            street_address=street_text,
            locality=locality_text,
            full_address=full_address,
            website=website,
            yp_rating=yp_rating,
            yp_review_count=yp_review_count,
            ta_rating=ta_rating,
            ta_review_count=ta_review_count,
            open_status=open_status,
            years_in_business=years_in_business,
            amenities=amenities,
            snippet=snippet,
            source_page=self.page_number,
        )

    @staticmethod
    def _rating_from_class(classes: list) -> str:
        class_str = " ".join(classes)
        if "five" in class_str and "half" not in class_str:
            return "5"
        if "four" in class_str and "half" in class_str:
            return "4.5"
        if "four" in class_str:
            return "4"
        if "three" in class_str and "half" in class_str:
            return "3.5"
        if "three" in class_str:
            return "3"
        if "two" in class_str:
            return "2"
        if "one" in class_str:
            return "1"
        return ""

    @staticmethod
    def _ta_rating_from_class(classes: list) -> str:
        for cls in classes:
            if cls.startswith("ta-"):
                return cls.replace("ta-", "").replace("-", ".")
        return ""

    @staticmethod
    def _extract_count(text: str) -> str:
        match = re.search(r"\((\d+)\)", text)
        return match.group(1) if match else text.strip("()")
