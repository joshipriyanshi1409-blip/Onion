#!/usr/bin/env python3
"""Build a small, attributed field-photo subset from the Zenodo onion image pack for the demo.

The source pack (Zenodo record 20254934, "Image Dataset of Red and White Onion Bulbs and
Leaves", CC BY 4.0) is ~1.5 GB and 16,300 images. The demo only needs a few dozen real
photographs, so this script extracts a deterministic, stratified subset next to a manifest
that records provenance, licence and the exact file each image came from.

Typical use, after downloading the archive (or if you already unpacked it):

    python data/demo/import_zenodo_onions.py --zip "~/Downloads/Onion Image Dataset.zip"
    python data/demo/import_zenodo_onions.py --source-dir "~/Downloads/Onion Image Dataset"
    python data/demo/import_zenodo_onions.py --download            # ~1.5 GB over the network

The API reads the subset per request, so a browser reload is enough: the photos appear in
**New inspection** and can be queued for annotation in **Dataset & labels**.

The images are photographs without instance masks. They are demo/annotation input, not
adjudicated ground truth, and importing them does not create a trained model.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import sys
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from xml.etree import ElementTree

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
RECORD_ID = "20254934"
CONCEPT_ID = "20254933"
DOI = "10.5281/zenodo.20254934"
TITLE = "Image Dataset of Red and White Onion Bulbs and Leaves"
CREATORS = [
    {"name": "Vinaya Kulkarni", "affiliation": "Vishwakarma University", "role": "Data collector"},
    {"name": "Sanjesh Pawale", "affiliation": "Vishwakarma University", "role": "Data curator"},
    {"name": "Suryawanshi Yogesh", "affiliation": "Vishwakarma University", "orcid": "0000-0002-1068-267X"},
]
LICENCE = "CC-BY-4.0"
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/legalcode"
PUBLICATION_DATE = "2026-05-17"
ARCHIVE_NAME = "Onion Image Dataset.zip"
ARCHIVE_URL = f"https://zenodo.org/api/records/{RECORD_ID}/files/{urllib.parse.quote(ARCHIVE_NAME)}/content"
METADATA_URL = f"https://zenodo.org/api/records/{RECORD_ID}/files/All%20Metadata.xlsx/content"
ARCHIVE_MD5 = "8d463f41734ebfb059e2dc03c7eb6def"
ARCHIVE_BYTES = 1_608_716_340
REPORTED_TOTAL_IMAGES = 16_300
SCHEMA = "pyaazscan-field-photo-subset/1"
ROOT = Path(__file__).resolve().parents[2]

PART_PATTERNS = (
    ("leaves", re.compile(r"\bleaf\b|\bleaves\b", re.I)),
    ("bulbs", re.compile(r"\bbulb(s)?\b|\bweeds?\b", re.I)),
)
VARIETY_PATTERNS = (
    ("red", re.compile(r"\bred\b|\bpurple\b|\bmaharashtra\b|\bnasik\b|\bnashik\b", re.I)),
    ("white", re.compile(r"\bwhite\b|\bpale\b|\bnavi\b|\bsafe\b", re.I)),
)
ARRANGEMENT_PATTERNS = (
    ("multiple", re.compile(r"\bmultiple\b|\bmany\b|\bgroup(s)?\b|\bcluster(s)?\b|\bheap(s)?\b", re.I)),
    ("single", re.compile(r"\bsingle\b|\bone\b|\bisolated\b", re.I)),
)
INDEX_PATTERN = re.compile(r"(\d+)")


def classify_path(relative: PurePosixPath) -> dict[str, str]:
    """Derive coarse classes from the pack's folder names, falling back to `unclassified`."""
    components = [part for part in relative.parts[:-1]]
    text = " / ".join(components)
    found = {"part": "unknown", "variety": "unclassified", "health": "unclassified", "arrangement": "unclassified"}
    for label, pattern in PART_PATTERNS:
        if pattern.search(text):
            found["part"] = label
            break
    for label, pattern in VARIETY_PATTERNS:
        if pattern.search(text):
            found["variety"] = label
            break
    # `unhealthy` must be tested before `healthy`, which it contains.
    if re.search(r"\bunhealthy\b|\bsick\b|\bdiseased\b|\bdamaged\b|\brotten\b", text, re.I):
        found["health"] = "unhealthy"
    elif re.search(r"\bhealthy\b|\bfresh\b|\bgood\b", text, re.I):
        found["health"] = "healthy"
    for label, pattern in ARRANGEMENT_PATTERNS:
        if pattern.search(text):
            found["arrangement"] = label
            break
    return found


