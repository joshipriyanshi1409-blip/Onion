# Demo rehearsal checklist

## Preflight

- Start the FastAPI service and open the dashboard.
- Confirm the API health status reports `trained_model: false` and `HSV-CONTOUR-DEMO-0.1`.
- Open **Rules & policy** and state that the default 45–65 mm band is illustrative and editable.
- Confirm `data/runtime` is writable and the sample synthetic fixture loads.
- If using a phone camera, test browser permission and HTTPS first; otherwise use **Scan from photo**.

## 60–90 second route

1. **New inspection** → context fields show lot, procurement centre and operator.
2. **Load demo image** → the API runs the same image pipeline as a user photo; the asset itself is labelled synthetic.
3. Point at numbered, coloured regions. Explain that the scale comes from the visible 50 mm blue square and that it remains an estimate.
4. Click the sprouted, dark-patch or damage-cue bulb; read the cue score, applicable rule and explicit reason. Say that the score is heuristic image evidence, not a calibrated probability.
5. Show Grade A / URS / Reject / Manual Review counts, lot percentages, calibrated diameter summary and defect-cue counts.
6. Select **Generate report** → show the PDF link, QR and report-data SHA-256. Open **Verify hash**.
7. Return to **Dashboard** and reopen the saved inspection.

## If the photo is not detected

Use the synthetic fixture for a predictable software-path demonstration. For a field photo, increase even lighting, use a contrasting plain background, keep bulbs separated, check focus, and place a flat, verified-size calibration marker in the bulb plane. Do not override the rule profile merely to force a desired result.

## Dataset annotation walkthrough

1. Open **Dataset & labels** and upload a real, consented source image. The synthetic inspection fixture is intentionally excluded from the annotation queue.
2. Choose **Annotate**, enter an annotator ID and the correct centre/lot, then draw and finish one polygon per visible bulb. Mark every visible class that the label guide supports; do not infer hidden defects.
3. Save a draft during work, or mark the image complete after review. Assign all images from the same centre/lot to one split. For a small export smoke test, use distinct lots for train and validation; do not pretend this constitutes a trained/evaluated model.
4. Upload and annotate at least one validation image, then select **Export annotated YOLO-seg**. Check the download and read `CONVERSION_NOTES.txt` plus `annotations.json` before training.

## Claims to avoid

- Do not call the current engine a trained AI model; no trained weights are bundled.
- Do not quote accuracy, precision, recall or field performance; no evaluation run exists.
- Do not call the output a complete onion-quality, food-safety or statutory grade assessment.
- Do not present a QR or local SHA-256 as blockchain or an external legal signature.
- Do not present the demo size rules as current official NAFED/NCCF/AGMARK rules.
