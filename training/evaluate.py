#!/usr/bin/env python3
"""Evaluate trained weights with actual YOLO val metrics; never supplies demo metrics."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def metric_value(container: Any, name: str) -> float | None:
    value = container.get(name) if isinstance(container, dict) else getattr(container, name, None)
    try:
        numeric = float(value) if value is not None else None
        return numeric if numeric is not None and math.isfinite(numeric) else None
    except (TypeError, ValueError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--project", type=Path, default=Path("data/training-runs/evaluation"))
    args = parser.parse_args()
    if not args.weights.is_file() or not args.data.is_file():
        parser.error("Both --weights and --data must exist.")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Install the optional ultralytics dependency to run evaluation.") from exc
    model = YOLO(str(args.weights))
    result = model.val(data=str(args.data.resolve()), imgsz=args.image_size, project=str(args.project.resolve()), plots=True)
    box = getattr(result, "box", None)
    seg = getattr(result, "seg", None)
    confusion = getattr(result, "confusion_matrix", None)
    raw_matrix = getattr(confusion, "matrix", None) if confusion is not None else None
    matrix_values = raw_matrix.tolist() if hasattr(raw_matrix, "tolist") else None
    names = getattr(model, "names", {})
    if isinstance(names, dict):
        class_names = [str(names.get(index, names.get(str(index), index))) for index in range(len(names))]
    elif isinstance(names, (list, tuple)):
        class_names = [str(name) for name in names]
    else:
        class_names = []
    matrix_labels = class_names + (["background"] if matrix_values and len(matrix_values) == len(class_names) + 1 else [])
    metrics = {
        "status": "evaluation_run",
        "weights": str(args.weights.resolve()),
        "dataset": str(args.data.resolve()),
        "split": "validation (as configured by dataset yaml)",
        "box": {"precision": metric_value(box, "mp"), "recall": metric_value(box, "mr"), "map50": metric_value(box, "map50"), "map50_95": metric_value(box, "map")},
        "segmentation": {"precision": metric_value(seg, "mp"), "recall": metric_value(seg, "mr"), "map50": metric_value(seg, "map50"), "map50_95": metric_value(seg, "map")},
        "fitness": metric_value(getattr(result, "results_dict", {}), "fitness"),
        "confusion_matrix": {"labels": matrix_labels, "matrix": matrix_values} if matrix_values is not None else None,
        "diameter_mae_mm": None,
        "note": "Metrics are from this exact validation run; diameter MAE requires separate calibrated ground-truth measurements.",
    }
    args.project.mkdir(parents=True, exist_ok=True)
    destination = args.project / "metrics.json"
    destination.write_text(json.dumps(metrics, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Saved {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
