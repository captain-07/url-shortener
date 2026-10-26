from datetime import UTC, datetime, timedelta

import pytest

from app.clock import utcnow
from app.config import settings
from app.models import Link

URL = "https://example.com/some/long/path"


def create(client, **overrides):
    return client.post("/links", json={"url": URL, **overrides})


def insert_expired_link(session_factory, code="old"):
    """The API rightly refuses past expiries, so seed the DB directly."""
    with session_factory() as db:
        db.add(Link(code=code, original_url=URL, expires_at=utcnow() - timedelta(minutes=1)))
        db.commit()


# ---------- creation ----------


def test_create_link_returns_generated_code(client):
    resp = create(client)
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["code"]) == settings.code_length
    assert body["short_url"].endswith("/" + body["code"])
    assert body["original_url"] == URL


def test_custom_alias_is_used_as_code(client):
    resp = create(client, custom_alias="promo")
    assert resp.status_code == 201
    assert resp.json()["code"] == "promo"


def test_duplicate_alias_returns_409_with_helpful_message(client):
    create(client, custom_alias="promo")
    resp = create(client, custom_alias="promo")
    assert resp.status_code == 409
    assert "already taken" in resp.json()["detail"]


@pytest.mark.parametrize("bad_url", ["not-a-url", "javascript:alert(1)", "ftp://example.com/f", ""])
def test_invalid_urls_are_rejected(client, bad_url):
    assert create(client, url=bad_url).status_code == 422


def test_past_expiry_is_rejected(client):
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    assert create(client, expires_at=past).status_code == 422


def test_reserved_alias_is_rejected(client):
    assert create(client, custom_alias="docs").status_code == 422


def test_generated_code_collision_is_retried(client, monkeypatch):
    codes = iter(["samecode", "samecode", "freshone"])
    monkeypatch.setattr("app.services.generate_code", lambda length: next(codes))
    first = create(client)
    second = create(client)  # first attempt collides, second attempt succeeds
    assert first.json()["code"] == "samecode"
    assert second.status_code == 201
    assert second.json()["code"] == "freshone"


# ---------- redirect ----------


def test_redirect_returns_302_to_original_url(client):
    code = create(client, custom_alias="promo").json()["code"]
    resp = client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == URL


def test_unknown_code_returns_404(client):
    assert client.get("/doesnotexist", follow_redirects=False).status_code == 404


def test_link_with_future_expiry_still_redirects(client):
    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    code = create(client, expires_at=future).json()["code"]
    assert client.get(f"/{code}", follow_redirects=False).status_code == 302


def test_expired_link_returns_410_and_is_not_counted(client, session_factory):
    insert_expired_link(session_factory, "old")
    resp = client.get("/old", follow_redirects=False)
    assert resp.status_code == 410
    assert "expired" in resp.json()["detail"].lower()
    assert client.get("/links/old/stats").json()["total_clicks"] == 0  # stats still readable


# ---------- analytics ----------


def test_clicks_are_counted_and_last_click_recorded(client):
    code = create(client).json()["code"]
    before = client.get(f"/links/{code}/stats").json()
    assert before["total_clicks"] == 0
    assert before["last_clicked_at"] is None

    for _ in range(3):
        client.get(f"/{code}", follow_redirects=False)

    after = client.get(f"/links/{code}/stats").json()
    assert after["total_clicks"] == 3
    assert after["last_clicked_at"] is not None


def test_stats_for_unknown_code_returns_404(client):
    assert client.get("/links/nope/stats").status_code == 404
