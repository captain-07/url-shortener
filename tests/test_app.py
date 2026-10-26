"""App bootstrap tests."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

import app.main as main
from app.main import app


def test_lifespan_creates_schema(tmp_path, monkeypatch):
    """Startup must create the tables, without touching the real shortener.db."""
    temp_engine = create_engine(f"sqlite:///{tmp_path / 'lifespan.db'}")
    monkeypatch.setattr(main, "engine", temp_engine)

    with TestClient(app):
        pass  # entering the context runs the lifespan startup hook

    assert "links" in inspect(temp_engine).get_table_names()
    temp_engine.dispose()
