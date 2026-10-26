"""Concurrent redirects must not lose click updates."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

CLICKS = 20


@pytest.fixture()
def file_client(tmp_path):
    """A file-backed SQLite database so several connections can write at once."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrency.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()


def test_concurrent_redirects_count_every_click(file_client):
    code = file_client.post("/links", json={"url": "https://example.com/x"}).json()["code"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(
            pool.map(lambda _: file_client.get(f"/{code}", follow_redirects=False), range(CLICKS))
        )

    assert [r.status_code for r in responses] == [302] * CLICKS

    stats = file_client.get(f"/links/{code}/stats").json()
    assert stats["total_clicks"] == CLICKS
    assert stats["last_clicked_at"] is not None
