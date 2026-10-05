# Dataset notes

## Bundled fixture

`frontend/assets/onion-demo.png` is a **synthetically rendered software test fixture**, not a field photograph and not a training or evaluation dataset. It contains a calibration marker to exercise the measurement path. It is offered for repeatable UI/API demonstration only; it must not be used to claim field performance.

The dataset API starts empty. It reports only files actually uploaded by an operator. The UI now supports manual per-onion polygon annotation, multi-label visible cues, annotator and lot/centre metadata, explicit splits, revision history, and a YOLO-seg export with a native multi-label JSON manifest. An initial image-level label is not instance ground truth. See [`docs/DATA_COLLECTION.md`](../docs/DATA_COLLECTION.md) for a careful curation workflow and the multi-label conversion caveat. Imported ZIPs are staged separately and are not automatically treated as validated labels.

## Splits and evaluation

No authentic, consented, adjudicated onion image dataset is bundled. Therefore train/validation/test counts and precision, recall, F1, mAP, IoU, confusion matrices, and diameter MAE are **not available** until real annotation and an evaluation run exist. Do not split frames or near-duplicates from one lot across train and test.

## External resources

The research page links official and research references for context. Their images are not redistributed here. Check each dataset's licence and collection protocol before use; public availability does not automatically permit redistribution or procurement use.
