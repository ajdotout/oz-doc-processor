import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add the current directory to sys.path to ensure src imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.agents import (
    OverviewAgent,
    FinancialAgent,
    PropertyAgent,
    MarketAgent,
    SponsorAgent
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_environment():
    env_path = Path(__file__).parent / '.env'
    logging.info(f"Loading environment from {env_path}")
    loaded = load_dotenv(dotenv_path=env_path)
    logging.info(f"load_dotenv returned: {loaded}")
    
    if not os.environ.get("GEMINI_API_KEY"):
        logging.error("GEMINI_API_KEY not found in environment variables.")
        # Debug: list keys
        logging.info(f"Available keys: {[k for k in os.environ.keys() if 'API' in k or 'GEMINI' in k]}")
        sys.exit(1)

async def run_agent_in_thread(agent, content):
    """Runs a blocking agent.run() method in a separate thread."""
    return await asyncio.to_thread(agent.run, content)

async def main():
    if len(sys.argv) < 2:
        print("Usage: python run_modular_pipeline.py <path_to_markdown_file>")
        sys.exit(1)

    markdown_path = sys.argv[1]
    if not os.path.exists(markdown_path):
        logging.error(f"File not found: {markdown_path}")
        sys.exit(1)

    load_environment()

    logging.info(f"Reading markdown file: {markdown_path}")
    with open(markdown_path, 'r') as f:
        markdown_content = f.read()

    logging.info("Initializing agents...")
    overview_agent = OverviewAgent()
    financial_agent = FinancialAgent()
    property_agent = PropertyAgent()
    market_agent = MarketAgent()
    sponsor_agent = SponsorAgent()

    logging.info("Running agents in parallel...")
    
    # Run all agents concurrently
    results = await asyncio.gather(
        run_agent_in_thread(overview_agent, markdown_content),
        run_agent_in_thread(financial_agent, markdown_content),
        run_agent_in_thread(property_agent, markdown_content),
        run_agent_in_thread(market_agent, markdown_content),
        run_agent_in_thread(sponsor_agent, markdown_content),
        return_exceptions=True
    )

    overview_data, financial_data, property_data, market_data, sponsor_data = results

    # Check for exceptions
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            logging.error(f"Agent {i} failed with error: {res}")
            # Decide whether to abort or continue. For now, aborting.
            sys.exit(1)

    logging.info("All agents completed successfully. Assembling final JSON...")

    # Construct the final Listing structure
    # Note: Mapping logic based on expected Listing structure in gemini_processor.py
    # and the Pydantic models returned by the agents.
    
    # Helper to convert Pydantic model to dict
    def to_dict(model):
        return model.model_dump()

    # Overview Data (Sections)
    sections = [
        to_dict(overview_data.hero),
        to_dict(overview_data.tickerMetrics),
        to_dict(overview_data.compellingReasons),
        to_dict(overview_data.executiveSummary),
        to_dict(overview_data.investmentCards)
    ]

    # Details Data
    details = {
        "financialReturns": to_dict(financial_data),
        "propertyOverview": to_dict(property_data),
        "marketAnalysis": to_dict(market_data),
        "sponsorProfile": to_dict(sponsor_data)
    }

    final_listing = {
        "listingName": overview_data.hero.listingName,
        "listingSlug": overview_data.hero.listingName.lower().replace(" ", "-"), # Simple slug generation
        "projectId": "generated-id", # Placeholder
        "sections": sections,
        "details": details
    }
    
    # Save output
    output_dir = os.path.dirname(markdown_path)
    base_name = os.path.splitext(os.path.basename(markdown_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_modular_listing.json")

    with open(output_path, 'w') as f:
        json.dump(final_listing, f, indent=2)

    logging.info(f"Pipeline complete. Output saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
