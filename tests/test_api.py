from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from backend import database as db_module
from backend import main as main_module


def test_end_to_end_scan_manual_review_report_and_dashboard(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(db_module, "DATA_DIR", runtime)
    monkeypatch.setattr(db_module, "DB_PATH", runtime / "pyaazscan.sqlite3")
    monkeypatch.setattr(main_module, "DATA_DIR", runtime)
    image = Path(__file__).resolve().parents[1] / "frontend" / "assets" / "onion-demo.png"

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/scan/image",
            files={"file": ("test-onion-lot.png", image.read_bytes(), "image/png")},
            data={"lot_id": "TEST-LOT-01", "procurement_centre": "Test centre", "operator": "Test user"},
        )
        assert response.status_code == 200, response.text
        inspection = response.json()
        assert inspection["sample_size"] == 8
        assert inspection["summary"] == {"grade_a": 2, "urs": 3, "reject": 3, "manual_review": 0, "sample_size": 8}
        assert inspection["percentages"]["grade_a"] + inspection["percentages"]["urs"] + inspection["percentages"]["reject"] + inspection["percentages"]["manual_review"] == 100
        assert inspection["defect_distribution"] == {"damaged": 1, "rotten": 1, "sprouted": 1, "undersized": 1}

        detail = client.get(f"/api/inspection/{inspection['inspection_id']}")
        assert detail.status_code == 200
        assert detail.json()["image"]["width"] == 1000
        assert len(detail.json()["onions"]) == 8

        manual = client.post("/api/manual-review", json={
            "inspection_id": inspection["inspection_id"], "onion_id": 1, "decision": "URS", "reviewer": "Test reviewer", "note": "Physical check override",
        })
        assert manual.status_code == 200
        assert manual.json()["result"]["summary"]["urs"] == 4
        assert client.get(f"/api/audit/{inspection['inspection_id']}").json()["items"][-1]["action"] == "manual_decision_recorded"

        generated = client.post("/api/reports/generate", json={"inspection_id": inspection["inspection_id"]})
        assert generated.status_code == 200, generated.text
        report = generated.json()
        pdf = client.get(report["pdf_url"])
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")
        verify = client.get(f"/api/reports/{report['report_id']}/verify")
        assert verify.status_code == 200
        assert verify.json()["verified"] is True
        assert verify.json()["rule_set_id"] == "DEMO_45_65"
        assert verify.json()["image_verified"] is True
        assert client.get(f"/api/reports/{report['report_id']}/qr").headers["content-type"] == "image/png"
        stored_image = next((runtime / "images").glob("*"))
        stored_image.write_bytes(stored_image.read_bytes() + b"tamper")
        tampered = client.get(f"/api/reports/{report['report_id']}/verify")
        assert tampered.status_code == 200
        assert tampered.json()["verified"] is False
        assert tampered.json()["image_verified"] is False

        dashboard = client.get("/api/dashboard").json()
        assert dashboard["today_inspections"] == 1
        assert dashboard["onions_inspected"] == 8
        assert dashboard["reports_generated"] == 1


def test_uncalibrated_scan_sends_size_dependent_bulbs_to_manual_review(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(db_module, "DATA_DIR", runtime)
    monkeypatch.setattr(db_module, "DB_PATH", runtime / "pyaazscan.sqlite3")
    monkeypatch.setattr(main_module, "DATA_DIR", runtime)
    demo = Path(__file__).resolve().parents[1] / "frontend" / "assets" / "onion-demo.png"
    with Image.open(demo) as original:
        no_scale = original.crop((0, 0, 760, 520))
        output = BytesIO()
        no_scale.save(output, format="PNG")
    with TestClient(main_module.app) as client:
        response = client.post("/api/scan/image", files={"file": ("uncalibrated.png", output.getvalue(), "image/png")})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["calibration"]["calibrated"] is False
        assert result["summary"]["manual_review"] >= 1
        assert any(item["grade"] == "MANUAL_REVIEW" for item in result["onions"])
        assert all(item["diameter_mm"] is None for item in result["onions"])


def test_upload_rejects_non_image(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(db_module, "DATA_DIR", runtime)
    monkeypatch.setattr(db_module, "DB_PATH", runtime / "pyaazscan.sqlite3")
    monkeypatch.setattr(main_module, "DATA_DIR", runtime)
    with TestClient(main_module.app) as client:
        response = client.post("/api/scan/image", files={"file": ("not-image.txt", b"not an image", "text/plain")})
        assert response.status_code == 415


def test_rules_profile_is_validated_and_versioned(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(db_module, "DATA_DIR", runtime)
    monkeypatch.setattr(db_module, "DB_PATH", runtime / "pyaazscan.sqlite3")
    monkeypatch.setattr(main_module, "DATA_DIR", runtime)
    with TestClient(main_module.app) as client:
        current = client.get("/api/rules").json()["active"]
        current["diameter_min_mm"] = 46
        response = client.post("/api/rules", json=current)
        assert response.status_code == 200
        assert response.json()["active"]["diameter_min_mm"] == 46
        assert response.json()["active"]["version"] != "1.0.0"
        history = client.get("/api/rules").json()["history"]
        assert len(history) == 2
        assert next(item for item in history if item["active"])["diameter_min_mm"] == 46
