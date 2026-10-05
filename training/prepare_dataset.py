#!/usr/bin/env python3
"""Structurally validate a YOLO-seg data manifest without inventing labels or splits."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp", ".dng", ".mpo"}
MAX_MANIFEST_BYTES = 1 * 1024 * 1024


def _split_entries(value: Any, split: str) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value]
    if isinstance(value, list) and value and all(isinstance(item, str) and item.strip() for item in value):
        return value
    raise ValueError(f"Dataset YAML '{split}' must be a non-empty path or list of paths.")


def _resolve_split_entry(entry: str, dataset_root: Path) -> Path:
    path = Path(entry).expanduser()
    return path.resolve() if path.is_absolute() else (dataset_root / path).resolve()


def _count_images(target: Path) -> int:
    if target.is_file() and target.suffix.lower() in IMAGE_SUFFIXES:
        return 1
    if target.is_file() and target.suffix.lower() == ".txt":
        count = 0
        for line in target.read_text(encoding="utf-8").splitlines():
            value = line.strip()
            if not value:
                continue
            item = Path(value).expanduser()
            image_path = item.resolve() if item.is_absolute() else (target.parent / item).resolve()
            if not image_path.is_file():
                raise ValueError(f"Image listed in {target.name} does not exist: {image_path}")
            if image_path.suffix.lower() not in IMAGE_SUFFIXES:
                raise ValueError(f"Unsupported image listed in {target.name}: {image_path.name}")
            count += 1
        return count
    if target.is_dir():
        return sum(1 for item in target.rglob("*") if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES)
    return 0


def validate_data_yaml(config_path: Path) -> dict[str, Any]:
    """Check manifest structure and that train/validation image paths exist."""
    config = config_path.expanduser().resolve()
    if not config.is_file() or config.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError("--data must point to an existing .yaml/.yml dataset manifest.")
    if config.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Dataset YAML exceeds the 1 MiB safety limit.")
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to validate a data.yaml; install the project requirements.") from exc

    try:
        data = yaml.safe_load(config.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Dataset YAML could not be parsed safely: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Dataset YAML must contain a mapping of paths and class names.")
    if "names" not in data and "nc" not in data:
        raise ValueError("Dataset YAML must define class names or nc.")
    names = data.get("names")
    if names is not None and (not isinstance(names, (list, dict)) or not names):
        raise ValueError("Dataset YAML 'names' must be a non-empty list or mapping.")
    if names is None and (not isinstance(data.get("nc"), int) or data["nc"] < 1):
        raise ValueError("Dataset YAML 'nc' must be a positive integer when names are omitted.")

    configured_root = data.get("path", str(config.parent))
    if not isinstance(configured_root, str) or not configured_root.strip():
        raise ValueError("Dataset YAML 'path' must be a non-empty directory path.")
    root_path = Path(configured_root).expanduser()
    dataset_root = root_path.resolve() if root_path.is_absolute() else (config.parent / root_path).resolve()
    if not dataset_root.is_dir():
        raise ValueError(f"Dataset root does not exist: {dataset_root}")

    split_counts: dict[str, int] = {}
    for split in ("train", "val"):
        entries = _split_entries(data.get(split), split)
        count = 0
        for entry in entries:
            target = _resolve_split_entry(entry, dataset_root)
            if not target.exists():
                raise ValueError(f"Dataset {split} path does not exist: {target}")
            count += _count_images(target)
        if count < 1:
            raise ValueError(f"Dataset {split} path contains no supported images.")
        split_counts[split] = count
    return {"config": str(config), "dataset_root": str(dataset_root), "image_counts": split_counts, "class_count": len(names) if names is not None else data["nc"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="Path to the dataset's YOLO data.yaml")
    args = parser.parse_args()
    try:
        result = validate_data_yaml(args.data)
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Dataset manifest looks structurally valid: {result['config']}")
    print(f"Images found: train={result['image_counts']['train']}, val={result['image_counts']['val']}")
    print("This check does not validate polygon quality, class balance, leakage, or label correctness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
