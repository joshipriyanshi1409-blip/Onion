from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from backend import main as main_module
from backend.services import field_photos

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "data" / "demo" / "import_zenodo_onions.py"


def load_ingest_module():
    spec = importlib.util.spec_from_file_location("import_zenodo_onions", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_bulb(path: Path, *, size=(900, 700), colour=(184, 96, 46), bulbs: int = 1, flat: bool = False, variant: int = 0) -> None:
    """Stand-in "photograph": warm bulbs sized inside the demo engine's contour-area window."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tone = 226 + (variant % 9)
    image = Image.new("RGB", size, (tone + 6, tone + 5, tone))
    if not flat:
        draw = ImageDraw.Draw(image)
        radius = (150 if bulbs == 1 else 95) - (variant % 7) * 3
        drift = (variant % 11) * 4
        centres = [(size[0] // 2 + drift, size[1] // 2 - drift)] if bulbs == 1 else [(size[0] // 3 + drift, size[1] // 2), (size[0] * 2 // 3, size[1] // 2 + 40 - drift)]
        for cx, cy in centres:
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=colour)
    image.save(path, "JPEG", quality=88)


@pytest.fixture()
def fake_pack(tmp_path: Path) -> Path:
    """A stand-in for the published archive: same folder conventions, synthetic pixels."""
    root = tmp_path / "Onion Image Dataset"
    layout = {
        "1. Leaves/1. Healthy/1. Single": 4,
        "2. Bulbs/1. Red/1. Healthy/1. Single": 12,
        "2. Bulbs/1. Red/2. Unhealthy/2. Multiple": 12,
        "2. Bulbs/2. White/1. Healthy/1. Single": 12,
    }
    index = 1
    for folder, count in layout.items():
        for _ in range(count):
            flat = index % 6 == 0  # information-free frames that the selector should drop
            write_bulb(
                root / folder / f"Onion{index:05d}.jpg",
                flat=flat,
                bulbs=2 if "Multiple" in folder else 1,
                colour=(228, 224, 214) if "White" in folder else (184, 96, 46),
                variant=index,
            )
            index += 1
    archive = tmp_path / "Onion Image Dataset.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for item in sorted(root.rglob("*.jpg")):
            bundle.write(item, item.relative_to(root.parent))
    return archive


def run_ingest(module, argv: list[str]) -> int:
    original = sys.argv
    sys.argv = [str(SCRIPT), *argv]
    try:
        return module.main()
    finally:
        sys.argv = original


def test_classify_path_reads_publisher_folder_conventions():
    from pathlib import PurePosixPath as P

    module = load_ingest_module()
    assert module.classify_path(P("Onion Image Dataset/2. Bulbs/1. Red/2. Unhealthy/2. Multiple/x.jpg")) == {
        "part": "bulbs",
        "variety": "red",
        "health": "unhealthy",
        "arrangement": "multiple",
    }
    assert module.classify_path(P("Onion Image Dataset/1. Leaves/1. Healthy/1. Single/x.jpg"))["part"] == "leaves"
    assert module.classify_path(P("unsorted/x.jpg"))["part"] == "unknown"


def test_import_builds_attributed_subset(fake_pack: Path, tmp_path: Path, capsys):
    module = load_ingest_module()
    output = tmp_path / "subset"
    code = run_ingest(module, ["--zip", str(fake_pack), "--output", str(output), "--limit", "6", "--skip-checksum"])
    assert code == 0
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == field_photos.SCHEMA
    assert manifest["source"]["licence"] == "CC-BY-4.0"
    assert manifest["source"]["doi"] == "10.5281/zenodo.20254934"
    assert len(manifest["images"]) == 6
    assert all(item["part"] == "bulbs" for item in manifest["images"]), "leaf photographs stay out of the bulb demo"
    assert all((output / item["file"]).is_file() for item in manifest["images"])
    assert all((output / item["thumbnail"]).is_file() for item in manifest["images"])
    assert manifest["counts"]["available"] == 40
    assert len({item["sha256"] for item in manifest["images"]}) == 6, "byte-identical frames are deduplicated"
    assert manifest["caveats"]["labels_note"]
    attribution = (output / "ATTRIBUTION.md").read_text(encoding="utf-8")
    assert "CC BY 4.0" in attribution and "Vinaya Kulkarni" in attribution
    assert "16,300" in attribution
    printed = capsys.readouterr().out
    assert "Wrote 6 photograph(s)" in printed


def test_import_records_checksum_mismatch_and_supports_dry_run(fake_pack: Path, tmp_path: Path, capsys):
    module = load_ingest_module()
    dry = run_ingest(module, ["--zip", str(fake_pack), "--dry-run"])
    assert dry == 0
    listing = capsys.readouterr().out
    assert "Bulbs" not in listing and "part=bulbs" in listing
    output = tmp_path / "subset"
    assert run_ingest(module, ["--zip", str(fake_pack), "--output", str(output), "--limit", "3"]) == 0
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"]["archive_md5_matches_published"] is False
    assert "published checksum" in (output / "ATTRIBUTION.md").read_text(encoding="utf-8")


def test_metadata_workbook_joins_by_file_stem(tmp_path: Path):
    module = load_ingest_module()
    sheet = (
        '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
        '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2" t="s"><v>3</v></c></row></worksheet>'
    )
    strings = (
        '<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="4" uniqueCount="4">'
        '<si><t>Image</t></si><si><t>Variety</t></si><si><t>Onion00007.jpg</t></si><si><t>Red</t></si></sst>'
    )
    book = tmp_path / "All Metadata.xlsx"
    with zipfile.ZipFile(book, "w") as bundle:
        bundle.writestr("xl/sharedStrings.xml", strings)
        bundle.writestr("xl/worksheets/sheet1.xml", sheet)
        bundle.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
    lookup, status = module.read_metadata_workbook(book)
    assert "1 rows" in status
    assert lookup["onion00007"]["Variety"] == "Red"


def test_missing_subset_reports_an_actionable_status(tmp_path: Path):
    subset = field_photos.load_subset(tmp_path / "absent")
    assert subset["status"] == "missing"
    assert "20254934" in subset["import_hint"]


def test_manifest_rejects_paths_outside_the_subset(tmp_path: Path):
    outside = tmp_path / "elsewhere.jpg"
    outside.write_bytes(b"nope")
    (tmp_path / "manifest.json").write_text(
        json.dumps({"schema": field_photos.SCHEMA, "images": [{"id": "evil", "file": "../elsewhere.jpg"}]}), encoding="utf-8"
    )
    subset = field_photos.load_subset(tmp_path)
    assert subset["status"] == "empty"
    assert subset["images"] == []
    assert field_photos.resolve_file(tmp_path, subset, "evil") is None


@pytest.fixture()
def client_with_subset(tmp_path: Path, monkeypatch, fake_pack: Path):
    module = load_ingest_module()
    output = tmp_path / "zenodo"
    assert run_ingest(module, ["--zip", str(fake_pack), "--output", str(output), "--limit", "4", "--skip-checksum"]) == 0
    monkeypatch.setattr(main_module, "FIELD_PHOTO_DIR", output)
    runtime = tmp_path / "runtime"
    from backend import database as db_module

    monkeypatch.setattr(db_module, "DATA_DIR", runtime)
    monkeypatch.setattr(db_module, "DB_PATH", runtime / "pyaazscan.sqlite3")
    monkeypatch.setattr(main_module, "DATA_DIR", runtime)
    with TestClient(main_module.app) as client:
        yield client, module, output


def test_gallery_endpoints_serve_subset_and_provenance(client_with_subset):
    client, _, output = client_with_subset
    gallery = client.get("/api/demo/field-photos")
    assert gallery.status_code == 200
    payload = gallery.json()
    assert payload["status"] == "ready"
    assert payload["counts"]["present"] == 4
    first = payload["images"][0]
    assert not any(key.startswith("_") for key in first), "relative paths stay server-side"
    assert first["image_url"].endswith("/image")

    full = client.get(first["image_url"])
    assert full.status_code == 200 and full.headers["content-type"] == "image/jpeg"
    thumb = client.get(f"{first['image_url']}?variant=thumb")
    assert thumb.status_code == 200 and len(thumb.content) < len(full.content)
    assert client.get("/api/demo/field-photos/no-such-photo/image").status_code == 404
    assert client.get("/api/demo/field-photos/..%2Fmanifest/image").status_code == 404
    assert client.get("/api/demo/field-photos").json()["counts"]["selected"] == len(json.loads((output / "manifest.json").read_text())["images"])


def test_field_photo_scan_records_source_and_queue_import(client_with_subset):
    client, _, _ = client_with_subset
    photo_id = client.get("/api/demo/field-photos").json()["images"][0]["id"]

    scan = client.post(f"/api/demo/field-photos/{photo_id}/scan", data={"operator": "Test officer"})
    assert scan.status_code == 200, scan.text
    inspection = scan.json()
    assert inspection["provenance"]["source"] == "zenodo_subset"
    assert inspection["provenance"]["doi"] == "10.5281/zenodo.20254934"
    assert inspection["provenance"]["licence"] == "CC-BY-4.0"
    assert inspection["calibration"]["calibrated"] is False
    detail = client.get(f"/api/inspection/{inspection['inspection_id']}").json()
    assert detail["provenance"]["source_path"].endswith(".jpg")
    audit = client.get(f"/api/audit/{inspection['inspection_id']}").json()["items"]
    assert audit[0]["payload"]["provenance"]["source"] == "zenodo_subset"

    queued = client.post("/api/demo/field-photos/to-dataset", json={"ids": [photo_id]})
    assert queued.status_code == 200 and queued.json()["imported"] == 1
    overview = client.get("/api/dataset").json()
    assert overview["items"][0]["source"] == "zenodo_subset"
    assert overview["items"][0]["label"] in {"healthy", "damaged"}

    bulk = client.post("/api/demo/field-photos/to-dataset", json={"limit": 2})
    assert bulk.json()["imported"] == 2
    assert client.post("/api/demo/field-photos/to-dataset", json={"ids": ["missing-id"]}).status_code == 404
    assert client.get("/api/dashboard").json()["field_photos"] == {"status": "ready", "count": 4, "licence": "CC-BY-4.0"}


def test_scan_still_works_without_an_imported_subset(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(main_module, "FIELD_PHOTO_DIR", tmp_path / "absent")
    runtime = tmp_path / "runtime"
    from backend import database as db_module

    monkeypatch.setattr(db_module, "DATA_DIR", runtime)
    monkeypatch.setattr(db_module, "DB_PATH", runtime / "pyaazscan.sqlite3")
    monkeypatch.setattr(main_module, "DATA_DIR", runtime)
    image = ROOT / "frontend" / "assets" / "onion-demo.png"
    with TestClient(main_module.app) as client:
        assert client.get("/api/demo/field-photos").json()["status"] == "missing"
        assert client.get("/api/demo/field-photos/whatever/image").status_code == 409
        assert client.post("/api/demo/field-photos/whatever/scan").status_code == 409
        assert client.post("/api/demo/field-photos/to-dataset", json={"limit": 5}).status_code == 409
        scan = client.post("/api/scan/image", files={"file": ("lot.png", image.read_bytes(), "image/png")}, data={"lot_id": "LOT-TEST"})
        assert scan.status_code == 200
        assert scan.json()["provenance"] == {"source": "operator_upload"}


def test_subset_shipped_under_frontend_assets_is_picked_up(tmp_path: Path, monkeypatch, fake_pack: Path):
    """A committed subset (for example on Vercel) is found without any environment variable."""
    module = load_ingest_module()
    shipped = tmp_path / "field-photos"
    assert run_ingest(module, ["--zip", str(fake_pack), "--output", str(shipped), "--limit", "2", "--skip-checksum"]) == 0
    monkeypatch.setattr(main_module, "FIELD_PHOTO_DIR", tmp_path / "not-imported-locally")
    monkeypatch.setattr(main_module, "FIELD_PHOTO_FALLBACK_DIR", shipped)
    runtime = tmp_path / "runtime"
    from backend import database as db_module

    monkeypatch.setattr(db_module, "DATA_DIR", runtime)
    monkeypatch.setattr(db_module, "DB_PATH", runtime / "pyaazscan.sqlite3")
    monkeypatch.setattr(main_module, "DATA_DIR", runtime)
    with TestClient(main_module.app) as client:
        payload = client.get("/api/demo/field-photos").json()
        assert payload["status"] == "ready" and payload["counts"]["present"] == 2
        photo_id = payload["images"][0]["id"]
        assert client.get(f"/api/demo/field-photos/{photo_id}/image").status_code == 200
        override = client.post("/api/demo/field-photos/to-dataset", json={"ids": [photo_id], "label": "undersized"})
        assert override.status_code == 200 and override.json()["images"][0]["label"] == "undersized"


def test_import_helper_reports_usage_without_arguments():
    module = load_ingest_module()
    with pytest.raises(SystemExit) as exit_info:
        run_ingest(module, [])
    assert exit_info.value.code == 2


def _stored_report_data(report_id: str) -> dict:
    from backend import database as db_module

    connection = sqlite3.connect(db_module.DB_PATH)
    try:
        raw = connection.execute("SELECT report_data_json FROM reports WHERE report_id = ?", (report_id,)).fetchone()[0]
    finally:
        connection.close()
    return json.loads(raw)


def test_report_carries_licence_attribution_for_third_party_photos(client_with_subset):
    client, _, _ = client_with_subset
    photo_id = client.get("/api/demo/field-photos").json()["images"][0]["id"]
    inspection = client.post(f"/api/demo/field-photos/{photo_id}/scan", data={"operator": "Test officer"}).json()

    report = client.post("/api/reports/generate", json={"inspection_id": inspection["inspection_id"]})
    assert report.status_code == 200, report.text
    report_id = report.json()["report_id"]
    record = client.get(f"/api/reports/{report_id}").json()
    # CC BY requires attribution wherever the photograph is reproduced, including the PDF.
    assert "10.5281/zenodo.20254934" in json.dumps(_stored_report_data(report_id)["inspection"]["provenance"])
    assert record["verified"] is True
    assert client.get(f"/api/reports/{report_id}/pdf").status_code == 200


def test_operator_upload_report_is_unchanged_by_provenance(tmp_path: Path, monkeypatch):
    """A normal upload still records a plain provenance value and a verifiable hash."""
    monkeypatch.setattr(main_module, "FIELD_PHOTO_DIR", tmp_path / "absent")
    runtime = tmp_path / "runtime"
    from backend import database as db_module

    monkeypatch.setattr(db_module, "DATA_DIR", runtime)
    monkeypatch.setattr(db_module, "DB_PATH", runtime / "pyaazscan.sqlite3")
    monkeypatch.setattr(main_module, "DATA_DIR", runtime)
    image = ROOT / "frontend" / "assets" / "onion-demo.png"
    with TestClient(main_module.app) as client:
        inspection = client.post("/api/scan/image", files={"file": ("lot.png", image.read_bytes(), "image/png")}, data={"lot_id": "LOT-PROV"}).json()
        report = client.post("/api/reports/generate", json={"inspection_id": inspection["inspection_id"]}).json()
        record = client.get(f"/api/reports/{report['report_id']}").json()
        assert _stored_report_data(report["report_id"])["inspection"]["provenance"] == {"source": "operator_upload"}
        assert record["verified"] is True
