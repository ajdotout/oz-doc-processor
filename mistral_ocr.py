import os
from mistralai import Mistral
import json
from dotenv import load_dotenv
from supabase import create_client, Client
import io
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# Supabase client initialization
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

def ocr_from_supabase(output_path: str = "ocr_output.json"):
    """
    Fetches a file from Supabase using a signed URL, performs OCR, and saves the results.

    Args:
        output_path (str): The path to save the OCR results.
    """
    # 1. Get Supabase details from environment variables
    bucket_name = os.environ.get("SUPABASE_BUCKET")
    folder_name = os.environ.get("SUPABASE_FOLDER")
    file_name = os.environ.get("SUPABASE_FILE")
    logging.info(f"Attempting to process file: {file_name} from folder: {folder_name} in bucket: {bucket_name}")

    if not all([bucket_name, folder_name, file_name]):
        logging.error("Supabase environment variables not set.")
        raise ValueError("Please set SUPABASE_BUCKET, SUPABASE_FOLDER, and SUPABASE_FILE environment variables.")

    file_path_in_bucket = f"{folder_name}/{file_name}"

    # 2. Create a signed URL from Supabase with a 5-minute validity
    try:
        signed_url_response = supabase.storage.from_(bucket_name).create_signed_url(file_path_in_bucket, 300)
        supabase_signed_url = signed_url_response['signedURL']
        logging.info(f"Successfully created signed URL: {supabase_signed_url}")
    except Exception as e:
        logging.error(f"Failed to create signed URL: {e}")
        raise

    # 3. Get Mistral API Key
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        logging.error("MISTRAL_API_KEY not set.")
        raise ValueError("MISTRAL_API_KEY environment variable not set.")
    
    client = Mistral(api_key=api_key)

    # 4. Get OCR results using the signed URL
    try:
        logging.info("Sending request to Mistral OCR API...")
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": supabase_signed_url,
            },
            include_image_base64=True
        )
        logging.info("Successfully received response from Mistral OCR API.")
    except Exception as e:
        logging.error(f"Mistral API call failed: {e}")
        raise

    with open(output_path, "w") as f:
        json.dump(ocr_response.dict(), f, indent=4)
    
    logging.info(f"OCR results saved to {output_path}")

    return ocr_response

def ocr_with_mistral(file_path: str, output_path: str = "ocr_output.json"):
    """
    Performs OCR on a PDF file using the Mistral API.

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


    # 4. Get OCR results
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": signed_url.url,
        },
        include_image_base64=True
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
                full_markdown += page["markdown"] + "\\n\\n"

    with open(output_markdown_path, 'w') as f:
        f.write(full_markdown)

    print(f"Aggregated markdown saved to {output_markdown_path}")

if __name__ == "__main__":
    # This is an example of how to use the function.
    # You would need to have a PDF file to test this.
    # For example, if you have a file named 'sample.pdf' in the same directory:
    #
    # if os.path.exists("sample.pdf"):
    #     results = ocr_with_mistral("sample.pdf", "sample_ocr_results.json")
    #     parse_and_save_markdown("sample_ocr_results.json", "sample_output.md")
    #     print(results)
    # else:
    #     print("Please provide a 'sample.pdf' file to run the example.")
    print("Mistral OCR script ready. To use it, call the ocr_with_mistral function with a file path.")
    print("Example: ocr_with_mistral('path/to/your/document.pdf', 'path/to/output.json')")
    print("Then call parse_and_save_markdown('path/to/output.json', 'path/to/output.md')")
    print("To process a file from Supabase, set the SUPABASE_BUCKET, SUPABASE_FOLDER, and SUPABASE_FILE env vars and call ocr_from_supabase('output.json')") 