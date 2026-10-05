# API notes

The FastAPI OpenAPI schema at `/openapi.json` is the source of endpoint request/response validation. Interactive documentation is at `/docs`.

## Scan response

`POST /api/scan/image` and `/api/scan/camera` accept multipart fields `file`, `lot_id`, `procurement_centre`, and `operator`. A successful response includes an `inspection_id`, `sample_size`, mutually exclusive decision counts and percentages, calibrated diameter statistics (or explicit absence), defect distribution, image quality/calibration status, rule snapshot, model/engine version, and onion-level boxes/polygons, evidence scores, grade, reasons and manual-review state.

`grade_a`, `urs`, `reject`, and `manual_review` percentages each use the photographed sample count as denominator and sum to 100% (subject to ordinary rounding for larger samples). These are sample results, not an estimate of the whole lot absent an agreed sampling method.

## Human overrides

`POST /api/manual-review` accepts JSON:

```json
{
  "inspection_id": "INS-…",
  "onion_id": 1,
  "decision": "URS",
  "reviewer": "Procurement Officer",
  "note": "Optional context"
}
```

Allowed decisions are `GRADE_A`, `URS`, and `REJECT`. The previous decision, reviewer, note and timestamp are retained in the inspection payload and audit tables.

## Polygon dataset curation and export

`POST /api/dataset/images` accepts multipart `file` and an initial image-level `label`. It creates an unassigned source image; this label is separate from per-onion segmentation labels. `GET /api/dataset` returns uploaded-record counts and the curation queue. `GET /api/dataset/images/{image_id}` returns EXIF-oriented pixel dimensions, the latest annotation, lot/split provenance and up to ten recent revision summaries. `GET /api/dataset/images/{image_id}/image` serves the source pixels inline.

`PUT /api/dataset/images/{image_id}/annotations` accepts:

```json
{
  "annotator": "Operator A",
  "status": "complete",
  "split": "train",
  "lot_id": "LOT-2026-014",
  "procurement_centre": "Example Centre",
  "objects": [
    {
      "onion_id": 1,
      "labels": ["healthy", "damaged"],
      "polygon": [[28, 20], [85, 24], [82, 70], [33, 73]],
      "notes": "Visible surface only"
    }
  ]
}
```

Polygon points are `[x, y]` source-image pixel coordinates, with at least three points inside the image. Each object needs a unique per-image onion ID and one or more labels from `healthy`, `damaged`, `rotten`, `sprouted`, `undersized`. Status is `draft` or `complete`; split is `unassigned`, `train`, `validation`, or `test`. An annotator name/ID is required for every saved revision; a complete annotation also requires a lot ID and procurement centre. Each successful save appends a revision and an audit event. Annotation labels are human observations, not verified diagnoses or model predictions.

`POST /api/dataset/export` exports the latest saved revisions only when their status is complete; it requires at least one train and one validation image, a split for every complete image, and no procurement-centre/lot group spread across splits. It responds with split counts and a same-origin `download_url`, served by `GET /api/dataset/exports/{export_id}`. The bundle contains `images/`, `labels/`, `data.yaml`, native multi-label `annotations.json`, and `CONVERSION_NOTES.txt`. YOLO-seg receives one class row per polygon/label pair, so multi-label polygons are duplicated in its labels; the original labels and provenance remain in the native manifest. Review before training.

`POST /api/training/start` runs the bounded structural validator in `training/prepare_dataset.py` before importing the optional trainer. It checks safe YAML parsing, class-name configuration and non-empty train/validation image paths. It does not adjudicate label quality, class balance, or scientific validity.

## Errors

- `413`: upload exceeds the size limit.
- `415`: file is not a supported decodable JPG/PNG/WEBP image, or dataset is not a ZIP.
- `422`: insufficient resolution, no candidate onions, invalid fields, or no usable image evidence.
- `409`: training prerequisites are not met, a manifest has missing/invalid train-validation image paths, a complete annotation is unassigned, required train/validation examples are missing, or images from the same procurement-centre/lot leak across dataset splits.
- `422`: invalid polygon coordinates/classes/status, missing annotator, missing lot/centre on a complete annotation, or an attempt to complete an image with no onion polygons.

Error messages are intended to help recapture or correct setup; they do not silently coerce a poor image into a grade.
