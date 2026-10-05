"""Read-only view over a locally imported field-photo subset (see data/demo/import_zenodo_onions.py).

The subset is third-party CC BY 4.0 photography used as demo input and annotation starting
material. Nothing here treats it as ground truth, and nothing here is a trained model.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "pyaazscan-field-photo-subset/1"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
MAX_MANIFEST_IMAGES = 500
# The publisher's coarse market class, offered as the dataset image-level curation field.
# It is not an instance label, not a defect observation, and not an adjudicated quality result.
HEALTH_TO_CURATION_LABEL = {"healthy": "healthy", "unhealthy": "damaged", "unclassified": "healthy"}
IMPORT_HINT = (
    "Download 'Onion Image Dataset.zip' from https://zenodo.org/records/20254934 (CC BY 4.0), then run "
    'python data/demo/import_zenodo_onions.py --zip "<path to the archive>", then reload the app (no restart needed).'
)


def _safe_member(root: Path, relative: Any) -> Path | None:
    if not isinstance(relative, str) or not relative:
        return None
    parts = Path(relative).parts
    if not parts or any(part in {"..", "/", ""} for part in parts) or Path(relative).is_absolute():
        return None
    candidate = root.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def load_subset(root: Path) -> dict[str, Any]:
    """Describe the subset on disk, with an explicit status for every failure mode.

    Returned image entries keep private `_file_relative` / `_thumb_relative` keys so the API can
    resolve bytes without re-reading the manifest; strip them with `public_subset` in responses.
    """
    root = Path(root)
    base: dict[str, Any] = {
        "root": str(root),
        "schema": SCHEMA,
        "images": [],
        "counts": {"selected": 0, "present": 0, "available": 0, "by_class": {}},
        "import_hint": IMPORT_HINT,
    }
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        return {**base, "status": "missing", "message": "No field-photo subset has been imported on this machine."}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        return {**base, "status": "invalid", "message": f"Subset manifest could not be read ({type(exc).__name__}). Re-import it."}
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        return {**base, "status": "invalid", "message": "Subset manifest has an unexpected schema. Re-import it with the current script."}

    entries = manifest.get("images")
    if not isinstance(entries, list):
        return {**base, "status": "invalid", "message": "Subset manifest lists no images. Re-import it."}

    images: list[dict[str, Any]] = []
    for entry in entries[:MAX_MANIFEST_IMAGES]:
        if not isinstance(entry, dict):
            continue
        photo_id = str(entry.get("id") or "")
        if not SAFE_ID.match(photo_id):
            continue
        image_path = _safe_member(root, entry.get("file"))
        if image_path is None:
            continue
        thumbnail_path = _safe_member(root, entry.get("thumbnail")) if entry.get("thumbnail") else None
        health = str(entry.get("health") or "unclassified")
        images.append(
            {
                "id": photo_id,
                "title": " · ".join(str(entry.get(key) or "unknown") for key in ("variety", "health", "arrangement")),
                "width": entry.get("width"),
                "height": entry.get("height"),
                "orientation": entry.get("orientation"),
                "bytes": entry.get("bytes"),
                "sha256": entry.get("sha256"),
                "part": entry.get("part"),
                "variety": entry.get("variety"),
                "health": health,
                "arrangement": entry.get("arrangement"),
                "detections_expected": entry.get("detections_expected"),
                "source_path": entry.get("source_path"),
                "image_url": f"/api/demo/field-photos/{photo_id}/image",
                "thumbnail_url": f"/api/demo/field-photos/{photo_id}/image{'?variant=thumb' if thumbnail_path else ''}",
                "dataset_label_suggestion": HEALTH_TO_CURATION_LABEL.get(health, "healthy"),
                "_file_relative": entry.get("file"),
                "_thumb_relative": entry.get("thumbnail") if thumbnail_path else None,
            }
        )

    declared = manifest.get("counts") if isinstance(manifest.get("counts"), dict) else {}
    return {
        **base,
        "status": "ready" if images else "empty",
        "message": (
            f"{len(images)} photograph(s) available"
            if len(images) == len(entries)
            else f"{len(images)} of {len(entries)} manifest photographs are present on disk; re-import to restore the rest."
        ),
        "generated_at": manifest.get("generated_at"),
        "generator": manifest.get("generator"),
        "attribution": manifest.get("attribution"),
        "source": manifest.get("source") if isinstance(manifest.get("source"), dict) else {},
        "selection": manifest.get("selection") if isinstance(manifest.get("selection"), dict) else {},
        "caveats": manifest.get("caveats") if isinstance(manifest.get("caveats"), dict) else {},
        "counts": {
            "selected": len(entries),
            "present": len(images),
            "available": declared.get("available", 0),
            "by_class": declared.get("by_class", {}),
        },
        "images": images,
    }


def public_subset(subset: dict[str, Any]) -> dict[str, Any]:
    """Strip the private relative-path keys before anything is sent to a client."""
    payload = {key: value for key, value in subset.items() if key != "root"}
    payload["images"] = [{key: value for key, value in item.items() if not key.startswith("_")} for item in subset.get("images", [])]
    return payload


def find(subset: dict[str, Any], photo_id: str) -> dict[str, Any] | None:
    if not SAFE_ID.match(photo_id or ""):
        return None
    return next((item for item in subset.get("images", []) if item["id"] == photo_id), None)


def resolve_file(root: Path, subset: dict[str, Any], photo_id: str, *, variant: str = "full") -> Path | None:
    """Resolve the stored bytes for one photo, falling back to the full image when no thumbnail exists."""
    entry = find(subset, photo_id)
    if not entry:
        return None
    if variant == "thumb":
        thumb = _safe_member(Path(root), entry.get("_thumb_relative"))
        if thumb is not None:
            return thumb
    return _safe_member(Path(root), entry.get("_file_relative"))
