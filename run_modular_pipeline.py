import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
import argparse

# Add the current directory to sys.path to ensure src imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.agents import (
    OverviewAgent,
    FinancialAgent,
    PropertyAgent,
    MarketAgent,
    SponsorAgent
)

AGENT_ROUTING = {
    "overview": {"om", "supplemental"},
    "financial": {"om", "proforma", "supplemental"},
    "property": {"om", "research", "supplemental"},
    "market": {"om", "research", "supplemental"},
    "sponsor": {"om", "supplemental"},
}

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


def to_dict(obj):
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    if isinstance(obj, list):
        return [to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj


def to_block(type_name, data):
    return {"type": type_name, "data": to_dict(data)}


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


async def run_pipeline(markdown_path: str, agent_filter: str = None):
    listing_dir = Path(markdown_path).parent
    if not listing_dir.exists():
        logging.error(f"Listing directory not found: {listing_dir}")
        return None

    load_environment()
    manifest_path = listing_dir / "doc_manifest.json"
    if not manifest_path.exists():
        logging.error("doc_manifest.json not found. Run the classify stage first.")
        return None

    logging.info(f"Loading manifest: {manifest_path}")
    with manifest_path.open("r") as f:
        manifest = json.load(f)

    file_entries = manifest.get("files", [])
    if not file_entries:
        logging.error("No files found in manifest. Run classify again.")
        return None

    per_file_markdowns = {}
    for entry in file_entries:
        fname = entry.get("filename")
        category = entry.get("category", "supplemental")
        temp_path = listing_dir / entry.get("temp_md_path", f"buckets/{category}/temp/{Path(fname).stem}.md")
        if not temp_path.exists():
            logging.error(f"Missing bucketed temp markdown for {fname}: {temp_path}")
            return None
        try:
            with temp_path.open("r") as f:
                per_file_markdowns[fname] = f.read()
        except Exception as e:
            logging.error(f"Failed reading markdown for {fname}: {e}")
            return None

    classifications = {entry.get("filename"): entry.get("category") for entry in file_entries}

    def build_content(agent_name):
        allowed = AGENT_ROUTING[agent_name]
        sections = []
        for fname, content in per_file_markdowns.items():
            if classifications.get(fname) in allowed:
                header = f"\n{'='*40}\nSOURCE FILE: {fname}\n{'='*40}\n\n"
                sections.append(header + content)
        return "\n".join(sections)

    agent_contents = {name: build_content(name) for name in AGENT_ROUTING}

    logging.info("Initializing agents...")
    all_agents = {
        "overview": OverviewAgent,
        "financial": FinancialAgent,
        "property": PropertyAgent,
        "market": MarketAgent,
        "sponsor": SponsorAgent,
    }

    if agent_filter:
        if agent_filter not in all_agents:
            logging.error(f"Unknown agent: {agent_filter}. Choose from: {list(all_agents.keys())}")
            return None
        agents_to_run = {agent_filter: all_agents[agent_filter]}
    else:
        agents_to_run = all_agents

    logging.info("Running agents in parallel...")
    results = await asyncio.gather(
        *[
            run_agent_in_thread(agent_class(), agent_contents[name])
            for name, agent_class in agents_to_run.items()
        ],
        return_exceptions=True
    )

    # Check for exceptions
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            logging.error(f"Agent {i} failed with error: {res}")
            return None

    ordered_keys = list(agents_to_run.keys())
    agent_outputs = dict(zip(ordered_keys, results))

    # If running a single agent, merge into the existing modular JSON to keep other agents untouched.
    existing_output_path = None
    output_dir = os.path.dirname(markdown_path)
    base_name = os.path.splitext(os.path.basename(markdown_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_modular_listing_gemini3.json")
    if agent_filter and os.path.exists(output_path):
        existing_output_path = output_path

    if agent_filter and not existing_output_path:
        logging.error("Single-agent extract requires existing output file to merge with.")
        return None

    if existing_output_path:
        with open(existing_output_path, "r") as f:
            final_listing = json.load(f)
    else:
        final_listing = {
            "listingName": "",
            "sections": [],
            "newsLinks": [],
            "details": {}
        }

    overview_data, financial_data, property_data, market_data, sponsor_data = (
        agent_outputs.get("overview"),
        agent_outputs.get("financial"),
        agent_outputs.get("property"),
        agent_outputs.get("market"),
        agent_outputs.get("sponsor"),
    )

    if "overview" in agents_to_run:
        if not overview_data:
            logging.error("Overview output missing.")
            return None
        sections = [
            to_block("hero", overview_data.hero),
            to_block("tickerMetrics", overview_data.tickerMetrics),
            to_block("compellingReasons", overview_data.compellingReasons),
            to_block("executiveSummary", overview_data.executiveSummary),
            to_block("investmentCards", overview_data.investmentCards)
        ]
        final_listing["listingName"] = overview_data.hero.listingName
        final_listing["sections"] = sections
        final_listing["newsLinks"] = to_dict(overview_data.newsLinks) if overview_data.newsLinks else []

    if "financial" in agents_to_run:
        if not financial_data:
            logging.error("Financial output missing.")
            return None
        final_listing.setdefault("details", {})["financialReturns"] = build_detail_page(
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
        )

    if "property" in agents_to_run:
        if not property_data:
            logging.error("Property output missing.")
            return None
        final_listing.setdefault("details", {})["propertyOverview"] = build_detail_page(
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
        )

    if "market" in agents_to_run:
        if not market_data:
            logging.error("Market output missing.")
            return None
        final_listing.setdefault("details", {})["marketAnalysis"] = build_detail_page(
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
        )

    if "sponsor" in agents_to_run:
        if not sponsor_data:
            logging.error("Sponsor output missing.")
            return None
        final_listing.setdefault("details", {})["sponsorProfile"] = {
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

        if sponsor_data.portfolio:
            final_listing["details"]["portfolioProjects"] = build_detail_page(
                "Portfolio Projects",
                "Overview of the assets currently in the portfolio",
                [("projectOverview", sponsor_data.portfolio)]
            )
        if sponsor_data.fundEntities or sponsor_data.fundDetails:
            final_listing["details"]["fundStructure"] = build_detail_page(
                "Fund Structure",
                "Entity structure and legal framework of the fund",
                [
                    ("fundSponsorEntities", sponsor_data.fundEntities),
                    ("fundDetails", sponsor_data.fundDetails)
                ]
            )
        if sponsor_data.participationSteps:
            final_listing["details"]["howInvestorsParticipate"] = build_detail_page(
                "How to Participate",
                "Next steps for qualified investors",
                [("participationSteps", sponsor_data.participationSteps)]
            )

    # Ensure output directory exists.
    output_dir = os.path.dirname(markdown_path)
    base_name = os.path.splitext(os.path.basename(markdown_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_modular_listing_gemini3.json")

    with open(output_path, 'w') as f:
        json.dump(final_listing, f, indent=2)

    logging.info(f"Pipeline complete. Output saved to: {output_path}")
    return output_path

async def main():
    parser = argparse.ArgumentParser(
        description="Run extraction from classified markdown buckets."
    )
    parser.add_argument("markdown_path")
    parser.add_argument("--agent", choices=["overview", "financial", "property", "market", "sponsor"], default=None)
    args = parser.parse_args()

    await run_pipeline(args.markdown_path, agent_filter=args.agent)

if __name__ == "__main__":
    asyncio.run(main())
