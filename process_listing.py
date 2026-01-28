import os
import json
import logging
import base64
import sys
from pathlib import Path
from mistral_ocr import ocr_with_mistral, parse_and_save_markdown
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_images_from_ocr(json_path: str, output_dir: str):
    """
    Extracts images from the OCR JSON response and saves them as actual image files.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    with open(json_path, 'r') as f:
        data = json.load(f)

    image_count = 0
    image_descriptions = []

    if "pages" in data and isinstance(data["pages"], list):
        for page_idx, page in enumerate(data["pages"]):
            if "images" in page and isinstance(page["images"], list):
                for img_index, image in enumerate(page["images"]):
                    if "image_base64" in image and "id" in image:
                        try:
                            image_data = image["image_base64"]
                            if image_data.startswith("data:image/"):
                                header, base64_data = image_data.split(",", 1)
                                image_format = header.split(";")[0].split("/")[1]
                            else:
                                base64_data = image_data
                                image_format = "jpeg"

                            decoded_image = base64.b64decode(base64_data)
                            image_id = image["id"]
                            # Clean filename
                            clean_id = image_id.split('/')[-1]
                            filename = clean_id if clean_id.endswith(f".{image_format}") else f"{clean_id}.{image_format}"
                            filepath = os.path.join(output_dir, filename)

                            with open(filepath, "wb") as f:
                                f.write(decoded_image)

                            logging.info(f"Saved image: {filename}")

                            annotation_info = {
                                "filename": filename,
                                "page": page_idx,
                                "image_index": img_index,
                                "image_id": image_id,
                                "top_left_x": image.get("top_left_x"),
                                "top_left_y": image.get("top_left_y"),
                                "bottom_right_x": image.get("bottom_right_x"),
                                "bottom_right_y": image.get("bottom_right_y")
                            }

                            # Extract annotation if available
                            if "image_annotation" in image and image["image_annotation"]:
                                # It might be a dict already if loaded from JSON or a string
                                ann = image["image_annotation"]
                                if isinstance(ann, str):
                                    try:
                                        ann = json.loads(ann)
                                    except:
                                        pass
                                
                                if isinstance(ann, dict):
                                    annotation_info.update({
                                        "image_type": ann.get("image_type"),
                                        "description": ann.get("description")
                                    })
                                else:
                                    annotation_info.update({"image_type": "unknown", "description": str(ann)})
                            else:
                                annotation_info.update({"image_type": "unknown", "description": "No annotation available"})

                            image_descriptions.append(annotation_info)
                            image_count += 1
                        except Exception as e:
                            logging.error(f"Error processing image {image.get('id', 'unknown')}: {e}")

    descriptions_path = os.path.join(output_dir, "image_descriptions.json")
    with open(descriptions_path, 'w') as f:
        json.dump(image_descriptions, f, indent=2)

    return image_count

def process_listing(listing_name: str):
    """
    Full pipeline for a listing: OCR -> Markdown -> Image Extraction
    """
    # Convert listing name to capitalized for directory and lowercase for filenames
    listing_dir = Path(f"listing-docs/{listing_name}")
    if not listing_dir.exists():
        # Try finding it case-insensitively
        parent = Path("listing-docs")
        found = False
        for d in parent.iterdir():
            if d.is_dir() and d.name.lower() == listing_name.lower():
                listing_dir = d
                listing_name = d.name
                found = True
                break
        if not found:
            logging.error(f"Listing directory {listing_dir} does not exist.")
            return

    # Find PDF file
    pdf_files = list(listing_dir.glob("*.pdf"))
    if not pdf_files:
        logging.error(f"No PDF files found in {listing_dir}")
        return
    
    pdf_path = pdf_files[0]
    base_name = listing_name.lower().replace(" ", "_")
    json_path = listing_dir / f"{base_name}_ocr.json"
    markdown_path = listing_dir / f"{base_name}_markdown.md"
    images_dir = listing_dir / "images"

    logging.info(f"Processing listing: {listing_name}")
    logging.info(f"PDF Path: {pdf_path}")

    # Step 1: OCR
    logging.info("Step 1: Running Mistral OCR (this may take a minute)...")
    ocr_with_mistral(str(pdf_path), str(json_path))

    # Step 2: Extract Markdown
    logging.info("Step 2: Extracting Markdown...")
    parse_and_save_markdown(str(json_path), str(markdown_path))

    # Step 3: Extract Images
    logging.info("Step 3: Extracting Images...")
    image_count = extract_images_from_ocr(str(json_path), str(images_dir))
    logging.info(f"Extracted {image_count} images to {images_dir}")

    logging.info(f"Processing complete for {listing_name}!")
    logging.info(f"JSON: {json_path}")
    logging.info(f"Markdown: {markdown_path}")
    logging.info(f"Images: {images_dir}/")

if __name__ == "__main__":
    load_dotenv()
    if len(sys.argv) > 1:
        process_listing(sys.argv[1])
    else:
        # Default to Celadon
        process_listing("Celadon")
