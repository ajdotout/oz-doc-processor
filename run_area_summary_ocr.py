import os
from mistral_ocr import ocr_with_mistral, parse_and_save_markdown
from process_listing import extract_images_from_ocr
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

listing_dir = Path("listing-docs/Sky-Everett-MA")
pdf_path = listing_dir / "2025 1121 area summary 5-2.pdf"
json_path = listing_dir / "area_summary_ocr.json"
markdown_path = listing_dir / "area_summary_markdown.md"
images_dir = listing_dir / "area_summary_images"

print(f"Processing {pdf_path}...")
try:
    ocr_with_mistral(str(pdf_path), str(json_path))
    parse_and_save_markdown(str(json_path), str(markdown_path))
    extract_images_from_ocr(str(json_path), str(images_dir))
    print("Done!")
except Exception as e:
    print(f"Error: {e}")
