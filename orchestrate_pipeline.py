import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add the current directory to sys.path to ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from process_listing import process_listing
from run_modular_pipeline import run_pipeline

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def orchestrate(listing_name: str):
    """
    Orchestrates the full pipeline:
    1. Process listing documents (PDFs, Excels) and consolidate into Markdown.
    2. Run the modular AI pipeline on the consolidated Markdown to generate JSON.
    """
    logging.info(f"=========== STARTING ORCHESTRATION FOR: {listing_name} ===========")
    
    # Step 1: Process and Consolidate
    logging.info("STEP 1: Processing documents and generating consolidated markdown...")
    try:
        markdown_path = await process_listing(listing_name)
        if not markdown_path or not os.path.exists(markdown_path):
            logging.error("Failed to generate markdown path. Aborting.")
            return
    except Exception as e:
        logging.error(f"Error in Step 1 (process_listing): {e}")
        return

    logging.info(f"Step 1 Complete. Markdown generated at: {markdown_path}")
    
    # Step 2: Run Modular Pipeline
    logging.info("STEP 2: Running modular AI pipeline...")
    try:
        json_path = await run_pipeline(markdown_path)
        if not json_path:
            logging.error("Failed to generate final JSON. Aborting.")
            return
    except Exception as e:
        logging.error(f"Error in Step 2 (run_pipeline): {e}")
        return

    logging.info(f"Step 2 Complete. Final JSON generated at: {json_path}")
    logging.info(f"=========== ORCHESTRATION SUCCESSFUL FOR: {listing_name} ===========")
    
    print(f"\nSuccessfully processed '{listing_name}'")
    print(f"Markdown and Images: {os.path.dirname(markdown_path)}")
    print(f"Final JSON: {json_path}\n")

if __name__ == "__main__":
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage: python orchestrate_pipeline.py <listing_name>")
        sys.exit(1)
        
    listing_name = sys.argv[1]
    asyncio.run(orchestrate(listing_name))
