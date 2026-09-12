# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Yellow Pages Scraper (onedir portable app)."""

from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None
ROOT = Path(SPECPATH).resolve()

datas: list = []
binaries: list = []
hiddenimports: list = [
    "undetected_chromedriver",
    "selenium",
    "selenium.webdriver",
    "selenium.webdriver.chrome",
    "selenium.webdriver.chrome.options",
    "selenium.webdriver.chrome.service",
    "selenium.webdriver.common",
    "selenium.webdriver.common.by",
    "selenium.webdriver.support",
    "selenium.webdriver.support.ui",
    "selenium.webdriver.support.expected_conditions",
    "bs4",
    "lxml",
    "lxml.etree",
    "certifi",
    "setuptools",
    "config",
    "config.settings",
    "src",
    "src.gui",
    "src.gui.app",
    "src.gui.theme",
    "src.browser",
    "src.browser.driver_factory",
    "src.scraper",
    "src.scraper.orchestrator",
    "src.parsers",
    "src.parsers.listing_parser",
    "src.parsers.detail_parser",
    "src.storage",
    "src.storage.app_store",
    "src.storage.csv_writer",
    "src.storage.json_writer",
    "src.storage.progress_tracker",
    "src.storage.image_downloader",
    "src.models",
    "src.models.business",
]

for package in ("undetected_chromedriver", "selenium", "certifi", "bs4"):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        pass

try:
    hiddenimports += collect_submodules("selenium")
except Exception:
    pass

# Optional preview image for about/help branding inside the bundle.
preview = ROOT / "docs" / "gui-preview.png"
if preview.exists():
    datas.append((str(preview), "docs"))

a = Analysis(
    [str(ROOT / "gui.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YellowPagesScraper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI app — no black console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "docs" / "app.ico") if (ROOT / "docs" / "app.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="YellowPagesScraper",
)
