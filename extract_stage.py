import os
import sys
import json
import asyncio
import logging
from pathlib import Path
import argparse
from typing import Dict, List

# Add the current directory to sys.path to ensure src imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from src.agents.agents import (
    OverviewAgent,
    FinancialAgent,
    PropertyAgent,
    MarketAgent,
    SponsorAgent
)
from src.config import EXTRACTION_MODEL
from src.pipeline.extraction_cache import (
    sanitize_model_name,
    cache_agent_paths,
    compute_agent_input_signature,
    compute_manifest_signature,
    compute_prompt_signature,
    load_cached_agent_output,
    write_cached_agent_output,
)
from src.prompts import financial, market, overview, property, sponsor


AGENT_ROUTING = {
    "overview": {"om", "supplemental"},
    "financial": {"om", "proforma", "supplemental"},
    "property": {"om", "research", "supplemental"},
    "market": {"om", "research", "supplemental"},
    "sponsor": {"om", "supplemental"},
}
AGENT_OUTPUT_TYPES = {
    "overview": overview.OverviewExtraction,
    "financial": financial.FinancialExtraction,
    "property": property.PropertyExtraction,
    "market": market.MarketExtraction,
    "sponsor": sponsor.SponsorExtraction,
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

def _run_agent_sync(agent_cls, content):
    agent = agent_cls()
    return agent.run(content)


async def run_agent_in_thread(agent_cls, content):
    """Runs a blocking agent inside a separate thread."""
    return await asyncio.to_thread(_run_agent_sync, agent_cls, content)


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


def _model_filename_suffix(model_name: str) -> str:
    return sanitize_model_name(model_name)


def _listing_output_path(markdown_path: str) -> str:
    output_dir = Path(markdown_path).parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(markdown_path))[0]
    model_name = os.getenv("EXTRACTION_MODEL", EXTRACTION_MODEL)
    return os.path.join(
        str(output_dir),
        f"{base_name}_{_model_filename_suffix(model_name)}.json"
    )


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


async def run_pipeline(markdown_path: str, agent_filter: str = None, no_cache: bool = False):
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

    all_agents = {
        "overview": OverviewAgent,
        "financial": FinancialAgent,
        "property": PropertyAgent,
        "market": MarketAgent,
        "sponsor": SponsorAgent,
    }

    model_name = os.getenv("EXTRACTION_MODEL", EXTRACTION_MODEL)
    manifest_signature = compute_manifest_signature(manifest, file_entries)

    if agent_filter:
        if agent_filter not in all_agents:
            logging.error(f"Unknown agent: {agent_filter}. Choose from: {list(all_agents.keys())}")
            return None
        agents_to_run = {agent_filter: all_agents[agent_filter]}
    else:
        agents_to_run = all_agents

    agent_outputs: Dict[str, object] = {}
    cached_output_paths: Dict[str, str] = {}
    failed_agents: List[str] = []
    run_tasks = []
    run_task_meta = []

    logging.info("Initializing agents...")
    for name in agents_to_run:
        content = agent_contents[name]
        prompt_signature = compute_prompt_signature(name)
        input_signature = compute_agent_input_signature(
            name,
            content,
            manifest_signature,
            prompt_signature,
        )
        if not no_cache:
            cached_output = load_cached_agent_output(
                listing_dir,
                model_name,
                name,
                manifest_signature,
                prompt_signature,
                input_signature,
            )
            if cached_output is not None:
                result_path, _ = cache_agent_paths(listing_dir, model_name, name)
                try:
                    model_type = AGENT_OUTPUT_TYPES[name]
                    agent_outputs[name] = model_type.model_validate(cached_output)
                    cached_output_paths[name] = str(result_path)
                    logging.info(f"Loaded cached output for {name}.")
                    continue
                except Exception as exc:
                    logging.warning(f"Cached output for {name} could not be loaded: {exc}")

        try:
            task = run_agent_in_thread(agents_to_run[name], content)
            run_tasks.append(task)
            run_task_meta.append((name, prompt_signature, input_signature))
        except Exception as exc:
            logging.error(f"Failed to start agent {name}: {exc}")
            failed_agents.append(name)

    if run_tasks:
        logging.info("Running agents in parallel...")
        results = await asyncio.gather(*run_tasks, return_exceptions=True)
        for idx, res in enumerate(results):
            name, prompt_signature, input_signature = run_task_meta[idx]
            result_path, _ = cache_agent_paths(listing_dir, model_name, name)
            if isinstance(res, Exception):
                logging.error(f"Agent {name} failed with error: {res}")
                failed_agents.append(name)
                continue

            agent_outputs[name] = res
            cached_output_paths[name] = str(result_path)
            try:
                write_cached_agent_output(
                    listing_dir=listing_dir,
                    model_name=model_name,
                    agent_name=name,
                    output=to_dict(res),
                    manifest_signature=manifest_signature,
                    prompt_signature=prompt_signature,
                    input_signature=input_signature,
                )
            except Exception as exc:
                logging.error(f"Failed to cache agent output for {name}: {exc}")

    if failed_agents:
        logging.error(
            "Extraction failed for: "
            + ", ".join(sorted(failed_agents))
        )
    if agent_filter:
        if agent_filter in failed_agents or agent_filter not in agent_outputs:
            logging.error(f"Single-agent extract for '{agent_filter}' did not produce output.")
            return None
        return cached_output_paths.get(agent_filter)

    if failed_agents:
        logging.error("Final listing will not be written because one or more agents failed.")
        return None
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
    output_path = _listing_output_path(markdown_path)

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
    parser.add_argument("--no-cache", action="store_true", help="Ignore cached agent outputs and regenerate.")
    args = parser.parse_args()

    result_path = await run_pipeline(args.markdown_path, agent_filter=args.agent, no_cache=args.no_cache)
    if result_path:
        if args.agent:
            print(f"Agent cache file: {result_path}")
        else:
            print(f"Final JSON: {result_path}")

if __name__ == "__main__":
    asyncio.run(main())
