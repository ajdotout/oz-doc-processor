from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.prompts import financial, market, overview, property, sponsor


AGENT_PROMPTS = {
    "overview": overview,
    "financial": financial,
    "property": property,
    "market": market,
    "sponsor": sponsor,
}

CACHE_SCHEMA_VERSION = "agent-cache-v1"
_CACHE_ROOT = "agent_cache"
_PIPELINE_DIR = "extraction"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_json_dumps(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_payload(payload: Any) -> str:
    return _sha256(_stable_json_dumps(payload))


def sanitize_model_name(model_name: str) -> str:
    import re

    sanitized = re.sub(r"[^a-zA-Z0-9_.-]+", "_", model_name.strip())
    return sanitized or "unknown-model"


def cache_pipeline_dir(listing_dir: Path, model_name: str) -> Path:
    return listing_dir / _CACHE_ROOT / _PIPELINE_DIR / sanitize_model_name(model_name)


def cache_agent_paths(listing_dir: Path, model_name: str, agent_name: str):
    base_dir = cache_pipeline_dir(listing_dir, model_name) / agent_name
    return base_dir / "result.json", base_dir / "meta.json"


def compute_manifest_signature(manifest: Dict[str, Any], file_entries: Optional[list[dict]] = None) -> str:
    entries = file_entries if file_entries is not None else manifest.get("files", [])
    if not isinstance(entries, list):
        entries = []

    normalized_entries = []
    for entry in sorted(entries, key=lambda item: str((item or {}).get("filename", ""))):
        if not isinstance(entry, dict):
            continue
        normalized_entries.append(
            {
                "filename": entry.get("filename"),
                "category": entry.get("category"),
                "source_path": entry.get("source_path"),
                "temp_md_path": entry.get("temp_md_path"),
                "file_hash": entry.get("file_hash"),
            }
        )

    payload = {
        "version": manifest.get("version"),
        "listing": manifest.get("listing"),
        "classified_with": manifest.get("classified_with"),
        "files": normalized_entries,
    }
    return _hash_payload(payload)


def compute_prompt_signature(agent_name: str) -> str:
    prompt_module = AGENT_PROMPTS[agent_name]
    return _hash_payload({"agent": agent_name, "prompt": prompt_module.SYSTEM_PROMPT})


def compute_agent_input_signature(agent_name: str, agent_content: str, manifest_signature: str, prompt_signature: str) -> str:
    return _hash_payload(
        {
            "agent": agent_name,
            "manifest_signature": manifest_signature,
            "prompt_signature": prompt_signature,
            "content": agent_content,
        }
    )


def _safe_load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _safe_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_cached_agent_output(
    listing_dir: Path,
    model_name: str,
    agent_name: str,
    manifest_signature: str,
    prompt_signature: str,
    input_signature: str,
) -> Optional[Dict[str, Any]]:
    result_path, meta_path = cache_agent_paths(listing_dir, model_name, agent_name)
    meta = _safe_load_json(meta_path)
    if not meta:
        return None

    if meta.get("status") != "success":
        return None
    if meta.get("agent") != agent_name or meta.get("model") != model_name:
        return None
    if meta.get("manifest_signature") != manifest_signature:
        return None
    if meta.get("prompt_signature") != prompt_signature:
        return None
    if meta.get("input_signature") != input_signature:
        return None

    result = _safe_load_json(result_path)
    if not result:
        return None

    output = result.get("output")
    if not isinstance(output, dict):
        return None
    return output


def write_cached_agent_output(
    listing_dir: Path,
    model_name: str,
    agent_name: str,
    output: Dict[str, Any],
    manifest_signature: str,
    prompt_signature: str,
    input_signature: str,
) -> Path:
    result_path, meta_path = cache_agent_paths(listing_dir, model_name, agent_name)

    _safe_write_json(
        result_path,
        {
            "schema_version": CACHE_SCHEMA_VERSION,
            "agent": agent_name,
            "model": model_name,
            "status": "success",
            "output": output,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    _safe_write_json(
        meta_path,
        {
            "schema_version": CACHE_SCHEMA_VERSION,
            "agent": agent_name,
            "model": model_name,
            "status": "success",
            "manifest_signature": manifest_signature,
            "prompt_signature": prompt_signature,
            "input_signature": input_signature,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return result_path
