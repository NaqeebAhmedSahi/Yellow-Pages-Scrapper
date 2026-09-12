"""Undetected Chrome WebDriver factory and helpers."""

from __future__ import annotations

import logging
import time
from typing import Callable

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


class BrowserManager:
    """Manages undetected Chrome lifecycle and page interactions."""

    def __init__(self, headless: bool = False) -> None:
        self.headless = headless
        self.driver: uc.Chrome | None = None

    def start(self) -> None:
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"--user-agent={USER_AGENT}")
        options.add_argument("--window-size=1920,1080")
        if self.headless:
            options.add_argument("--headless=new")

        self.driver = uc.Chrome(options=options, use_subprocess=True)
        self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        self.driver.implicitly_wait(IMPLICIT_WAIT)
        logger.info("Undetected Chrome driver started")

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
