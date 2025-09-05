import os
from mistralai import Mistral
import json
from dotenv import load_dotenv

load_dotenv()

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