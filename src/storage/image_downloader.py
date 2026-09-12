"""Download gallery images to local storage."""

from __future__ import annotations

import base64
import logging
import re
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

_FETCH_SCRIPT = """
const url = arguments[0];
const callback = arguments[arguments.length - 1];
fetch(url, {credentials: "include"})
  .then(async (response) => {
    if (!response.ok) {
      callback({ok: false, status: response.status});
      return;
    }
    const buffer = await response.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    callback({
      ok: true,
      contentType: response.headers.get("content-type") || "",
      data: btoa(binary),
    });
  })
  .catch((error) => callback({ok: false, error: String(error)}));
"""


def _safe_folder_name(value: str) -> str:
    cleaned = re.sub(r"[^\w.\-]+", "_", value.strip())[:80]
    return cleaned or "unknown"


def _guess_extension(url: str, content_type: str | None) -> str:
    if content_type:
        mime = content_type.split(";")[0].strip().lower()
        if mime in _CONTENT_TYPE_EXT:
            return _CONTENT_TYPE_EXT[mime]
    path = url.split("?", 1)[0].lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def _existing_file(images_root: Path, media_id: str) -> Path | None:
    return next((p for p in images_root.glob(f"{media_id}.*") if p.is_file()), None)


def _download_via_browser(driver: Any, url: str) -> tuple[bytes, str | None] | None:
    try:
        result = driver.execute_async_script(_FETCH_SCRIPT, url)
    except Exception as exc:
        logger.debug("Browser fetch failed for %s: %s", url, exc)
        return None
    if not isinstance(result, dict) or not result.get("ok"):
        logger.debug("Browser fetch rejected for %s: %s", url, result)
        return None
    try:
        data = base64.b64decode(result["data"])
    except (KeyError, ValueError, TypeError):
        return None
    return data, result.get("contentType") or None


def _download_via_http(
    url: str,
    *,
    referer: str | None = None,
    cookie_header: str | None = None,
    timeout: int = 30,
) -> tuple[bytes, str | None] | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": referer or "https://www.yellowpages.com/",
    }
    if cookie_header:
        headers["Cookie"] = cookie_header
    try:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=timeout) as response:
            return response.read(), response.headers.get("Content-Type")
    except (URLError, OSError, TimeoutError, ValueError) as exc:
        logger.debug("HTTP download failed for %s: %s", url, exc)
        return None


def _cookie_header_from_driver(driver: Any) -> str | None:
    try:
        cookies = driver.get_cookies()
    except Exception:
        return None
    if not cookies:
        return None
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies if "name" in c and "value" in c)


def download_gallery_images(
    images: list[dict[str, str]],
    output_dir: Path,
    listing_id: str,
    driver: Any | None = None,
    referer: str | None = None,
    timeout: int = 30,
) -> list[dict[str, str]]:
    """
    Download gallery images under ``{output_dir}/images/{listing_id}/``.

    Each image dict gains a ``local_path`` key with a path relative to ``output_dir``
    (e.g. ``images/12345/abc.jpg``). Remote ``url`` is preserved.
    """
    if not images:
        return images

    folder_name = _safe_folder_name(listing_id)
    images_root = output_dir / "images" / folder_name
    images_root.mkdir(parents=True, exist_ok=True)
    cookie_header = _cookie_header_from_driver(driver) if driver is not None else None

    for index, image in enumerate(images):
        url = (image.get("url") or "").strip()
        if not url:
            continue

        media_id = _safe_folder_name(image.get("media_id") or f"img_{index}")
        existing = _existing_file(images_root, media_id)
        if existing:
            image["local_path"] = str(existing.relative_to(output_dir)).replace("\\", "/")
            continue

        payload = None
        if driver is not None:
            payload = _download_via_browser(driver, url)
        if payload is None:
            payload = _download_via_http(
                url,
                referer=referer,
                cookie_header=cookie_header,
                timeout=timeout,
            )
        if payload is None:
            logger.warning("Failed to download gallery image %s", url)
            continue

        data, content_type = payload
        if not data:
            logger.warning("Empty gallery image response for %s", url)
            continue

        ext = _guess_extension(url, content_type)
        dest = images_root / f"{media_id}{ext}"
        try:
            dest.write_bytes(data)
            image["local_path"] = str(dest.relative_to(output_dir)).replace("\\", "/")
            logger.debug("Saved gallery image: %s", image["local_path"])
        except OSError as exc:
            logger.warning("Could not write gallery image %s: %s", dest, exc)

    return images
