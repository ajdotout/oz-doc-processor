import os
import json
import logging
import base64
import sys
from pathlib import Path
from mistral_ocr import ocr_with_mistral, parse_and_save_markdown
from excel_processor import process_excel_to_markdown
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import asyncio

def extract_images_from_ocr(json_path: str, output_dir: str):
    """
    Extracts images from the OCR JSON response and saves them as actual image files.
    """
    if not os.path.exists(json_path):
        logging.warning(f"No OCR JSON found at {json_path}. Skipping image extraction.")
        return 0
        
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logging.error(f"Failed to load OCR JSON at {json_path}: {e}")
        return 0

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

                            logging.info(f"Saved image: {filename} to {output_dir}")

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

async def process_listing(listing_name: str):
    """
    Full pipeline for a listing: 
    Iterates through ALL PDF and Excel files in the directory and 
    consolidates them into one grand Markdown document.
    """
    # Convert listing name to capitalized for directory
    listing_dir = Path(f"listing-docs/{listing_name}")
    if not listing_dir.exists():
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

    # Find relevant listing documents (.pdf, .xlsx, .xls)
    all_files = sorted(list(listing_dir.glob("*"))) 
    process_files = [f for f in all_files if f.suffix.lower() in [".pdf", ".xlsx", ".xls"]]
    
    if not process_files:
        logging.error(f"No PDF or Excel files found in {listing_dir}")
        return

    base_name = listing_name.lower().replace(" ", "_").replace("-", "_")
    markdown_path = listing_dir / f"{base_name}_markdown.md"
    images_dir = listing_dir / "images"
    temp_dir = listing_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    logging.info(f"📁 Processing {len(process_files)} files in parallel for {listing_name}...")

    async def process_file(doc_path: Path):
        ext = doc_path.suffix.lower()
        file_md = ""
        logging.info(f"🔍 Starting: {doc_path.name}")

        try:
            if ext == ".pdf":
                temp_json = temp_dir / f"{doc_path.stem}_ocr.json"
                temp_md = temp_dir / f"{doc_path.stem}.md"
                # Store images in a per-file subdirectory
                file_images_dir = images_dir / doc_path.stem
                
                # Run OCR in a separate thread
                await asyncio.to_thread(ocr_with_mistral, str(doc_path), str(temp_json))
                await asyncio.to_thread(parse_and_save_markdown, str(temp_json), str(temp_md))
                await asyncio.to_thread(extract_images_from_ocr, str(temp_json), str(file_images_dir))
                
                with open(temp_md, 'r') as f:
                    file_md = f.read()

            elif ext in [".xlsx", ".xls"]:
                temp_md = temp_dir / f"{doc_path.stem}.md"
                await asyncio.to_thread(process_excel_to_markdown, str(doc_path), str(temp_md))
                with open(temp_md, 'r') as f:
                    file_md = f.read()

            if file_md:
                header = f"\n\n{'='*40}\n"
                header += f"SOURCE FILE: {doc_path.name}\n"
                header += f"{'='*40}\n\n"
                return header + file_md
            
        except Exception as e:
            logging.error(f"Error processing {doc_path.name}: {e}")
        
        return ""

    # Process all files in parallel
    results = await asyncio.gather(*(process_file(f) for f in process_files))
    
    consolidated_markdown = [f"# Listing Context: {listing_name}\n\n"]
    consolidated_markdown.extend([r for r in results if r])

    # Save the grand consolidated markdown
    with open(markdown_path, 'w') as f:
        f.write("".join(consolidated_markdown))

    logging.info(f"🚀 CONSOLIDATION COMPLETE for {listing_name}!")
    logging.info(f"Final Consolidated Markdown: {markdown_path}")
    return str(markdown_path)


if __name__ == "__main__":
    load_dotenv()
    if len(sys.argv) > 1:
        asyncio.run(process_listing(sys.argv[1]))
    else:
        # Default to Celadon
        asyncio.run(process_listing("Celadon"))
