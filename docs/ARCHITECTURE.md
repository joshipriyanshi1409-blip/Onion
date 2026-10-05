# PYAazScan architecture

## Current MVP

```text
Responsive browser UI (vanilla HTML/CSS/ES modules)
    ├── photo upload / still camera capture / bundled demo fixture
    ├── inspection map, explanations, rules, research and reports
    ├── polygon annotation studio with revision/provenance controls
    └── same-origin JSON API calls
            ↓
FastAPI modular monolith
    ├── scan API → OpenCV/Pillow heuristic visual pipeline
    ├── independent, editable procurement rules engine
    ├── SQLite persistence + append-only audit events
    ├── report snapshot → SHA-256 + QR → PDF
    ├── image-level dataset staging + versioned polygon annotation API
    ├── lot-aware YOLO-seg export, native multi-label manifest and optional training jobs
    └── static frontend and demo asset serving
```

## Inference boundary

`ml/inference/pipeline.py` returns image quality, candidate instance polygons/boxes, pixel dimensions, optional calibrated millimetres, and heuristic defect evidence. It does not assign grades. `backend/services/rules_engine.py` consumes those measurements/evidence and a snapshot of the currently selected rule profile. The deployed engine is `HSV-CONTOUR-DEMO-0.1`, a transparent classical-CV demo fallback; no trained model weights or evaluation metrics are present. The API and model registry expose this fact.

The optional 50 mm blue-square reference gives a scale estimate from its observed side length. Without it, millimetres remain `null` and the size rule abstains to manual review. This single-marker scale is a demo calibration aid, not metrology certification. A separate, operator-editable rules profile is stored in SQLite; past inspections retain their original rule snapshot.

## Storage and audit

SQLite is the local MVP database. It stores operator records, procurement centres, lots, inspections, original image metadata and SHA-256, per-onion decisions, defect evidence, measurements, active and historical rule versions, human overrides, reports, image-level dataset labels, versioned polygon annotations with annotator/status, lot/split metadata, exported archive records, training jobs, model versions and audit events. Uploaded images and generated PDFs live under `PYAaZSCAN_DATA_DIR` (default `data/runtime`), outside version control. A report's SHA-256 is over canonical JSON report data (including a source-image SHA-256); verification compares the snapshot and current source-image bytes. QR verification resolves to a same-origin report page. This is tamper-evident integrity checking, not blockchain or external trusted timestamping.

## API

- `POST /api/scan/image`, `POST /api/scan/camera`
- `GET /api/inspection/{id}`, `GET /api/inspections`, `GET /api/dashboard`
- `GET /api/rules`, `POST /api/rules`
- `POST /api/manual-review`
- `POST /api/reports/generate`, `GET /api/reports`, `GET /api/reports/{id}`, `GET /api/reports/{id}/pdf`, `GET /api/reports/{id}/verify`
- `GET /api/models`, `GET /api/research/sources`, `GET /api/dataset`
- `POST /api/dataset/images`, `GET /api/dataset/images/{id}`, `GET /api/dataset/images/{id}/image`
- `PUT /api/dataset/images/{id}/annotations`, `POST /api/dataset/export`, `GET /api/dataset/exports/{id}`
- `POST /api/dataset/upload`, `POST /api/training/start`, `GET /api/training/{id}`

## Boundaries and next steps

The browser capture mode takes a still image and reuses the upload endpoint. The default backend is one FastAPI process and SQLite, with no cloud requirement. For a production system, add authentication/roles, managed PostgreSQL and migrations, encrypted/retained image storage, signed report manifests and trusted timestamps, formal rule approval, an independently validated trained instance-segmentation model, and a reviewed offline ONNX/TFLite runtime. None of those production controls are claimed by this demo.
