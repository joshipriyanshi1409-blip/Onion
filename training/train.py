#!/usr/bin/env python3
"""Train an optional Ultralytics YOLO instance-segmentation model on reviewed labels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path, help="Validated YOLO segmentation data.yaml")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--weights", default="yolo11n-seg.pt", help="Small replaceable starting checkpoint")
    parser.add_argument("--project", type=Path, default=Path("data/training-runs"))
    parser.add_argument("--name", default="pyaazscan-yolo-seg")
    args = parser.parse_args()
    if not args.data.is_file():
        parser.error("The dataset manifest does not exist.")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Optional training dependency missing. Install ultralytics to run training; the UI inference fallback is unaffected.") from exc
    model = YOLO(args.weights)
    result = model.train(
        data=str(args.data.resolve()),
        epochs=args.epochs,
        imgsz=args.image_size,
        batch=args.batch_size,
        lr0=args.learning_rate,
        project=str(args.project.resolve()),
        name=args.name,
        exist_ok=True,
        task="segment",
        plots=True,
    )
    save_dir = Path(getattr(result, "save_dir", args.project / args.name))
    summary = {
        "status": "training_complete",
        "weights": str(save_dir / "weights" / "best.pt"),
        "run_directory": str(save_dir),
        "dataset": str(args.data.resolve()),
        "parameters": {"epochs": args.epochs, "image_size": args.image_size, "batch_size": args.batch_size, "learning_rate": args.learning_rate},
    }
    (save_dir / "pyaazscan_run.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
