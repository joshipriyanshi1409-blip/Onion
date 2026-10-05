#!/usr/bin/env python3
"""Export an evaluated Ultralytics checkpoint to an edge-friendly format."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--format", choices=("onnx", "tflite", "torchscript", "engine"), default="onnx")
    parser.add_argument("--image-size", type=int, default=640)
    args = parser.parse_args()
    if not args.weights.is_file():
        parser.error("Checkpoint does not exist.")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Install the optional ultralytics dependency to export a model.") from exc
    model = YOLO(str(args.weights))
    exported = model.export(format=args.format, imgsz=args.image_size)
    print(f"Exported model: {exported}")
    print("Validate parity, latency, memory, class mapping, and calibration on target devices before deployment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
