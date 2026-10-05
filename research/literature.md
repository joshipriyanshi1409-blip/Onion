# Research notes

## Problem framing

Procurement grading depends on observable condition, market-specific size ranges, tolerances, sampling, and the applicable buyer specification. A photo can document visible evidence and reduce variation in measurements, but it cannot replace destructive, tactile, laboratory, or statistically representative sampling where those are required.

## Visible cues in the prototype

The modular demonstration pipeline extracts candidate bulb regions from colour/saturation, estimates an ellipse diameter, and scores green sprout-like pixels and dark surface patches. These are transparent image-processing heuristics, not a trained detector/classifier and not calibrated probabilities. Lighting, background, cultivar colour, soil, skin, camera white balance, overlap, and compression can all change the evidence. The system abstains when calibration or evidence is insufficient.

Onion sprouting and decay are documented postharvest quality concerns in the cited review. Published image-classification work illustrates that RGB/CNN approaches are being explored, but reported metrics belong to the cited study's particular data and evaluation protocol. No performance number from another paper is attributed to this repository.

## Computer-vision approach

1. Decode and quality-check a still RGB image.
2. Look for the included high-contrast 50 mm blue-square reference; otherwise retain pixel measurements and label physical size unavailable.
3. Segment warm-coloured candidate regions and produce per-instance contour polygons and boxes.
4. Compute shape, colour, local dark-patch and green-pixel evidence.
5. Pass measurements/evidence through a separate, versioned procurement rules engine.
6. Abstain to manual review for low confidence, overlap, missing calibration, or ambiguous evidence.
7. Preserve source image, model/engine version, rule snapshot, officer overrides, report data hash, and audit events.

The live camera path captures a still frame and uses the same image pipeline. Continuous video inference is deliberately out of scope for this stable MVP.

## Future research

Collect consented, diverse procurement-centre images with calibrated scales and onion-level polygon/defect labels; split train/validation/test by lot and collection site to reduce leakage; record variety, camera, lighting, and annotator adjudication; report per-class precision/recall, calibration, and diameter MAE; then validate on unseen sites and seasons. Investigate on-device ONNX/TFLite inference only after a representative dataset and independent evaluation exist.

See [`sources.json`](sources.json) for sourced references. No model evaluation has been run for this repository.
