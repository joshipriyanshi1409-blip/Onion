# PYAazScan

**AI-assisted onion procurement inspection · Smart India Hackathon 26031**

PYAazScan turns a smartphone photo into a traceable, onion-by-onion **external visual quality assessment**. It separates image evidence, buyer-configurable procurement rules, the resulting decision, and the report that records it.

> **AI measures. Procurement rules define. The rules engine decides. The report proves.**

This repository is a working local MVP. The current inference engine is a transparent classical computer-vision demo fallback, **not a trained model**. Its visual scores are heuristic evidence, not calibrated probabilities. No classification accuracy or field-performance result is claimed. The bundled photo is synthetic and is for software demonstration only.

## Problem

Onion grading at procurement centres can vary between inspectors. The project brief calls for a smartphone workflow to identify individual bulbs, surface damage, rot, sprouting and undersized onions; estimate lot-level Grade A/URS/reject proportions; explain decisions; and create an immediate digital record.

## Solution and demo workflow

```text
Take a photo / choose a photo / load synthetic fixture
        ↓
Image validation + quality cues
        ↓
50 mm calibration-reference detection (if present)
        ↓
Per-onion colour segmentation, contours and visual evidence scores
        ↓
Independent, versioned procurement rules engine
        ↓
Grade A / URS / Reject / Manual review + reasons
        ↓
Clickable evidence map + lot statistics + visible-cue analytics
        ↓
PDF quality record + QR link + SHA-256 report-data verification
```

### Implemented

- Responsive field dashboard, inspection ledger, inspection detail, research, dataset, training, model/evaluation, rules, reports and limitations views.
- **Scan from photo** and **camera capture** (a single still frame is inferred after capture); synthetic-fixture button for repeatable demos.
- Upload validation, file-size limit, supported JPG/PNG/WEBP formats, image-quality warnings, per-onion boxes/polygons, IDs, measurements, visible sprout/dark-patch/damage cues, confidence/evidence semantics, and image-map overlays.
- Optional high-contrast **50 mm blue-square reference**. Without the marker, measurements stay in pixels, physical millimetres are not invented, and size-dependent cases can go to manual review. A printable SVG is under `frontend/assets/calibration-sheet.svg`.
- Separate versioned rules engine, editable diameter range and defect allowances, Grade A/URS/Reject/Manual Review, lot percentages, diameter statistics, defect counts, and officer overrides with audit events.
- SQLite persistence for inspections, images, onions, defects, measurements, rules, reports, versioned polygon annotations, lot/split metadata, dataset exports, training jobs and audit events.
- PDF evidence report, QR verification URL and SHA-256 over the canonical JSON report-data snapshot (which includes a SHA-256 of the source image); verification checks both snapshot and current image bytes.
- Research sources stored in `research/sources.json`; explicit synthetic/field-data and evaluation status.
- Interactive polygon annotation studio for source images, per-onion multi-labels, annotator/lot/centre provenance, explicit splits, immutable annotation revisions, lot-leakage safeguards and YOLO-seg export that retains a native multi-label manifest.
- Safe prepared-dataset ZIP staging and optional YOLO-seg training/evaluation scripts; training is gated on a dataset manifest and the optional dependency.
- API, procurement-rule, image-pipeline, persistence, manual-review, report-generation and verification tests.

## Important scope and honesty

The displayed grade is a **rule profile outcome for a photographed sample**, not a statutory grade certificate or autonomous procurement decision. The starter `DEMO_45_65` profile uses the 45–65 mm interval from the supplied project brief as an editable engineering assumption; it is **not claimed to be a current NAFED/NCCF/AGMARK specification**. Inspectors must confirm and configure their buyer's current written rules.

RGB photographs cannot reliably assess internal rot, firmness, maturity, weight, moisture, smell, pesticide residue or hidden damage. Colour, lighting, overlap, variety and camera processing affect this demo pipeline. Lot percentages describe only the captured sample; sampling quality matters. Low-confidence, overlapping, or uncalibrated cases should receive human review.

## Architecture

```text
Browser: vanilla HTML / CSS / JavaScript
  ├── photo upload, still camera capture, map, analytics and reports
  └── same-origin JSON API calls
                ↓
FastAPI modular monolith
  ├── OpenCV + Pillow visual pipeline (replaceable inference boundary)
  ├── separate versioned procurement rules service
  ├── SQLite database + local evidence/report storage
  ├── reportlab PDF + QR + canonical report-data hash
  └── optional training subprocess endpoints
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for actual modules, persistence and API boundaries, and [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md) for the active engine's scope and evidence semantics. Local uploads/reports/database files live under `data/runtime` by default and are ignored by Git.

## Requirements and installation

- Python 3.11+ (tested with Python 3.11)
- `pip`
- A current browser. Camera capture requires browser camera permission and a secure origin (`localhost` or HTTPS).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # optional local configuration
python data/demo/generate_demo.py  # deterministic synthetic fixture (already bundled)
```

