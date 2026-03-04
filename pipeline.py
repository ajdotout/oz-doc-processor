import os
import sys
import asyncio
import logging
from pathlib import Path
import argparse
from typing import Optional
from dotenv import load_dotenv

# Add the current directory to sys.path to ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from convert_stage import get_listing_dir, run_convert_stage
from extract_stage import run_pipeline
from src.pipeline.classify_stage import classify_listing

STAGES = ("convert", "classify", "extract", "all")
AGENT_CHOICES = ["overview", "financial", "property", "market", "sponsor"]

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _markdown_path(listing_dir: Path) -> str:
    base_name = listing_dir.name.lower().replace(" ", "_").replace("-", "_")
    return str(listing_dir / f"{base_name}_markdown.md")


async def orchestrate(listing_name: str, stage: str = "all", agent: Optional[str] = None, no_cache: bool = False):
    """
    Orchestrates the 3-stage pipeline:
    convert -> classify -> extract
    """
    logging.info(f"=========== STARTING ORCHESTRATION FOR: {listing_name} ===========")

    if stage not in STAGES:
        raise ValueError(f"Unknown stage: {stage}")
    if agent and stage != "extract":
        logging.error("--agent can only be used with --stage extract")
        return
    if no_cache and stage not in ("extract", "all"):
        logging.error("--no-cache can only be used with --stage extract or --stage all")
        return

    listing_dir = None
    markdown_path: Optional[str] = None

    if stage in ("convert", "all"):
        logging.info("STAGE 1: Converting documents to markdown...")
        try:
            markdown_path = await run_convert_stage(listing_name)
            if not markdown_path or not os.path.exists(markdown_path):
                logging.error("Failed to generate markdown path. Aborting.")
                return
            listing_dir = Path(markdown_path).parent
            logging.info(f"STAGE 1 COMPLETE: {markdown_path}")
        except Exception as e:
            logging.error(f"Error in Stage 1 (convert): {e}")
            return

        if stage == "convert":
            logging.info(f"=========== STAGE COMPLETE FOR: {listing_name} ===========")
            print(f"\nSuccessfully processed '{listing_name}'")
            print(f"Markdown: {markdown_path}\n")
            return

    if stage in ("classify", "all"):
        logging.info("STAGE 2: Classifying docs and rebuilding buckets...")
        try:
            if listing_dir is None:
                listing_dir = get_listing_dir(listing_name)
            markdown_path = markdown_path or _markdown_path(listing_dir)
            manifest_path = await asyncio.to_thread(classify_listing, listing_dir)
            logging.info(f"STAGE 2 COMPLETE: {manifest_path}")

            if stage == "classify":
                logging.info(f"=========== STAGE COMPLETE FOR: {listing_name} ===========")
                print(f"\nSuccessfully processed '{listing_name}'")
                print(f"Manifest: {manifest_path}")
                print(f"Markdown: {markdown_path}\n")
                return
        except Exception as e:
            logging.error(f"Error in Stage 2 (classify): {e}")
            return

    if stage in ("extract", "all"):
        logging.info("STAGE 3: Running extraction...")
        try:
            if listing_dir is None:
                listing_dir = get_listing_dir(listing_name)
            markdown_path = markdown_path or _markdown_path(listing_dir)
            json_path = await run_pipeline(markdown_path, agent_filter=agent, no_cache=no_cache)
            if not json_path:
                if agent:
                    logging.error("Failed to generate agent cache output. Aborting.")
                else:
                    logging.error("Failed to generate final JSON. Aborting.")
                return
            if agent:
                logging.info(f"Single-agent cache artifact: {json_path}")
                print(f"\nSuccessfully processed '{listing_name}'")
                print(f"Agent cache file: {json_path}\n")
            else:
                logging.info(f"STAGE 3 COMPLETE: {json_path}")
                logging.info(f"=========== ORCHESTRATION SUCCESSFUL FOR: {listing_name} ===========")
                print(f"\nSuccessfully processed '{listing_name}'")
                print(f"Final JSON: {json_path}\n")
        except Exception as e:
            logging.error(f"Error in Stage 3 (extract): {e}")
            return

if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run the staged pipeline.")
    parser.add_argument("listing_name")
    parser.add_argument("--stage", choices=STAGES, default="all")
    parser.add_argument("--agent", choices=AGENT_CHOICES, default=None)
    parser.add_argument("--no-cache", action="store_true", help="Ignore cached agent outputs and regenerate.")
    args = parser.parse_args()

    asyncio.run(orchestrate(args.listing_name, stage=args.stage, agent=args.agent, no_cache=args.no_cache))
