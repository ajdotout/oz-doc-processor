import os
from gemini_processor import generate_listing_json

# Define paths relative to the oz-doc-processor directory
OCR_MARKDOWN_PATH = "supabase_ocr_output.md"
PERPLEXITY_PROMPT_PATH = "/Users/aryanjain/Desktop/OZListings/oz-dev-dash/docs/perplexity-prompt.md"
OUTPUT_LISTING_JSON_PATH = "test_listing_page_data.json"

if __name__ == "__main__":
    print("Starting direct Gemini functionality test...")
    try:
        generate_listing_json(OCR_MARKDOWN_PATH, PERPLEXITY_PROMPT_PATH, OUTPUT_LISTING_JSON_PATH)
        print(f"Gemini functionality test completed. Output saved to {OUTPUT_LISTING_JSON_PATH}")
    except Exception as e:
        print(f"Gemini functionality test failed: {e}") 