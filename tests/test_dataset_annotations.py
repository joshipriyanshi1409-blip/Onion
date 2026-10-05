from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import sqlite3
import zipfile

from fastapi.testclient import TestClient
from PIL import Image

from backend import database as db_module
from backend import main as main_module


def _configure_runtime(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(db_module, "DATA_DIR", runtime)
    monkeypatch.setattr(db_module, "DB_PATH", runtime / "pyaazscan.sqlite3")
    monkeypatch.setattr(main_module, "DATA_DIR", runtime)
    return runtime


def _image_bytes(color=(184, 112, 55)):
    image = Image.new("RGB", (120, 90), "#e8e5d9")
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    draw.ellipse((25, 16, 89, 78), fill=color, outline="#70452d", width=2)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _upload(client: TestClient, name: str):
    response = client.post(
        "/api/dataset/images",
        files={"file": (name, _image_bytes(), "image/png")},
        data={"label": "healthy"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _annotation(*, lot: str, centre: str, split: str, annotator: str, labels=None):
    return {
        "annotator": annotator,
        "status": "complete",
        "split": split,
        "lot_id": lot,
        "procurement_centre": centre,
        "objects": [{
            "onion_id": 1,
            "labels": labels or ["healthy"],
            "polygon": [[28, 20], [85, 24], [82, 70], [33, 73]],
            "notes": "Visible surface only",
        }],
    }


def test_polygon_revisions_and_multilabel_yolo_export(tmp_path, monkeypatch):
    runtime = _configure_runtime(tmp_path, monkeypatch)
    with TestClient(main_module.app) as client:
        train_image = _upload(client, "train-lot.png")
        validation_image = _upload(client, "validation-lot.png")

        saved = client.put(
            f"/api/dataset/images/{train_image['id']}/annotations",
            json=_annotation(lot="LOT-TRAIN-1", centre="Centre North", split="train", annotator="Operator A", labels=["healthy", "damaged"]),
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["version"] == 1

        revised = client.put(
            f"/api/dataset/images/{train_image['id']}/annotations",
            json=_annotation(lot="LOT-TRAIN-1", centre="Centre North", split="train", annotator="Reviewer B", labels=["healthy", "damaged"]),
        )
        assert revised.status_code == 200, revised.text
        assert revised.json()["version"] == 2

        validation_saved = client.put(
            f"/api/dataset/images/{validation_image['id']}/annotations",
            json=_annotation(lot="LOT-VALID-1", centre="Centre South", split="validation", annotator="Operator C"),
        )
        assert validation_saved.status_code == 200, validation_saved.text

        detail = client.get(f"/api/dataset/images/{train_image['id']}")
        assert detail.status_code == 200
        item = detail.json()
        assert item["annotation_status"] == "complete"
        assert item["annotation_version"] == 2
        assert item["annotation_count"] == 1
        assert [entry["version"] for entry in item["annotation_history"]] == [2, 1]
        assert item["annotations"]["annotator"] == "Reviewer B"
        assert item["lot_id"] == "LOT-TRAIN-1"
        assert item["split"] == "train"

        source = client.get(item["image_url"])
        assert source.status_code == 200
        assert source.headers["content-type"] == "image/png"
        assert "inline" in source.headers.get("content-disposition", "")

        overview = client.get("/api/dataset").json()
        assert overview["annotated_images"] == 2
        assert overview["annotated_onions"] == 2
        assert overview["splits"]["train"] == 1
        assert overview["splits"]["validation"] == 1

        exported = client.post("/api/dataset/export")
        assert exported.status_code == 200, exported.text
        manifest = exported.json()
        assert manifest["image_count"] == 2
        assert manifest["split_counts"] == {"train": 1, "validation": 1, "test": 0}
        assert "native multi-label" in manifest["message"]

        download = client.get(manifest["download_url"])
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(BytesIO(download.content)) as archive:
            names = set(archive.namelist())
            assert "data.yaml" in names
            assert "annotations.json" in names
            assert "CONVERSION_NOTES.txt" in names
            label_path = f"labels/train/{train_image['id']}.txt"
            rows = archive.read(label_path).decode("utf-8").strip().splitlines()
            assert len(rows) == 2  # YOLO gets one class row per class on the same polygon.
            assert {int(row.split()[0]) for row in rows} == {0, 1}
            native = json.loads(archive.read("annotations.json"))
            train_record = next(entry for entry in native["images"] if entry["split"] == "train")
            assert train_record["annotation_version"] == 2
            assert train_record["annotator"] == "Reviewer B"
            assert train_record["objects"][0]["labels"] == ["damaged", "healthy"]
            assert train_record["lot_id"] == "LOT-TRAIN-1"
            assert "repeats the same polygon once per label" in archive.read("CONVERSION_NOTES.txt").decode()

        exported_overview = client.get("/api/dataset").json()
        export_row = next(row for row in exported_overview["archives"] if row["id"] == manifest["export_id"])
        assert export_row["download_url"] == manifest["download_url"]
        assert Path(runtime / "archives" / manifest["export_id"].lower() / "data.yaml").is_file()


def test_annotation_validation_and_lot_split_leakage_guard(tmp_path, monkeypatch):
    _configure_runtime(tmp_path, monkeypatch)
    with TestClient(main_module.app) as client:
        first = _upload(client, "same-lot-a.png")
        second = _upload(client, "same-lot-b.png")

        missing_annotator = _annotation(lot="LOT-SHARED", centre="Centre West", split="train", annotator=" ")
        response = client.put(f"/api/dataset/images/{first['id']}/annotations", json=missing_annotator)
        assert response.status_code == 422
        assert "annotator name or operator ID" in response.json()["detail"]
        missing_provenance = _annotation(lot="", centre="Centre West", split="train", annotator="Annotator")
        response = client.put(f"/api/dataset/images/{first['id']}/annotations", json=missing_provenance)
        assert response.status_code == 422
        assert "lot ID and procurement centre" in response.json()["detail"]

        invalid_polygon = _annotation(lot="LOT-SHARED", centre="Centre West", split="train", annotator="Annotator")
        invalid_polygon["objects"][0]["polygon"][0] = [-1, 20]
        bad = client.put(f"/api/dataset/images/{first['id']}/annotations", json=invalid_polygon)
        assert bad.status_code == 422
        assert "inside the source image" in bad.json()["detail"]
        assert client.get(f"/api/dataset/images/{first['id']}").json()["annotation_version"] == 0

        for image, split, centre in ((first, "train", "Centre West"), (second, "validation", "centre west")):
            response = client.put(
                f"/api/dataset/images/{image['id']}/annotations",
                json=_annotation(lot="LOT-SHARED", centre=centre, split=split, annotator="Annotator"),
            )
            assert response.status_code == 200, response.text

        exported = client.post("/api/dataset/export")
        assert exported.status_code == 409
        assert "Lot leakage guard" in exported.json()["detail"]


def test_dataset_export_requires_train_and_validation_and_nonempty_complete_objects(tmp_path, monkeypatch):
    _configure_runtime(tmp_path, monkeypatch)
    with TestClient(main_module.app) as client:
        image = _upload(client, "train-only.png")
        no_objects = _annotation(lot="LOT-ONLY", centre="Centre East", split="train", annotator="Annotator")
        no_objects["objects"] = []
        rejected = client.put(f"/api/dataset/images/{image['id']}/annotations", json=no_objects)
        assert rejected.status_code == 422
        assert "at least one onion polygon" in rejected.json()["detail"]

        saved = client.put(
            f"/api/dataset/images/{image['id']}/annotations",
            json=_annotation(lot="LOT-ONLY", centre="Centre East", split="train", annotator="Annotator"),
        )
        assert saved.status_code == 200
        exported = client.post("/api/dataset/export")
        assert exported.status_code == 409
        assert "at least one complete train image and one complete validation image" in exported.json()["detail"]


def test_javascript_and_frontend_routes_are_available(tmp_path, monkeypatch):
    _configure_runtime(tmp_path, monkeypatch)
    with TestClient(main_module.app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "Polygon annotation studio" in page.text or "app.js" in page.text
        script = client.get("/app.js")
        assert script.status_code == 200
        assert "finish-annotation-polygon" in script.text
        assert "export-dataset" in script.text


def test_existing_dataset_images_table_receives_metadata_migration(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    db_path = runtime / "pyaazscan.sqlite3"
    runtime.mkdir()
    monkeypatch.setattr(db_module, "DATA_DIR", runtime)
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE dataset_images (id TEXT PRIMARY KEY,file_name TEXT NOT NULL,image_path TEXT NOT NULL,label TEXT NOT NULL,split TEXT NOT NULL DEFAULT 'unassigned',source TEXT NOT NULL DEFAULT 'operator_upload',created_at TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO dataset_images(id,file_name,image_path,label,split,source,created_at) VALUES(?,?,?,?,?,?,?)",
            ("legacy-image", "legacy.png", "/tmp/legacy.png", "healthy", "unassigned", "operator_upload", "2025-01-01T00:00:00Z"),
        )

    db_module.init_db()
    with db_module.database() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(dataset_images)").fetchall()}
        legacy = connection.execute("SELECT lot_id,procurement_centre FROM dataset_images WHERE id='legacy-image'").fetchone()
        annotation_table = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dataset_annotations'").fetchone()
    assert {"lot_id", "procurement_centre"}.issubset(columns)
    assert tuple(legacy) == ("", "")
    assert annotation_table is not None
