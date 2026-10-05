from copy import deepcopy

import pytest

from backend.services.rules_engine import DEFAULT_RULES, evaluate_onion, summarize_onions, validate_rules


def onion(diameter, defects=None, confidence=0.96):
    return {
        "diameter_mm": diameter,
        "diameter_px": 80,
        "detection_confidence": confidence,
        "defects": defects or [],
    }


def test_inclusive_diameter_boundaries_are_grade_a():
    rules = validate_rules(DEFAULT_RULES)
    assert evaluate_onion(onion(45.0), rules, calibration_available=True)["grade"] == "GRADE_A"
    assert evaluate_onion(onion(65.0), rules, calibration_available=True)["grade"] == "GRADE_A"


def test_diameter_outside_range_is_urs():
    rules = validate_rules(DEFAULT_RULES)
    assert evaluate_onion(onion(44.9), rules, calibration_available=True)["grade"] == "URS"
    assert evaluate_onion(onion(65.1), rules, calibration_available=True)["grade"] == "URS"


@pytest.mark.parametrize("defect", ["sprouted", "rotten", "damaged"])
def test_disallowed_visible_defect_is_rejected(defect):
    rules = validate_rules(DEFAULT_RULES)
    result = evaluate_onion(onion(55, [{"type": defect, "detected": True, "confidence": 0.97}]), rules, calibration_available=True)
    assert result["grade"] == "REJECT"
    assert result["decision_reasons"]


def test_high_and_assisted_evidence_bands_use_configured_threshold():
    rules = validate_rules(DEFAULT_RULES)
    assert evaluate_onion(onion(55, confidence=0.91), rules, calibration_available=True)["confidence_band"] == "high"
    assert evaluate_onion(onion(55, confidence=0.75), rules, calibration_available=True)["confidence_band"] == "assisted"


def test_missing_scale_abstains_instead_of_claiming_mm():
    rules = validate_rules(DEFAULT_RULES)
    result = evaluate_onion(onion(None), rules, calibration_available=False)
    assert result["grade"] == "MANUAL_REVIEW"
    assert "calibration" in result["decision_reasons"][0].lower()


def test_low_evidence_requires_manual_review():
    rules = validate_rules(DEFAULT_RULES)
    assert evaluate_onion(onion(55, confidence=0.59), rules, calibration_available=True)["grade"] == "MANUAL_REVIEW"


def test_summary_percentages_are_exclusive_and_cover_sample():
    onions = []
    for grade in ("GRADE_A", "URS", "REJECT", "MANUAL_REVIEW"):
        onions.append({"grade": grade, "diameter_mm": None, "defects": []})
    result = summarize_onions(onions)
    assert result["summary"]["sample_size"] == 4
    assert result["percentages"] == {"grade_a": 25.0, "urs": 25.0, "reject": 25.0, "manual_review": 25.0}
    assert sum(result["percentages"].values()) == 100


def test_invalid_rule_ranges_are_rejected():
    rules = deepcopy(DEFAULT_RULES)
    rules["diameter_min_mm"] = 66
    rules["diameter_max_mm"] = 65
    with pytest.raises(ValueError):
        validate_rules(rules)
