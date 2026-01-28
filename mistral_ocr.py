import os
import json
import logging
from mistralai import Mistral
from mistralai.extra import response_format_from_pydantic_model
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# 1. Define the schema for image descriptions
class ImageAnnotation(BaseModel):
    image_type: str = Field(..., description="Type of image: chart, table, or photo")
    description: str = Field(..., description="A 1-sentence description of the image content")

def ocr_with_mistral(file_path: str, output_path: str = "ocr_output.json"):
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
    logging.info(f"Uploading file: {file_path}")
    with open(file_path, "rb") as f:
        uploaded_pdf = client.files.upload(
            file={"file_name": os.path.basename(file_path), "content": f},
            purpose="ocr"
        )

    # 2. Retrieve the file to confirm upload
    retrieved_file = client.files.retrieve(file_id=uploaded_pdf.id)
    logging.info(f"Retrieved file: {retrieved_file.id}")

    # 3. Get a signed URL for the file
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

    # 4. Get OCR results with image annotations
    annotation_format = response_format_from_pydantic_model(ImageAnnotation)

    logging.info("Starting Mistral OCR processing...")
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

    logging.info(f"OCR results saved to {output_path}")

    return ocr_response

def parse_and_save_markdown(json_path: str, output_markdown_path: str):
    """
    Parses the JSON output from the OCR process, aggregates the markdown content,
    and saves it to a markdown file.
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

    logging.info(f"Aggregated markdown saved to {output_markdown_path}")
