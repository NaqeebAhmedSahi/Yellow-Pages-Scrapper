"""Undetected Chrome WebDriver factory and helpers."""

from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path

import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import (
    IMPLICIT_WAIT,
    PAGE_LOAD_TIMEOUT,
    SCROLL_PAUSE_SECONDS,
    USER_AGENT,
)

logger = logging.getLogger(__name__)


def find_chrome_binary() -> str | None:
    """Locate Google Chrome / Chromium on the current machine."""
    system = platform.system()

    if system == "Windows":
        candidates = [
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
            / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
            / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
            / "Chromium/Application/chrome.exe",
        ]
    elif system == "Darwin":
        candidates = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
    else:
        for name in (
            "google-chrome",
            "google-chrome-stable",
            "chromium-browser",
            "chromium",
            "chrome",
        ):
            found = shutil.which(name)
            if found:
                return found
        candidates = [
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/google-chrome-stable"),
            Path("/usr/bin/chromium"),
            Path("/usr/bin/chromium-browser"),
            Path("/snap/bin/chromium"),
        ]

    for path in candidates:
        if path and path.is_file():
            return str(path)
    return None


def get_chrome_major_version(binary: str | None = None) -> int | None:
    """Return installed Chrome major version (e.g. 143), or None if unknown."""
    binary = binary or find_chrome_binary()
    if not binary:
        return None

    try:
        output = subprocess.check_output(
            [binary, "--version"],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=15,
        )
        match = re.search(r"(\d+)\.\d+\.\d+(?:\.\d+)?", output)
        if match:
            return int(match.group(1))
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Could not read Chrome version from %s: %s", binary, exc)

    if platform.system() == "Windows":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Google\Chrome\BLBeacon",
            ) as key:
                version, _ = winreg.QueryValueEx(key, "version")
                match = re.match(r"(\d+)\.", str(version))
                if match:
                    return int(match.group(1))
        except OSError:
            pass

    return None


def _user_agent_for_chrome(major: int | None) -> str:
    if major is None:
        return USER_AGENT
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{major}.0.0.0 Safari/537.36"
    )


def _uc_driver_cache_path() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"
    return base / "undetected_chromedriver" / "undetected_chromedriver"


def _cached_driver_major_version(driver_path: Path) -> int | None:
    if not driver_path.is_file():
        return None
    try:
        output = subprocess.check_output(
            [str(driver_path), "--version"],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
        match = re.search(r"ChromeDriver\s+(\d+)\.", output)
        if match:
            return int(match.group(1))
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _ensure_matching_driver_cache(chrome_major: int) -> None:
    """Drop cached ChromeDriver when it does not match installed Chrome."""
    cache_path = _uc_driver_cache_path()
    cached_major = _cached_driver_major_version(cache_path)
    if cached_major is None:
        return
    if cached_major != chrome_major:
        logger.warning(
            "Cached ChromeDriver %s does not match Chrome %s; removing cache",
            cached_major,
            chrome_major,
        )
        try:
            cache_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Could not remove cached driver %s: %s", cache_path, exc)


class BrowserManager:
    """Manages undetected Chrome lifecycle and page interactions."""

    def __init__(self, headless: bool = False) -> None:
        self.headless = headless
        self.driver: uc.Chrome | None = None

    def start(self) -> None:
        chrome_binary = find_chrome_binary()
        chrome_major = get_chrome_major_version(chrome_binary)

        if not chrome_binary:
            raise RuntimeError(
                "Google Chrome / Chromium was not found. "
                "Install Chrome and try again."
            )

        if chrome_major is None:
            logger.warning(
                "Could not detect Chrome version from %s; "
                "undetected-chromedriver will auto-select a driver",
                chrome_binary,
            )
        else:
            logger.info("Detected Chrome %s at %s", chrome_major, chrome_binary)
            _ensure_matching_driver_cache(chrome_major)

        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"--user-agent={_user_agent_for_chrome(chrome_major)}")
        options.add_argument("--window-size=1920,1080")
        if self.headless:
            options.add_argument("--headless=new")

        chrome_kwargs: dict = {
            "options": options,
            "use_subprocess": True,
            "browser_executable_path": chrome_binary,
        }
        if chrome_major is not None:
            chrome_kwargs["version_main"] = chrome_major

        try:
            self.driver = uc.Chrome(**chrome_kwargs)
        except Exception as first_error:
            # Force a fresh driver download on version mismatch / corrupt cache.
            if chrome_major is not None:
                logger.warning(
                    "Driver start failed (%s); clearing cache and retrying for Chrome %s",
                    first_error,
                    chrome_major,
                )
                _ensure_matching_driver_cache(chrome_major)
                cache_path = _uc_driver_cache_path()
                cache_path.unlink(missing_ok=True)
                self.driver = uc.Chrome(**chrome_kwargs)
            else:
                raise

        self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        self.driver.implicitly_wait(IMPLICIT_WAIT)
        logger.info(
            "Undetected Chrome driver started (Chrome %s)",
            chrome_major if chrome_major is not None else "auto",
        )

    def stop(self) -> None:
        if self.driver:
            try:
                self.driver.quit()
            except WebDriverException:
                pass
            self.driver = None
            logger.info("Browser stopped")

    def get_page_source(self, url: str, wait_selector: str | None = None) -> str:
        if not self.driver:
            raise RuntimeError("Browser not started")

        self.driver.get(url)
        if wait_selector:
            self.wait_for_selector(wait_selector)
        return self.driver.page_source

    def wait_for_selector(self, selector: str, timeout: int = PAGE_LOAD_TIMEOUT) -> None:
        if not self.driver:
            raise RuntimeError("Browser not started")
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    def scroll_to_bottom(self, pause: float = SCROLL_PAUSE_SECONDS) -> None:
        if not self.driver:
            return
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def scroll_element_into_view(self, selector: str) -> None:
        if not self.driver:
            return
        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                elements[0],
            )
            time.sleep(SCROLL_PAUSE_SECONDS)

    def click_if_present(self, selector: str) -> bool:
        if not self.driver:
            return False
        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
        if not elements:
            return False
        try:
            elements[0].click()
            time.sleep(SCROLL_PAUSE_SECONDS)
            return True
        except WebDriverException:
            return False

    def scroll_carousel(self, next_selector: str, max_clicks: int) -> None:
        """Click carousel next button repeatedly to load all items."""
        for _ in range(max_clicks):
            if not self.click_if_present(next_selector):
                break

    def safe_get(self, url: str, retries: int = 3) -> str | None:
        for attempt in range(1, retries + 1):
            try:
                return self.get_page_source(url, wait_selector="body")
            except TimeoutException:
                logger.warning("Timeout loading %s (attempt %d/%d)", url, attempt, retries)
            except WebDriverException as exc:
                logger.warning("Error loading %s: %s (attempt %d/%d)", url, exc, attempt, retries)
            time.sleep(2 * attempt)
        return None

    def __enter__(self) -> BrowserManager:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()
