import os


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "gemini-2.0-flash-lite")
CLASSIFIER_LINES = _env_int("CLASSIFIER_LINES", 100)
CLASSIFIER_EXCEL_SHEET_LINES = _env_int("CLASSIFIER_EXCEL_SHEET_LINES", 10)
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "gemini-3-flash-preview")

DOC_CATEGORIES = ("om", "proforma", "research", "supplemental")
PROCESSABLE_EXTS = (".pdf", ".xlsx", ".xls", ".md")
