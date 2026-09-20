"""FacilityIQ portal load test.

Exercise the deployed Streamlit health endpoint, the stable HTTP surface used
by Azure/App Service and Streamlit Cloud health checks. UI correctness is
covered separately by Selenium.
"""
from locust import HttpUser, between, task

class FacilityIQUser(HttpUser):
    wait_time = between(0.2, 0.8)

    @task(4)
    def health(self):
        with self.client.get("/_stcore/health", name="Streamlit health", catch_response=True) as r:
            if r.status_code != 200 or "ok" not in r.text.lower():
                r.failure(f"unexpected health response {r.status_code}: {r.text[:100]}")

    @task(1)
    def root(self):
        with self.client.get("/", name="Portal root", catch_response=True) as r:
            if r.status_code != 200 or "streamlit" not in r.text.lower():
                r.failure(f"portal shell unavailable: {r.status_code}")
