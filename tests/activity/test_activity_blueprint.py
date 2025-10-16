from unittest.mock import patch

from app.services.activity import ActivityService


def test_activity_requires_login(activity_client):
    response = activity_client.get("/activity/")
    assert response.status_code == 302
    # Redirects to the login route
    assert "_login" in response.headers.get("Location", "")


def test_activity_index_renders(logged_activity_client):
    response = logged_activity_client.get("/activity/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Monitor media playback activity" in body


def test_activity_dashboard_tab_uses_service(logged_activity_client):
    default_stats = ActivityService().get_dashboard_stats()
    with patch(
        "app.services.activity.ActivityService.get_dashboard_stats",
        return_value=default_stats,
    ) as mocked:
        response = logged_activity_client.get("/activity/dashboard")

    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "dashboard" in body.lower()
    mocked.assert_called_once_with(days=7)


def test_activity_grid_returns_table(logged_activity_client):
    response = logged_activity_client.get("/activity/grid")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Failed to load activity data" not in body