def series_index(stem: str) -> int:
    numbers = INDEX_PATTERN.findall(stem)
    return int(numbers[-1]) if numbers else 0


class SourceArchive:
    """Uniform read access over a ZIP member set or an unpacked directory tree."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._zip: zipfile.ZipFile | None = None
        self.entries: list[tuple[PurePosixPath, int]] = []
        if path.is_dir():
            for item in sorted(path.rglob("*")):
                if not item.is_file() or item.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                if any(part.startswith((".", "__MACOSX")) for part in item.relative_to(path).parts):
                    continue
                self.entries.append((PurePosixPath(item.relative_to(path)), item.stat().st_size))
        else:
            self._zip = zipfile.ZipFile(path)
            for info in self._zip.infolist():
                if info.is_dir():
                    continue
                member = PurePosixPath(info.filename.replace("\\", "/"))
                if not member.parts or member.parts[0].startswith((".", "__MACOSX")):
                    continue
                if Path(member.name).suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                self.entries.append((member, info.file_size))

    def read(self, relative: PurePosixPath) -> bytes:
        if self._zip is not None:
            return self._zip.read(str(relative))
        return (self.path / Path(*relative.parts)).read_bytes()

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()

    def __enter__(self) -> "SourceArchive":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _ensure_repo_on_path() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


def candidate_stream(entries: Iterable[tuple[PurePosixPath, int]], *, include_leaves: bool, min_bytes: int) -> tuple[list[tuple[PurePosixPath, dict[str, str]]], dict[str, int]]:
    ordered = sorted(entries, key=lambda item: (str(item[0])))
    buckets: dict[tuple[str, str, str, str], list[tuple[PurePosixPath, dict[str, str]]]] = defaultdict(list)
    skipped_leaves = 0
    too_small = 0
    for relative, size in ordered:
        if size < min_bytes:
            too_small += 1
            continue
        info = classify_path(relative)
        if info["part"] == "leaves" and not include_leaves:
            skipped_leaves += 1
            continue
        key = (info["part"], info["variety"], info["health"], info["arrangement"])
        buckets[key].append((relative, info))
    # Round-robin across classes so the subset shows variety, health and arrangement, not one folder.
    interleaved: list[tuple[PurePosixPath, dict[str, str]]] = []
    keys = sorted(buckets)
    position = 0
    while True:
        added = False
        for key in keys:
            bucket = buckets[key]
            if position < len(bucket):
                interleaved.append(bucket[position])
                added = True
        if not added:
            break
        position += 1
    stats = {"bucket_count": len(keys), "skipped_leaf_images": skipped_leaves, "skipped_below_min_bytes": too_small}
    return interleaved, stats


def detect_onions(raw: bytes) -> int | None:
    """Run the active visual engine on a candidate; return its region count (None if unavailable)."""
    _ensure_repo_on_path()
    try:
        from backend.services.rules_engine import DEFAULT_RULES
        from ml.inference.pipeline import ImageQualityError, analyze_image
    except Exception:
        return None
    try:
        result = analyze_image(raw, DEFAULT_RULES)
    except ImageQualityError:
        return 0
    except Exception:
        return None
    return int(len(result.get("onions") or []))


def read_metadata_workbook(path: Path) -> tuple[dict[str, dict[str, str]], str]:
    """Best-effort read of the pack's metadata sheet using only the standard library."""
    try:
        rows = _read_xlsx_rows(path)
    except Exception as exc:  # The sheet is optional context, never a hard dependency.
        return {}, f"metadata sheet not parsed ({type(exc).__name__}: {exc})"
    if not rows:
        return {}, "metadata sheet contained no readable rows"
    header = [str(cell).strip() for cell in rows[0]]
    key_column = 0
    for index, name in enumerate(header):
        if re.search(r"image|file|name|id|no\.?|serial", name, re.I):
            key_column = index
            break
    lookup: dict[str, dict[str, str]] = {}
    for row in rows[1:]:
        if not row:
            continue
        key = str(row[key_column]).strip() if key_column < len(row) else ""
        stem = Path(key).stem.lower() or key.lower()
        if not stem:
            continue
        record: dict[str, str] = {}
        for index, name in enumerate(header):
            if not name or index >= len(row):
                continue
            value = str(row[index]).strip()
            if value:
                record[name] = value
        lookup[stem] = record
    return lookup, f"{len(lookup)} rows"


