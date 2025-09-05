import os
import json
import logging
from typing import List, Optional, Union, Literal
from datetime import date

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from dotenv import load_dotenv
import time

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure Google Gemini API
gemini_api_key = os.environ.get("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

provider = GoogleProvider(api_key=gemini_api_key)
model = GoogleModel("gemini-2.5-flash", provider=provider)

# --- Pydantic Models for the Listing Schema ---

# --- Listing Overview Page Sections ---

class HeroSectionData(BaseModel):
    listingName: str
    location: str
    minInvestment: int
    fundName: str

class TickerMetric(BaseModel):
    label: Literal["10-Yr Equity Multiple", "Preferred Return", "Min Investment", "Location", "Hold Period", "Tax Benefit"]
    value: str
    change: str

class TickerMetricsSectionData(BaseModel):
    metrics: List[TickerMetric] = Field(..., min_length=6, max_length=6)

class CompellingReason(BaseModel):
    title: str
    description: str
    icon: str # Lucide icon name

class CompellingReasonsSectionData(BaseModel):
    reasons: List[CompellingReason] = Field(..., min_length=3, max_length=3)

class ExecutiveSummaryData(BaseModel):
    quote: str
    paragraphs: List[str] = Field(..., min_length=2, max_length=2)
    conclusion: str

class ExecutiveSummarySectionData(BaseModel):
    summary: ExecutiveSummaryData

class InvestmentCardMetric(BaseModel):
    label: str
    value: str

class InvestmentCard(BaseModel):
    id: Literal["financial-returns", "property-overview", "market-analysis", "sponsor-profile"]
    title: str
    keyMetrics: List[InvestmentCardMetric]
    summary: str

class InvestmentCardsSectionData(BaseModel):
    cards: List[InvestmentCard]

# --- Detail Page Sections: Sponsor Profile ---

class SponsorIntroContentHighlightsItem(BaseModel):
    text: str
    icon: Optional[str]

class SponsorIntroContent(BaseModel):
    paragraphs: List[str]
    highlights: dict # type: Literal['list', 'icons'], items: List[SponsorIntroContentHighlightsItem]

class SponsorIntroSectionData(BaseModel):
    sponsorName: str
    content: SponsorIntroContent

class PartnershipOverviewPartner(BaseModel):
    name: str
    description: List[str]

class PartnershipOverviewSectionData(BaseModel):
    partners: List[PartnershipOverviewPartner]

class TrackRecordMetric(BaseModel):
    label: Optional[str]
    value: str
    description: str

class TrackRecordSectionData(BaseModel):
    metrics: List[TrackRecordMetric] # Must contain 4 or 8 metrics

class LeadershipTeamMember(BaseModel):
    name: str
    title: str
    experience: str
    background: str

class LeadershipTeamSectionData(BaseModel):
    teamMembers: List[LeadershipTeamMember] # Must contain 3 or 6 members

class DevelopmentPortfolioProject(BaseModel):
    name: str
    location: str
    units: Union[int, str]
    year: Union[int, str]
    status: Literal['Completed', 'In Progress', 'Planning', 'Operating']
    returnsOrFocus: str

class DevelopmentPortfolioInvestmentPhilosophy(BaseModel):
    title: str
    description: str

class DevelopmentPortfolioSectionData(BaseModel):
    projects: List[DevelopmentPortfolioProject]
    investmentPhilosophy: Optional[DevelopmentPortfolioInvestmentPhilosophy]

class KeyDevelopmentPartner(BaseModel):
    name: str
    role: str
    description: str

class KeyDevelopmentPartnersSectionData(BaseModel):
    partners: List[KeyDevelopmentPartner] = Field(..., min_length=2, max_length=2)

class CompetitiveAdvantage(BaseModel):
    icon: str # Lucide icon name
    title: str
    description: str

class CompetitiveAdvantagesSectionData(BaseModel):
    advantages: List[CompetitiveAdvantage] # Must contain 2, 4, or 6 advantages

# --- Detail Page Sections: Financial Returns ---

class Projection(BaseModel):
    label: str
    value: str
    description: str

class ProjectionsSectionData(BaseModel):
    projections: List[Projection] = Field(..., min_length=6, max_length=6)

class DistributionTimelineItem(BaseModel):
    year: str
    phase: str
    distribution: str
    description: str

class DistributionTimelineSectionData(BaseModel):
    timeline: List[DistributionTimelineItem]

class TaxBenefit(BaseModel):
    icon: str # Lucide icon name
    title: str
    description: str

class TaxBenefitsSectionData(BaseModel):
    benefits: List[TaxBenefit]

class InvestmentStructureItem(BaseModel):
    label: str
    value: str

class InvestmentStructureSectionData(BaseModel):
    structure: List[InvestmentStructureItem]

# --- Detail Page Sections: Property Overview ---

class KeyFact(BaseModel):
    label: str
    value: str
    description: str

class KeyFactsSectionData(BaseModel):
    facts: List[KeyFact] = Field(..., min_length=4, max_length=4)

class Amenity(BaseModel):
    name: str
    icon: str # Lucide icon name

class AmenitiesSectionData(BaseModel):
    amenities: List[Amenity] # Must contain 4 or 8 items

class UnitMixItem(BaseModel):
    type: str
    count: int
    sqft: str
    rent: str

class UnitMixSpecialFeatures(BaseModel):
    title: str
    description: str

class UnitMixSectionData(BaseModel):
    unitMix: List[UnitMixItem]
    specialFeatures: Optional[UnitMixSpecialFeatures]

class LocationHighlightColors(BaseModel):
    bg: str # TailwindCSS background color class
    text: str # TailwindCSS text color class

class LocationHighlight(BaseModel):
    title: str
    description: str
    icon: str # Lucide icon name
    colors: Optional[LocationHighlightColors]

class LocationHighlightsSectionData(BaseModel):
    highlights: List[LocationHighlight] = Field(..., min_length=3, max_length=3)

class LocationFeature(BaseModel):
    category: str
    icon: str # Lucide icon name
    features: List[str]

class LocationFeaturesSectionData(BaseModel):
    featureSections: List[LocationFeature] = Field(..., min_length=3, max_length=3)

class DevelopmentTimelineItem(BaseModel):
    status: Literal['completed', 'in_progress']
    title: str
    description: str

class DevelopmentTimelineSectionData(BaseModel):
    timeline: List[DevelopmentTimelineItem]

class DevelopmentPhase(BaseModel):
    phase: str
    units: int
    sqft: str
    features: str
    timeline: str

class DevelopmentPhasesSectionData(BaseModel):
    phases: List[DevelopmentPhase]

# --- Detail Page Sections: Market Analysis ---

class MarketMetric(BaseModel):
    label: str
    value: str
    description: str

class MarketMetricsSectionData(BaseModel):
    metrics: List[MarketMetric] = Field(..., min_length=6, max_length=6)

class MajorEmployer(BaseModel):
    name: str
    employees: str
    industry: str
    distance: str

class MajorEmployersSectionData(BaseModel):
    employers: List[MajorEmployer] = Field(..., min_length=4, max_length=8)

class DemographicsItem(BaseModel):
    category: str
    value: str
    description: str

class DemographicsSectionData(BaseModel):
    demographics: List[DemographicsItem]

class KeyMarketDriver(BaseModel):
    title: str
    description: str
    icon: str # Lucide icon name

class KeyMarketDriversSectionData(BaseModel):
    drivers: List[KeyMarketDriver] = Field(..., min_length=4, max_length=4)

class SupplyDemandAnalysisItem(BaseModel):
    icon: str # Lucide icon name
    title: str
    description: str

class SupplyDemandSectionData(BaseModel):
    analysis: List[SupplyDemandAnalysisItem]

class Competitor(BaseModel):
    name: str
    built: str
    beds: str
    rent: str
    occupancy: str
    rentGrowth: str

class CompetitiveAnalysisSectionData(BaseModel):
    competitors: List[Competitor]
    summary: Optional[str]

class EconomicDiversificationSector(BaseModel):
    title: str
    description: str

class EconomicDiversificationSectionData(BaseModel):
    sectors: List[EconomicDiversificationSector]

# Define the overall structure for the `details` field, using a union of all possible detail page sections.

class FinancialReturnsDetails(BaseModel):
    pageTitle: str
    pageSubtitle: str
    backgroundImages: List[str]
    sections: List[Union[ProjectionsSectionData, DistributionTimelineSectionData, TaxBenefitsSectionData, InvestmentStructureSectionData]]

class PropertyOverviewDetails(BaseModel):
    pageTitle: str
    pageSubtitle: str
    backgroundImages: List[str]
    sections: List[Union[KeyFactsSectionData, AmenitiesSectionData, UnitMixSectionData, LocationHighlightsSectionData, LocationFeaturesSectionData, DevelopmentTimelineSectionData, DevelopmentPhasesSectionData]]

class MarketAnalysisDetails(BaseModel):
    pageTitle: str
    pageSubtitle: str
    backgroundImages: List[str]
    sections: List[Union[MarketMetricsSectionData, MajorEmployersSectionData, DemographicsSectionData, KeyMarketDriversSectionData, SupplyDemandSectionData, CompetitiveAnalysisSectionData, EconomicDiversificationSectionData]]

class SponsorProfileDetails(BaseModel):
    sponsorName: str
    sections: List[Union[SponsorIntroSectionData, PartnershipOverviewSectionData, TrackRecordSectionData, LeadershipTeamSectionData, DevelopmentPortfolioSectionData, KeyDevelopmentPartnersSectionData, CompetitiveAdvantagesSectionData]]

class Details(BaseModel):
    financialReturns: FinancialReturnsDetails
    propertyOverview: PropertyOverviewDetails
    marketAnalysis: MarketAnalysisDetails
    sponsorProfile: SponsorProfileDetails


# Main Listing Model with nested Pydantic models for sections and details
class Listing(BaseModel):
    listingName: str
    listingSlug: str
    projectId: str
    sections: List[Union[
        HeroSectionData,
        TickerMetricsSectionData,
        CompellingReasonsSectionData,
        ExecutiveSummarySectionData,
        InvestmentCardsSectionData
    ]]
    details: Details


def generate_listing_json(
    ocr_markdown_path: str,
    perplexity_prompt_path: str,
    output_json_path: str
):
    logging.info(f"Starting Gemini processing for {ocr_markdown_path}")

    # Read the OCR'd markdown content
    with open(ocr_markdown_path, 'r') as f:
        ocr_content = f.read()

    # Read the perplexity prompt instructions
    with open(perplexity_prompt_path, 'r') as f:
        prompt_instructions = f.read()

    # Construct the full prompt for Gemini
    full_prompt = f"""
    You are a real estate investment analyst. Your task is to extract relevant information from the provided real estate deal document and supplement it with web research to generate a structured JSON object.

    --- INSTRUCTIONS ---
    {prompt_instructions}

    --- DEAL DOCUMENT CONTENT ---
    {ocr_content}
    """

    # Create the PydanticAI agent with the GoogleModel instance
    gemini_agent = Agent(
        model,
        system_prompt="You are an expert real estate investment analyst tasked with extracting structured data from deal documents and generating a comprehensive JSON object according to a strict schema. Prioritize information from the deal document and use web research to supplement and verify. Maintain a positive, truthful investment narrative.",
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            logging.info(f"Sending prompt to Gemini 2.5 Pro (Attempt {attempt + 1}/{max_retries})...")
            result = gemini_agent.run_sync(full_prompt)

            # The result.output will be an instance of the Listing Pydantic model
            # listing = Listing.model_validate_json(result.output)
            # output_listing_data = listing.model_dump_json(indent=2)
            
            # For debugging: print raw output and write to file
            print("--- RAW GEMINI RESPONSE ---")
            print(result.output)
            print("---------------------------")
            output_listing_data = result.output


            with open(output_json_path, 'w') as f:
                f.write(output_listing_data)
            logging.info(f"Successfully generated and saved raw JSON to {output_json_path}")
            return  # Exit the function on success

        except Exception as e:
            logging.error(f"Error during Gemini processing on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logging.error("Max retries reached. Gemini processing failed.")
                raise 