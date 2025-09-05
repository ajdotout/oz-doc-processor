import os
from mistral_ocr import ocr_from_supabase, parse_and_save_markdown

def main():
    """
    Orchestrates the full OCR pipeline:
    1. Fetches a file from Supabase and gets OCR results as JSON.
    2. Parses the JSON to create an aggregated Markdown file.
    """
    # Define output paths
    json_output_path = "supabase_ocr_output.json"
    markdown_output_path = "supabase_ocr_output.md"

    print("Starting the OCR pipeline...")

    # Step 1: Process file from Supabase
    print(f"Fetching file from Supabase and performing OCR...")
    ocr_from_supabase(json_output_path)
    print(f"OCR results saved to {json_output_path}")

    # Step 2: Parse the JSON and save as Markdown
    print(f"Parsing JSON and creating Markdown file...")
    parse_and_save_markdown(json_output_path, markdown_output_path)
    print(f"Markdown file saved to {markdown_output_path}")

    print("Pipeline finished successfully!")

if __name__ == "__main__":
    main() 