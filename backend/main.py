"""PYAazScan modular-monolith API and static demo frontend."""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import qrcode
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field

from backend.database import DATA_DIR, ROOT, add_audit, database, init_db, parse_json, utc_now
from backend.services.dataset_export import write_yolo_seg_bundle
from backend.services.reporting import build_pdf, canonical_json, sha256_report_data
from backend.services.rules_engine import DEFAULT_RULES, evaluate_onion, summarize_onions, validate_rules
from ml.inference.pipeline import ENGINE_NAME, MODEL_VERSION, ImageQualityError, analyze_image

FRONTEND_DIR = ROOT / "frontend"
DEMO_IMAGE = FRONTEND_DIR / "assets" / "onion-demo.png"
MAX_UPLOAD = int(os.environ.get("PYAaZSCAN_MAX_UPLOAD_BYTES", str(12 * 1024 * 1024)))
SUPPORTED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
ALLOWED_LABELS = {"healthy", "damaged", "rotten", "sprouted", "undersized"}
DATASET_CLASSES = ["healthy", "damaged", "rotten", "sprouted", "undersized"]
ACTIVE_PROCESSES: dict[str, subprocess.Popen[bytes]] = {}

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="PYAazScan API",
    description="AI-assisted onion procurement inspection — external visual decision support.",
    version="0.1.0",
    lifespan=lifespan,
)
_origins = [item.strip() for item in os.environ.get("PYAaZSCAN_CORS_ORIGINS", "").split(",") if item.strip()]
if _origins:
    app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET", "POST", "PUT", "OPTIONS"], allow_headers=["*"])


class ManualReviewBody(BaseModel):
    inspection_id: str
    onion_id: int = Field(ge=1)
    decision: str
    reviewer: str = "Procurement Officer"
    note: str = ""


class TrainingBody(BaseModel):
    epochs: int = Field(default=50, ge=1, le=300)
    image_size: int = Field(default=640, ge=128, le=1280)
    batch_size: int = Field(default=16, ge=1, le=128)
    learning_rate: float = Field(default=0.001, gt=0, le=0.1)
    dataset_yaml: str | None = None


class AnnotationObjectBody(BaseModel):
    onion_id: int = Field(ge=1, le=1000)
    labels: list[str] = Field(min_length=1, max_length=5)
    polygon: list[list[float]] = Field(min_length=3, max_length=200)
    notes: str = ""


class DatasetAnnotationBody(BaseModel):
    annotator: str = ""
    status: str = "draft"
    split: str = "unassigned"
    lot_id: str = ""
    procurement_centre: str = ""
    objects: list[AnnotationObjectBody] = Field(default_factory=list, max_length=100)


def _clean_text(value: str | None, fallback: str, limit: int = 120) -> str:
    text = (value or "").strip()
    text = re.sub(r"[\x00-\x1f\x7f]", "", text)
    return (text or fallback)[:limit]


def _read_active_rules() -> dict[str, Any]:
    with database() as db:
        row = db.execute("SELECT rules_json FROM grading_rules WHERE active = 1 ORDER BY updated_at DESC LIMIT 1").fetchone()
        if not row:
            return DEFAULT_RULES.copy()
        stored = parse_json(row["rules_json"], DEFAULT_RULES.copy())
        return validate_rules(stored)


def _record_to_list_item(row: Any) -> dict[str, Any]:
    result = parse_json(row["result_json"], {})
    return {
        "inspection_id": row["id"],
        "lot_id": row["lot_id"],
        "procurement_centre": row["procurement_centre"],
        "operator": row["operator"],
        "captured_at": row["captured_at"],
        "created_at": row["created_at"],
        "sample_size": result.get("sample_size", 0),
        "summary": result.get("summary", {}),
        "percentages": result.get("percentages", {}),
        "status": row["status"],
        "model_version": row["model_version"],
        "rule_set_id": row["rule_set_id"],
    }


def _get_inspection(db: Any, inspection_id: str) -> tuple[Any, dict[str, Any]]:
    row = db.execute("SELECT * FROM inspections WHERE id = ?", (inspection_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    result = parse_json(row["result_json"], {})
    return row, result


def _insert_onion_rows(db: Any, inspection_id: str, onions: list[dict[str, Any]]) -> None:
    db.execute("DELETE FROM onions WHERE inspection_id = ?", (inspection_id,))
    for onion in onions:
        db.execute(
            "INSERT INTO onions(inspection_id,onion_id,grade,diameter_mm,diameter_px,manual_review,result_json) VALUES(?,?,?,?,?,?,?)",
            (inspection_id, onion["onion_id"], onion["grade"], onion.get("diameter_mm"), onion.get("diameter_px"), int(onion.get("manual_review", False)), json.dumps(onion, sort_keys=True)),
        )
        for defect in onion.get("defect_assessments", {}).values():
            # Store positive and negative model evidence alike for an auditable per-class record.
            key = next((name for name, item in onion["defect_assessments"].items() if item is defect), "unknown")
            db.execute(
                "INSERT INTO defects(inspection_id,onion_id,defect_type,confidence,detected) VALUES(?,?,?,?,?)",
                (inspection_id, onion["onion_id"], key, float(defect.get("confidence", 0)), int(bool(defect.get("detected")))),
            )
        db.execute(
            "INSERT INTO measurements(inspection_id,onion_id,measurement_type,value,unit,calibrated) VALUES(?,?,?,?,?,?)",
            (inspection_id, onion["onion_id"], "equivalent_diameter", onion.get("diameter_mm") if onion.get("diameter_mm") is not None else onion.get("diameter_px"), "mm" if onion.get("diameter_mm") is not None else "px", int(onion.get("diameter_mm") is not None)),
        )


def _validate_image_upload(raw: bytes, filename: str) -> tuple[str, int, int]:
    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail=f"Image exceeds the {MAX_UPLOAD // (1024 * 1024)} MiB upload limit.")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image_format = image.format
            raw_width, raw_height = image.size
            if raw_width * raw_height > 25_000_000:
                raise HTTPException(status_code=413, detail="Image dimensions exceed the 25 megapixel safety limit.")
            image.verify()
        if image_format not in SUPPORTED_FORMATS:
            raise HTTPException(status_code=415, detail="Use a JPG, PNG, or WEBP image. HEIC conversion is not enabled in this MVP.")
        with Image.open(io.BytesIO(raw)) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            width, height = image.size
    except HTTPException:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise HTTPException(status_code=415, detail="The file is not a valid supported image. Use a JPG, PNG, or WEBP photo.") from exc
    safe_name = Path(filename or "inspection-image").name
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)[:120] or "inspection-image"
    return safe_name, width, height


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "PYAazScan", "model_version": MODEL_VERSION, "inference_engine": ENGINE_NAME, "trained_model": False}


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    with database() as db:
        rows = db.execute("SELECT * FROM inspections ORDER BY created_at DESC").fetchall()
        reports = db.execute("SELECT COUNT(*) AS count FROM reports").fetchone()["count"]
        audit = db.execute("SELECT COUNT(*) AS count FROM audit_logs").fetchone()["count"]
    items = [_record_to_list_item(row) for row in rows]
    today_items = [item for item in items if (item["created_at"] or "").startswith(today)]
    total_onions = sum(item["sample_size"] for item in items)
    grade_values = [item["percentages"].get("grade_a", 0) for item in items if item["sample_size"]]
    manual_values = [item["percentages"].get("manual_review", 0) for item in items if item["sample_size"]]
    return {
        "today_inspections": len(today_items),
        "total_inspections": len(items),
        "onions_inspected": total_onions,
        "average_grade_a_percentage": round(sum(grade_values) / len(grade_values), 1) if grade_values else None,
        "average_manual_review_percentage": round(sum(manual_values) / len(manual_values), 1) if manual_values else None,
        "reports_generated": reports,
        "audit_events": audit,
        "recent_inspections": items[:8],
        "grade_a_trend": [{"lot_id": item["lot_id"], "percentage": item["percentages"].get("grade_a", 0)} for item in items[:7]][::-1],
    }


