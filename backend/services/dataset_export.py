"""Export reviewed polygon labels into a YOLO-seg bundle while retaining multi-label source JSON."""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

CLASS_NAMES = ["healthy", "damaged", "rotten", "sprouted", "undersized"]


def _oriented_copy(source: Path, destination: Path) -> tuple[int, int]:
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        width, height = image.size
        suffix = destination.suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            image.save(destination, format="JPEG", quality=95, optimize=True)
        elif suffix == ".webp":
            image.save(destination, format="WEBP", quality=95, method=4)
        else:
            image.save(destination, format="PNG", optimize=True)
    return width, height


def _yolo_rows(objects: list[dict[str, Any]], width: int, height: int) -> list[str]:
    rows: list[str] = []
    class_to_index = {name: index for index, name in enumerate(CLASS_NAMES)}
    for obj in objects:
        polygon = obj["polygon"]
        normalized = [(max(0.0, min(1.0, float(x) / width)), max(0.0, min(1.0, float(y) / height))) for x, y in polygon]
        for label in sorted(set(obj["labels"])):
            if label not in class_to_index:
                raise ValueError(f"Unsupported class label in annotation: {label}")
            coordinates = " ".join(f"{value:.6f}" for point in normalized for value in point)
            rows.append(f"{class_to_index[label]} {coordinates}")
    return rows


def write_yolo_seg_bundle(records: list[dict[str, Any]], extracted_dir: Path, archive_path: Path) -> dict[str, Any]:
    """Create actual image, segmentation-label, YAML and native annotation files."""
    if not records:
        raise ValueError("No complete annotated images were selected for export.")
    extracted_dir.mkdir(parents=True, exist_ok=False)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    native_manifest: list[dict[str, Any]] = []
    split_counts = {"train": 0, "validation": 0, "test": 0}
    try:
        for record in records:
            split = record["split"]
            if split not in split_counts:
                raise ValueError(f"Invalid dataset split: {split}")
            image_source = Path(record["image_path"])
            if not image_source.is_file():
                raise ValueError(f"Image file is missing for dataset record {record['id']}.")
            suffix = image_source.suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
                suffix = ".png"
            filename = f"{record['id']}{suffix}"
            image_dir = extracted_dir / "images" / split
            label_dir = extracted_dir / "labels" / split
            image_dir.mkdir(parents=True, exist_ok=True)
            label_dir.mkdir(parents=True, exist_ok=True)
            width, height = _oriented_copy(image_source, image_dir / filename)
            objects = record["objects"]
            label_lines = _yolo_rows(objects, width, height)
            (label_dir / f"{Path(filename).stem}.txt").write_text("\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8")
            native_manifest.append({"image": f"images/{split}/{filename}", "width": width, "height": height, "split": split, "lot_id": record.get("lot_id", ""), "procurement_centre": record.get("procurement_centre", ""), "annotator": record["annotator"], "annotation_version": record["annotation_version"], "objects": objects})
            split_counts[split] += 1

        yaml_lines = ["# Generated from operator-saved polygon annotations. Review labels and split provenance.", "path: .", "train: images/train", "val: images/validation"]
        if split_counts["test"]:
            yaml_lines.append("test: images/test")
        yaml_lines.append("names:")
        for index, name in enumerate(CLASS_NAMES):
            yaml_lines.append(f"  {index}: {name}")
        (extracted_dir / "data.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
        (extracted_dir / "annotations.json").write_text(json.dumps({"schema": "pyaazscan-polygon-multilabel-v1", "class_names": CLASS_NAMES, "images": native_manifest}, indent=2, ensure_ascii=False), encoding="utf-8")
        (extracted_dir / "CONVERSION_NOTES.txt").write_text(
            "YOLO-seg labels use one class id per polygon row. If an onion has multiple labels, this export repeats the same polygon once per label. "
            "The original multi-label annotation is retained in annotations.json. Review this conversion before training; a custom multi-label mask head may be more appropriate.\n",
            encoding="utf-8",
        )
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
            for path in sorted(extracted_dir.rglob("*")):
                if path.is_file():
                    bundle.write(path, arcname=path.relative_to(extracted_dir).as_posix())
    except Exception:
        shutil.rmtree(extracted_dir, ignore_errors=True)
        archive_path.unlink(missing_ok=True)
        raise
    return {"image_count": len(records), "split_counts": split_counts, "classes": CLASS_NAMES}
