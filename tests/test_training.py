from __future__ import annotations

import builtins
from io import BytesIO
from pathlib import Path
import sqlite3
import zipfile

from fastapi.testclient import TestClient
import pytest

from backend import database as db_module
from backend import main as main_module
from training.prepare_dataset import validate_data_yaml


def _configure_runtime(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(db_module, "DATA_DIR", runtime)
    monkeypatch.setattr(db_module, "DB_PATH", runtime / "pyaazscan.sqlite3")
    monkeypatch.setattr(main_module, "DATA_DIR", runtime)
    return runtime


def _dataset_zip(*, include_images: bool) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("data.yaml", "path: .\ntrain: images/train\nval: images/validation\nnames:\n  0: onion\n")
        if include_images:
            archive.writestr("images/train/train.jpg", b"train-image-placeholder")
            archive.writestr("images/validation/validation.jpg", b"validation-image-placeholder")
    return output.getvalue()


def test_manifest_validation_checks_splits_and_images(tmp_path):
    root = tmp_path / "dataset"
    for split in ("train", "validation"):
        folder = root / "images" / split
        folder.mkdir(parents=True)
        (folder / f"{split}.jpg").write_bytes(b"image placeholder")
    config = root / "data.yaml"
    config.write_text("path: .\ntrain: images/train\nval: images/validation\nnames: [onion]\n", encoding="utf-8")

    result = validate_data_yaml(config)
    assert result["image_counts"] == {"train": 1, "val": 1}
    assert result["class_count"] == 1

    config.write_text("train: images/train\nval: images/missing\nnames: [onion]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="val path does not exist"):
        validate_data_yaml(config)


def test_training_api_validates_manifest_before_optional_trainer(tmp_path, monkeypatch):
    runtime = _configure_runtime(tmp_path, monkeypatch)
    with TestClient(main_module.app) as client:
        invalid = client.post("/api/dataset/upload", files={"file": ("missing-images.zip", _dataset_zip(include_images=False), "application/zip")})
        assert invalid.status_code == 200, invalid.text
        rejected = client.post("/api/training/start", json={"epochs": 1})
        assert rejected.status_code == 409
        assert "path does not exist" in rejected.json()["detail"]

        valid = client.post("/api/dataset/upload", files={"file": ("ready-images.zip", _dataset_zip(include_images=True), "application/zip")})
        assert valid.status_code == 200, valid.text
        valid_yaml = runtime / "archives" / valid.json()["id"] / "data.yaml"
        real_import = builtins.__import__

        def block_optional_trainer(name, *args, **kwargs):
            if name == "ultralytics" or name.startswith("ultralytics."):
                raise ImportError("simulated missing optional dependency")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", block_optional_trainer)
        missing_extra = client.post("/api/training/start", json={"epochs": 1, "dataset_yaml": str(valid_yaml)})
        assert missing_extra.status_code == 409
        assert "Training is not installed" in missing_extra.json()["detail"]

    connection = sqlite3.connect(runtime / "pyaazscan.sqlite3")
    try:
        jobs = connection.execute("SELECT COUNT(*) FROM training_jobs").fetchone()[0]
    finally:
        connection.close()
    assert jobs == 0
