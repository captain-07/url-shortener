"""Contract tests: the exact status codes and body shapes the README promises."""

from datetime import UTC, datetime, timedelta

import pytest

from app.clock import utcnow
from app.config import settings
from app.constants import MAX_URL_LENGTH
from app.models import Link

URL = "https://example.com/some/long/path"


def create(client, **overrides):
    return client.post("/links", json={"url": URL, **overrides})


def insert_expired_link(session_factory, code="old"):
    with session_factory() as db:
        db.add(Link(code=code, original_url=URL, expires_at=utcnow() - timedelta(minutes=1)))
        db.commit()


# ---------- error contract ----------


def test_422_detail_is_a_human_readable_string(client):
    resp = create(client, url="not-a-url")
    assert resp.status_code == 422
    body = resp.json()
    assert isinstance(body["detail"], str)
    assert "url" in body["detail"]
    assert body["errors"][0]["loc"] == ["body", "url"]


def test_404_body_matches_documented_shape(client):
    resp = client.get("/missing")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Short link 'missing' does not exist."}


def test_409_body_matches_documented_shape(client):
    create(client, custom_alias="promo")
    resp = create(client, custom_alias="promo")
    assert resp.status_code == 409
    assert resp.json() == {
        "detail": "Alias 'promo' is already taken. Please choose a different alias."
    }


def test_410_body_matches_documented_shape(client, session_factory):
    insert_expired_link(session_factory)
    resp = client.get("/old")
    assert resp.status_code == 410
    assert resp.json()["detail"].startswith("Short link 'old' expired on ")
    assert resp.json()["detail"].endswith("and is no longer available.")


# ---------- request validation ----------


@pytest.mark.parametrize(
    "field,value",
    [("custom_alais", "typo"), ("expires", "2030-01-01T00:00:00Z")],
)
def test_unknown_fields_are_rejected(client, field, value):
    resp = client.post("/links", json={"url": URL, field: value})
    assert resp.status_code == 422
    assert field in resp.json()["detail"]


@pytest.mark.parametrize("alias", ["ab", "a" * 33, "my link", "a.b", "a/b"])
def test_invalid_aliases_are_rejected(client, alias):
    assert create(client, custom_alias=alias).status_code == 422


@pytest.mark.parametrize("alias", ["abc", "a" * 32, "a-b_C9"])
def test_valid_alias_boundaries_are_accepted(client, alias):
    resp = create(client, custom_alias=alias)
    assert resp.status_code == 201
    assert resp.json()["code"] == alias


def test_health_alias_is_reserved(client):
    assert create(client, custom_alias="health").status_code == 422


def test_url_pointing_back_at_service_is_rejected(client):
    own_url = f"{settings.base_url.rstrip('/')}/abc123"
    resp = create(client, url=own_url)
    assert resp.status_code == 422
    assert "loop" in resp.json()["detail"]


def test_url_at_length_limit_is_accepted(client):
    url = "https://example.com/" + "a" * (MAX_URL_LENGTH - len("https://example.com/"))
    assert len(url) == MAX_URL_LENGTH
    assert create(client, url=url).status_code == 201


def test_too_long_url_is_rejected(client):
    long_url = "https://example.com/" + "a" * MAX_URL_LENGTH
    assert create(client, url=long_url).status_code == 422


def test_naive_expiry_is_treated_as_utc(client):
    naive_future = (utcnow() + timedelta(hours=1)).isoformat()
    assert create(client, expires_at=naive_future).status_code == 201


# ---------- response contract ----------


def test_timestamps_are_utc_and_monotonic(client):
    expires = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    created = create(client, expires_at=expires).json()
    assert created["created_at"].endswith("Z")
    assert created["expires_at"].endswith("Z")

    code = created["code"]
    client.get(f"/{code}", follow_redirects=False)
    stats = client.get(f"/links/{code}/stats").json()
    assert stats["last_clicked_at"].endswith("Z")
    assert stats["last_clicked_at"] >= stats["created_at"]


def test_redirect_is_not_cacheable(client):
    code = create(client).json()["code"]
    resp = client.get(f"/{code}", follow_redirects=False)
    assert resp.headers["cache-control"] == "no-store"


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_codegen_exhaustion_returns_500(client, monkeypatch):
    monkeypatch.setattr("app.services.generate_code", lambda length: "samecode")
    assert create(client).status_code == 201  # occupies the only code we will generate
    resp = create(client)
    assert resp.status_code == 500
    assert "could not generate" in resp.json()["detail"].lower()
