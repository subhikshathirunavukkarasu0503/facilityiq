"""Capture portal screenshots with Selenium (headless Chrome).

Also serves as the Selenium E2E evidence: drives login, role navigation and
every screen of the live portal at http://localhost:8501.

Usage: python scripts/capture_screens.py
Writes PNGs to docs/screenshots/.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
URL = "http://localhost:8501"


def wait_for(driver, text: str, timeout: int = 90) -> None:
    WebDriverWait(driver, timeout).until(
        lambda d: text in d.find_element(By.TAG_NAME, "body").text)


def settle(seconds: float = 2.5) -> None:
    time.sleep(seconds)


def shot(driver, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    driver.save_screenshot(str(OUT / f"{name}.png"))
    print("captured", name)


def main() -> None:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1600,1000")
    opts.add_argument("--force-device-scale-factor=1")
    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(URL)
        wait_for(driver, "sign in")
        settle()
        shot(driver, "01_login")

        # login as admin (sees all screens)
        boxes = driver.find_elements(By.CSS_SELECTOR, "input")
        boxes[0].send_keys("admin")
        boxes[1].send_keys("admin@123")
        boxes[1].send_keys(Keys.RETURN)
        wait_for(driver, "Facility Health Overview", timeout=180)
        settle(6)  # weather + charts
        shot(driver, "02_screen1_health_overview")

        # scroll to show alerts
        driver.execute_script("window.scrollTo(0, 700)")
        settle(1)
        shot(driver, "03_screen1_alerts")

        def goto(label_substr: str, expect: str, name: str,
                 extra_wait: float = 5) -> None:
            driver.execute_script("window.scrollTo(0, 0)")
            settle(0.5)
            for attempt in range(3):
                for lab in driver.find_elements(
                        By.CSS_SELECTOR, '[role="radiogroup"] label'):
                    if label_substr in lab.text:
                        driver.execute_script(
                            "arguments[0].scrollIntoView();"
                            "arguments[0].click();", lab)
                        break
                try:
                    wait_for(driver, expect, timeout=60)
                    break
                except Exception:
                    if attempt == 2:
                        raise
            settle(extra_wait)
            shot(driver, name)

        goto("Equipment Detail", "Select asset", "04_screen2_equipment_detail")
        goto("Maintenance", "Work orders", "05_screen3_maintenance")
        goto("AI Predictive", "Failure predictions", "06_screen4_ai")

        # generate a Gemini explanation on screen 4
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            if "Generate AI explanation" in btn.text:
                btn.click()
                break
        settle(12)
        driver.execute_script("window.scrollTo(0, 500)")
        settle(1)
        shot(driver, "07_screen4_gemini_narrative")

        goto("Admin", "Users & roles", "08_admin_panel", extra_wait=3)
        print("ALL CAPTURED")
    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main())