@app.get("/api/inspections")
def list_inspections(limit: int = 100, offset: int = 0) -> dict[str, Any]:
    limit = min(max(limit, 1), 250)
    offset = max(offset, 0)
    with database() as db:
        total = db.execute("SELECT COUNT(*) FROM inspections").fetchone()[0]
        rows = db.execute("SELECT * FROM inspections ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
    return {"total": total, "items": [_record_to_list_item(row) for row in rows]}


@app.get("/api/inspection/{inspection_id}")
def get_inspection(inspection_id: str) -> dict[str, Any]:
    with database() as db:
        row, result = _get_inspection(db, inspection_id)
        reports = db.execute("SELECT report_id,generated_at,report_hash FROM reports WHERE inspection_id = ? ORDER BY generated_at DESC", (inspection_id,)).fetchall()
        audit_rows = db.execute("SELECT action,actor,payload_json,created_at FROM audit_logs WHERE entity_id = ? ORDER BY created_at", (inspection_id,)).fetchall()
    result["inspection_id"] = row["id"]
    result["lot_id"] = row["lot_id"]
    result["procurement_centre"] = row["procurement_centre"]
    result["operator"] = row["operator"]
    result["captured_at"] = row["captured_at"]
    result["created_at"] = row["created_at"]
    result["file_name"] = row["file_name"]
    result["image"] = {"url": f"/api/inspection/{inspection_id}/image", "width": row["image_width"], "height": row["image_height"]}
    result["image_quality"] = parse_json(row["image_quality_json"], result.get("image_quality", {}))
    result["calibration"] = parse_json(row["calibration_json"], result.get("calibration", {}))
    result["reports"] = [dict(item) for item in reports]
    result["audit_trail"] = [{**dict(item), "payload": parse_json(item["payload_json"], {})} for item in audit_rows]
    return result


@app.get("/api/inspection/{inspection_id}/image")
def inspection_image(inspection_id: str) -> FileResponse:
    with database() as db:
        row = db.execute("SELECT image_path,file_name FROM inspections WHERE id = ?", (inspection_id,)).fetchone()
    if not row or not Path(row["image_path"]).is_file():
        raise HTTPException(status_code=404, detail="Inspection image not found.")
    return FileResponse(row["image_path"], filename=row["file_name"], media_type="image/jpeg" if Path(row["image_path"]).suffix.lower() in {".jpg", ".jpeg"} else None)


async def _scan(file: UploadFile, lot_id: str | None, procurement_centre: str | None, operator: str | None) -> dict[str, Any]:
    raw = await file.read(MAX_UPLOAD + 1)
    safe_name, width, height = _validate_image_upload(raw, file.filename or "inspection-image")
    rules = _read_active_rules()
    try:
        visual = analyze_image(raw, rules)
    except ImageQualityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Image analysis failed safely. Please retry with a JPG or PNG photo.") from exc
    width, height = visual["image_width"], visual["image_height"]

    inspection_id = f"INS-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
    now = utc_now()
    lot = _clean_text(lot_id, f"LOT-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:4].upper()}", 64)
    centre = _clean_text(procurement_centre, "Unspecified procurement centre")
    user = _clean_text(operator, "Field officer")
    for onion in visual["onions"]:
        decision = evaluate_onion(onion, rules, calibration_available=visual["calibration"]["calibrated"])
        onion.update(decision)
        if visual["image_quality"]["status"] == "review":
            if onion["grade"] != "MANUAL_REVIEW":
                onion["grade_before_review"] = onion["grade"]
            onion["grade"] = "MANUAL_REVIEW"
            onion["manual_review"] = True
            onion["confidence_band"] = "manual_review"
            onion["decision_reasons"].append("Image quality warning: verify this onion or capture a sharper, evenly lit image")
        if onion.get("oversized"):
            onion["decision_reasons"].append(f"Measured diameter is above the configured maximum of {rules['diameter_max_mm']:.1f} mm")
        if onion.get("visual_flags"):
            if onion["grade"] != "MANUAL_REVIEW":
                onion["grade_before_review"] = onion["grade"]
            onion["grade"] = "MANUAL_REVIEW"
            onion["manual_review"] = True
            onion["confidence_band"] = "manual_review"
            onion["decision_reasons"].extend(onion["visual_flags"])
    aggregate = summarize_onions(visual["onions"])
    result: dict[str, Any] = {
        "inspection_id": inspection_id,
        "lot_id": lot,
        "procurement_centre": centre,
        "operator": user,
        "captured_at": now,
        "created_at": now,
        "sample_size": len(visual["onions"]),
        **aggregate,
        "onions": visual["onions"],
        "defect_distribution": aggregate["defect_distribution"],
        "image_quality": visual["image_quality"],
        "calibration": visual["calibration"],
        "model": visual["model"],
        "rules": rules,
        "warnings": visual["warnings"],
        "status": "complete",
        "external_visual_assessment_only": True,
    }
    with Image.open(io.BytesIO(raw)) as decoded_image:
        suffix = SUPPORTED_FORMATS.get(decoded_image.format or "JPEG", ".jpg")
    image_path = DATA_DIR / "images" / f"{inspection_id.lower()}{suffix}"
    image_path.write_bytes(raw)
    image_sha256 = hashlib.sha256(raw).hexdigest()
    result["image_sha256"] = image_sha256
    try:
        with database() as db:
            operator_id = uuid.uuid5(uuid.NAMESPACE_URL, user.casefold()).hex
            db.execute("INSERT OR IGNORE INTO users(id,display_name,role,created_at) VALUES(?,?,?,?)", (operator_id, user, "inspector", now))
            db.execute("INSERT OR IGNORE INTO procurement_centres(name,created_at) VALUES(?,?)", (centre, now))
            db.execute("INSERT OR IGNORE INTO lots(id,procurement_centre,operator,created_at) VALUES(?,?,?,?)", (lot, centre, user, now))
            db.execute(
                "INSERT INTO inspections(id,lot_id,procurement_centre,operator,captured_at,file_name,image_path,image_width,image_height,image_quality_json,calibration_json,model_version,rule_set_id,rule_version,rule_snapshot_json,result_json,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (inspection_id, lot, centre, user, now, safe_name, str(image_path), width, height, json.dumps(visual["image_quality"]), json.dumps(visual["calibration"]), visual["model"]["version"], rules["rule_set_id"], rules["version"], json.dumps(rules, sort_keys=True), json.dumps(result, sort_keys=True), "complete", now),
            )
            db.execute("INSERT INTO images(id,inspection_id,file_name,image_path,sha256,width,height,created_at) VALUES(?,?,?,?,?,?,?,?)", (f"IMG-{uuid.uuid4().hex[:12].upper()}", inspection_id, safe_name, str(image_path), image_sha256, width, height, now))
            _insert_onion_rows(db, inspection_id, visual["onions"])
            add_audit(db, "inspection", inspection_id, "inspection_created", user, {"lot_id": lot, "sample_size": result["sample_size"], "model_version": visual["model"]["version"], "rule_set_id": rules["rule_set_id"], "rule_version": rules["version"]})
    except Exception:
        image_path.unlink(missing_ok=True)
        raise
    return result


@app.post("/api/scan/image")
async def scan_image(
    file: UploadFile = File(...),
    lot_id: str | None = Form(default=None),
    procurement_centre: str | None = Form(default=None),
    operator: str | None = Form(default=None),
) -> dict[str, Any]:
    return await _scan(file, lot_id, procurement_centre, operator)


@app.post("/api/scan/camera")
async def scan_camera(
    file: UploadFile = File(...),
    lot_id: str | None = Form(default=None),
    procurement_centre: str | None = Form(default=None),
    operator: str | None = Form(default=None),
) -> dict[str, Any]:
    """Still-frame capture endpoint; the client reuses the stable photo inference path."""
    return await _scan(file, lot_id, procurement_centre, operator)


@app.get("/api/rules")
def get_rules() -> dict[str, Any]:
    with database() as db:
        rows = db.execute("SELECT v.rule_set_id,v.version,v.name,v.rules_json,v.updated_at,CASE WHEN r.active = 1 AND r.version = v.version THEN 1 ELSE 0 END AS active FROM grading_rule_versions v LEFT JOIN grading_rules r ON r.rule_set_id = v.rule_set_id ORDER BY v.updated_at DESC").fetchall()
    history = []
    for row in rows:
        item = parse_json(row["rules_json"], {})
        item.update({"active": bool(row["active"]), "updated_at": row["updated_at"]})
        history.append(item)
    active = next((row for row in history if row["active"]), history[0] if history else DEFAULT_RULES)
    return {"active": active, "history": history, "disclaimer": "Demo engineering profile only; confirm buyer-specific current rules before procurement use."}


@app.post("/api/rules")
def save_rules(body: dict[str, Any]) -> dict[str, Any]:
    try:
        rules = validate_rules(body)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    now = utc_now()
    with database() as db:
        requested_version = rules["version"]
        exists = db.execute("SELECT 1 FROM grading_rule_versions WHERE rule_set_id = ? AND version = ?", (rules["rule_set_id"], requested_version)).fetchone()
        if exists:
            parts = requested_version.split(".")
            try:
                parts[-1] = str(int(parts[-1]) + 1)
                requested_version = ".".join(parts)
            except (ValueError, IndexError):
                requested_version = f"{requested_version}-next"
            while db.execute("SELECT 1 FROM grading_rule_versions WHERE rule_set_id = ? AND version = ?", (rules["rule_set_id"], requested_version)).fetchone():
                parts = requested_version.split(".")
                try:
                    parts[-1] = str(int(parts[-1]) + 1)
                    requested_version = ".".join(parts)
                except (ValueError, IndexError):
                    requested_version = f"{requested_version}-next"
        rules["version"] = requested_version
        rules_json = json.dumps(rules, sort_keys=True)
        db.execute("UPDATE grading_rules SET active = 0")
        db.execute(
            "INSERT INTO grading_rules(rule_set_id,version,name,rules_json,active,updated_at) VALUES(?,?,?,?,1,?) ON CONFLICT(rule_set_id) DO UPDATE SET version=excluded.version,name=excluded.name,rules_json=excluded.rules_json,active=1,updated_at=excluded.updated_at",
            (rules["rule_set_id"], rules["version"], rules["name"], rules_json, now),
        )
        db.execute("INSERT INTO grading_rule_versions(rule_set_id,version,name,rules_json,updated_at) VALUES(?,?,?,?,?)", (rules["rule_set_id"], rules["version"], rules["name"], rules_json, now))
        add_audit(db, "rules", rules["rule_set_id"], "rule_profile_updated", "Procurement administrator", {"version": rules["version"], "diameter_min_mm": rules["diameter_min_mm"], "diameter_max_mm": rules["diameter_max_mm"]})
    return {"active": rules, "message": "Rule profile saved. New inspections use this version; existing snapshots are unchanged."}


@app.post("/api/manual-review")
def manual_review(body: ManualReviewBody) -> dict[str, Any]:
    decision = body.decision.strip().upper()
    if decision not in {"GRADE_A", "URS", "REJECT"}:
        raise HTTPException(status_code=422, detail="Choose Grade A, URS, or Reject.")
    with database() as db:
        row, result = _get_inspection(db, body.inspection_id)
        onion = next((item for item in result.get("onions", []) if int(item["onion_id"]) == body.onion_id), None)
        if onion is None:
            raise HTTPException(status_code=404, detail="Onion was not found in this inspection.")
        previous = onion.get("grade")
        onion["grade_before_review"] = previous
        onion["grade"] = decision
        onion["manual_review"] = False
        onion["confidence_band"] = "human_reviewed"
        onion["human_decision"] = {"decision": decision, "reviewer": _clean_text(body.reviewer, "Procurement Officer"), "note": _clean_text(body.note, "", 500), "created_at": utc_now()}
        onion["decision_reasons"] = [f"Officer decision: {decision.replace('_', ' ')}"]
        aggregate = summarize_onions(result.get("onions", []))
        result.update(aggregate)
        result["defect_distribution"] = aggregate["defect_distribution"]
        review_id = str(uuid.uuid4())
        reviewer = _clean_text(body.reviewer, "Procurement Officer")
        db.execute("INSERT INTO manual_reviews(id,inspection_id,onion_id,decision,reviewer,note,created_at) VALUES(?,?,?,?,?,?,?)", (review_id, body.inspection_id, body.onion_id, decision, reviewer, _clean_text(body.note, "", 500), onion["human_decision"]["created_at"]))
        db.execute("UPDATE inspections SET result_json = ? WHERE id = ?", (json.dumps(result, sort_keys=True), body.inspection_id))
        db.execute("UPDATE onions SET grade = ?, manual_review = 0, result_json = ? WHERE inspection_id = ? AND onion_id = ?", (decision, json.dumps(onion, sort_keys=True), body.inspection_id, body.onion_id))
        add_audit(db, "inspection", body.inspection_id, "manual_decision_recorded", reviewer, {"onion_id": body.onion_id, "previous_decision": previous, "decision": decision, "note": body.note})
    return {"inspection_id": body.inspection_id, "onion_id": body.onion_id, "decision": decision, "result": result}


@app.get("/api/models")
def models() -> dict[str, Any]:
    with database() as db:
        rows = db.execute("SELECT version,engine,trained_model,metrics_json,created_at FROM model_versions ORDER BY created_at DESC").fetchall()
        used = db.execute("SELECT model_version,COUNT(*) AS inspections FROM inspections GROUP BY model_version ORDER BY inspections DESC").fetchall()
    metric_files: list[Path] = []
    for directory in (DATA_DIR / "training", ROOT / "data" / "training-runs"):
        if directory.is_dir():
            metric_files.extend(directory.rglob("metrics.json"))
    latest_metrics: dict[str, Any] | None = None
    metrics_path: Path | None = None
    for candidate in sorted(metric_files, key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            loaded = json.loads(candidate.read_text(encoding="utf-8"))
            if loaded.get("status") == "evaluation_run":
                latest_metrics, metrics_path = loaded, candidate
                break
        except (OSError, json.JSONDecodeError):
            continue
    evaluation_metrics: dict[str, Any] | None = None
    confusion = None
    evaluation = {"status": "No evaluation run yet", "metrics": None, "confusion_matrix": None, "weights": None, "dataset": None, "evaluated_at": None}
    if latest_metrics:
        box = latest_metrics.get("box", {})
        segmentation = latest_metrics.get("segmentation", {})
        def f1_score(part: dict[str, Any]) -> float | None:
            precision, recall = part.get("precision"), part.get("recall")
            if precision is None or recall is None or float(precision) + float(recall) == 0:
                return None
            return round(2 * float(precision) * float(recall) / (float(precision) + float(recall)), 4)

        evaluation_metrics = {
            "box_precision": box.get("precision"),
            "box_recall": box.get("recall"),
            "box_F1": f1_score(box),
            "box_mAP50": box.get("map50"),
            "box_mAP50_95": box.get("map50_95"),
            "segmentation_precision": segmentation.get("precision"),
            "segmentation_recall": segmentation.get("recall"),
            "segmentation_F1": f1_score(segmentation),
            "segmentation_mAP50": segmentation.get("map50"),
            "segmentation_mAP50_95": segmentation.get("map50_95"),
            "diameter_MAE_mm": latest_metrics.get("diameter_mae_mm"),
        }
        evaluation = {
            "status": "Evaluation run available",
            "metrics": evaluation_metrics,
            "confusion_matrix": latest_metrics.get("confusion_matrix"),
            "weights": latest_metrics.get("weights"),
            "dataset": latest_metrics.get("dataset"),
            "evaluated_at": datetime.fromtimestamp(metrics_path.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z") if metrics_path else None,
        }
    return {
        "active_version": MODEL_VERSION,
        "items": [{"version": row["version"], "engine": row["engine"], "trained_model": bool(row["trained_model"]), "metrics": parse_json(row["metrics_json"], None), "created_at": row["created_at"], "evaluation_status": "No evaluation run yet" if not row["metrics_json"] else "Evaluated"} for row in rows],
        "usage": {row["model_version"]: row["inspections"] for row in used},
        "evaluation": evaluation,
        "confidence_note": "Current evidence scores are generated by classical image-processing heuristics. They are not calibrated probabilities and no classification accuracy is claimed.",
    }


@app.get("/api/research/sources")
def research_sources() -> dict[str, Any]:
    source_path = ROOT / "research" / "sources.json"
    try:
        sources = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        sources = []
    return {"items": sources, "loaded_from": "research/sources.json"}


def _latest_annotation(db: Any, image_id: str) -> dict[str, Any] | None:
    row = db.execute("SELECT version,annotator,status,objects_json,created_at FROM dataset_annotations WHERE dataset_image_id=? ORDER BY version DESC LIMIT 1", (image_id,)).fetchone()
    if not row:
        return None
    return {"version": row["version"], "annotator": row["annotator"], "status": row["status"], "objects": parse_json(row["objects_json"], []), "created_at": row["created_at"]}


def _dataset_image_response(db: Any, row: Any) -> dict[str, Any]:
    annotation = _latest_annotation(db, row["id"])
    history_rows = db.execute("SELECT version,annotator,status,objects_json,created_at FROM dataset_annotations WHERE dataset_image_id=? ORDER BY version DESC LIMIT 10", (row["id"],)).fetchall()
    history = [{"version": item["version"], "annotator": item["annotator"], "status": item["status"], "object_count": len(parse_json(item["objects_json"], [])), "created_at": item["created_at"]} for item in history_rows]
    try:
        with Image.open(row["image_path"]) as image:
            image = ImageOps.exif_transpose(image)
            width, height = image.size
    except (OSError, Image.DecompressionBombError):
        width, height = 0, 0
    return {
        "id": row["id"], "file_name": row["file_name"], "label": row["label"],
        "split": row["split"], "lot_id": row["lot_id"], "procurement_centre": row["procurement_centre"],
        "source": row["source"], "created_at": row["created_at"],
        "image_url": f"/api/dataset/images/{row['id']}/image", "width": width, "height": height,
        "annotation_status": annotation["status"] if annotation else "unannotated",
        "annotation_version": annotation["version"] if annotation else 0,
        "annotation_count": len(annotation["objects"]) if annotation else 0,
        "annotations": annotation,
        "annotation_history": history,
    }


@app.get("/api/dataset")
def dataset_overview() -> dict[str, Any]:
    with database() as db:
        rows = db.execute("SELECT id,file_name,image_path,label,split,lot_id,procurement_centre,source,created_at FROM dataset_images ORDER BY created_at DESC").fetchall()
        archive_rows = db.execute("SELECT id,file_name,image_count,created_at,extracted_path FROM dataset_archives ORDER BY created_at DESC").fetchall()
        images = [_dataset_image_response(db, row) for row in rows]
    counts = {label: 0 for label in sorted(ALLOWED_LABELS | {"unlabeled"})}
    splits = {"train": 0, "validation": 0, "test": 0, "unassigned": 0}
    annotated_images = annotated_onions = 0
    for item in images:
        counts[item["label"]] = counts.get(item["label"], 0) + 1
        split = item["split"] if item["split"] in {"train", "validation", "test"} else "unassigned"
        splits[split] += 1
        if item["annotation_status"] == "complete":
            annotated_images += 1
        annotated_onions += item["annotation_count"]
    archives = []
    trainable_archive = None
    for row in archive_rows:
        extracted = Path(row["extracted_path"])
        yamls = list(extracted.rglob("data.yaml")) + list(extracted.rglob("data.yml")) if extracted.exists() else []
        if yamls and trainable_archive is None:
            trainable_archive = str(yamls[0])
        archives.append({"id": row["id"], "file_name": row["file_name"], "image_count": row["image_count"], "created_at": row["created_at"], "contains_yolo_config": bool(yamls), "download_url": f"/api/dataset/exports/{row['id']}" if str(row["id"]).startswith("EXP-") else None})
    return {
        "image_count": len(images),
        "annotated_images": annotated_images,
        "annotated_onions": annotated_onions,
        "class_counts": counts,
        "splits": splits,
        "items": images[:500],
        "archives": archives,
        "trainable_dataset_yaml": trainable_archive,
        "demo_fixture_images": 1 if DEMO_IMAGE.exists() else 0,
        "demo_fixture_note": "Synthetic software-test image only; excluded from uploaded/training/evaluation counts.",
        "evaluation_note": "No field dataset or evaluation run is bundled; no accuracy metrics are available.",
    }


@app.post("/api/dataset/images")
async def upload_dataset_image(file: UploadFile = File(...), label: str = Form(...)) -> dict[str, Any]:
    label = label.strip().lower()
    if label not in ALLOWED_LABELS:
        raise HTTPException(status_code=422, detail=f"Label must be one of: {', '.join(sorted(ALLOWED_LABELS))}.")
    raw = await file.read(MAX_UPLOAD + 1)
    safe_name, _, _ = _validate_image_upload(raw, file.filename or "dataset-image")
    image_id = uuid.uuid4().hex
    with Image.open(io.BytesIO(raw)) as decoded_image:
        suffix = SUPPORTED_FORMATS.get(decoded_image.format or "JPEG", ".jpg")
    destination = DATA_DIR / "dataset" / f"{image_id}{suffix}"
    destination.write_bytes(raw)
    now = utc_now()
    try:
        with database() as db:
            db.execute("INSERT INTO dataset_images(id,file_name,image_path,label,split,lot_id,procurement_centre,source,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (image_id, safe_name, str(destination), label, "unassigned", "", "", "operator_upload", now))
            add_audit(db, "dataset_image", image_id, "image_labelled", "Dataset annotator", {"label": label, "file_name": safe_name})
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {"id": image_id, "file_name": safe_name, "label": label, "created_at": now, "image_url": f"/api/dataset/images/{image_id}/image", "message": "Image saved. Draw each onion polygon and assign one or more visible labels in the annotation studio."}


@app.get("/api/dataset/images/{image_id}")
def dataset_image_detail(image_id: str) -> dict[str, Any]:
    with database() as db:
        row = db.execute("SELECT id,file_name,image_path,label,split,lot_id,procurement_centre,source,created_at FROM dataset_images WHERE id=?", (image_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dataset image not found.")
        return _dataset_image_response(db, row)


@app.get("/api/dataset/images/{image_id}/image")
def dataset_image_file(image_id: str) -> FileResponse:
    with database() as db:
        row = db.execute("SELECT image_path,file_name FROM dataset_images WHERE id=?", (image_id,)).fetchone()
    if not row or not Path(row["image_path"]).is_file():
        raise HTTPException(status_code=404, detail="Dataset image file not found.")
    return FileResponse(row["image_path"], filename=row["file_name"], content_disposition_type="inline")


@app.put("/api/dataset/images/{image_id}/annotations")
def save_dataset_annotation(image_id: str, body: DatasetAnnotationBody) -> dict[str, Any]:
    if body.status not in {"draft", "complete"}:
        raise HTTPException(status_code=422, detail="Annotation status must be draft or complete.")
    if body.split not in {"unassigned", "train", "validation", "test"}:
        raise HTTPException(status_code=422, detail="Choose train, validation, test, or unassigned for the image split.")
    annotator = _clean_text(body.annotator, "", 120)
    lot_id = _clean_text(body.lot_id, "", 64)
    procurement_centre = _clean_text(body.procurement_centre, "", 120)
    if not annotator:
        raise HTTPException(status_code=422, detail="Enter an annotator name or operator ID before saving a revision.")
    if body.status == "complete" and (not lot_id or not procurement_centre):
        raise HTTPException(status_code=422, detail="Complete annotations require both a lot ID and procurement centre for split provenance.")
    with database() as db:
        row = db.execute("SELECT image_path,file_name FROM dataset_images WHERE id=?", (image_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dataset image not found.")
        try:
            with Image.open(row["image_path"]) as opened:
                oriented = ImageOps.exif_transpose(opened)
                width, height = oriented.size
        except (OSError, Image.DecompressionBombError) as exc:
            raise HTTPException(status_code=422, detail="The stored image can no longer be decoded.") from exc
        if body.status == "complete" and not body.objects:
            raise HTTPException(status_code=422, detail="A complete annotation needs at least one onion polygon.")
        object_ids: set[int] = set()
        normalized_objects: list[dict[str, Any]] = []
        for obj in body.objects:
            if obj.onion_id in object_ids:
                raise HTTPException(status_code=422, detail="Each onion ID must be unique within an image.")
            object_ids.add(obj.onion_id)
            if not obj.labels or any(label not in DATASET_CLASSES for label in obj.labels):
                raise HTTPException(status_code=422, detail=f"Labels must be selected from: {', '.join(DATASET_CLASSES)}.")
            polygon: list[list[float]] = []
            for point in obj.polygon:
                if len(point) != 2:
                    raise HTTPException(status_code=422, detail="Polygon points must be [x, y] pairs in source-image pixels.")
                x, y = float(point[0]), float(point[1])
                if not (math.isfinite(x) and math.isfinite(y) and 0 <= x <= width and 0 <= y <= height):
                    raise HTTPException(status_code=422, detail="Polygon points must stay inside the source image.")
                polygon.append([round(x, 2), round(y, 2)])
            area2 = abs(sum(polygon[i][0] * polygon[(i + 1) % len(polygon)][1] - polygon[(i + 1) % len(polygon)][0] * polygon[i][1] for i in range(len(polygon))))
            if area2 < 2:
                raise HTTPException(status_code=422, detail="Polygon area is too small; add distinct points around the onion boundary.")
            normalized_objects.append({"onion_id": obj.onion_id, "labels": sorted(set(obj.labels)), "polygon": polygon, "notes": _clean_text(obj.notes, "", 500)})
        if len(normalized_objects) != len(body.objects):
            raise HTTPException(status_code=422, detail="One or more annotation objects are invalid.")
        now = utc_now()
        status = "complete" if body.status == "complete" and normalized_objects else "draft"
        next_version = db.execute("SELECT COALESCE(MAX(version),0)+1 FROM dataset_annotations WHERE dataset_image_id=?", (image_id,)).fetchone()[0]
        db.execute("INSERT INTO dataset_annotations(dataset_image_id,version,annotator,status,objects_json,created_at) VALUES(?,?,?,?,?,?)", (image_id, next_version, annotator, status, json.dumps(normalized_objects, sort_keys=True), now))
        db.execute("UPDATE dataset_images SET split=?,lot_id=?,procurement_centre=? WHERE id=?", (body.split, lot_id, procurement_centre, image_id))
        add_audit(db, "dataset_image", image_id, "polygon_annotation_saved", annotator, {"version": next_version, "status": status, "object_count": len(normalized_objects), "split": body.split})
    return {"image_id": image_id, "version": next_version, "status": status, "object_count": len(normalized_objects), "created_at": now, "message": "Polygon annotation revision saved. Complete annotations can be exported with explicit train/validation/test splits."}


@app.post("/api/dataset/export")
def export_annotated_dataset() -> dict[str, Any]:
    with database() as db:
        rows = db.execute(
            "SELECT i.id,i.image_path,i.split,i.lot_id,i.procurement_centre,a.version AS annotation_version,a.annotator,a.objects_json "
            "FROM dataset_images i JOIN dataset_annotations a ON a.dataset_image_id=i.id "
            "AND a.version=(SELECT MAX(a2.version) FROM dataset_annotations a2 WHERE a2.dataset_image_id=i.id) "
            "WHERE a.status='complete' ORDER BY i.created_at"
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=409, detail="No complete polygon annotations are ready for export.")
    missing_provenance = [row["id"] for row in rows if not row["lot_id"].strip() or not row["procurement_centre"].strip()]
    if missing_provenance:
        raise HTTPException(status_code=409, detail=f"Complete annotations need a lot ID and procurement centre. {len(missing_provenance)} image(s) are missing provenance.")
    unassigned = [row["id"] for row in rows if row["split"] not in {"train", "validation", "test"}]
    if unassigned:
        raise HTTPException(status_code=409, detail=f"Assign every complete annotation to a train/validation/test split before export. {len(unassigned)} complete image(s) are unassigned.")
    splits_by_lot: dict[tuple[str, str] | tuple[str], set[str]] = {}
    for row in rows:
        lot_id = row["lot_id"].strip().casefold()
        centre = row["procurement_centre"].strip().casefold()
        group_key = (centre, lot_id) if lot_id else (f"image:{row['id']}",)
        splits_by_lot.setdefault(group_key, set()).add(row["split"])
    leaked_groups = [group for group, split_values in splits_by_lot.items() if len(split_values) > 1]
    if leaked_groups:
        raise HTTPException(status_code=409, detail="Lot leakage guard: images from one lot must stay in a single split. Move all images from each affected lot to one split before export.")
    split_counts = {split: sum(1 for row in rows if row["split"] == split) for split in ("train", "validation", "test")}
    if not split_counts["train"] or not split_counts["validation"]:
        raise HTTPException(status_code=409, detail="YOLO segmentation export requires at least one complete train image and one complete validation image.")
    records = []
    for row in rows:
        objects = parse_json(row["objects_json"], [])
        if not objects:
            raise HTTPException(status_code=409, detail=f"Image {row['id']} is marked complete but has no polygon objects.")
        records.append({
            "id": row["id"], "image_path": row["image_path"], "split": row["split"],
            "lot_id": row["lot_id"], "procurement_centre": row["procurement_centre"],
            "annotation_version": row["annotation_version"], "annotator": row["annotator"], "objects": objects,
        })
    export_id = f"EXP-{uuid.uuid4().hex[:12].upper()}"
    extracted_dir = DATA_DIR / "archives" / export_id.lower()
    archive_path = DATA_DIR / "exports" / f"{export_id.lower()}.zip"
    try:
        exported = write_yolo_seg_bundle(records, extracted_dir, archive_path)
    except (OSError, ValueError) as exc:
        shutil.rmtree(extracted_dir, ignore_errors=True)
        archive_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Dataset export failed: {exc}") from exc
    now = utc_now()
    file_name = f"PYAazScan-polygons-{export_id}.zip"
    try:
        with database() as db:
            db.execute("INSERT INTO dataset_archives(id,file_name,archive_path,extracted_path,image_count,created_at) VALUES(?,?,?,?,?,?)", (export_id, file_name, str(archive_path), str(extracted_dir), exported["image_count"], now))
            add_audit(db, "dataset_archive", export_id, "annotated_dataset_exported", "Dataset curator", {"file_name": file_name, "image_count": exported["image_count"], "split_counts": exported["split_counts"], "classes": exported["classes"]})
    except Exception:
        shutil.rmtree(extracted_dir, ignore_errors=True)
        archive_path.unlink(missing_ok=True)
        raise
    return {"export_id": export_id, "file_name": file_name, "image_count": exported["image_count"], "split_counts": exported["split_counts"], "classes": exported["classes"], "download_url": f"/api/dataset/exports/{export_id}", "training_yaml": str(extracted_dir / "data.yaml"), "message": "YOLO-seg bundle created from saved annotations. Multi-label polygons are duplicated per class in YOLO labels; native multi-label data is preserved in annotations.json."}


@app.get("/api/dataset/exports/{export_id}")
def download_dataset_export(export_id: str) -> FileResponse:
    with database() as db:
        row = db.execute("SELECT file_name,archive_path FROM dataset_archives WHERE id=?", (export_id,)).fetchone()
    if not row or not Path(row["archive_path"]).is_file():
        raise HTTPException(status_code=404, detail="Dataset export not found.")
    return FileResponse(row["archive_path"], filename=row["file_name"], media_type="application/zip")


@app.post("/api/dataset/upload")
async def upload_dataset_archive(file: UploadFile = File(...)) -> dict[str, Any]:
    raw = await file.read(50 * 1024 * 1024 + 1)
    if not raw or len(raw) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Dataset ZIP must be no larger than 50 MiB.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=415, detail="Upload a valid ZIP dataset archive.") from exc
    bundle_id = uuid.uuid4().hex
    extracted_dir = DATA_DIR / "archives" / bundle_id
    extracted_dir.mkdir(parents=True, exist_ok=False)
    archive_path = DATA_DIR / "archives" / f"{bundle_id}.zip"
    allowed_suffixes = {".yaml", ".yml", ".txt", ".jpg", ".jpeg", ".png", ".webp", ".names"}
    image_count = 0
    total_uncompressed = 0
    try:
        infos = archive.infolist()
        if len(infos) > 20000:
            raise HTTPException(status_code=413, detail="Dataset archive contains too many entries.")
        for info in infos:
            if info.is_dir():
                continue
            raw_name = info.filename.replace("\\", "/")
            member = PurePosixPath(raw_name)
            if member.is_absolute() or ".." in member.parts or not member.parts:
                raise HTTPException(status_code=400, detail="Dataset ZIP contains an unsafe file path.")
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise HTTPException(status_code=400, detail="Symbolic links are not allowed in a dataset ZIP.")
            suffix = Path(member.name).suffix.lower()
            if suffix not in allowed_suffixes:
                continue
            total_uncompressed += info.file_size
            if total_uncompressed > 200 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Expanded dataset exceeds the 200 MiB safety limit.")
            target = extracted_dir.joinpath(*member.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            data = archive.read(info)
            target.write_bytes(data)
            if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
                image_count += 1
        archive_path.write_bytes(raw)
        now = utc_now()
        safe_name = Path(file.filename or "dataset.zip").name[:120]
        with database() as db:
            db.execute("INSERT INTO dataset_archives(id,file_name,archive_path,extracted_path,image_count,created_at) VALUES(?,?,?,?,?,?)", (bundle_id, safe_name, str(archive_path), str(extracted_dir), image_count, now))
            add_audit(db, "dataset_archive", bundle_id, "dataset_archive_uploaded", "Dataset curator", {"file_name": safe_name, "image_count": image_count})
    except Exception:
        shutil.rmtree(extracted_dir, ignore_errors=True)
        archive_path.unlink(missing_ok=True)
        raise
    finally:
        archive.close()
    return {"id": bundle_id, "file_name": safe_name, "image_count": image_count, "contains_yolo_config": any(extracted_dir.rglob("data.yaml")) or any(extracted_dir.rglob("data.yml")), "message": "Archive staged safely. Review its labels and splits before any training run."}


@app.post("/api/training/start")
def start_training(body: TrainingBody) -> dict[str, Any]:
    with database() as db:
        archive_rows = db.execute("SELECT extracted_path FROM dataset_archives ORDER BY created_at DESC").fetchall()
    candidates = []
    if body.dataset_yaml:
        requested = Path(body.dataset_yaml)
        if requested.is_absolute() and requested.exists() and DATA_DIR in requested.resolve().parents:
            candidates.append(requested.resolve())
        elif not requested.is_absolute():
            for row in archive_rows:
                root = Path(row["extracted_path"]).resolve()
                maybe = (root / requested).resolve()
                if root in maybe.parents and maybe.is_file():
                    candidates.append(maybe)
    else:
        for row in archive_rows:
            extracted = Path(row["extracted_path"])
            candidates.extend(list(extracted.rglob("data.yaml")) + list(extracted.rglob("data.yml")))
    dataset_yaml = next((candidate for candidate in candidates if candidate.is_file()), None)
    if dataset_yaml is None:
        raise HTTPException(status_code=409, detail="No YOLO data.yaml found in the staged dataset archives. Image-level labels alone are not sufficient.")
    try:
        validation = subprocess.run(
            [sys.executable, str(ROOT / "training" / "prepare_dataset.py"), "--data", str(dataset_yaml)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=409, detail="Dataset manifest validation timed out. Check the YAML and image paths before training.") from exc
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Could not start the dataset manifest validator.") from exc
    if validation.returncode != 0:
        validation_detail = (validation.stderr or validation.stdout or "Dataset validation failed.").strip()[-800:]
        raise HTTPException(status_code=409, detail=f"Dataset manifest validation failed: {validation_detail}")
    try:
        import ultralytics  # type: ignore[import-not-found]  # optional training dependency
        del ultralytics
    except ImportError as exc:
        raise HTTPException(status_code=409, detail="Training is not installed in this MVP environment. Install the optional ultralytics extra, then provide a reviewed YOLO-seg dataset. No training job was started.") from exc
    job_id = f"TRN-{uuid.uuid4().hex[:10].upper()}"
    now = utc_now()
    log_path = DATA_DIR / "training" / f"{job_id.lower()}.log"
    args = [sys.executable, str(ROOT / "training" / "train.py"), "--data", str(dataset_yaml), "--epochs", str(body.epochs), "--image-size", str(body.image_size), "--batch-size", str(body.batch_size), "--learning-rate", str(body.learning_rate), "--project", str(DATA_DIR / "training" / "runs"), "--name", job_id.lower()]
    log_file = open(log_path, "wb")
    try:
        process = subprocess.Popen(args, cwd=ROOT, stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True)
    finally:
        log_file.close()
    ACTIVE_PROCESSES[job_id] = process
    with database() as db:
        db.execute("INSERT INTO training_jobs(id,parameters_json,status,message,log_path,process_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (job_id, json.dumps(body.model_dump()), "running", "Training subprocess started.", str(log_path), process.pid, now, now))
        add_audit(db, "training_job", job_id, "training_started", "Model developer", {"parameters": body.model_dump(), "dataset_yaml": str(dataset_yaml)})
    return {"training_id": job_id, "status": "running", "message": "Training subprocess started.", "parameters": body.model_dump()}


@app.get("/api/training/{training_id}")
def training_status(training_id: str) -> dict[str, Any]:
    with database() as db:
        row = db.execute("SELECT * FROM training_jobs WHERE id = ?", (training_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Training job not found.")
        process = ACTIVE_PROCESSES.get(training_id)
        status = row["status"]
        message = row["message"]
        if process is not None:
            code = process.poll()
            if code is not None:
                status = "completed" if code == 0 else "failed"
                message = "Training completed; review produced metrics and weights." if code == 0 else f"Training exited with status {code}; inspect the log before using any weights."
                db.execute("UPDATE training_jobs SET status=?,message=?,updated_at=? WHERE id=?", (status, message, utc_now(), training_id))
                ACTIVE_PROCESSES.pop(training_id, None)
        log_path = Path(row["log_path"]) if row["log_path"] else None
        tail = ""
        if log_path and log_path.is_file():
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-6000:]
        return {"training_id": row["id"], "status": status, "message": message, "parameters": parse_json(row["parameters_json"], {}), "log_tail": tail, "created_at": row["created_at"], "updated_at": row["updated_at"]}


@app.get("/api/reports")
def list_reports(limit: int = 100) -> dict[str, Any]:
    with database() as db:
        rows = db.execute("SELECT report_id,inspection_id,generated_at,report_hash,verification_url FROM reports ORDER BY generated_at DESC LIMIT ?", (min(max(limit, 1), 250),)).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.post("/api/reports/generate")
def generate_report(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    inspection_id = _clean_text(str(body.get("inspection_id", "")), "", 80)
    if not inspection_id:
        raise HTTPException(status_code=422, detail="inspection_id is required.")
    report_id = f"RPT-{uuid.uuid4().hex[:12].upper()}"
    generated_at = utc_now()
    verification_url = str(request.base_url).rstrip("/") + f"/?verify={report_id}"
    with database() as db:
        row, inspection = _get_inspection(db, inspection_id)
        try:
            image_hash = hashlib.sha256(Path(row["image_path"]).read_bytes()).hexdigest()
        except OSError as exc:
            raise HTTPException(status_code=409, detail="The source image evidence is unavailable; report generation was stopped.") from exc
        # Freeze all report fields needed to reproduce the verification hash.
        report_inspection = {
            "image_evidence_sha256": image_hash,
            "inspection_id": row["id"],
            "lot_id": row["lot_id"],
            "procurement_centre": row["procurement_centre"],
            "operator": row["operator"],
            "captured_at": row["captured_at"],
            "sample_size": inspection.get("sample_size", 0),
            "summary": inspection.get("summary", {}),
            "percentages": inspection.get("percentages", {}),
            "statistics": inspection.get("statistics", {}),
            "defect_distribution": inspection.get("defect_distribution", {}),
            "onions": inspection.get("onions", []),
            "image_quality": inspection.get("image_quality", {}),
            "calibration": inspection.get("calibration", {}),
            "rules": inspection.get("rules", parse_json(row["rule_snapshot_json"], {})),
            "model": inspection.get("model", {"version": row["model_version"], "engine": ENGINE_NAME}),
            "warnings": inspection.get("warnings", []),
        }
        report_data = {"schema_version": "1.0", "report_id": report_id, "generated_at": generated_at, "verification_url": verification_url, "inspection": report_inspection}
        report_hash = sha256_report_data(report_data)
        pdf_path = DATA_DIR / "reports" / f"{report_id.lower()}.pdf"
        try:
            build_pdf(report_data, report_hash, verification_url, row["image_path"], pdf_path)
            db.execute("INSERT INTO reports(report_id,inspection_id,generated_at,report_hash,report_data_json,pdf_path,verification_url) VALUES(?,?,?,?,?,?,?)", (report_id, inspection_id, generated_at, report_hash, canonical_json(report_data), str(pdf_path), verification_url))
            add_audit(db, "inspection", inspection_id, "report_generated", "Procurement Officer", {"report_id": report_id, "report_hash": report_hash})
        except Exception:
            pdf_path.unlink(missing_ok=True)
            pdf_path.with_suffix(".evidence.jpg").unlink(missing_ok=True)
            raise
    return {"report_id": report_id, "inspection_id": inspection_id, "generated_at": generated_at, "report_hash": report_hash, "verification_url": verification_url, "pdf_url": f"/api/reports/{report_id}/pdf", "qr_url": f"/api/reports/{report_id}/qr"}


@app.get("/api/reports/{report_id}")
def get_report(report_id: str) -> dict[str, Any]:
    with database() as db:
        row = db.execute("SELECT r.report_id,r.inspection_id,r.generated_at,r.report_hash,r.verification_url,r.pdf_path,i.image_path FROM reports r JOIN inspections i ON i.id = r.inspection_id WHERE r.report_id = ?", (report_id,)).fetchone()
        data_row = db.execute("SELECT report_data_json FROM reports WHERE report_id = ?", (report_id,)).fetchone()
    if not row or not data_row:
        raise HTTPException(status_code=404, detail="Report not found.")
    report_data = parse_json(data_row["report_data_json"], {})
    data_verified = bool(report_data) and sha256_report_data(report_data) == row["report_hash"]
    recorded_image_hash = report_data.get("inspection", {}).get("image_evidence_sha256")
    try:
        current_image_hash = hashlib.sha256(Path(row["image_path"]).read_bytes()).hexdigest()
    except OSError:
        current_image_hash = None
    image_verified = bool(recorded_image_hash and recorded_image_hash == current_image_hash)
    return {"report_id": row["report_id"], "inspection_id": row["inspection_id"], "generated_at": row["generated_at"], "report_hash": row["report_hash"], "verification_url": row["verification_url"], "pdf_url": f"/api/reports/{report_id}/pdf", "verified": data_verified and image_verified, "image_evidence_sha256": recorded_image_hash, "image_verified": image_verified}


@app.get("/api/reports/{report_id}/verify")
def verify_report(report_id: str) -> dict[str, Any]:
    with database() as db:
        row = db.execute("SELECT r.report_id,r.inspection_id,r.generated_at,r.report_hash,r.verification_url,i.image_path FROM reports r JOIN inspections i ON i.id = r.inspection_id WHERE r.report_id = ?", (report_id,)).fetchone()
        data_row = db.execute("SELECT report_data_json FROM reports WHERE report_id = ?", (report_id,)).fetchone()
    if not row or not data_row:
        raise HTTPException(status_code=404, detail="Report not found.")
    report_data = parse_json(data_row["report_data_json"], {})
    computed_hash = sha256_report_data(report_data) if report_data else None
    recorded_image_hash = report_data.get("inspection", {}).get("image_evidence_sha256")
    try:
        current_image_hash = hashlib.sha256(Path(row["image_path"]).read_bytes()).hexdigest()
    except OSError:
        current_image_hash = None
    image_matches = bool(recorded_image_hash and recorded_image_hash == current_image_hash)
    verified = computed_hash == row["report_hash"] and image_matches
    return {"verified": verified, "report_id": row["report_id"], "inspection_id": row["inspection_id"], "generated_at": row["generated_at"], "report_hash": row["report_hash"], "computed_hash": computed_hash, "image_evidence_sha256": recorded_image_hash, "current_image_sha256": current_image_hash, "image_verified": image_matches, "rule_set_id": report_data.get("inspection", {}).get("rules", {}).get("rule_set_id"), "rule_version": report_data.get("inspection", {}).get("rules", {}).get("version"), "model_version": report_data.get("inspection", {}).get("model", {}).get("version"), "verification_url": row["verification_url"]}


@app.get("/api/reports/{report_id}/pdf")
def download_report(report_id: str) -> FileResponse:
    with database() as db:
        row = db.execute("SELECT pdf_path FROM reports WHERE report_id = ?", (report_id,)).fetchone()
    if not row or not Path(row["pdf_path"]).is_file():
        raise HTTPException(status_code=404, detail="Report PDF not found.")
    return FileResponse(row["pdf_path"], filename=f"PYAazScan-{report_id}.pdf", media_type="application/pdf")


@app.get("/api/reports/{report_id}/qr")
def report_qr(report_id: str) -> Response:
    with database() as db:
        row = db.execute("SELECT verification_url FROM reports WHERE report_id = ?", (report_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found.")
    code = qrcode.QRCode(box_size=7, border=2)
    code.add_data(row["verification_url"])
    code.make(fit=True)
    image = code.make_image(fill_color="#173e32", back_color="white")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return Response(content=output.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


@app.get("/api/audit/{inspection_id}")
def audit_events(inspection_id: str) -> dict[str, Any]:
    with database() as db:
        exists = db.execute("SELECT 1 FROM inspections WHERE id = ?", (inspection_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Inspection not found.")
        rows = db.execute("SELECT id,entity_type,entity_id,action,actor,payload_json,created_at FROM audit_logs WHERE entity_id = ? ORDER BY created_at ASC,id ASC", (inspection_id,)).fetchall()
    return {"items": [{**dict(row), "payload": parse_json(row["payload_json"], {})} for row in rows]}


@app.get("/demo/onion-lot.png")
def demo_image() -> FileResponse:
    if not DEMO_IMAGE.is_file():
        raise HTTPException(status_code=404, detail="Synthetic demo fixture is not available.")
    return FileResponse(DEMO_IMAGE, filename="pyaazscan-synthetic-demo.png", media_type="image/png")


# Mount the UI last so API routes keep precedence and the preview is same-origin.
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