The repository does not require network access after Python packages are installed. Inference is local to the FastAPI service; it is not yet on-device inference.

## Run locally

```bash
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000). Interactive API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

Optional container run:

```bash
docker compose up --build
```

The container keeps SQLite, uploads, dataset staging and generated PDFs in the mounted runtime directory. SQLite is appropriate for this local demo; use managed PostgreSQL, migrations and production access controls before deployment.

## 90-second demo

1. Open **New inspection**.
2. Keep or edit the lot, centre and operator fields.
3. Select **Load demo image** (a synthetic fixture clearly labeled as such) or upload a suitable photo.
4. Review the numbered colour-coded inspection map and lot percentages.
5. Click a red, amber, or blue onion to see its size/evidence and **Why rejected?** / decision reasons; resolve a manual-review case with an officer override when available.
6. Select **Generate report**. Download the PDF or open **Verify hash**; the report contains the QR, rule/model versions, image evidence map, per-onion decisions and report-data hash.
7. Return to **Dashboard** or the inspection ledger to reopen the saved assessment.

Camera scan opens a browser preview and runs inference only after a still frame is captured. No continuous video processing is performed.

## AI / CV pipeline

`ml/inference/pipeline.py` implements decoding with EXIF correction; basic resolution/focus/contrast/lighting warnings; an optional high-contrast blue square scale reference; warm-colour segmentation; contour instance candidates and polygons; equivalent-pixel diameter; green-pixel/sprout-like and dark-patch/rot-like cues; and visible damage/undersized evidence. `backend/services/rules_engine.py` independently applies the rule snapshot and abstains when evidence or physical scale is insufficient.

The running engine is `HSV-CONTOUR-DEMO-0.1`. It is deliberately replaceable by a trained YOLO segmentation model or mobile ONNX/TFLite runtime, but no trained checkpoint is included. Heuristic scores must not be described as calibrated model probabilities.

## Dataset and annotation

- The bundled `frontend/assets/onion-demo.png` is a generated **synthetic software test fixture** with eight drawn bulbs and a scale marker. It is excluded from uploaded dataset counts, annotation export and model evaluation.
- Upload real source images on **Dataset & labels**, then open **Annotate**. Click around each onion to draw a polygon, choose one or more visible classes, record the annotator (required) and procurement-centre/lot metadata (required to complete), and assign the source image to one split. Save drafts or mark a reviewed image complete; every save adds a versioned revision.
- Keep every image from the same procurement-centre/lot in one split. The export endpoint rejects lot leakage and unassigned complete images, and requires at least one train and one validation image. Test is optional; no random or automatic splits are fabricated.
- **Export annotated YOLO-seg** creates a ZIP with image/label split folders, `data.yaml`, `annotations.json` and `CONVERSION_NOTES.txt`. YOLO-seg stores one class per polygon row; an onion with multiple labels becomes repeated polygon rows. The original multi-label polygons, annotator, lot, split and annotation version are retained in `annotations.json`. Review this conversion before training; the export does not claim a custom multi-label model is trained.
- No field dataset is bundled. Counts describe only uploaded operator records; no training/evaluation metrics are available until a real, reviewed dataset is assembled and evaluated.
- See [`docs/DATA_COLLECTION.md`](docs/DATA_COLLECTION.md), [`research/datasets.md`](research/datasets.md) and `training/` for workflow and caveats.

## Training and evaluation

The UI is not a pretend progress bar. It structurally validates a staged YOLO-seg `data.yaml` and confirms train/validation image paths exist before it starts a subprocess; the optional `ultralytics` package must also be installed. To install the optional trainer:

```bash
pip install ultralytics
```

Then curate a valid segmentation dataset (with polygons) and run:

```bash
python training/prepare_dataset.py --data /path/to/data.yaml
python training/train.py --data /path/to/data.yaml --epochs 50 --image-size 640 --batch-size 16
python training/evaluate.py --weights /path/to/best.pt --data /path/to/data.yaml
python training/export.py --weights /path/to/best.pt --format onnx
```

Training may download its starting checkpoint and is not needed for the photo-scan demo. Evaluation metrics are written only by an actual evaluation run. Validate per-class precision/recall and cross-site/lot performance; diameter MAE needs calibrated ground truth and is not inferred from detection metrics. See `research/literature.md` for the recommended collection/evaluation protocol.

## Procurement rules

The starter profile is stored in SQLite and editable in **Rules & policy**. Default demonstration logic:

- Calibrated diameter inside the configured inclusive range with no disallowed visible cue → Grade A.
- Outside the range → URS.
- Disallowed visible rot, sprout-like growth or damage cue → Reject.
- Missing required scale, ambiguous evidence or possible overlap → Manual Review.

Rules are validated and versioned. Each inspection snapshots its rule profile, rule-set ID/version, model/engine version and timestamp. Editing the active profile affects new inspections only. This is a demonstration policy, not procurement advice.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/scan/image` | Validate and inspect an uploaded photo |
| `POST` | `/api/scan/camera` | Infer a captured still frame |
| `GET` | `/api/inspection/{id}` | Inspection, onions, rules, image URL and audit trail |
| `GET` | `/api/inspections` | Saved inspection ledger |
| `GET` | `/api/dashboard` | Dashboard metrics from saved data only |
| `GET`, `POST` | `/api/rules` | Read or save the active versioned rule profile |
| `POST` | `/api/manual-review` | Save an officer's per-onion decision |
| `POST` | `/api/reports/generate` | Generate a PDF, QR link and data hash |
| `GET` | `/api/reports`, `/api/reports/{id}` | List or inspect saved report metadata |
| `GET` | `/api/reports/{id}/pdf` | Download report PDF |
| `GET` | `/api/reports/{id}/verify` | Recompute and compare report-data SHA-256 |
| `GET` | `/api/reports/{id}/qr` | QR image for the verification URL |
| `GET` | `/api/models` | Active engine and evaluation availability |
| `GET` | `/api/research/sources` | Sourced reference library |
| `GET` | `/api/dataset` | Actual uploaded-image, annotation and split counts |
| `POST` | `/api/dataset/images` | Upload a source image |
| `GET` | `/api/dataset/images/{id}` and `/image` | Image metadata, latest polygons and recent revision history; source pixels |
| `PUT` | `/api/dataset/images/{id}/annotations` | Save a validated, versioned polygon annotation and lot/split metadata |
| `POST` | `/api/dataset/export`, `GET /api/dataset/exports/{id}` | Export/download a reviewed YOLO-seg ZIP with native multi-label manifest |
| `POST` | `/api/dataset/upload` | Safely stage an existing dataset ZIP |
| `POST` | `/api/training/start`, `GET /api/training/{id}` | Optional guarded training subprocess |