def _read_xlsx_rows(path: Path) -> list[list[Any]]:
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(path) as book:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in book.namelist():
            root = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
            for item in root.findall(f"{ns}si"):
                shared.append("".join(node.text or "" for node in item.iter(f"{ns}t")))
        sheet_name = next((name for name in book.namelist() if re.match(r"xl/worksheets/sheet1\.xml$", name)), None)
        if sheet_name is None:
            sheet_name = next((name for name in book.namelist() if name.startswith("xl/worksheets/sheet")), "")
        if not sheet_name:
            return []
        rows: list[list[Any]] = []
        sheet = ElementTree.fromstring(book.read(sheet_name))
        for row in sheet.iter(f"{ns}row"):
            values: dict[int, Any] = {}
            for cell in row.findall(f"{ns}c"):
                reference = cell.get("r") or ""
                column = 0
                for character in re.match(r"[A-Z]+", reference).group(0) if re.match(r"[A-Z]+", reference) else "":
                    column = column * 26 + (ord(character) - 64)
                kind = cell.get("t")
                if kind == "s":
                    node = cell.find(f"{ns}v")
                    value = shared[int(node.text)] if node is not None and node.text else ""
                elif kind == "inlineStr":
                    value = "".join(node.text or "" for node in cell.iter(f"{ns}t"))
                else:
                    node = cell.find(f"{ns}v")
                    value = node.text if node is not None else ""
                values[column - 1 if column else len(values)] = value
            if values:
                width = max(values) + 1
                rows.append([values.get(index, "") for index in range(width)])
        return rows


