"""Versioned procurement decisions, kept deliberately independent of image inference."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_RULES: dict[str, Any] = {
    "rule_set_id": "DEMO_45_65",
    "version": "1.0.0",
    "name": "Illustrative buyer profile (editable)",
    "diameter_min_mm": 45.0,
    "diameter_max_mm": 65.0,
    "sprouting_allowed": False,
    "rotten_allowed": False,
    "mechanical_damage_allowed": False,
    "require_calibration": True,
    "high_confidence_threshold": 0.90,
    "manual_review_threshold": 0.60,
    "notes": "Demo engineering assumption, not an approved or universal procurement specification. Confirm the current buyer/tender rule before use.",
}

_ALLOWED_GRADES = {"GRADE_A", "URS", "REJECT"}


def validate_rules(candidate: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a saved buyer profile without silently changing policy."""
    merged = {**deepcopy(DEFAULT_RULES), **candidate}
    minimum = float(merged["diameter_min_mm"])
    maximum = float(merged["diameter_max_mm"])
    high = float(merged["high_confidence_threshold"])
    review = float(merged["manual_review_threshold"])
    if not (0 < minimum < maximum <= 500):
        raise ValueError("Diameter limits must be positive and minimum must be below maximum.")
    if not (0.5 <= review < high <= 1.0):
        raise ValueError("Confidence thresholds must satisfy 0.5 ≤ manual-review threshold < high-confidence threshold ≤ 1.0.")
    merged.update({
        "rule_set_id": str(merged["rule_set_id"])[:64],
        "version": str(merged["version"])[:32],
        "name": str(merged["name"])[:120],
        "diameter_min_mm": minimum,
        "diameter_max_mm": maximum,
        "sprouting_allowed": bool(merged["sprouting_allowed"]),
        "rotten_allowed": bool(merged["rotten_allowed"]),
        "mechanical_damage_allowed": bool(merged["mechanical_damage_allowed"]),
        "require_calibration": bool(merged["require_calibration"]),
        "high_confidence_threshold": high,
        "manual_review_threshold": review,
        "notes": str(merged.get("notes", ""))[:1000],
    })
    return merged


def evaluate_onion(
    onion: dict[str, Any],
    rules: dict[str, Any],
    *,
    calibration_available: bool,
) -> dict[str, Any]:
    """Apply policy to extracted evidence; never infer the policy from the model."""
    reasons: list[str] = []
    detected = {item["type"]: item for item in onion.get("defects", []) if item.get("detected")}
    evidence = float(onion.get("detection_confidence", 0.0))
    weak_defects = [
        item for item in detected.values()
        if float(item.get("confidence", 0.0)) < rules["manual_review_threshold"]
    ]
    if evidence < rules["manual_review_threshold"] or weak_defects:
        reasons.append("Visual evidence is ambiguous or below the configured review threshold")
        return _decision("MANUAL_REVIEW", reasons, onion, high_confidence_threshold=rules["high_confidence_threshold"])

    # Critical visual defects are independently actionable even if no size reference exists.
    if "rotten" in detected and not rules["rotten_allowed"]:
        reasons.append("Visible rot detected; this profile does not allow rot")
    if "sprouted" in detected and not rules["sprouting_allowed"]:
        reasons.append("Sprouting detected; this profile does not allow sprouting")
    if "damaged" in detected and not rules["mechanical_damage_allowed"]:
        reasons.append("Visible mechanical damage detected; this profile does not allow it")
    if reasons:
        return _decision("REJECT", reasons, onion, high_confidence_threshold=rules["high_confidence_threshold"])

    diameter = onion.get("diameter_mm")
    if rules["require_calibration"] and not calibration_available:
        reasons.append("Physical diameter is unavailable; size rule needs a calibration reference")
        return _decision("MANUAL_REVIEW", reasons, onion, provisional="URS", high_confidence_threshold=rules["high_confidence_threshold"])
    if diameter is None:
        reasons.append("Diameter could not be measured in millimetres")
        return _decision("MANUAL_REVIEW", reasons, onion, provisional="URS", high_confidence_threshold=rules["high_confidence_threshold"])

    diameter = float(diameter)
    if diameter < rules["diameter_min_mm"]:
        reasons.append(
            f"Diameter {diameter:.1f} mm is below the configured minimum of {rules['diameter_min_mm']:.1f} mm"
        )
        return _decision("URS", reasons, onion, high_confidence_threshold=rules["high_confidence_threshold"])
    if diameter > rules["diameter_max_mm"]:
        reasons.append(
            f"Diameter {diameter:.1f} mm is above the configured maximum of {rules['diameter_max_mm']:.1f} mm"
        )
        return _decision("URS", reasons, onion, high_confidence_threshold=rules["high_confidence_threshold"])
    if "damaged" in detected:
        reasons.append("Visible damage requires an assisted URS decision under this profile")
        return _decision("URS", reasons, onion, high_confidence_threshold=rules["high_confidence_threshold"])
    reasons.append("Measured diameter is in range and no disallowed visible defect was detected")
    return _decision("GRADE_A", reasons, onion, high_confidence_threshold=rules["high_confidence_threshold"])


