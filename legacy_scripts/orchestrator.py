import os
from mistral_ocr import ocr_from_supabase, parse_and_save_markdown
from gemini_processor import generate_listing_json

def main():
    """
    Orchestrates the full OCR and Gemini pipeline:
    1. Fetches a file from Supabase and gets OCR results as JSON.
    2. Parses the JSON to create an aggregated Markdown file.
    3. Uses Gemini 2.5 Pro to generate a structured JSON listing from the Markdown.
    """
    # Define output paths
    json_output_path = "supabase_ocr_output.json"
    markdown_output_path = "supabase_ocr_output.md"
    listing_json_output_path = "listing_page_data.json"

    print("Starting the OCR and Gemini pipeline...")

    # Step 1: Process file from Supabase
    print(f"Fetching file from Supabase and performing OCR...")
    ocr_from_supabase(json_output_path)
    print(f"OCR results saved to {json_output_path}")

    # Step 2: Parse the JSON and save as Markdown
    print(f"Parsing JSON and creating Markdown file...")
    parse_and_save_markdown(json_output_path, markdown_output_path)
    print(f"Markdown file saved to {markdown_output_path}")

    # Step 3: Use Gemini to generate structured JSON
    print(f"Generating structured JSON using Gemini 2.5 Pro...")
    # The perplexity prompt is located in the oz-dev-dash repo
    perplexity_prompt_path = "/Users/aryanjain/Desktop/OZListings/oz-dev-dash/docs/perplexity-prompt.md"
    generate_listing_json(markdown_output_path, perplexity_prompt_path, listing_json_output_path)
    print(f"Structured listing JSON saved to {listing_json_output_path}")

    print("Pipeline finished successfully!")

if __name__ == "__main__":
    main() 