def download(url: str, destination: Path, *, expected_md5: str | None = None, chunk: int = 1 << 20) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.md5()
    request = urllib.request.Request(url, headers={"User-Agent": "PYAazScan-demo-import/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        seen = 0
        while True:
            block = response.read(chunk)
            if not block:
                break
            digest.update(block)
            handle.write(block)
            seen += len(block)
            if total:
                print(f"\r  downloaded {seen / 1e6:7.1f} / {total / 1e6:.1f} MB", end="", flush=True)
    print()
    if expected_md5 and digest.hexdigest() != expected_md5:
        partial.unlink(missing_ok=True)
        raise SystemExit(f"Downloaded file checksum mismatch (expected {expected_md5}, got {digest.hexdigest()}).")
    partial.replace(destination)
    return digest.hexdigest()


def write_outputs(output: Path, manifest: dict[str, Any]) -> None:
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    source = manifest["source"]
    attribution = "\n".join(
        [
            "# Field-photo subset — provenance and licence",
            "",
            f"Generated by `data/demo/import_zenodo_onions.py` on {manifest['generated_at']}.",
            "This directory holds a locally generated subset. `data/demo/zenodo/` is git-ignored; commit a subset elsewhere only if the deployment needs to ship it.",
            "",
            "## Source",
            "",
            f"- Dataset: **{TITLE}** (v1, published {source['publication_date']})",
            f"- Record: https://zenodo.org/records/{source['record_id']} · concept {source['concept_id']}",
            f"- DOI: [{source['doi']}](https://doi.org/{source['doi']})",
            f"- Licence: **{source['licence']}** — {LICENCE_URL}",
            f"- Full published archive: `{ARCHIVE_NAME}` ({source['archive_bytes']:,} bytes; published md5 `{source['archive_md5_expected']}`)",
            "- Authors: " + "; ".join(f"{item['name']} ({item.get('affiliation', '—')})" for item in CREATORS),
            "- Collection: onion bulbs and leaves photographed in local markets in Pune, Maharashtra, India, Jul 2025 – Feb 2026.",
            "",
            "## Required attribution",
            "",
            "> " + manifest["attribution"],
            "",
            "Keep this notice with any copy, screen recording or exported report that redistributes these images.",
            "",
            "## What these images are — and are not",
            "",
            f"- Photograph bytes are copied verbatim from the source archive (`{source['archive_name']}`): no cropping, no re-encoding.",
            f"- Archive integrity: {source['archive_md5_actual']}{'' if not source['archive_md5_matches_published'] else ' — matches the published checksum'}{'; published checksum ' + source['archive_md5_expected'] if not source['archive_md5_matches_published'] else ''}.",
            f"- {manifest['caveats']['labels_note']}",
            f"- {manifest['caveats']['training_note']}",
            "- The pack contains no 50 mm calibration reference, so millimetre diameter stays unavailable and the demo reports it as such.",
            f"- {len(manifest['images'])} of {source['reported_total_images']:,} images are present here; selection is deterministic "
            f"(seed {manifest['selection']['seed']}, strategy: {manifest['selection']['strategy']}).",
            "",
        ]
    )
    (output / "ATTRIBUTION.md").write_text(attribution, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--zip", type=Path, help="Path to the published 'Onion Image Dataset.zip'.")
    source.add_argument("--source-dir", type=Path, help="Path to the already-unpacked dataset directory.")
    source.add_argument("--download", action="store_true", help=f"Fetch the ~{ARCHIVE_BYTES // 10**6} MB archive from Zenodo first.")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache" / "zenodo", help="Where --download stores the archive.")
    parser.add_argument("--metadata", type=Path, help="Optional 'All Metadata.xlsx' from the same record, joined by file stem.")
    parser.add_argument("--download-metadata", action="store_true", help="With a cached/fetched archive, also fetch the ~1.3 MB metadata workbook.")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "demo" / "zenodo", help="Subset destination (git-ignored by default).")
    parser.add_argument("--limit", type=int, default=24, help="How many photographs to copy into the demo subset.")
    parser.add_argument("--seed", type=int, default=7, help="Recorded in the manifest; selection is deterministic without it.")
    parser.add_argument("--include-leaves", action="store_true", help="Leaf photos are excluded by default: the app inspects bulbs.")
    parser.add_argument("--min-bytes", type=int, default=12_000, help="Ignore suspiciously small image entries.")
    parser.add_argument("--min-edge", type=int, default=260, help="Ignore images whose short edge is smaller than this (the engine needs 200 px).")
    parser.add_argument("--max-candidates", type=int, default=900, help="Upper bound on images decoded while selecting.")
    parser.add_argument("--no-verify-detection", action="store_true", help="Skip running the CV engine on candidates.")
    parser.add_argument("--dry-run", action="store_true", help="Report the discovered archive structure and stop.")
    parser.add_argument("--force", action="store_true", help="Replace an existing subset directory.")
    parser.add_argument("--keep-archive", action="store_true", help="Do not delete a file fetched with --download.")
    parser.add_argument("--skip-checksum", action="store_true", help="Skip the md5 check against the published archive checksum.")
    parser.add_argument("--thumbnail-edge", type=int, default=360, help="Longest edge of the generated grid thumbnails; 0 disables them.")
    args = parser.parse_args()

    if args.limit < 1 or args.limit > 500:
        parser.error("--limit must be between 1 and 500.")

    for flag in ("zip", "source_dir", "metadata", "output", "cache_dir"):
        if getattr(args, flag) is not None:
            setattr(args, flag, Path(getattr(args, flag)).expanduser())
    archive_path = args.zip or args.source_dir
    downloaded = False
    if args.download:
        archive_path = args.cache_dir / ARCHIVE_NAME
        if archive_path.is_file():
            print(f"Reusing cached archive: {archive_path}")
        else:
            print(f"Downloading {ARCHIVE_NAME} (~{ARCHIVE_BYTES / 10**6:.0f} MB) … this can take a while.")
            download(ARCHIVE_URL, archive_path, expected_md5=ARCHIVE_MD5)
            downloaded = True
    if args.download_metadata:
        metadata_workbook = args.cache_dir / "All Metadata.xlsx"
        if not metadata_workbook.is_file():
            print("Downloading All Metadata.xlsx …")
            download(METADATA_URL, metadata_workbook)
        args.metadata = metadata_workbook
    if not archive_path or not archive_path.exists():
        parser.error(f"Source not found: {archive_path}")
    if args.metadata and not args.metadata.is_file():
        parser.error(f"Metadata workbook not found: {args.metadata}")

    archive_md5: str | None = None
    if archive_path.is_file() and not args.skip_checksum:
        digest = hashlib.md5()
        with archive_path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 22), b""):
                digest.update(block)
        archive_md5 = digest.hexdigest()
        if archive_path.name == ARCHIVE_NAME and archive_md5 != ARCHIVE_MD5:
            print(f"\nNote: this archive's md5 is {archive_md5}, not the published {ARCHIVE_MD5}.")
            print("      Continuing, but the provenance record notes the difference.\n")

    with SourceArchive(archive_path) as bundle:
        entries = bundle.entries
        if not entries:
            raise SystemExit("No readable images were found in that archive or directory.")

        if args.dry_run:
            tree: dict[str, int] = defaultdict(int)
            for relative, _size in entries:
                info = classify_path(relative)
                tree[" / ".join(f"{k}={v}" for k, v in info.items() if v not in {"unknown", "unclassified"}) or "(unclassified)"] += 1
            print(f"{len(entries):,} image entries in {archive_path.name}\n")
            for label in sorted(tree):
                print(f"  {tree[label]:7,}  {label}")
            print("\nClass counts come from folder names. Pass --include-leaves to keep leaf photos.")
            return 0

        ordered, selection_stats = candidate_stream(entries, include_leaves=args.include_leaves, min_bytes=args.min_bytes)
        if not ordered:
            raise SystemExit("Every entry was filtered out; try --include-leaves or a lower --min-bytes.")

        output: Path = args.output
        if output.exists() and any(output.iterdir()):
            if not args.force:
                raise SystemExit(f"{output} is not empty. Re-run with --force to replace it.")
            shutil.rmtree(output)
        (output / "images").mkdir(parents=True, exist_ok=True)
        thumbs_dir = output / "thumbs"
        if args.thumbnail_edge >= 64:
            thumbs_dir.mkdir(parents=True, exist_ok=True)

        metadata_lookup: dict[str, dict[str, str]] = {}
        metadata_status = "not supplied"
        if args.metadata:
            metadata_lookup, metadata_status = read_metadata_workbook(args.metadata)

        verify = not args.no_verify_detection
        if verify:
            _ensure_repo_on_path()
        try:
            from PIL import Image, ImageOps
        except ImportError as exc:
            raise SystemExit("Pillow is required (pip install -r requirements.txt).") from exc

        selected: list[dict[str, Any]] = []
        seen_hashes: set[str] = set()
        inspected = 0
        rejected: dict[str, int] = defaultdict(int)
        for relative, info in ordered:
            if len(selected) >= args.limit:
                break
            if inspected >= args.max_candidates:
                break
            inspected += 1
            try:
                raw = bundle.read(relative)
            except Exception:
                rejected["unreadable"] += 1
                continue
            digest = hashlib.sha256(raw).hexdigest()
            if digest in seen_hashes:
                rejected["duplicate-bytes"] += 1
                continue
            with Image.open(io.BytesIO(raw)) as image:
                image = image.convert("RGB")
                width, height = image.size
            if width < args.min_edge or height < args.min_edge:
                rejected["below-minimum-size"] += 1
                continue
            detections = detect_onions(raw) if verify else None
            if verify and detections == 0:
                rejected["no-visible-onion-region"] += 1
                continue
            photo_id = Path(relative).stem
            if any(item["id"] == photo_id for item in selected):
                rejected["duplicate-name"] += 1
                continue
            filename = f"{photo_id}.jpg"
            (output / "images" / filename).write_bytes(raw)
            thumbnail = None
            if args.thumbnail_edge >= 64:
                with Image.open(io.BytesIO(raw)) as picture:
                    picture = ImageOps.exif_transpose(picture).convert("RGB")
                    picture.thumbnail((args.thumbnail_edge, args.thumbnail_edge), Image.LANCZOS)
                    thumbnail_path = thumbs_dir / filename
                    picture.save(thumbnail_path, "JPEG", quality=74, optimize=True)
                thumbnail = f"thumbs/{filename}"
            seen_hashes.add(digest)
            selected.append(
                {
                    "id": photo_id,
                    "file": f"images/{filename}",
                    "thumbnail": thumbnail,
                    "bytes": len(raw),
                    "sha256": digest,
                    "width": width,
                    "height": height,
                    "orientation": "landscape" if width >= height else "portrait",
                    "source_path": str(relative),
                    **info,
                    "detections_expected": detections,
                    "metadata": metadata_lookup.get(photo_id.lower(), {}),
                }
            )

    by_class: dict[str, int] = defaultdict(int)
    for item in selected:
        by_class[f"{item['part']}/{item['variety']}/{item['health']}/{item['arrangement']}"] += 1

    manifest = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "data/demo/import_zenodo_onions.py",
        "attribution": (
            "Kulkarni, V., Pawale, S., & Yogesh, S. (2026). Image Dataset of Red and White Onion Bulbs "
            f"and Leaves (Version 1) [Data set]. Zenodo. https://doi.org/{DOI} (CC BY 4.0)"
        ),
        "source": {
            "title": TITLE,
            "record_id": RECORD_ID,
            "concept_id": CONCEPT_ID,
            "doi": DOI,
            "url": f"https://zenodo.org/records/{RECORD_ID}",
            "publication_date": PUBLICATION_DATE,
            "licence": LICENCE,
            "licence_url": LICENCE_URL,
            "creators": CREATORS,
            "archive_name": archive_path.name,
            "archive_bytes": archive_path.stat().st_size,
            "archive_md5_expected": ARCHIVE_MD5,
            "archive_md5_actual": archive_md5 or "not computed",
            "archive_md5_matches_published": bool(archive_md5) and archive_md5 == ARCHIVE_MD5,
            "reported_total_images": REPORTED_TOTAL_IMAGES,
            "archive_entries_seen": len(entries),
            "collection_context": "Onion bulbs and leaves photographed in local markets in Pune, Maharashtra, India, July 2025 – February 2026.",
        },
        "selection": {
            "strategy": "deterministic round-robin across folder classes, then per-class order by file name",
            "seed": args.seed,
            "limit": args.limit,
            "include_leaves": args.include_leaves,
            "verified_with_cv_engine": verify,
            "candidates_decoded": inspected,
            "candidate_stats": selection_stats,
            "rejected": dict(rejected),
            "metadata_workbook": metadata_status,
        },
        "counts": {"available": len(entries), "selected": len(selected), "by_class": dict(sorted(by_class.items()))},
        "caveats": {
            "labels_note": (
                "Class fields (part/variety/health/arrangement) are copied from the publisher's folder names. "
                "There are no onion-level polygons or per-onion defect labels, and no independent quality "
                "adjudication, buyer lot identity or sampling design."
            ),
            "training_note": (
                "These photos are demo input and annotation starting material. They do not certify grading "
                "accuracy and do not by themselves make this repository a trained or evaluated model."
            ),
            "calibration_note": "No printed 50 mm reference appears in the pack, so millimetre diameter stays unavailable for these images.",
        },
        "images": sorted(selected, key=lambda item: series_index(item["id"])),
    }
    write_outputs(output, manifest)

    if args.download and not args.keep_archive and args.cache_dir.is_dir():
        archive_path.unlink(missing_ok=True)
        cache_dir = archive_path.parent
        if cache_dir.is_dir() and not any(cache_dir.iterdir()):
            cache_dir.rmdir()
        print("Removed the downloaded archive (pass --keep-archive to retain it).")

    print(f"\nWrote {len(selected)} photograph(s) of {len(entries):,} entries to {output}")
    if verify:
        print(f"Decoded {inspected} candidate image(s); skipped {dict(rejected) or 'nothing'}.")
    for label, count in sorted(by_class.items()):
        print(f"  {count:3d}  {label}")
    if not selected:
        print("\nNothing was selected. Re-run with --no-verify-detection (or --include-leaves) to widen the pool.")
        return 1
    if rejected.get("no-visible-onion-region", 0) > len(selected):
        print(f"\nNote: {rejected['no-visible-onion-region']} candidate(s) produced no usable bulb region for the current"
              " demo engine (common for pale varieties on light surfaces, crowded heaps, or strong shadows)."
              " They stay in the published pack; only images the engine can see are offered in the demo.")
    print(f"\nReload the app to see them. Licence: {LICENCE}. Attribution stored in {output / 'ATTRIBUTION.md'}")
    if downloaded:
        print("Keep the downloaded archive out of git; only the small subset is meant to sit next to the app.")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
