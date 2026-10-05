"""Lightweight, explainable CV demo pipeline. Scores are heuristic evidence, not probabilities."""
from __future__ import annotations

import io
import math
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageOps

MODEL_VERSION = "HSV-CONTOUR-DEMO-0.1"
ENGINE_NAME = "Classical CV demo heuristic (not a trained model)"
CALIBRATION_MARKER_MM = 50.0


class ImageQualityError(ValueError):
    """An uploaded image cannot support even a cautious visual inspection."""


def _decode(image_bytes: bytes) -> np.ndarray:
    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            if im.width < 200 or im.height < 200:
                raise ImageQualityError("Image quality insufficient. Use a photo at least 200 × 200 pixels.")
            rgb = np.asarray(im)
    except ImageQualityError:
        raise
    except Exception as exc:
        raise ImageQualityError("This image could not be decoded. Use a JPG or PNG photo.") from exc
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _calibration(hsv: np.ndarray) -> dict[str, Any]:
    """Find the optional high-contrast blue 50 mm square reference in the demo sheet."""
    blue = cv2.inRange(hsv, np.array([94, 95, 60], np.uint8), np.array([137, 255, 255], np.uint8))
    blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = hsv.shape[0] * hsv.shape[1]
    candidates: list[tuple[float, tuple[int, int, int, int]]] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        ratio = w / max(h, 1)
        if area < max(100, image_area * 0.00015) or area > image_area * 0.16:
            continue
        if not (0.76 <= ratio <= 1.32):
            continue
        if min(w, h) < min(hsv.shape[:2]) * 0.025:
            continue
        candidates.append((area, (x, y, w, h)))
    if not candidates:
        return {
            "calibrated": False,
            "pixels_per_mm": None,
            "marker_mm": CALIBRATION_MARKER_MM,
            "method": None,
            "message": "No 50 mm reference marker detected. Physical diameter will not be inferred.",
        }
    _, (x, y, w, h) = max(candidates, key=lambda item: item[0])
    px_per_mm = (w + h) / 2.0 / CALIBRATION_MARKER_MM
    return {
        "calibrated": True,
        "pixels_per_mm": round(px_per_mm, 4),
        "marker_mm": CALIBRATION_MARKER_MM,
        "marker_bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
        "method": "Observed side of PYAazScan 50 mm blue-square reference",
        "message": "Estimated scale from one visible 50 mm marker; perspective and print-size error are not corrected.",
    }


def _base_defect_assessments() -> dict[str, dict[str, Any]]:
    return {
        key: {"detected": False, "confidence": 0.88, "score_type": "heuristic_evidence"}
        for key in ("healthy", "damaged", "rotten", "sprouted", "undersized")
    }


