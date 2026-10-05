"""Deterministic report manifest hashing and human-readable PDF rendering."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any

from PIL import Image as PILImage, ImageDraw, ImageFont, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
import qrcode

GRADE_COLORS = {
    "GRADE_A": (35, 120, 79),
    "URS": (210, 130, 38),
    "REJECT": (192, 68, 60),
    "MANUAL_REVIEW": (69, 112, 177),
}


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_report_data(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def make_annotated_evidence(image_path: str | Path, inspection: dict[str, Any], destination: str | Path) -> Path:
    with PILImage.open(image_path) as opened:
        source = ImageOps.exif_transpose(opened).convert("RGB")
    draw = ImageDraw.Draw(source)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", max(14, source.width // 58))
    except OSError:
        font = ImageFont.load_default()
    width, height = source.size
    for onion in inspection.get("onions", []):
        box = onion.get("bbox", {})
        color = GRADE_COLORS.get(onion.get("grade"), GRADE_COLORS["MANUAL_REVIEW"])
        x, y = int(box.get("x", 0)), int(box.get("y", 0))
        x1 = min(width - 1, x + int(box.get("width", 0)))
        y1 = min(height - 1, y + int(box.get("height", 0)))
        draw.rectangle((x, y, x1, y1), outline=color, width=max(3, width // 320))
        tag = f"#{int(onion.get('onion_id', 0)):02d}"
        left, top, right, bottom = draw.textbbox((0, 0), tag, font=font)
        tag_w, tag_h = right - left, bottom - top
        tag_y = max(0, y - tag_h - 8)
        draw.rounded_rectangle((x, tag_y, x + tag_w + 12, tag_y + tag_h + 8), radius=4, fill=color)
        draw.text((x + 6, tag_y + 3), tag, fill="white", font=font)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.save(destination, format="JPEG", quality=86, optimize=True)
    return destination


def build_pdf(report_data: dict[str, Any], report_hash: str, verification_url: str, image_path: str | Path | None, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=colors.HexColor("#173e32"), alignment=TA_LEFT, spaceAfter=4))
    styles.add(ParagraphStyle(name="ReportEyebrow", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#b16a2a"), spaceAfter=5))
    styles.add(ParagraphStyle(name="SectionHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#173e32"), spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="SmallMuted", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#66756b")))
    styles.add(ParagraphStyle(name="CellText", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#24352d")))
    styles.add(ParagraphStyle(name="CenterCell", parent=styles["CellText"], alignment=TA_CENTER))

    inspection = report_data["inspection"]
    summary = inspection["summary"]
    percentages = inspection["percentages"]
    rules = inspection["rules"]
    model = inspection["model"]
    page_width, _ = A4
    story: list[Any] = [
        Paragraph("FIELD QUALITY RECORD  /  EXTERNAL VISUAL ASSESSMENT", styles["ReportEyebrow"]),
        Paragraph("PYAazScan", styles["ReportTitle"]),
        Paragraph("AI-assisted onion procurement inspection · Decision support, not a statutory certificate", styles["SmallMuted"]),
        Spacer(1, 8),
    ]

    meta_rows = [
        ["LOT ID", inspection["lot_id"], "INSPECTION ID", inspection["inspection_id"]],
        ["PROCUREMENT CENTRE", inspection["procurement_centre"], "OPERATOR", inspection["operator"]],
        ["CAPTURED", inspection["captured_at"], "REPORT GENERATED", report_data["generated_at"]],
        ["SAMPLE SIZE", str(inspection["sample_size"]), "RULE PROFILE", f"{rules['rule_set_id']} · v{rules['version']}"],
    ]
    meta_table = Table(meta_rows, colWidths=[31 * mm, 57 * mm, 33 * mm, 57 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f6f2")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6b7c70")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#6b7c70")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("LEADING", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([meta_table, Paragraph("Lot quality summary", styles["SectionHeading"])])
    grade_data = [
        ["GRADE A", "URS", "REJECT", "MANUAL REVIEW"],
        [f"{percentages['grade_a']:.2f}%  ·  {summary['grade_a']}", f"{percentages['urs']:.2f}%  ·  {summary['urs']}", f"{percentages['reject']:.2f}%  ·  {summary['reject']}", f"{percentages['manual_review']:.2f}%  ·  {summary['manual_review']}"],
    ]
    grade_table = Table(grade_data, colWidths=[44.5 * mm] * 4)
    grade_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf5ee")),
        ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#fbf3e8")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#fbefee")),
        ("BACKGROUND", (3, 0), (3, -1), colors.HexColor("#edf2f9")),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.HexColor("#23784f")),
        ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor("#b06b20")),
        ("TEXTCOLOR", (2, 0), (2, 0), colors.HexColor("#bd433a")),
        ("TEXTCOLOR", (3, 0), (3, 0), colors.HexColor("#416da8")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTSIZE", (0, 1), (-1, 1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.white),
        ("INNERGRID", (0, 0), (-1, -1), 1, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([grade_table, Paragraph("Diameter statistics", styles["SectionHeading"])])
    stats = inspection["statistics"]
    stat_values = [
        ["Mean", "Median", "Minimum", "Maximum", "Measured"],
        [*[_format_diameter(stats.get(key)) for key in ("mean_diameter_mm", "median_diameter_mm", "minimum_diameter_mm", "maximum_diameter_mm")], str(stats["measured_count"])],
    ]
    stat_table = Table(stat_values, colWidths=[35.6 * mm] * 5)
    stat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f6f3")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#738075")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
        ("INNERGRID", (0, 0), (-1, -1), 1, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([stat_table, Paragraph("Visible defect indicators", styles["SectionHeading"])])
    defect_rows = [["INDICATOR", "AFFECTED ONIONS", "INTERPRETATION"]]
    labels = {"sprouted": "Sprout-like green growth", "rotten": "Dark surface patch (rot cue)", "damaged": "Surface damage cue", "undersized": "Below configured minimum"}
    for key, count in inspection["defect_distribution"].items():
        defect_rows.append([labels.get(key, key.replace("_", " ").title()), str(count), "Heuristic visual evidence; verify manually"])
    if len(defect_rows) == 1:
        defect_rows.append(["No listed indicators", "0", "No visible cue detected by the demo pipeline"])
    defect_table = Table(defect_rows, colWidths=[63 * mm, 31 * mm, 90 * mm], repeatRows=1)
    defect_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ed")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#314138")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f8f6")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e2e8e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([defect_table, Paragraph("Per-onion evidence and decision", styles["SectionHeading"])])
    rows = [["ID", "SIZE", "DECISION", "VISIBLE EVIDENCE / RULE REASON"]]
    for onion in inspection["onions"]:
        size = _format_diameter(onion.get("diameter_mm")) if onion.get("diameter_mm") is not None else f"{onion['diameter_px']:.0f} px (uncalibrated)"
        reason = "; ".join(onion.get("decision_reasons", []))
        defects = ", ".join(f"{item['type']} {float(item['confidence']) * 100:.0f}%" for item in onion.get("defects", []))
        content = " · ".join(part for part in (defects, reason) if part) or "No listed defect cue"
        rows.append([f"#{int(onion['onion_id']):02d}", size, onion.get("grade", "MANUAL_REVIEW").replace("_", " "), Paragraph(_escape(content), styles["CellText"])])
    onion_table = LongTable(rows, colWidths=[14 * mm, 31 * mm, 31 * mm, 108 * mm], repeatRows=1)
    onion_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173e32")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f8f6")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e2e8e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(onion_table)

    if image_path and Path(image_path).is_file():
        story.extend([PageBreak(), Paragraph("Image evidence map", styles["SectionHeading"])])
        annotated = make_annotated_evidence(image_path, inspection, output_path.with_suffix(".evidence.jpg"))
        evidence = Image(str(annotated))
        evidence._restrictSize(174 * mm, 112 * mm)
        story.extend([evidence, Spacer(1, 6), Paragraph("Green = Grade A · Amber = URS · Red = Reject · Blue = Manual review. Boxes show detected regions, not certified grading boundaries.", styles["SmallMuted"])])

    story.extend([Paragraph("Rules, model, limitations and verification", styles["SectionHeading"])])
    rule_text = (
        f"Rule profile: {_escape(rules['rule_set_id'])} v{_escape(rules['version'])} — {_escape(rules['name'])}. "
        f"Diameter range: {rules['diameter_min_mm']:.1f}–{rules['diameter_max_mm']:.1f} mm. "
        f"{_escape(rules.get('notes', ''))}"
    )
    story.append(Paragraph(rule_text, styles["CellText"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Model/engine: {_escape(model['version'])} — {_escape(model['engine'])}. "
        f"{_escape(model.get('confidence_semantics', ''))} This is external visual assessment only; RGB imagery cannot reliably assess internal defects. Human review and the buyer's current written specification remain authoritative.",
        styles["CellText"],
    ))
    story.append(Spacer(1, 12))
    qr_buffer = io.BytesIO()
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data(verification_url)
    qr.make(fit=True)
    qr.make_image(fill_color="#173e32", back_color="white").save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_image = Image(qr_buffer, width=28 * mm, height=28 * mm)
    hash_block = Paragraph(
        f"<b>Report-data SHA-256</b><br/>{report_hash}<br/><br/><b>Source image SHA-256</b><br/>{_escape(report_data['inspection'].get('image_evidence_sha256', 'Unavailable'))}<br/><br/><b>Verification URL</b><br/>{_escape(verification_url)}<br/><br/>The report-data hash covers the canonical snapshot (including the source-image hash), not the PDF bytes. Verification checks the stored snapshot and current source-image bytes; it is not an external trusted timestamp or blockchain record.",
        styles["SmallMuted"],
    )
    verification = Table([[qr_image, hash_block]], colWidths=[34 * mm, 145 * mm])
    verification.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f6f2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(verification)

    def footer(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#dfe6dd"))
        canvas.line(16 * mm, 14 * mm, page_width - 16 * mm, 14 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#78837b"))
        canvas.drawString(16 * mm, 9 * mm, "PYAazScan · External visual assessment · Verify the applicable current procurement rule")
        canvas.drawRightString(page_width - 16 * mm, 9 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=16 * mm, bottomMargin=20 * mm, title=f"PYAazScan inspection {inspection['inspection_id']}", author="PYAazScan")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output_path


def _format_diameter(value: Any) -> str:
    return "—" if value is None else f"{float(value):.1f} mm"


def _escape(value: Any) -> str:
    text = str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
