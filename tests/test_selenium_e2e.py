"""Browser-level E2E for the live Streamlit portal."""
from __future__ import annotations
import os
from pathlib import Path
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.getenv("FACILITYIQ_E2E_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="set FACILITYIQ_E2E_URL for browser E2E")

@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1600,1000")
    d = webdriver.Chrome(options=options)
    yield d
    d.quit()

def wait_text(driver, text, timeout=90):
    WebDriverWait(driver, timeout).until(lambda d: text in d.find_element(By.TAG_NAME, "body").text)

def login(driver, username="admin", password="admin@123"):
    driver.get(BASE_URL)
    wait_text(driver, "sign in")
    fields = driver.find_elements(By.CSS_SELECTOR, "input")
    fields[0].send_keys(username)
    fields[1].send_keys(password)
    fields[1].send_keys(Keys.RETURN)
    wait_text(driver, "Facility Health Overview", 180)

def goto(driver, label, expected):
    for item in driver.find_elements(By.CSS_SELECTOR, '[role="radiogroup"] label'):
        if label in item.text:
            driver.execute_script("arguments[0].click();", item)
            break
    wait_text(driver, expected)

def test_admin_can_navigate_all_five_screens(driver):
    login(driver)
    for label, expected in [
        ("Equipment Detail", "Select asset"),
        ("Maintenance", "Work orders"),
        ("AI Predictive", "Failure predictions"),
        ("Admin", "Users & roles"),
    ]:
        goto(driver, label, expected)

def test_viewer_is_limited_to_health_overview(driver):
    login(driver, "viewer", "viewer@123")
    body = driver.find_element(By.TAG_NAME, "body").text
    assert "Health Overview" in body
    assert "Maintenance Scheduling" not in body
    assert "Admin" not in body
