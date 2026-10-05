from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from backend.services.rules_engine import DEFAULT_RULES, evaluate_onion
from ml.inference.pipeline import ImageQualityError, MODEL_VERSION, analyze_image

DEMO = Path(__file__).resolve().parents[1] / "frontend" / "assets" / "onion-demo.png"


def test_demo_pipeline_finds_instances_scale_and_visible_cues():
    result = analyze_image(DEMO.read_bytes(), DEFAULT_RULES)
    assert result["model"]["version"] == MODEL_VERSION
    assert result["model"]["trained_model"] is False
    assert result["calibration"]["calibrated"] is True
    assert result["calibration"]["pixels_per_mm"] > 0
    assert len(result["onions"]) == 8
    labels = {defect["type"] for item in result["onions"] for defect in item["defects"]}
    assert {"sprouted", "rotten", "damaged", "undersized"}.issubset(labels)
    assert all(item["diameter_mm"] is not None for item in result["onions"])
    assert all(0 <= item["detection_confidence"] <= 1 for item in result["onions"])


def test_missing_marker_does_not_invent_physical_diameter():
    image = Image.open(DEMO).convert("RGB")
    # Remove the marker and the unrelated bottom margin, retaining several test bulbs.
    image = image.crop((0, 0, 760, 520))
    from io import BytesIO
    output = BytesIO()
    image.save(output, format="PNG")
    result = analyze_image(output.getvalue(), DEFAULT_RULES)
    assert result["calibration"]["calibrated"] is False
    assert all(item["diameter_mm"] is None for item in result["onions"])
    for item in result["onions"]:
        decision = evaluate_onion(item, DEFAULT_RULES, calibration_available=False)
        if not any(d["type"] in {"sprouted", "rotten", "damaged"} for d in item["defects"]):
            assert decision["grade"] == "MANUAL_REVIEW"


def test_blank_image_reports_no_onions():
    image = Image.new("RGB", (480, 320), (240, 240, 240))
    from io import BytesIO
    output = BytesIO()
    image.save(output, format="PNG")
    with pytest.raises(ImageQualityError, match="No onions detected"):
        analyze_image(output.getvalue(), DEFAULT_RULES)


def test_too_small_image_is_rejected():
    image = Image.new("RGB", (80, 80), (220, 100, 60))
    from io import BytesIO
    output = BytesIO()
    image.save(output, format="PNG")
    with pytest.raises(ImageQualityError, match="at least 200"):
        analyze_image(output.getvalue(), DEFAULT_RULES)