## Reports and audit integrity

The report contains lot/inspection metadata, sample percentages, defect-cue counts, diameter statistics, per-onion reasons, image evidence, rules/model versions, generation time, SHA-256 report-data hash and a QR verification link. Hashing uses canonical JSON report data, including the source image SHA-256; verification checks both the stored snapshot and current source-image bytes. It does not sign PDF bytes or provide an independent trusted timestamp. QR verification is served by the same application. Audit events record inspection creation, rule-profile edits, human decisions and report generation.

## Security and configuration

- No secrets are required or hard-coded. `.env.example` documents optional runtime settings.
- Uploads are checked by decoded image format, size and image dimensions; filenames are sanitized. Dataset ZIP members are path-checked and extraction is size-limited.
- This is a local MVP without user authentication, roles, encryption-at-rest, malware scanning or production-grade retention policy. Do not expose it as a public procurement service without adding these controls.
- Set `PYAaZSCAN_DATA_DIR`, `PYAaZSCAN_MAX_UPLOAD_BYTES`, and optionally `PYAaZSCAN_CORS_ORIGINS` using environment variables. Do not commit `data/runtime` or real field images.

## Tests

```bash
python -m pytest
```

Tests cover rule boundaries and defect outcomes, calibrated/un-calibrated inference, image upload validation, the end-to-end scan/decision/audit/PDF/QR/hash flow, rule versioning, polygon validation/revision history, YOLO-seg export, native multi-label preservation, split prerequisites, lot-leakage rejection, manifest validation and training gates.

## Research sources

Real source URLs and provenance labels are stored in [`research/sources.json`](research/sources.json). `research/standards.md` distinguishes official/reference materials from the editable engineering assumption. References from other jurisdictions or archival documents are contextual reading only; they are not applied as current Indian procurement rules.

## Roadmap

1. Collect representative, consented field images across cultivars, sites, camera types and seasons.
2. Collect independent expert review/adjudication of the operator-drawn bulb polygons and multi-label external defect annotations.
3. Benchmark a small instance-segmentation model on held-out lots/sites; publish actual calibration, size error, false negatives and latency.
4. Validate a marked scale or calibrated depth/reference method and a repeatable sampling protocol.
5. Add officer roles, approval/signature, PostgreSQL migrations, secure offline synchronization and retention controls.
6. Export a validated ONNX/TFLite model for true on-device inference.

## Team roles

For a hackathon presentation, responsibilities map to: product/procurement research; field data collection and annotation; computer vision/model training and evaluation; backend/database/report integrity; responsive frontend and accessibility; DevOps/security and demo rehearsal. Keep real-world grading policy and farmer-facing wording under review by procurement and domain experts.
