# Dataset notes

## Bundled fixture

`frontend/assets/onion-demo.png` is a **synthetically rendered software test fixture**, not a field photograph and not a training or evaluation dataset. It contains a calibration marker to exercise the measurement path. It is offered for repeatable UI/API demonstration only; it must not be used to claim field performance.

### Published field photographs (imported on demand, not committed)

| Item | Value |
|---|---|
| Record | [Zenodo 20254934](https://zenodo.org/records/20254934) · concept 20254933 · DOI `10.5281/zenodo.20254934` |
| Title / version | Image Dataset of Red and White Onion Bulbs and Leaves, v1 (published 2026-05-17) |
| Authors | Vinaya Kulkarni, Sanjesh Pawale, Suryawanshi Yogesh (Vishwakarma University) |
| Licence | CC BY 4.0 — attribution required when shown, exported or redistributed |
| Contents | 16,300 JPGs: 12,260 bulb + 4,040 leaf; folders by variety (red/white), health (healthy/unhealthy) and arrangement (single/multiple); 1024×768 or 576×768, 96 DPI |
| Capture | Motorola 50 Ultra (50 MP rear camera), local markets in Pune, Maharashtra, Jul 2025 – Feb 2026 |
| Files | `Onion Image Dataset.zip` 1,608,716,340 bytes (md5 `8d463f41734ebfb059e2dc03c7eb6def`); `All Metadata.xlsx` 1,312,773 bytes |
| Use in this repo | Optional demo input and annotation practice via `data/demo/import_zenodo_onions.py` → `data/demo/zenodo/` (git-ignored), served by `/api/demo/field-photos` |
| Not present | Instance masks/polygons, per-onion defect labels, label guide, lot/centre/site identity, capture protocol for procurement sampling, calibrated size references, held-out splits |

Consequences for claims: because the pack carries no per-onion annotation and no lot structure, it cannot support precision/recall/mAP statements, cannot be split into leakage-safe subsets by folder name alone, and its `healthy`/`unhealthy` folders describe whole photographs taken in a market — not buyer-grade quality of an inspected bulb. Attribution must accompany any reuse of the images.

The dataset API starts empty. It reports only files actually uploaded by an operator. The UI now supports manual per-onion polygon annotation, multi-label visible cues, annotator and lot/centre metadata, explicit splits, revision history, and a YOLO-seg export with a native multi-label JSON manifest. An initial image-level label is not instance ground truth. See [`docs/DATA_COLLECTION.md`](../docs/DATA_COLLECTION.md) for a careful curation workflow and the multi-label conversion caveat. Imported ZIPs are staged separately and are not automatically treated as validated labels.

## Splits and evaluation

No authentic, consented, **adjudicated** onion image dataset is bundled. Therefore train/validation/test counts and precision, recall, F1, mAP, IoU, confusion matrices, and diameter MAE are **not available** until real annotation and an evaluation run exist. Do not split frames or near-duplicates from one lot across train and test.

## External resources

The research page links official and research references for context. Their images are not redistributed here; only the CC BY 4.0 subset described above may be copied into a local `data/demo/zenodo/` directory by the operator running the importer. Check each dataset's licence and collection protocol before use; public availability does not automatically permit redistribution or procurement use.
