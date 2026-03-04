---
name: listing-doc-pipeline
description: Use this skill when running or debugging the staged oz-doc-processor pipeline for any listing in the oz-doc-processor repository. Covers convert -> classify -> extract, plus single-agent re-runs.
---

# Listing Document Pipeline Skill

This skill documents the current **three-stage pipeline** in `oz-doc-processor/`:

1. Convert source documents to markdown artifacts.
2. Classify each source file and copy assets into category buckets.
3. Run extraction agents to produce final listing JSON.

All scripts operate on directories under `listing-docs/`.

> **Prerequisite**: Always use the `uv-management` skill when running Python in this repo. Use `uv run python <script>`.

---

## Repository Layout

```text
oz-doc-processor/
├── listing-docs/                       # One folder per listing
│   ├── 491-Baltic-Brooklyn-NY/
│   ├── Lakewire-Lakeland-FL/
│   └── <other-listings>/
├── orchestrate_pipeline.py               # Main staged orchestrator
├── process_listing.py                    # Stage 1 conversion
├── src/pipeline/classify_and_bucket.py   # Stage 2 classification + buckets
├── run_modular_pipeline.py               # Stage 3 extraction
├── mistral_ocr.py                        # PDF OCR
├── excel_processor.py                    # Excel → Markdown
├── run_area_summary_ocr.py               # One-off OCR helper
├── src/
│   ├── config.py                         # Centralized env settings
│   ├── agents/
│   │   ├── document_classifier.py        # Classifier agent
│   │   ├── base_extractor.py
│   │   └── agents.py                     # Overview, Financial, Property, Market, Sponsor
│   └── pipeline/
│       └── classify_and_bucket.py        # Stage 2 implementation
```

---

## Stage 1 — Convert (`--stage convert`)

### What it does
- Scans `listing-docs/<ListingFolder>/` for processable files: `.pdf`, `.xlsx`, `.xls`, `.md`.
- PDF: runs Mistral OCR, stores raw OCR JSON, converts OCR output to markdown.
- Excel: converts all sheets to markdown tables via pandas.
- Markdown: reads supplemental markdown directly.
- Writes consolidated markdown with per-file `SOURCE FILE:` headers.

### Stage 1 artifacts
- `temp/<stem>_ocr.json` (PDF OCR JSON)
- `temp/<stem>.md` (per-file markdown)
- `images/<stem>/` and `images/<stem>/image_descriptions.json`
- `<listing_name>_markdown.md` consolidated markdown

### Run Stage 1

```bash
uv run python orchestrate_pipeline.py "Lakewire-Lakeland-FL" --stage convert
```

Direct run:

```bash
uv run python process_listing.py "Lakewire-Lakeland-FL"
```

---

## Stage 2 — Classify + Bucket (`--stage classify`)

### What it does
- Builds file previews for classification:
  - PDF/MD: first lines from converted text
  - Excel: first 10 lines per sheet section (configurable with `CLASSIFIER_EXCEL_SHEET_LINES`)
- Classifies each processable file into one category:
  - `om`
  - `proforma`
  - `research`
  - `supplemental`
- Clears and regenerates buckets on each run.
- Copies both source + converted markdown into:
  - `buckets/<category>/source/`
  - `buckets/<category>/temp/`
- Writes `doc_manifest.json` with deterministic metadata.

### Stage 2 output example paths
- `doc_manifest.json`
- `buckets/om/source/...`
- `buckets/om/temp/...`
- `buckets/proforma/source/...`
- `buckets/proforma/temp/...`
- `buckets/research/source/...`
- `buckets/research/temp/...`
- `buckets/supplemental/source/...`
- `buckets/supplemental/temp/...`

### Run Stage 2

```bash
uv run python orchestrate_pipeline.py "Lakewire-Lakeland-FL" --stage classify
```

---

## Stage 3 — Extract (`--stage extract`)

### What it does
- Requires `doc_manifest.json` (strict fail if missing).
- Reads per-file markdown from bucketed paths in the manifest.
- Renders 5 extraction agents:
  - `overview`
  - `financial`
  - `property`
  - `market`
  - `sponsor`
- Outputs final JSON with model name in filename:
  - `<listing_name>_modular_listing_<EXTRACTION_MODEL_SANITIZED>.json`
  - example: `lakewire_lakeland_fl_markdown_modular_listing_gemini-3-flash-preview.json`

### Run full extract

```bash
uv run python orchestrate_pipeline.py "Lakewire-Lakeland-FL" --stage extract
```

### Single agent rerun

```bash
uv run python orchestrate_pipeline.py "Lakewire-Lakeland-FL" --stage extract --agent financial
```

Direct extraction run (markdown path):

```bash
uv run python run_modular_pipeline.py "listing-docs/Lakewire-Lakeland-FL/lakewire_lakeland_fl_markdown.md" --agent overview
```

---

## Run all stages

```bash
uv run python orchestrate_pipeline.py "Lakewire-Lakeland-FL"
```

Equivalent to `--stage all`.

---

## Environment Variables (`.env`)

Required:

- `GEMINI_API_KEY`
- `MISTRAL_API_KEY`

Optional / pipeline behavior:

- `CLASSIFIER_MODEL`
- `CLASSIFIER_LINES` (default `100`)
- `CLASSIFIER_EXCEL_SHEET_LINES` (default `10`)
- `EXTRACTION_MODEL` (default `gemini-3-flash-preview`)

---

## Troubleshooting

- `doc_manifest.json not found`: run Stage 2 first.
- `Missing converted markdown`: rerun Stage 1.
- `Single-agent extract requires existing output`: rerun full extract first for that model.
- `Listing directory does not exist`: check folder name under `listing-docs/`.
