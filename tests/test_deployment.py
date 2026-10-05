import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

from backend import database, main


def test_vercel_runtime_uses_writable_ephemeral_storage(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("PYAaZSCAN_DATA_DIR", raising=False)
    assert database._runtime_data_dir() == Path("/tmp/pyaazscan-runtime")


def test_vercel_ignores_relative_data_dir_that_resolves_read_only(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("PYAaZSCAN_DATA_DIR", "./data/runtime")
    assert database._runtime_data_dir() == Path("/tmp/pyaazscan-runtime")


def test_local_runtime_keeps_data_inside_repository(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("PYAaZSCAN_DATA_DIR", raising=False)
    assert database._runtime_data_dir() == database.ROOT / "data" / "runtime"


def test_vercel_entrypoint_points_to_existing_fastapi_app():
    config = tomllib.loads((database.ROOT / "pyproject.toml").read_text())
    assert config["tool"]["vercel"]["entrypoint"] == "backend.main:app"


def test_fastapi_serves_frontend_and_demo_route(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(database, "DATA_DIR", runtime)
    monkeypatch.setattr(database, "DB_PATH", runtime / "pyaazscan.sqlite3")
    monkeypatch.setattr(main, "DATA_DIR", runtime)

    with TestClient(main.app) as client:
        assert client.get("/").status_code == 200
        assert "PYAazScan" in client.get("/").text
        assert client.get("/app.js").status_code == 200
        demo = client.get("/demo/onion-lot.png")
        assert demo.status_code == 200
        assert demo.headers["content-type"] == "image/png"
