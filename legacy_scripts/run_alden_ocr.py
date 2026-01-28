#!/usr/bin/env python3
"""
Script to run OCR on the Alden Investment Deck PDF and extract markdown with Base64-encoded images.
"""

import os
from mistralai import Mistral
from mistralai.extra import response_format_from_pydantic_model
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# 1. Define the schema for image descriptions
class ImageAnnotation(BaseModel):
    image_type: str = Field(..., description="Type of image: chart, table, or photo")
    description: str = Field(..., description="A 1-sentence description of the image content")

def ocr_with_mistral_simple(file_path: str, output_path: str = "ocr_output.json"):
    """
    Performs OCR on a PDF file using the Mistral API with image annotations.

    Args:
        file_path (str): The path to the PDF file.
        output_path (str): The path to save the OCR results.
    """
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable not set.")

    client = Mistral(api_key=api_key)

    # 1. Upload the file
    with open(file_path, "rb") as f:
        uploaded_pdf = client.files.upload(
            file={"file_name": os.path.basename(file_path), "content": f},
            purpose="ocr"
        )

    # 2. Retrieve the file to confirm upload
    retrieved_file = client.files.retrieve(file_id=uploaded_pdf.id)
    print(f"Retrieved file: {retrieved_file}")

    # 3. Get a signed URL for the file
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

    # 4. Get OCR results with image annotations
    annotation_format = response_format_from_pydantic_model(ImageAnnotation)

    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": signed_url.url,
        },
        include_image_base64=True,
        bbox_annotation_format=annotation_format
    )

    with open(output_path, "w") as f:
        json.dump(ocr_response.dict(), f, indent=4)

    print(f"OCR results saved to {output_path}")

    return ocr_response

def parse_and_save_markdown(json_path: str, output_markdown_path: str):
    """
    Parses the JSON output from the OCR process, aggregates the markdown content,
    and saves it to a markdown file.

    Args:
        json_path (str): The path to the JSON file from the OCR process.
        output_markdown_path (str): The path to save the aggregated markdown file.
    """
    with open(json_path, 'r') as f:
        data = json.load(f)

    full_markdown = ""
    if "pages" in data and isinstance(data["pages"], list):
        for page in data["pages"]:
            if "markdown" in page:
                full_markdown += page["markdown"] + "\n\n"

    with open(output_markdown_path, 'w') as f:
        f.write(full_markdown)

    print(f"Aggregated markdown saved to {output_markdown_path}")

def main():
    # Path to the Alden Investment Deck PDF
    pdf_path = "/Users/aryanjain/Documents/OZL/UsefulDocs/Alden-Apt-Ma/Alden Investment Deck.pdf"

    # Output paths in the oz-doc-processor directory
    json_output_path = "alden_investment_deck_ocr.json"
    markdown_output_path = "alden_investment_deck_markdown.md"

    # Check if PDF exists
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return

    # Check for required environment variables
    mistral_api_key = os.environ.get("MISTRAL_API_KEY")
    if not mistral_api_key:
        print("Error: MISTRAL_API_KEY environment variable not set.")
        print("Please set your Mistral API key in a .env file or environment variable.")
        return

    print("Starting OCR processing on Alden Investment Deck PDF...")
    print(f"Input PDF: {pdf_path}")
    print(f"JSON output: {json_output_path}")
    print(f"Markdown output: {markdown_output_path}")

    try:
        # Step 1: Run OCR with Mistral API (includes include_image_base64=True)
        print("\n1. Running OCR with Mistral API...")
        ocr_response = ocr_with_mistral_simple(pdf_path, json_output_path)
        print(f"OCR completed. JSON saved to {json_output_path}")

        # Step 2: Parse JSON and extract markdown content
        print("\n2. Extracting markdown content from OCR results...")
        parse_and_save_markdown(json_output_path, markdown_output_path)
        print(f"Markdown extracted and saved to {markdown_output_path}")

        print("\n✅ OCR processing completed successfully!")
        print(f"📄 Markdown file with Base64-encoded images: {markdown_output_path}")

        # Show some stats about the output
        if os.path.exists(markdown_output_path):
            with open(markdown_output_path, 'r') as f:
                content = f.read()
                print(f"📊 Markdown file size: {len(content)} characters")

    except Exception as e:
        print(f"❌ Error during OCR processing: {e}")
        return

if __name__ == "__main__":
    main()