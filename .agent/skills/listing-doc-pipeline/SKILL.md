---
name: listing-doc-pipeline
description: Use this skill when running or debugging the Dock Extraction and Dock Processing pipeline for any listing in the oz-doc-processor repository. Covers the full flow from raw PDFs/Excels → OCR → Markdown consolidation → AI agent extraction → final listing JSON output.
---

# Listing Doc Pipeline (Dock Extraction & Dock Processing)

This skill describes the **full two-phase pipeline** for processing OZ investment listing documents into structured JSON data. All scripts live in the root of `oz-doc-processor/` and operate on folders inside `listing-docs/`.

> **Prerequisite**: Always follow the `uv-management` skill when running any Python scripts in this repo. Use `uv run python <script>` — never bare `python`.

---

## Repository Layout

```
oz-doc-processor/
├── listing-docs/                     # One sub-folder per property
│   ├── 491-Baltic-Brooklyn-NY/       # Raw PDFs/Excels go here
│   ├── Lakewire-Lakeland-FL/         # Mixed: PDF + Excel supported
│   └── <other-properties>/
│
├── orchestrate_pipeline.py           # ⭐ MAIN ENTRY POINT (runs both phases)
├── process_listing.py                # Phase 1 — Extraction (OCR + Excel → Markdown)
├── run_modular_pipeline.py           # Phase 2 — Processing (Markdown → JSON via AI agents)
├── mistral_ocr.py                    # OCR engine (Mistral API)
├── excel_processor.py                # Excel → Markdown converter
├── run_area_summary_ocr.py           # One-off OCR for supplemental area-summary docs
│
└── src/
    ├── agents/
    │   ├── base_extractor.py         # Base agent class (pydantic-ai + Gemini model)
    │   └── agents.py                 # 5 specialized agents: Overview, Financial, Property, Market, Sponsor
    └── prompts/
        ├── overview.py
        ├── financial.py
        ├── property.py
        ├── market.py
        └── sponsor.py
```

---

## Phase 1 — Dock Extraction (`process_listing.py`)

Converts **all PDFs and Excel files** in the listing folder into a single consolidated Markdown file.

### What it does
1. Scans `listing-docs/<ListingName>/` for all `.pdf`, `.xlsx`, `.xls` files.
2. For each **PDF**: uploads to Mistral OCR API → saves raw JSON to `temp/` → parses to Markdown → extracts embedded images into `images/<stem>/`.
3. For each **Excel**: converts all sheets to Markdown tables using pandas.
4. Concatenates everything (with `SOURCE FILE:` headers) into one grand `<listing_name>_markdown.md`.

### Output artifacts (all inside the listing folder)
| Artifact | Description |
|---|---|
| `<name>_markdown.md` | Grand consolidated Markdown (input to Phase 2) |
| `temp/<stem>_ocr.json` | Raw Mistral OCR JSON per PDF |
| `temp/<stem>.md` | Per-file intermediate Markdown |
| `images/<stem>/` | Extracted images from each PDF |
| `images/<stem>/image_descriptions.json` | Bounding-box + annotation metadata for images |

### API keys required
- `MISTRAL_API_KEY` — for OCR (PDF only)

---

## Phase 2 — Dock Processing (`run_modular_pipeline.py`)

Runs **5 specialized AI agents in parallel** on the consolidated Markdown to produce a structured listing JSON.

### What it does
1. Reads the `<name>_markdown.md` produced by Phase 1.
2. Spins up 5 pydantic-ai agents (each backed by `gemini-3-flash-preview`):
   - **OverviewAgent** → hero, ticker metrics, compelling reasons, executive summary, investment cards
   - **FinancialAgent** → projections, capital stack, distribution timeline, tax benefits, waterfall
   - **PropertyAgent** → key facts, amenities, unit mix, location highlights, development timeline/phases
   - **MarketAgent** → market metrics, employers, demographics, key drivers, supply/demand, competitive analysis
   - **SponsorAgent** → intro, partnership, track record, leadership team, key partners, advantages, portfolio, fund structure
