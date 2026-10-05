# Model card — `HSV-CONTOUR-DEMO-0.1`

## Status

- **Kind:** classical computer-vision demo pipeline (OpenCV/Pillow); not a learned model.
- **Weights:** none.
- **Training:** none.
- **Evaluation:** no held-out field dataset; no precision, recall, F1, mAP, IoU or accuracy result available.
- **Intended use:** repeatable software demonstration and engineering workflow testing only.
- **Optional photo subset:** `data/demo/import_zenodo_onions.py` can import CC BY 4.0 photographs from [Zenodo 20254934](https://zenodo.org/records/20254934) as demo/annotation input. Photographs are not labels: no polygons, no lot identity and no adjudicated quality ground truth arrive with them, so nothing here becomes a trained or evaluated model.
- **Not intended for:** autonomous procurement, payment, food-safety certification, disease diagnosis or statistically representative lot acceptance.

## Input and output

Input is one decoded RGB photograph. The pipeline returns image-quality cues; per-instance candidate boxes and polygons; a pixel-equivalent diameter; an optional approximate millimetre diameter if the 50 mm blue-square marker is observed; per-class heuristic scores for healthy, damaged, rotten, sprouted and undersized; and warnings that can route a decision to manual review.

A separate, versioned buyer rules engine assigns Grade A / URS / Reject / Manual Review. The visual pipeline does not decide the procurement rule.

## Evidence-score semantics

`confidence` and `detection_confidence` are bounded **heuristic evidence scores**, derived from the observed colour mask, contour shape, local dark-pixel ratio or green-pixel ratio. They have not been calibrated on a labelled validation set and must not be interpreted as probabilities. Configurable evidence bands are an initial engineering control, not a scientific guarantee.

## Known failure modes

Warm-coloured backgrounds, red/purple or white varieties, soil, harsh shadows, glare, blur, high compression, merged bulbs, sprout colour, background objects and camera white balance can alter segmentation or surface-cue scores. A single printed reference has perspective and print-size error. It does not correct camera pose or lens distortion.

RGB photography cannot establish hidden/internal defects, firmness, maturity, moisture, mass, odour or chemical residues. A photo's inspected bulbs may not represent the whole lot.

## Human oversight

Low evidence, poor image quality, overlap or missing scale can trigger manual review. Officers can record an explicit override with a reviewer, note, timestamp and audit event. The buyer's current written specification and human inspection remain authoritative.

## Upgrade criteria

Only replace or augment this engine after obtaining a licensed/consented, diverse, expert-adjudicated dataset with instance masks, multi-label defect annotations, calibrated diameter references, lot/site/season metadata and held-out-site evaluation. The optional Zenodo photo pack covers image diversity only; the remaining requirements must still be produced. Publish per-class metrics, uncertainty calibration, diameter MAE, failure analysis, latency and inference-device details before operational use.
