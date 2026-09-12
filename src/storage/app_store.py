"""Persistent app settings, presets, and scrape history."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import (
    DATA_DIR,
    DEFAULT_START_URL,
    DOWNLOAD_IMAGES_DEFAULT,
    HEADLESS_DEFAULT,
    HISTORY_FILE,
    IMPLICIT_WAIT,
    MAX_GALLERY_SCROLLS,
    PAGE_LOAD_TIMEOUT,
    PRESETS_FILE,
    REQUEST_DELAY_SECONDS,
    SETTINGS_FILE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def default_settings() -> dict[str, Any]:
    return {
        "start_url": DEFAULT_START_URL,
        "output_dir": str(DATA_DIR),
        "headless": HEADLESS_DEFAULT,
        "download_images": DOWNLOAD_IMAGES_DEFAULT,
        "max_pages": 0,
        "page_load_timeout": PAGE_LOAD_TIMEOUT,
        "implicit_wait": IMPLICIT_WAIT,
        "request_delay_seconds": REQUEST_DELAY_SECONDS,
        "max_gallery_scrolls": MAX_GALLERY_SCROLLS,
        "auto_scroll_logs": True,
        "theme": "light",
    }


class AppStore:
    """File-backed store for GUI settings, presets, and history."""

    def __init__(self) -> None:
        self.settings = default_settings()
        self.presets: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        loaded = _read_json(SETTINGS_FILE, {})
        merged = default_settings()
        if isinstance(loaded, dict):
            merged.update({k: v for k, v in loaded.items() if k in merged})
        self.settings = merged

        presets = _read_json(PRESETS_FILE, {"presets": []})
        self.presets = presets.get("presets", []) if isinstance(presets, dict) else []

        history = _read_json(HISTORY_FILE, {"sessions": []})
        self.history = history.get("sessions", []) if isinstance(history, dict) else []

    def save_settings(self, updates: dict[str, Any] | None = None) -> None:
        if updates:
            self.settings.update(updates)
        _write_json(SETTINGS_FILE, self.settings)

    def save_presets(self) -> None:
        _write_json(PRESETS_FILE, {"presets": self.presets})

    def save_history(self) -> None:
        _write_json(HISTORY_FILE, {"sessions": self.history})

    def upsert_preset(self, name: str, config: dict[str, Any]) -> None:
        name = name.strip()
        if not name:
            raise ValueError("Preset name is required")
        payload = {
            "name": name,
            "updated_at": _now(),
            "config": {
                "start_url": config.get("start_url", DEFAULT_START_URL),
                "output_dir": config.get("output_dir", str(DATA_DIR)),
                "headless": bool(config.get("headless", False)),
                "download_images": bool(config.get("download_images", True)),
                "max_pages": int(config.get("max_pages", 0) or 0),
            },
        }
        for idx, item in enumerate(self.presets):
            if item.get("name") == name:
                self.presets[idx] = payload
                self.save_presets()
                return
        self.presets.append(payload)
        self.save_presets()

    def delete_preset(self, name: str) -> None:
        self.presets = [p for p in self.presets if p.get("name") != name]
        self.save_presets()

    def get_preset(self, name: str) -> dict[str, Any] | None:
        for item in self.presets:
            if item.get("name") == name:
                return item
        return None

    def start_session(self, config: dict[str, Any]) -> str:
        session_id = uuid.uuid4().hex[:12]
        session = {
            "id": session_id,
            "start_url": config.get("start_url", ""),
            "output_dir": config.get("output_dir", ""),
            "headless": bool(config.get("headless", False)),
            "download_images": bool(config.get("download_images", True)),
            "max_pages": int(config.get("max_pages", 0) or 0),
            "started_at": _now(),
            "ended_at": None,
            "status": "running",
            "scraped_count": 0,
            "pending_count": 0,
            "failed_count": 0,
            "total_results": None,
        }
        self.history.insert(0, session)
        self.history = self.history[:200]
        self.save_history()
        return session_id

    def update_session(self, session_id: str, **fields: Any) -> None:
        for session in self.history:
            if session.get("id") == session_id:
                session.update(fields)
                self.save_history()
                return

    def finish_session(self, session_id: str, status: str, stats: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"status": status, "ended_at": _now()}
        if stats:
            payload.update(
                {
                    "scraped_count": stats.get("scraped_count", 0),
                    "pending_count": stats.get("pending_count", 0),
                    "failed_count": stats.get("failed_count", 0),
                    "total_results": stats.get("total_results"),
                }
            )
        self.update_session(session_id, **payload)

    def clear_history(self) -> None:
        self.history = []
        self.save_history()

    def delete_session(self, session_id: str) -> None:
        self.history = [s for s in self.history if s.get("id") != session_id]
        self.save_history()


def export_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def import_json_records(src: Path, dest: Path) -> int:
    """Merge business records from imported JSON into dest JSON. Returns added count."""
    incoming = _read_json(src, [])
    if isinstance(incoming, dict):
        incoming = incoming.get("businesses", incoming.get("data", []))
    if not isinstance(incoming, list):
        raise ValueError("Import JSON must be a list of business objects")

    existing = _read_json(dest, [])
    if not isinstance(existing, list):
        existing = []

    seen = {item.get("url") or item.get("listing_id") for item in existing if isinstance(item, dict)}
    added = 0
    for item in incoming:
        if not isinstance(item, dict):
            continue
        key = item.get("url") or item.get("listing_id")
        if key and key in seen:
            continue
        existing.append(item)
        if key:
            seen.add(key)
        added += 1
    _write_json(dest, existing)
    return added


def import_csv_records(src: Path, dest: Path) -> int:
    """Append CSV rows into dest CSV (header-aware). Returns appended row count."""
    import csv

    if not src.exists():
        raise FileNotFoundError(src)

    with open(src, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if not rows:
        return 0

    dest.parent.mkdir(parents=True, exist_ok=True)
    write_header = not dest.exists() or dest.stat().st_size == 0
    with open(dest, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)
    return len(rows)