def analyze_image(image_bytes: bytes, rules: dict[str, Any]) -> dict[str, Any]:
    """Decode, quality-check, detect contours and extract conservative visible evidence."""
    original = _decode(image_bytes)
    image_h, image_w = original.shape[:2]
    max_dimension = 1600
    factor = min(1.0, max_dimension / max(image_h, image_w))
    if factor < 1.0:
        working = cv2.resize(original, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)
    else:
        working = original.copy()
    work_h, work_w = working.shape[:2]
    sx, sy = image_w / work_w, image_h / work_h

    gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
    laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    contrast = float(gray.std())
    warnings: list[str] = []
    if laplacian_variance < 18:
        warnings.append("Image may be out of focus; confirm the result before procurement.")
    if brightness < 38 or brightness > 240:
        warnings.append("Lighting is unusually dark or bright; colour-based defect evidence may be unreliable.")
    if contrast < 22:
        warnings.append("Low image contrast; spread onions on a contrasting, evenly lit background.")

    hsv = cv2.cvtColor(working, cv2.COLOR_BGR2HSV)
    calibration = _calibration(hsv)
    hue, saturation, value = cv2.split(hsv)
    warm_hue = (hue <= 43) | (hue >= 170)
    warm_mask = (warm_hue & (saturation >= 42) & (value >= 38)).astype(np.uint8) * 255
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    warm_mask = cv2.morphologyEx(warm_mask, cv2.MORPH_CLOSE, kernel_close)
    warm_mask = cv2.morphologyEx(warm_mask, cv2.MORPH_OPEN, kernel_open)

    contours, _ = cv2.findContours(warm_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = work_h * work_w
    min_area = max(350.0, image_area * 0.00035)
    max_area = image_area * 0.22
    candidates: list[tuple[float, np.ndarray, tuple[int, int, int, int], float, float]] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if not min_area <= area <= max_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if min(w, h) < 22:
            continue
        aspect = w / max(h, 1)
        fill = area / max(w * h, 1)
        perimeter = cv2.arcLength(contour, True)
        circularity = (4 * math.pi * area / (perimeter * perimeter)) if perimeter > 0 else 0
        if not (0.48 <= aspect <= 2.05) or fill < 0.36 or circularity < 0.20:
            continue
        candidates.append((area, contour, (x, y, w, h), circularity, fill))
    candidates.sort(key=lambda obj: (obj[2][1] // 80, obj[2][0]))

    if not candidates:
        raise ImageQualityError(
            "No onions detected. Try a well-lit photo with bulbs separated from a plain, contrasting background."
        )
    if len(candidates) > 60:
        raise ImageQualityError("Too many regions to inspect confidently. Capture a smaller, less crowded sample.")

    green = cv2.inRange(hsv, np.array([32, 55, 35], np.uint8), np.array([91, 255, 255], np.uint8))
    onions: list[dict[str, Any]] = []
    raw_boxes: list[tuple[int, int, int, int]] = []

    for sequence, (area, contour, (x, y, w, h), circularity, fill) in enumerate(candidates, start=1):
        raw_boxes.append((x, y, w, h))
        # Scale boxes/polygons back to the original EXIF-corrected source image.
        x0, y0 = max(0, int(round(x * sx))), max(0, int(round(y * sy)))
        x1, y1 = min(image_w, int(round((x + w) * sx))), min(image_h, int(round((y + h) * sy)))
        original_w, original_h = max(1, x1 - x0), max(1, y1 - y0)
        diameter_px = math.sqrt(original_w * original_h)
        diameter_mm = diameter_px / (calibration["pixels_per_mm"] * (sx + sy) / 2) if calibration["calibrated"] else None

        contour_full = contour.reshape(-1, 2).astype(np.float32)
        polygon_work = cv2.approxPolyDP(contour_full, max(1.5, cv2.arcLength(contour, True) * 0.012), True).reshape(-1, 2)
        polygon = [[int(round(px * sx)), int(round(py * sy))] for px, py in polygon_work[:100]]

        # Map evidence is collected in a padded crop to capture a sprout just above the bulb.
        pad_x = max(4, int(w * 0.16))
        pad_top = max(8, int(h * 0.42))
        crop_x0, crop_x1 = max(0, x - pad_x), min(work_w, x + w + pad_x)
        crop_y0, crop_y1 = max(0, y - pad_top), min(work_h, y + h + max(5, int(h * 0.08)))
        green_crop = green[crop_y0:crop_y1, crop_x0:crop_x1]
        green_fraction = float(cv2.countNonZero(green_crop)) / max(1, green_crop.size)
        sprout_detected = green_fraction >= 0.009
        sprout_confidence = min(0.98, 0.66 + green_fraction * 8.5) if sprout_detected else 0.90

        local_hsv = hsv[y:y + h, x:x + w]
        local_bulb = np.zeros((h, w), dtype=np.uint8)
        local_contour = contour.copy()
        local_contour[:, :, 0] -= x
        local_contour[:, :, 1] -= y
        cv2.drawContours(local_bulb, [local_contour], -1, 255, thickness=cv2.FILLED)
        erode_size = max(3, (min(w, h) // 12) | 1)
        interior = cv2.erode(local_bulb, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode_size, erode_size)))
        local_s = local_hsv[:, :, 1]
        local_v = local_hsv[:, :, 2]
        dark = ((local_v < 52) & (local_s > 35) & (interior > 0)).astype(np.uint8)
        interior_count = max(1, cv2.countNonZero(interior))
        dark_fraction = float(dark.sum()) / interior_count
        rot_detected = dark_fraction >= 0.026
        damage_detected = 0.006 <= dark_fraction < 0.026
        rot_confidence = min(0.98, 0.72 + dark_fraction * 4.2) if rot_detected else 0.91
        damage_confidence = min(0.95, 0.62 + dark_fraction * 8.5) if damage_detected else 0.89

        assessments = _base_defect_assessments()
        assessments["sprouted"] = {
            "detected": sprout_detected,
            "confidence": round(sprout_confidence, 3),
            "score_type": "heuristic_evidence",
        }
        assessments["rotten"] = {
            "detected": rot_detected,
            "confidence": round(rot_confidence, 3),
            "score_type": "heuristic_evidence",
        }
        assessments["damaged"] = {
            "detected": damage_detected,
            "confidence": round(damage_confidence, 3),
            "score_type": "heuristic_evidence",
        }

        if diameter_mm is not None:
            undersized = diameter_mm < float(rules["diameter_min_mm"])
            oversized = diameter_mm > float(rules["diameter_max_mm"])
            assessments["undersized"] = {
                "detected": undersized,
                "confidence": 0.99 if undersized else 0.90,
                "score_type": "calibrated_measurement_rule",
            }
        else:
            undersized = False
            oversized = False
            assessments["undersized"] = {
                "detected": False,
                "confidence": 0.0,
                "score_type": "not_assessable_without_scale",
            }

        # Shape and colour support score; elongated/merged regions are deliberately sent to review.
        detection_confidence = min(0.96, 0.68 + min(circularity, 0.9) * 0.24 + min(fill, 0.9) * 0.08)
        overlap_suspected = (w / max(h, 1) > 1.55 or h / max(w, 1) > 1.55 or fill < 0.47 or area > image_area * 0.075)
        if overlap_suspected:
            detection_confidence = min(detection_confidence, 0.56)
        detected_defects = [
            {"type": key, "detected": True, "confidence": value["confidence"], "score_type": value["score_type"]}
            for key, value in assessments.items()
            if key != "healthy" and value["detected"]
        ]
        if not detected_defects:
            assessments["healthy"] = {"detected": True, "confidence": round(detection_confidence, 3), "score_type": "heuristic_evidence"}
        else:
            assessments["healthy"] = {"detected": False, "confidence": round(max(0.5, 1 - max(d["confidence"] for d in detected_defects) * 0.4), 3), "score_type": "heuristic_evidence"}

        item: dict[str, Any] = {
            "onion_id": sequence,
            "bbox": {"x": x0, "y": y0, "width": original_w, "height": original_h},
            "polygon": polygon,
            "diameter_px": round(diameter_px, 1),
            "diameter_mm": round(diameter_mm, 1) if diameter_mm is not None else None,
            "size_basis": "calibrated" if diameter_mm is not None else "pixel_estimate",
            "detection_confidence": round(detection_confidence, 3),
            "evidence_type": "heuristic_evidence",
            "defect_assessments": assessments,
            "defects": detected_defects,
            "visual_flags": ["Possible overlap or irregular contour; manual verification recommended"] if overlap_suspected else [],
            "oversized": bool(oversized),
        }
        onions.append(item)

    # Flag adjacent bounding boxes; strong object-level overlap evidence reduces confidence.
    for index, onion in enumerate(onions):
        box = onion["bbox"]
        ax0, ay0 = box["x"], box["y"]
        ax1, ay1 = ax0 + box["width"], ay0 + box["height"]
        for other in onions[index + 1:]:
            other_box = other["bbox"]
            ix = max(0, min(ax1, other_box["x"] + other_box["width"]) - max(ax0, other_box["x"]))
            iy = max(0, min(ay1, other_box["y"] + other_box["height"]) - max(ay0, other_box["y"]))
            intersection = ix * iy
            union = box["width"] * box["height"] + other_box["width"] * other_box["height"] - intersection
            if union and intersection / union > 0.08:
                for affected in (onion, other):
                    affected["visual_flags"].append("Detection boxes overlap; verify onion count and grading")
                    affected["detection_confidence"] = min(affected["detection_confidence"], 0.55)

    return {
        "image_width": int(image_w),
        "image_height": int(image_h),
        "model": {
            "version": MODEL_VERSION,
            "engine": ENGINE_NAME,
            "trained_model": False,
            "metrics_available": False,
            "confidence_semantics": "Heuristic evidence score, not a calibrated probability.",
        },
        "calibration": calibration,
        "image_quality": {
            "status": "review" if warnings else "good",
            "laplacian_variance": round(laplacian_variance, 2),
            "brightness_mean": round(brightness, 1),
            "contrast_std": round(contrast, 1),
            "warnings": warnings,
        },
        "warnings": warnings.copy(),
        "onions": onions,
    }
