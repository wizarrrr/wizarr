import json

from app.services import notifications


def test_pushover_posts_token_user_title_and_message(monkeypatch):
    captured = {}

    def fake_post(url, data, headers, timeout):
        captured["url"] = url
        captured["data"] = data
        captured["headers"] = headers
        return type("Resp", (), {"status_code": 200, "text": ""})()

    monkeypatch.setattr(notifications.requests, "post", fake_post)

    ok = notifications._pushover(
        "hello world", "My Title", user_key="uKey123", api_token="aToken456"
    )

    assert ok is True
    assert captured["url"] == "https://api.pushover.net/1/messages.json"
    payload = json.loads(captured["data"])
    assert payload == {
        "token": "aToken456",
        "user": "uKey123",
        "title": "My Title",
        "message": "hello world",
    }
