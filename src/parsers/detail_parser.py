"""Parser for Yellow Pages business detail (MIP) pages."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config.settings import BASE_URL
from src.models.business import BusinessDetail, BusinessListing


class DetailPageParser:
    """Extract full business details from MIP HTML."""

    def __init__(self, html: str, url: str, listing: BusinessListing | None = None) -> None:
        self.soup = BeautifulSoup(html, "lxml")
        self.url = url
        self.listing = listing

    def parse(self) -> BusinessDetail:
        detail = BusinessDetail(
            url=self.url,
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )

        if self.listing:
            self._merge_listing(detail, self.listing)

        self._parse_header(detail)
        self._parse_ctas(detail)
        self._parse_gallery(detail)
        self._parse_hours(detail)
        self._parse_reviews(detail)
        self._parse_places_near(detail)
        self._parse_details_card(detail)
        self._parse_more_info(detail)
        self._parse_similar(detail)
        self._parse_coordinates(detail)

        return detail

    def _merge_listing(self, detail: BusinessDetail, listing: BusinessListing) -> None:
        detail.listing_id = listing.listing_id
        detail.name = listing.name or detail.name
        detail.phone = listing.phone or detail.phone
        detail.website = listing.website or detail.website
        detail.street_address = listing.street_address or detail.street_address
        detail.locality = listing.locality or detail.locality
        detail.full_address = listing.full_address or detail.full_address
        detail.categories = listing.categories or detail.categories
        detail.yp_rating = listing.yp_rating or detail.yp_rating
        detail.yp_review_count = listing.yp_review_count or detail.yp_review_count
        detail.ta_rating = listing.ta_rating or detail.ta_rating
        detail.ta_review_count = listing.ta_review_count or detail.ta_review_count
        detail.open_status = listing.open_status or detail.open_status
        detail.years_in_business = listing.years_in_business or detail.years_in_business
        detail.amenities = listing.amenities or detail.amenities
        detail.snippet = listing.snippet or detail.snippet
        detail.source_page = listing.source_page

    def _parse_header(self, detail: BusinessDetail) -> None:
        card = self.soup.select_one("#listing-card")
        if not card:
            return

        name_el = card.select_one("h1.business-name")
        if name_el:
            detail.name = name_el.get_text(strip=True)

        categories = [a.get_text(strip=True) for a in card.select(".categories a")]
        if categories:
            detail.categories = categories

        yp_rating_el = card.select_one(".yp-ratings .rating-stars")
        if yp_rating_el:
            detail.yp_rating = self._rating_from_class(yp_rating_el.get("class", []))
        yp_count = card.select_one(".yp-ratings .count")
        if yp_count:
            detail.yp_review_count = self._extract_count(yp_count.get_text())

        ta_rating_el = card.select_one(".ta-rating-wrapper .ta-rating")
        if ta_rating_el:
            detail.ta_rating = self._ta_rating_from_class(ta_rating_el.get("class", []))
        ta_count = card.select_one(".ta-rating-wrapper .ta-count")
        if ta_count:
            detail.ta_review_count = self._extract_count(ta_count.get_text())

        time_info = card.select_one(".time-info")
        if time_info:
            status = time_info.select_one(".status-text")
            if status:
                detail.open_status = status.get_text(strip=True)
            divs = time_info.find_all("div", recursive=False)
            for div in divs:
                text = div.get_text(strip=True)
                if text.lower().startswith("today:"):
                    detail.today_hours = text.replace("Today:", "").strip()
                elif text.lower().startswith("tomorrow:"):
                    detail.tomorrow_hours = text.replace("Tomorrow:", "").strip()

        years_el = card.select_one(".years-in-business .count strong")
        if years_el:
            detail.years_in_business = years_el.get_text(strip=True)

        detail.amenities = [
            span.get_text(strip=True)
            for span in card.select(".amenities-info span")
            if span.get_text(strip=True)
        ]

    def _parse_ctas(self, detail: BusinessDetail) -> None:
        ctas = self.soup.select_one("#default-ctas")
        if not ctas:
            return

        phone_el = ctas.select_one("a.phone")
        if phone_el:
            detail.phone = phone_el.get_text(strip=True)

        website_el = ctas.select_one("a.website-link")
        if website_el and website_el.get("href"):
            detail.website = website_el["href"].strip()

        directions_el = ctas.select_one("a.directions")
        if directions_el:
            detail.directions_url = urljoin(BASE_URL, directions_el.get("href", ""))
            addr_spans = directions_el.select(".address span")
            if addr_spans:
                parts = [s.get_text(strip=True) for s in addr_spans]
                if parts:
                    detail.street_address = parts[0]
                    if len(parts) > 1:
                        detail.locality = parts[1]
                    detail.full_address = ", ".join(parts)

    def _parse_gallery(self, detail: BusinessDetail) -> None:
        gallery = self.soup.select_one("#gallery")
        if not gallery:
            return

        view_all = gallery.select_one(".section-title a")
        if view_all:
            match = re.search(r"\((\d+)\)", view_all.get_text())
            if match:
                detail.gallery_count = int(match.group(1))

        images: list[dict[str, str]] = []
        seen_urls: set[str] = set()

        for item in gallery.select(".collage-item"):
            anchor = item.select_one("a.collage-pic")
            img = item.select_one("img")

            url = ""
            caption = ""
            media_id = ""
            username = ""
            source = "yp"

            if anchor:
                media_id = anchor.get("data-media-id", "")
                media_raw = anchor.get("data-media")
                if media_raw:
                    try:
                        media = json.loads(media_raw)
                        url = media.get("fullImagePath") or media.get("src", "")
                        caption = media.get("caption", "")
                        username = media.get("userName", "")
                        if media.get("isThirdParty"):
                            source = "tripadvisor"
                    except json.JSONDecodeError:
                        pass
                style = anchor.get("style", "")
                if not url and "background-image" in style:
                    match = re.search(r"url\(([^)]+)\)", style)
                    if match:
                        url = match.group(1).strip("'\"")
                        source = "tripadvisor"

            if img and not url:
                url = img.get("data-url") or img.get("src", "")

            if url and "_crop" in url:
                url = re.sub(r"_\d+x\d+_crop", "", url)

            if url and url not in seen_urls:
                seen_urls.add(url)
                images.append(
                    {
                        "url": url,
                        "media_id": media_id,
                        "caption": caption,
                        "username": username,
                        "source": source,
                    }
                )

        detail.gallery_images = images
        if not detail.gallery_count:
            detail.gallery_count = len(images)

    def _parse_hours(self, detail: BusinessDetail) -> None:
        hours_section = self.soup.select_one("#aside-hours")
        if not hours_section:
            return

        hours: dict[str, str] = {}
        for row in hours_section.select("table tbody tr"):
            day_el = row.select_one("th.day-label")
            time_el = row.select_one("td.day-hours time") or row.select_one("td.day-hours")
            if day_el and time_el:
                day = day_el.get_text(strip=True).rstrip(":")
                hours[day] = time_el.get_text(strip=True)
        detail.regular_hours = hours

    def _parse_reviews(self, detail: BusinessDetail) -> None:
        reviews_section = self.soup.select_one("#reviews")
        if not reviews_section:
            return

        yp_reviews: list[dict] = []
        for article in reviews_section.select("#yp-reviews-container article"):
            review = self._parse_yp_review(article)
            if review:
                yp_reviews.append(review)
        detail.reviews_yp = yp_reviews

        ta_reviews: list[dict] = []
        for article in reviews_section.select("#ta-reviews-container article.clearfix"):
            if "see-more" in (article.get("class") or []):
                continue
            review = self._parse_ta_review(article)
            if review:
                ta_reviews.append(review)
        detail.reviews_ta = ta_reviews

    def _parse_yp_review(self, article) -> dict | None:
        author_el = article.select_one("a.author")
        date_el = article.select_one(".date-posted span") or article.select_one(".date-posted")
        title_el = article.select_one("header.review-title")
        body_el = article.select_one(".review-response p")

        ratings: dict[str, str] = {}
        for block in article.select(".result-ratings"):
            label_el = block.select_one(".rating-label")
            indicator = block.select_one(".rating-indicator")
            if label_el and indicator:
                ratings[label_el.get_text(strip=True)] = self._rating_from_class(
                    indicator.get("class", [])
                )

        helpful_el = article.select_one(".helpful-vote .count")
        helpful = helpful_el.get_text(strip=True) if helpful_el else "0"

        if not author_el and not body_el:
            return None

        return {
            "review_id": article.get("id", ""),
            "author": author_el.get_text(strip=True) if author_el else "",
            "date": date_el.get_text(strip=True) if date_el else "",
            "title": title_el.get_text(strip=True) if title_el else "",
            "text": body_el.get_text(strip=True) if body_el else "",
            "ratings": ratings,
            "helpful_count": helpful.strip("()"),
        }

    def _parse_ta_review(self, article) -> dict | None:
        name_el = article.select_one(".author-info .name")
        location_el = article.select_one(".author-info .location")
        date_el = article.select_one(".date-posted")
        rating_el = article.select_one(".ta-rating")
        title_el = article.select_one(".review-response header")
        body_el = article.select_one(".review-response p")

        if not name_el and not body_el:
            return None

        return {
            "author": name_el.get_text(strip=True) if name_el else "",
            "location": location_el.get_text(strip=True) if location_el else "",
            "date": date_el.get_text(strip=True) if date_el else "",
            "rating": self._ta_rating_from_class(rating_el.get("class", []) if rating_el else []),
            "title": title_el.get_text(strip=True) if title_el else "",
            "text": body_el.get_text(strip=True) if body_el else "",
        }

    def _parse_places_near(self, detail: BusinessDetail) -> None:
        for section in self.soup.select("section.cross-links"):
            header = section.select_one("header h2")
            if not header or "places near" not in header.get_text(strip=True).lower():
                continue
            places = []
            for link in section.select("ul li a"):
                places.append(
                    {
                        "name": link.get_text(strip=True),
                        "url": urljoin(BASE_URL, link.get("href", "")),
                    }
                )
            detail.places_near = places
            break

    def _parse_details_card(self, detail: BusinessDetail) -> None:
        card = self.soup.select_one("#details-card")
        if not card:
            return

        phone_p = card.select_one("p.phone")
        if phone_p:
            detail.phone = phone_p.get_text(strip=True).replace("Phone:", "").strip()

        for p in card.select("p"):
            text = p.get_text(strip=True)
            if text.startswith("Address:"):
                detail.full_address = text.replace("Address:", "").strip()
            elif p.select_one("a") and "website" in (p.get("class") or []):
                link = p.select_one("a")
                if link:
                    detail.website = link.get("href", "").strip()

    def _parse_more_info(self, detail: BusinessDetail) -> None:
        section = self.soup.select_one("#business-info")
        if not section:
            return

        extra_phones: list[str] = []
        for p in section.select("dd.extra-phones p"):
            extra_phones.append(p.get_text(strip=True))
        detail.extra_phones = extra_phones

        payment = section.select_one("dd.payment")
        if payment:
            detail.payment_methods = payment.get_text(strip=True)

        detail.neighborhoods = [
            a.get_text(strip=True) for a in section.select("dd.neighborhoods a")
        ]

        detail.aka = [p.get_text(strip=True) for p in section.select("dd.aka p")]

        detail.other_links = [
            a.get("href", "").strip()
            for a in section.select("dd.weblinks a")
            if a.get("href")
        ]

        categories = [a.get_text(strip=True) for a in section.select("dd.categories a")]
        if categories:
            detail.categories = categories

        other_info: dict[str, str] = {}
        for p in section.select("dd.other-information p"):
            strong = p.select_one("strong")
            if strong:
                key = strong.get_text(strip=True).rstrip(":")
                value = p.get_text(strip=True).replace(f"{key}:", "").strip()
                other_info[key] = value
        detail.other_information = other_info

    def _parse_similar(self, detail: BusinessDetail) -> None:
        similar_section = self.soup.select_one("#similar-listings") or self.soup.select_one(
            ".similar-listings"
        )
        if not similar_section:
            return

        similar = []
        for item in similar_section.select("a.business-name, .result a.business-name"):
            similar.append(
                {
                    "name": item.get_text(strip=True),
                    "url": urljoin(BASE_URL, item.get("href", "").split("#")[0]),
                }
            )
        detail.similar_businesses = similar

    def _parse_coordinates(self, detail: BusinessDetail) -> None:
        map_el = self.soup.select_one("[data-latitude], [data-longitude]")
        if map_el:
            detail.latitude = map_el.get("data-latitude", "")
            detail.longitude = map_el.get("data-longitude", "")

        for script in self.soup.find_all("script"):
            text = script.string or ""
            lat_match = re.search(r'"latitude"\s*:\s*([-\d.]+)', text)
            lng_match = re.search(r'"longitude"\s*:\s*([-\d.]+)', text)
            if lat_match and not detail.latitude:
                detail.latitude = lat_match.group(1)
            if lng_match and not detail.longitude:
                detail.longitude = lng_match.group(1)

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
