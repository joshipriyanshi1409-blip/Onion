# Field image collection and polygon annotation

PYAazScan includes a manual curation workflow; it does **not** include a real onion field dataset, adjudicated ground truth, or a trained segmentation model. The current annotation tools help create a dataset; they do not certify label quality.

## 1. Collect source photographs

1. Use images collected with appropriate consent and permission for the intended research/training use. Avoid faces, identity documents, personal devices/screens, and unrelated personal information.
2. Photograph representative procurement samples across centres, lots, cultivars, seasons, lighting, phones, and visible condition. Keep the original image where possible; record centre and lot identifiers in the annotation form.
3. Spread bulbs apart where practical. Include a useful view of the whole visible surface, avoid strong glare and motion blur, and do not imply a photo reveals internal rot, firmness, moisture, mass, or other hidden properties.
4. Use a visible calibrated reference in the same plane if a physical size label is needed. A casual photo or apparent image size alone is not enough to label an onion `undersized`; agree on a buyer-specific reference and measurement protocol first.
5. Upload each source image through **Dataset & labels**. The initial image-level label is only a curation field; it is not the per-onion segmentation annotation.

The app has no user authentication, encrypted storage, or production retention controls. Runtime images are stored locally under `data/runtime` by default. Do not upload sensitive or restricted data to an exposed instance.

## 2. Draw and review polygons

1. Open **Annotate** for an uploaded image.
2. Click along the visible outer boundary of one onion, add at least three points, and finish the polygon. Each object receives an image-local onion ID. Remove and redraw a polygon if it includes neighbouring bulbs or a large background area.
3. Assign all supported visible labels that apply: `healthy`, `damaged`, `rotten`, `sprouted`, and/or `undersized`. These are operator observations, not model outputs or official diagnoses. Agree on a written label guide before collecting at scale.
   - Use `healthy` only when no target visible cue is being recorded.
   - `damaged`, `rotten`, and `sprouted` refer to visible external cues only.
   - Use `undersized` only with an agreed size reference/rule and adequate scale/context; otherwise leave it unlabelled or route it for expert review.
4. Record the annotator, procurement centre, lot, and split. An annotator is required on every revision; lot and centre are required to mark the image complete. A lot is kept together by the export guard within a centre. Use stable, non-identifying lot IDs.
5. Save as **Draft** while work is in progress. Mark **Complete** only after checking each polygon and label. Every successful save appends a revision; the latest revision is used for export. The UI exposes recent revision summaries.

Polygon vertices use source-image pixel coordinates. Image coordinates and annotations are stored locally; EXIF orientation is applied consistently when dimensions are returned and when export images are normalized.

## 3. Assign leakage-safe splits

Assign each procurement-centre/lot group wholly to exactly one of `train`, `validation`, or `test`. Do not distribute frames, near-duplicates, or onions from one lot across subsets. The app does not invent split assignments or choose a split ratio for you.

Export checks that:

- every latest complete annotation has an explicit split;
- at least one complete train and validation image are present (test is optional); and
- no procurement-centre/lot group is represented in more than one split.

A group that violates the leakage guard can be corrected by editing the affected images to the same split, then retrying export. Incomplete and draft annotations are excluded.

## 4. Export and conversion caveat

Choose **Export annotated YOLO-seg** to create a ZIP with `images/{train,validation,test}/`, `labels/{train,validation,test}/`, `data.yaml`, `annotations.json`, and `CONVERSION_NOTES.txt`. Polygon coordinates are normalized for YOLO-seg. `annotations.json` retains the native per-onion multi-label representation, annotator, lot/centre, split, and annotation revision.

YOLO-seg's standard text format has a single class ID per polygon row. To represent an onion assigned more than one class, this exporter repeats the same polygon once per class in the YOLO text label. That can be interpreted as duplicate same-location instances by a conventional single-label segmentation trainer. **Review this mapping before training**; for principled multi-label segmentation, adapt the training target/loss and evaluator to the native multi-label manifest rather than assuming the duplicated rows are equivalent.

Export bundles are stored under the ignored runtime directory and can be downloaded again from the dataset page. Imported ZIP files are staged separately and are not automatically merged into the native annotation queue or certified as valid.

## 5. Before training or publishing metrics

- Have domain experts review the label guide and adjudicate a sample of polygons; double-annotate a subset and measure agreement.
- Inspect class balance, per-site/cultivar/season coverage, image quality, overlap, annotator agreement, and split provenance. Do not treat the `healthy` image-level upload field as polygon ground truth.
- Hold out entire lots (and preferably sites/time periods for a generalization test) before tuning. Keep a final test set untouched until model selection is complete.
- Evaluate per-class segmentation and classification behavior, false negatives, calibration/uncertainty, and size error against calibrated measurements. Report only metrics from an actual, documented run on an appropriate held-out dataset.
- Keep procurement rules configurable and separate from model labels. RGB imagery cannot reliably establish internal quality or legal grade.

The synthetic demo fixture is for software behavior only; it must not be mixed into field training or evaluation data.
