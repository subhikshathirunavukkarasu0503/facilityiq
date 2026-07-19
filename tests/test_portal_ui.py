"""Portal UI tests via Streamlit's AppTest harness (headless, no browser).

Covers the login gate, role-based screen visibility, and that each screen
renders without exceptions against the real lake + trained models.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "src" / "facilityiq"
          / "portal" / "app.py")

MODELS = Path(__file__).resolve().parents[1] / "models"
LAKE = Path(__file__).resolve().parents[1] / "data" / "lake"

needs_artifacts = pytest.mark.skipif(
    not (MODELS / "hvac_compressor_failure.joblib").exists()
    or not LAKE.exists(),
    reason="models/lake not built; run simulation + training first")


def _login(at: AppTest, user: str, password: str) -> AppTest:
    at.text_input[0].set_value(user)
    at.text_input[1].set_value(password)
    at.button[0].set_value(True)  # form submit
    return at.run()


def _fresh() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180)
    return at.run()


def test_login_page_shown_when_logged_out():
    at = _fresh()
    assert len(at.text_input) == 2
    assert not at.exception


def test_bad_credentials_rejected():
    at = _login(_fresh(), "manager", "wrong-password")
    assert any("Invalid credentials" in e.value for e in at.error)
    assert "user" not in at.session_state


@needs_artifacts
def test_manager_login_lands_on_dashboard():
    at = _login(_fresh(), "manager", "manager@123")
    assert not at.exception
    assert at.session_state["user"]["role"] == "manager"
    # sidebar radio exposes exactly the manager screens (formatted labels)
    options = at.sidebar.radio[0].options
    assert options == ["🏢 Health Overview", "🔍 Equipment Detail",
                       "🗓️ Maintenance Scheduling"]


@needs_artifacts
def test_viewer_sees_only_overview():
    at = _login(_fresh(), "viewer", "viewer@123")
    assert at.sidebar.radio[0].options == ["🏢 Health Overview"]


@needs_artifacts
def test_admin_sees_all_screens_and_admin_panel_renders():
    at = _login(_fresh(), "admin", "admin@123")
    assert at.sidebar.radio[0].options == [
        "🏢 Health Overview", "🔍 Equipment Detail",
        "🗓️ Maintenance Scheduling", "⚙️ Admin"]
    at.sidebar.radio[0].set_value("admin").run()
    assert not at.exception


@needs_artifacts
def test_maintenance_screen_renders_for_manager():
    at = _login(_fresh(), "manager", "manager@123")
    at.sidebar.radio[0].set_value("maintenance").run()
    assert not at.exception
    # work-order metric present
    assert any("Work orders" in (m.label or "") for m in at.metric)


@needs_artifacts
def test_detail_screen_renders():
    at = _login(_fresh(), "tech", "tech@123")
    at.sidebar.radio[0].set_value("detail").run()
    assert not at.exception


@needs_artifacts
def test_sign_out_returns_to_login():
    at = _login(_fresh(), "viewer", "viewer@123")
    # sidebar buttons: refresh, sign out
    at.sidebar.button[1].set_value(True).run()
    assert "user" not in at.session_state
