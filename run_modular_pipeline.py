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
        if hasattr(model, 'model_dump'):
            return model.model_dump()
        return model

    # Helper to wrap in block structure
    def to_block(type_name, data):
        return {"type": type_name, "data": to_dict(data)}

    # Overview Data (Sections)
    sections = [
        to_block("hero", overview_data.hero),
        to_block("tickerMetrics", overview_data.tickerMetrics),
        to_block("compellingReasons", overview_data.compellingReasons),
        to_block("executiveSummary", overview_data.executiveSummary),
        to_block("investmentCards", overview_data.investmentCards)
    ]

    # Helper for detail page construction
    def build_detail_page(title, subtitle, sections_data):
        page_sections = []
        for s_type, s_data in sections_data:
            if s_data:
                page_sections.append(to_block(s_type, s_data))
        return {
            "pageTitle": title,
            "pageSubtitle": subtitle,
            "backgroundImages": [],
            "sections": page_sections
        }

    # Details Data
    details = {
        "financialReturns": build_detail_page(
            "Financial Returns", 
            "Detailed financial projections and investment structure",
            [
                ("projections", financial_data.projections),
                ("capitalStack", financial_data.capitalStack),
                ("distributionTimeline", financial_data.timeline),
                ("taxBenefits", financial_data.taxBenefits),
                ("investmentStructure", financial_data.structure),
                ("distributionWaterfall", financial_data.waterfall)
            ]
        ),
        "propertyOverview": build_detail_page(
            "Property Overview",
            "Physical asset details and site characteristics",
            [
                ("keyFacts", property_data.keyFacts),
                ("amenities", property_data.amenities),
                ("unitMix", property_data.unitMix),
                ("locationHighlights", property_data.locationHighlights),
                ("locationFeatures", property_data.locationFeatures),
                ("developmentTimeline", property_data.timeline),
                ("developmentPhases", property_data.phases)
            ]
        ),
        "marketAnalysis": build_detail_page(
            "Market Analysis",
            "Local economic drivers and competitive landscape",
            [
                ("marketMetrics", market_data.metrics),
                ("majorEmployers", market_data.employers),
                ("demographics", market_data.demographics),
                ("keyMarketDrivers", market_data.drivers),
                ("supplyDemand", market_data.supplyDemand),
                ("competitiveAnalysis", market_data.competitors),
                ("economicDiversification", market_data.diversification)
            ]
        ),
        "sponsorProfile": {
            "sponsorName": sponsor_data.intro.sponsorName if sponsor_data.intro else "Sponsor Profile",
            "sections": [
                to_block(t, d) for t, d in [
                    ("sponsorIntro", sponsor_data.intro),
                    ("partnershipOverview", sponsor_data.partnership),
                    ("trackRecord", sponsor_data.trackRecord),
                    ("leadershipTeam", sponsor_data.team),
                    ("keyDevelopmentPartners", sponsor_data.keyPartners),
                    ("competitiveAdvantages", sponsor_data.advantages)
                ] if d
            ]
        }
    }

    # Add optional detail pages
    if sponsor_data.portfolio:
        details["portfolioProjects"] = build_detail_page(
            "Portfolio Projects",
            "Overview of the assets currently in the portfolio",
            [("projectOverview", sponsor_data.portfolio)]
        )

    if sponsor_data.fundEntities or sponsor_data.fundDetails:
        details["fundStructure"] = build_detail_page(
            "Fund Structure",
            "Entity structure and legal framework of the fund",
            [
                ("fundSponsorEntities", sponsor_data.fundEntities),
                ("fundDetails", sponsor_data.fundDetails)
            ]
        )

    if sponsor_data.participationSteps:
        details["howInvestorsParticipate"] = build_detail_page(
            "How to Participate",
            "Next steps for qualified investors",
            [("participationSteps", sponsor_data.participationSteps)]
        )

    final_listing = {
        "listingName": overview_data.hero.listingName,
        "sections": sections,
        "newsLinks": to_dict(overview_data.newsLinks) if overview_data.newsLinks else [],
        "details": details
    }
    
    # Save output
    output_dir = os.path.dirname(markdown_path)
    base_name = os.path.splitext(os.path.basename(markdown_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_modular_listing_gemini3.json")

    with open(output_path, 'w') as f:
        json.dump(final_listing, f, indent=2)

    logging.info(f"Pipeline complete. Output saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