def _decision(
    grade: str,
    reasons: list[str],
    onion: dict[str, Any],
    provisional: str | None = None,
    high_confidence_threshold: float = 0.90,
) -> dict[str, Any]:
    evidence = round(float(onion.get("detection_confidence", 0.0)), 3)
    band = "manual_review" if grade == "MANUAL_REVIEW" else ("high" if evidence >= high_confidence_threshold else "assisted")
    return {
        "grade": grade,
        "decision_reasons": reasons,
        "manual_review": grade == "MANUAL_REVIEW",
        "provisional_grade": provisional,
        "evidence_confidence": evidence,
        "confidence_band": band,
    }


def summarize_onions(onions: list[dict[str, Any]]) -> dict[str, Any]:
    """Produce mutually-exclusive counts/percentages, diameter stats, and visible defect counts."""
    total = len(onions)
    grades = {"GRADE_A": 0, "URS": 0, "REJECT": 0, "MANUAL_REVIEW": 0}
    defect_distribution: dict[str, int] = {}
    diameters: list[float] = []
    for onion in onions:
        grade = onion.get("grade", "MANUAL_REVIEW")
        grades[grade if grade in grades else "MANUAL_REVIEW"] += 1
        if onion.get("diameter_mm") is not None:
            diameters.append(float(onion["diameter_mm"]))
        for defect in onion.get("defects", []):
            if defect.get("detected"):
                key = str(defect.get("type", "other"))
                defect_distribution[key] = defect_distribution.get(key, 0) + 1

    def percent(n: int) -> float:
        return round(n * 100.0 / total, 2) if total else 0.0

    import statistics
    statistics_block: dict[str, Any] = {
        "mean_diameter_mm": round(statistics.fmean(diameters), 2) if diameters else None,
        "median_diameter_mm": round(statistics.median(diameters), 2) if diameters else None,
        "minimum_diameter_mm": round(min(diameters), 2) if diameters else None,
        "maximum_diameter_mm": round(max(diameters), 2) if diameters else None,
        "measured_count": len(diameters),
        "size_basis": "calibrated millimetres" if diameters else "pixel estimates only; no physical scale",
    }
    summary = {
        "grade_a": grades["GRADE_A"],
        "urs": grades["URS"],
        "reject": grades["REJECT"],
        "manual_review": grades["MANUAL_REVIEW"],
        "sample_size": total,
    }
    percentages = {
        "grade_a": percent(grades["GRADE_A"]),
        "urs": percent(grades["URS"]),
        "reject": percent(grades["REJECT"]),
        "manual_review": percent(grades["MANUAL_REVIEW"]),
    }
    return {
        "summary": summary,
        "percentages": percentages,
        "statistics": statistics_block,
        "defect_distribution": dict(sorted(defect_distribution.items())),
    }