3. Assembles all outputs into a single `<name>_modular_listing_gemini3.json`.

### Output artifact
| Artifact | Description |
|---|---|
| `<name>_modular_listing_gemini3.json` | Final structured listing JSON (used by oz-homepage) |

### API keys required
- `GEMINI_API_KEY` — for all 5 AI extraction agents

---

## Running the Full Pipeline

The canonical entry point is `orchestrate_pipeline.py`, which chains Phase 1 → Phase 2 automatically.

### Most common command (full pipeline)
```bash
# From the oz-doc-processor root directory
uv run python orchestrate_pipeline.py "<ListingFolderName>"
```

### Examples for specific properties

**491 Baltic Brooklyn NY:**
```bash
uv run python orchestrate_pipeline.py "491-Baltic-Brooklyn-NY"
```

**Lakewire Lakeland FL:**
```bash
uv run python orchestrate_pipeline.py "Lakewire-Lakeland-FL"
```

> **Note**: The listing name must match the folder name inside `listing-docs/`. The script does case-insensitive matching, but exact folder name is safest.

---

## Running Phases Individually

### Phase 1 only (Extraction)
```bash
uv run python process_listing.py "491-Baltic-Brooklyn-NY"
```
This generates the consolidated markdown but does NOT run AI agents. Use this to:
- Verify OCR output before spending Gemini API credits
- Re-run extraction if source documents change

### Phase 2 only (Processing — requires Markdown already generated)
```bash
uv run python run_modular_pipeline.py "listing-docs/491-Baltic-Brooklyn-NY/491_baltic_brooklyn_ny_markdown.md"
```
Pass the **full path to the markdown file** as the argument.

### Re-running OCR on a supplemental document (one-off)
Edit `run_area_summary_ocr.py` to point to the correct listing and PDF, then:
```bash
uv run python run_area_summary_ocr.py
```

---

## Adding a New Listing

1. **Create the listing folder** inside `listing-docs/`:
   ```
   listing-docs/<Property-Name-Kebab-Case>/
   ```
2. **Drop raw documents** into the folder:
   - PDFs (Offering Memorandums, area summaries, etc.)
   - Excel files (HUD data, financial models, etc.)
   - **Supplemental `.md` files** (e.g., `EmailInfo.md` with sponsor email context, notes) — read directly, no OCR needed
   - Note: The pipeline auto-excludes the consolidated `*_markdown.md` output file to avoid circular inclusion
3. **Run the pipeline**:
   ```bash
   uv run python orchestrate_pipeline.py "<Property-Name-Kebab-Case>"
   ```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `GEMINI_API_KEY not found` | `.env` not loaded or missing key | Ensure `.env` exists in oz-doc-processor root with `GEMINI_API_KEY=...` |
| `MISTRAL_API_KEY not set` | Missing API key for OCR | Add `MISTRAL_API_KEY=...` to `.env` |
| `Listing directory does not exist` | Folder name mismatch | Check exact folder name inside `listing-docs/`; casing is matched case-insensitively |
| OCR JSON already exists but re-run needed | Stale temp files | Delete `temp/*.json` files in the listing folder before re-running |
| Agent extraction fails for one domain | Gemini model error or malformed markdown | Check the markdown quality first; re-run Phase 1 if needed |
| File not processed | Only `.pdf`, `.xlsx`, `.xls` files are scanned | Rename/convert supplemental docs accordingly |

---

## Environment Variables (`.env` in repo root)

```env
GEMINI_API_KEY=...       # Required for Phase 2 (AI extraction agents)
MISTRAL_API_KEY=...      # Required for Phase 1 (PDF OCR)
```

Optional / unused by core pipeline:
```
CENSUS_API_KEY, BLS_API_KEY, FRED_API_KEY, GOOGLE_MAPS_API_KEY, etc.
```
(These are used by `address_data_fetcher.py` for supplemental data enrichment, not the listing doc pipeline.)
