#!/usr/bin/env python3
"""
Script to extract images from the OCR JSON response and save them as actual image files.
"""

import os
import json
import base64
from pathlib import Path

def extract_images_from_ocr(json_path: str, output_dir: str = "extracted_images"):
    """
    Extracts images from the OCR JSON response and saves them as image files.

    Args:
        json_path (str): Path to the OCR JSON file
        output_dir (str): Directory to save the extracted images
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)

    # Load the OCR JSON data
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Extract images from pages
    image_count = 0
    image_descriptions = []

    if "pages" in data and isinstance(data["pages"], list):
        for page_idx, page in enumerate(data["pages"]):
            if "images" in page and isinstance(page["images"], list):
                for img_index, image in enumerate(page["images"]):
                    if "image_base64" in image and "id" in image:
                        try:
                            # Decode base64 image data
                            image_data = image["image_base64"]
                            if image_data.startswith("data:image/"):
                                # Handle data URL format
                                header, base64_data = image_data.split(",", 1)
                                image_format = header.split(";")[0].split("/")[1]
                            else:
                                base64_data = image_data
                                image_format = "jpeg"  # Default format

                            # Decode the base64 string
                            decoded_image = base64.b64decode(base64_data)

                            # Create filename
                            image_id = image["id"]
                            if image_id.endswith(f".{image_format}"):
                                filename = image_id
                            else:
                                filename = f"{image_id}.{image_format}"
                            filepath = os.path.join(output_dir, filename)

                            # Save the image
                            with open(filepath, "wb") as f:
                                f.write(decoded_image)

                            print(f"✅ Saved image: {filepath}")

                            # Extract annotation if available
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

                            # Check for annotation - it comes as a JSON string in image_annotation field
                            if "image_annotation" in image and image["image_annotation"]:
                                try:
                                    # Parse the JSON string annotation
                                    import json as json_lib
                                    annotation_data = json_lib.loads(image["image_annotation"])
                                    annotation_info.update({
                                        "image_type": annotation_data.get("image_type"),
                                        "description": annotation_data.get("description")
                                    })
                                    print(f"   📝 AI Description: {annotation_data.get('description', 'N/A')}")
                                except json_lib.JSONDecodeError:
                                    annotation_info.update({
                                        "image_type": "unknown",
                                        "description": "Failed to parse annotation"
                                    })
                            else:
                                annotation_info.update({
                                    "image_type": "unknown",
                                    "description": "No annotation available"
                                })

                            image_descriptions.append(annotation_info)
                            image_count += 1

                        except Exception as e:
                            print(f"❌ Error processing image {image.get('id', 'unknown')}: {e}")
                            continue

    # Save image descriptions to JSON file
    descriptions_path = os.path.join(output_dir, "image_descriptions.json")
    with open(descriptions_path, 'w') as f:
        json.dump(image_descriptions, f, indent=2)

    print(f"\n📊 Total images extracted: {image_count}")
    print(f"📁 Images saved to: {output_dir}/")
    print(f"📄 Image descriptions saved to: {descriptions_path}")

    return image_count

def main():
    # Paths
    json_path = "alden_investment_deck_ocr.json"
    output_dir = "extracted_images"

    # Check if JSON file exists
    if not os.path.exists(json_path):
        print(f"❌ Error: JSON file not found at {json_path}")
        return

    print("🔄 Starting image extraction from OCR JSON...")
    print(f"📄 Input JSON: {json_path}")
    print(f"📁 Output directory: {output_dir}")

    # Extract images
    image_count = extract_images_from_ocr(json_path, output_dir)

    if image_count > 0:
        print("\n✅ Image extraction completed successfully!")
        print(f"📸 {image_count} images were extracted and saved to {output_dir}/")
        print("\n📋 Image files created:")
        for filename in sorted(os.listdir(output_dir)):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                print(f"   • {filename}")
    else:
        print("⚠️  No images were found in the OCR JSON file.")

if __name__ == "__main__":
    main()