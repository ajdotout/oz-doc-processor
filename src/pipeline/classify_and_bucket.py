import hashlib
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from src.config import (
    PROCESSABLE_EXTS,
    CLASSIFIER_LINES,
    CLASSIFIER_EXCEL_SHEET_LINES,
    DOC_CATEGORIES,
)
from src.agents.document_classifier import DocumentClassifier


def _safe_read_text(path: Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        logging.error(f"Failed to read {path}: {exc}")
        return fallback


def _file_hash(path: Path) -> str:
    try:
        data = path.read_bytes()
        return hashlib.sha256(data).hexdigest()
    except Exception:
        return ""


def build_excel_sheet_preview(markdown_text: str, lines_per_sheet: int = CLASSIFIER_EXCEL_SHEET_LINES) -> str:
    """
    For a converted excel markdown blob, keep only the first `lines_per_sheet` lines from each sheet section.
    Uses sheet headers as anchors and keeps them in the preview.
    """
    if "### EXTERNAL DATA SOURCE: Excel Sheet - " not in markdown_text:
        lines = markdown_text.splitlines()
        return "\n".join(lines[: lines_per_sheet + 1])

    marker_re = re.compile(r"(?m)^### EXTERNAL DATA SOURCE: Excel Sheet - ")
    parts = re.split(marker_re, markdown_text)
    if not parts:
        return ""

    snippets: List[str] = []
    for idx, part in enumerate(parts):
        normalized = part.strip("\n")
        if not normalized:
            continue

        if idx == 0:
            lines = normalized.splitlines()
            if lines:
                snippets.append("\n".join(lines[: lines_per_sheet + 1]))
            continue

        # part is a sheet section without the split marker; re-add it for clarity
        with_marker = f"### EXTERNAL DATA SOURCE: Excel Sheet - {part}"
        lines = with_marker.splitlines()
        snippets.append("\n".join(lines[: lines_per_sheet + 1]))

    return "\n\n".join(snippets)


def _build_file_preview(file_path: Path, temp_dir: Path, classifier_lines: int, excel_lines: int) -> str:
    ext = file_path.suffix.lower()
    if ext == ".md":
        full_text = _safe_read_text(file_path)
        return "\n".join(full_text.splitlines()[:classifier_lines])

    if ext in [".pdf", ".xlsx", ".xls"]:
        temp_md = temp_dir / f"{file_path.stem}.md"
        markdown_text = _safe_read_text(temp_md)
        if not markdown_text:
            raise FileNotFoundError(
                f"No converted markdown found for {file_path.name}. "
                "Run convert stage before classify."
            )
        if ext in [".xlsx", ".xls"]:
            return build_excel_sheet_preview(markdown_text, lines_per_sheet=excel_lines)
        return "\n".join(markdown_text.splitlines()[:classifier_lines])

    return ""


def get_process_files(listing_dir: Path) -> List[Path]:
    all_files = sorted(listing_dir.glob("*"))
    excluded = {"temp", "images", "buckets"}
    return [
        f for f in all_files
        if f.is_file()
        and f.suffix.lower() in PROCESSABLE_EXTS
        and f.name not in {"doc_manifest.json", ".DS_Store"}
        and not f.name.endswith("_markdown.md")
        and f.parent.name not in excluded
    ]


def _copy_file(source_path: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination)


def classify_listing(
    listing_dir: Path,
    classifier: Optional[DocumentClassifier] = None,
    classifier_lines: int = CLASSIFIER_LINES,
    excel_lines: int = CLASSIFIER_EXCEL_SHEET_LINES,
    force_rebuild_buckets: bool = True,
) -> Path:
    listing_dir = Path(listing_dir)
    temp_dir = listing_dir / "temp"
    buckets_dir = listing_dir / "buckets"
    if force_rebuild_buckets:
        shutil.rmtree(buckets_dir, ignore_errors=True)

    for category in DOC_CATEGORIES:
        (buckets_dir / category / "source").mkdir(parents=True, exist_ok=True)
        (buckets_dir / category / "temp").mkdir(parents=True, exist_ok=True)

    process_files = get_process_files(listing_dir)
    if not process_files:
        raise RuntimeError(f"No processable files found in {listing_dir}")

    classifier = classifier or DocumentClassifier()
    manifest_files: List[Dict[str, object]] = []

    for source_file in process_files:
        ext = source_file.suffix.lower()
        preview = _build_file_preview(
            source_file,
            temp_dir=temp_dir,
            classifier_lines=classifier_lines,
            excel_lines=excel_lines,
        )
        if not preview.strip():
            logging.warning(f"No preview text for {source_file.name}; using filename fallback.")
            preview = source_file.name

        classification = classifier.run(source_file.name, preview)

        category = classification.category
        bucket_source_dir = buckets_dir / category / "source"
        bucket_temp_dir = buckets_dir / category / "temp"
        bucket_source_file = bucket_source_dir / source_file.name
        _copy_file(source_file, bucket_source_file)

        temp_output_name = f"{source_file.stem}.md"
        temp_dest = bucket_temp_dir / temp_output_name
        source_md = temp_dir / f"{source_file.stem}.md"
        if ext == ".md":
            shutil.copy2(source_file, bucket_temp_dir / temp_output_name)
        elif source_md.exists():
            _copy_file(source_md, temp_dest)
        else:
            raise RuntimeError(
                f"Missing converted markdown for {source_file.name}; "
                "rerun stage convert before classify."
            )

        manifest_files.append({
            "filename": source_file.name,
            "category": category,
            "reasoning": classification.reasoning,
            "file_hash": _file_hash(source_file),
            "source_path": str(source_file.relative_to(listing_dir)),
            "temp_md_path": str(temp_dest.relative_to(listing_dir)),
            "char_count": len(preview),
        })

        logging.info(
            f"[{category:>11}] {source_file.name} ({len(preview)} chars) "
            f"- {classification.reasoning}"
        )

    # Deterministic ordering for reproducibility.
    manifest_files.sort(key=lambda x: x["filename"])
    summary: Dict[str, int] = {category: 0 for category in DOC_CATEGORIES}
    for manifest_entry in manifest_files:
        summary[manifest_entry["category"]] += 1

    manifest = {
        "version": "1.0",
        "listing": listing_dir.name,
        "files": manifest_files,
        "classified_with": classifier.model_name,
    }

    manifest_path = listing_dir / "doc_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logging.info(f"Document manifest written: {manifest_path}")
    for category, count in summary.items():
        logging.info(f"{category}: {count} file(s)")
    return manifest_path
