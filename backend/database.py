"""SQLite repository for the local MVP. Each operation gets its own short-lived connection."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services.rules_engine import DEFAULT_RULES

ROOT = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass

DATA_DIR = Path(os.environ.get("PYAaZSCAN_DATA_DIR", ROOT / "data" / "runtime")).resolve()
DB_PATH = DATA_DIR / "pyaazscan.sqlite3"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def ensure_runtime_dirs() -> None:
    for child in (DATA_DIR, DATA_DIR / "images", DATA_DIR / "reports", DATA_DIR / "dataset", DATA_DIR / "archives", DATA_DIR / "exports", DATA_DIR / "training"):
        child.mkdir(parents=True, exist_ok=True)


def connect() -> sqlite3.Connection:
    ensure_runtime_dirs()
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


from contextlib import contextmanager
from collections.abc import Iterator


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    ensure_runtime_dirs()
    with database() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'inspector',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS procurement_centres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lots (
                id TEXT PRIMARY KEY,
                procurement_centre TEXT,
                operator TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS grading_rules (
                rule_set_id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                name TEXT NOT NULL,
                rules_json TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS grading_rule_versions (
                rule_set_id TEXT NOT NULL,
                version TEXT NOT NULL,
                name TEXT NOT NULL,
                rules_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(rule_set_id, version)
            );
            CREATE TABLE IF NOT EXISTS inspections (
                id TEXT PRIMARY KEY,
                lot_id TEXT NOT NULL,
                procurement_centre TEXT NOT NULL,
                operator TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                file_name TEXT NOT NULL,
                image_path TEXT NOT NULL,
                image_width INTEGER NOT NULL,
                image_height INTEGER NOT NULL,
                image_quality_json TEXT NOT NULL,
                calibration_json TEXT NOT NULL,
                model_version TEXT NOT NULL,
                rule_set_id TEXT NOT NULL,
                rule_version TEXT NOT NULL,
                rule_snapshot_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'complete',
                created_at TEXT NOT NULL,
                FOREIGN KEY(rule_set_id) REFERENCES grading_rules(rule_set_id)
            );
            CREATE TABLE IF NOT EXISTS images (
                id TEXT PRIMARY KEY,
                inspection_id TEXT NOT NULL UNIQUE,
                file_name TEXT NOT NULL,
                image_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(inspection_id) REFERENCES inspections(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS onions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_id TEXT NOT NULL,
                onion_id INTEGER NOT NULL,
                grade TEXT NOT NULL,
                diameter_mm REAL,
                diameter_px REAL,
                manual_review INTEGER NOT NULL DEFAULT 0,
                result_json TEXT NOT NULL,
                UNIQUE(inspection_id, onion_id),
                FOREIGN KEY(inspection_id) REFERENCES inspections(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS defects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_id TEXT NOT NULL,
                onion_id INTEGER NOT NULL,
                defect_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                detected INTEGER NOT NULL,
                FOREIGN KEY(inspection_id, onion_id) REFERENCES onions(inspection_id, onion_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_id TEXT NOT NULL,
                onion_id INTEGER NOT NULL,
                measurement_type TEXT NOT NULL,
                value REAL,
                unit TEXT NOT NULL,
                calibrated INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(inspection_id, onion_id) REFERENCES onions(inspection_id, onion_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS manual_reviews (
                id TEXT PRIMARY KEY,
                inspection_id TEXT NOT NULL,
                onion_id INTEGER NOT NULL,
                decision TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(inspection_id, onion_id) REFERENCES onions(inspection_id, onion_id)
            );
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                inspection_id TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                report_hash TEXT NOT NULL,
                report_data_json TEXT NOT NULL,
                pdf_path TEXT NOT NULL,
                verification_url TEXT NOT NULL,
                FOREIGN KEY(inspection_id) REFERENCES inspections(id)
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS model_versions (
                version TEXT PRIMARY KEY,
                engine TEXT NOT NULL,
                trained_model INTEGER NOT NULL,
                metrics_json TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dataset_images (
                id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                image_path TEXT NOT NULL,
                label TEXT NOT NULL,
                split TEXT NOT NULL DEFAULT 'unassigned',
                lot_id TEXT NOT NULL DEFAULT '',
                procurement_centre TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'operator_upload',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dataset_annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_image_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                annotator TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                objects_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(dataset_image_id, version),
                FOREIGN KEY(dataset_image_id) REFERENCES dataset_images(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS dataset_archives (
                id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                archive_path TEXT NOT NULL,
                extracted_path TEXT NOT NULL,
                image_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS training_jobs (
                id TEXT PRIMARY KEY,
                parameters_json TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL,
                log_path TEXT,
                process_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_inspections_created ON inspections(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_onions_inspection ON onions(inspection_id);
            CREATE INDEX IF NOT EXISTS idx_reports_inspection ON reports(inspection_id);
            CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id);
            """
        )
        dataset_columns = {row["name"] for row in db.execute("PRAGMA table_info(dataset_images)").fetchall()}
        if "lot_id" not in dataset_columns:
            db.execute("ALTER TABLE dataset_images ADD COLUMN lot_id TEXT NOT NULL DEFAULT ''")
        if "procurement_centre" not in dataset_columns:
            db.execute("ALTER TABLE dataset_images ADD COLUMN procurement_centre TEXT NOT NULL DEFAULT ''")
        db.execute("CREATE INDEX IF NOT EXISTS idx_dataset_annotations_image ON dataset_annotations(dataset_image_id, version DESC)")
        db.execute(
            "INSERT OR IGNORE INTO grading_rules(rule_set_id, version, name, rules_json, active, updated_at) VALUES (?, ?, ?, ?, 1, ?)",
            (DEFAULT_RULES["rule_set_id"], DEFAULT_RULES["version"], DEFAULT_RULES["name"], json.dumps(DEFAULT_RULES), utc_now()),
        )
        db.execute(
            "INSERT OR IGNORE INTO grading_rule_versions(rule_set_id, version, name, rules_json, updated_at) VALUES (?, ?, ?, ?, ?)",
            (DEFAULT_RULES["rule_set_id"], DEFAULT_RULES["version"], DEFAULT_RULES["name"], json.dumps(DEFAULT_RULES, sort_keys=True), utc_now()),
        )
        db.execute(
            "INSERT OR IGNORE INTO model_versions(version, engine, trained_model, metrics_json, created_at) VALUES (?, ?, 0, NULL, ?)",
            ("HSV-CONTOUR-DEMO-0.1", "Classical CV demo heuristic (not a trained model)", utc_now()),
        )


def add_audit(db: sqlite3.Connection, entity_type: str, entity_id: str, action: str, actor: str, payload: dict[str, Any]) -> None:
    db.execute(
        "INSERT INTO audit_logs(entity_type, entity_id, action, actor, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (entity_type, entity_id, action, actor[:120], json.dumps(payload, sort_keys=True), utc_now()),
    )


def parse_json(value: str | None, fallback: Any = None) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return fallback
