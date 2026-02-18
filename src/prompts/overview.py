from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# --- System Prompt ---
SYSTEM_PROMPT = """
You are an expert Real Estate Investment Analyst. Your goal is to extract the high-level OVERVIEW details from a real estate offering memorandum (OM) to populate the listing homepage.

You will be provided with the full text of the document (OCR output). Focus ONLY on the following sections, adhering strictly to the constraints.

### 1. HERO SECTION
- **Goal**: Extract key identifiers.
- **Rules**:
    - `listingName`: Use the official marketing name (e.g. "The Edge on Main").
    - `location`: City, State format (e.g. "Mesa, AZ").
    - `minInvestment`: Number only.
    - `fundName`: The legal entity name of the fund.

### 2. TICKER METRICS (Critical)
- **Goal**: A scrolling marquee of key metrics.
- **Constraint**: **EXACTLY 6 metrics**.
- **Labels**: You MUST use these exact labels where possible: '10-Yr Equity Multiple', 'Preferred Return', 'Min Investment', 'Location', 'Hold Period', 'Tax Benefit'.
- **Heuristic**: If '10-Yr Equity Multiple' is not explicit, look for "Multiple of Capital" or "MOIC".
- **Formatting**:
    - `value`: Concise (e.g., "2.8x", "15%").
    - `change`: A short "pop" of context (e.g., "+12%", "Guaranteed", "OZ Qualified").

### 3. COMPELLING REASONS
- **Goal**: Three highlighted cards explaining the top reasons to invest.
- **Constraint**: **EXACTLY 3 items**.
- **Content**: Focus on the most positive aspects (e.g., Tax Status, Location, Innovation).
- **Icons**: Choose a relevant Lucide icon name (e.g., "Rocket", "BarChart3", "MapPin").

### 4. EXECUTIVE SUMMARY
- **Goal**: A detailed narrative summary.
- **Structure**:
    - `quote`: A standout, punchy sentence from the documents.
    - `paragraphs`: **EXACTLY A LIST OF 2 STRINGS**. concise paragraphs (3-4 sentences each).
    - `conclusion`: A final closing sentence summarizing the opportunity.

### 5. INVESTMENT CARDS (Summary & Selection)
- **Goal**: Select EXACTLY 4 detail page links to display in the 2x2 grid.
- **Constraints**: 
    - **Total Cards**: EXACTLY 4.
    - **Logic & Ordering**:
        1. **Card 1 (Value)**: Choose 'financial-returns' (default) OR 'how-investors-participate' if the deal emphasizes the subscription process or is in its final funding phase.
        2. **Card 2 (Product)**: Choose 'property-overview' (default) OR 'portfolio-projects' if the document describes a fund/collection of assets rather than a single development.
        3. **Card 3 (Context)**: Always 'market-analysis'.
        4. **Card 4 (Trust)**: Always 'sponsor-profile'.
- **Metrics**: Select the top 3 metrics for each card that best represent that specific section.
- **Sponsor Profile Formatting**:
    - `title`: MUST be exactly "Sponsor Profile" (do not include the sponsor's name in the title).
    - `keyMetrics`: 
        - The FIRST metric MUST have `label`: "Sponsor Name" and `value`: the actual name of the sponsor.
        - The remaining 2 metrics should be credibility markers (e.g., "Years Active", "Units Built").
- **IDs**: Use exactly one of the IDs: 'financial-returns', 'property-overview', 'market-analysis', 'sponsor-profile', 'portfolio-projects', 'how-investors-participate'.

### 6. NEWS LINKS (Optional)
- Extract external validation links if present (news articles, press releases).
"""

# --- Schema ---

class HeroSectionData(BaseModel):
    listingName: str = Field(..., description="The main title of the listing.")
    location: str = Field(..., description="City and State, e.g. 'Mesa, AZ'")
    minInvestment: int = Field(..., description="Minimum investment amount in USD, e.g. 250000")
    fundName: str = Field(..., description="Name of the associated fund")

class TickerMetric(BaseModel):
    label: Literal["10-Yr Equity Multiple", "Preferred Return", "Min Investment", "Location", "Hold Period", "Tax Benefit"]
    value: str = Field(..., description="The value, e.g. '2.8x'")
    change: str = Field(..., description="Short context, e.g. '+12%' or 'Guaranteed'")

class TickerMetricsSectionData(BaseModel):
    metrics: List[TickerMetric] = Field(..., min_length=6, max_length=6, description="Exactly 6 key metrics")

class CompellingReason(BaseModel):
    title: str = Field(..., description="Short title, e.g. '100% Tax-Free Growth'")
    description: str = Field(..., description="1-2 sentences explaining the benefit.")
    highlight: str = Field(..., description="Short highlight text, e.g. '5-Minute Walk'")
    icon: str = Field(..., description="Lucide icon name, e.g. 'Rocket'")

class CompellingReasonsSectionData(BaseModel):
    reasons: List[CompellingReason] = Field(..., min_length=3, max_length=3, description="Exactly 3 compelling reasons")

class ExecutiveSummaryData(BaseModel):
    quote: str = Field(..., description="A standout quote from the document")
    paragraphs: List[str] = Field(..., min_length=2, max_length=2, description="Exactly two paragraphs summarizing the deal")
    conclusion: str = Field(..., description="A concluding sentence")

class ExecutiveSummarySectionData(BaseModel):
    summary: ExecutiveSummaryData

class InvestmentCardKeyMetric(BaseModel):
    label: str
    value: str

class InvestmentCard(BaseModel):
    id: Literal['financial-returns', 'fund-structure', 'property-overview', 'portfolio-projects', 'how-investors-participate', 'market-analysis', 'sponsor-profile']
    title: str
    keyMetrics: List[InvestmentCardKeyMetric] = Field(..., min_length=3, max_length=3)
    summary: str

class InvestmentCardsSectionData(BaseModel):
    cards: List[InvestmentCard] = Field(..., min_length=4, max_length=4, description="Exactly 4 investment summary cards")

class NewsCardMetadata(BaseModel):
    url: str
    title: str
    description: str
    image: str
    source: str

class OverviewExtraction(BaseModel):
    hero: HeroSectionData
    tickerMetrics: TickerMetricsSectionData
    compellingReasons: CompellingReasonsSectionData
    executiveSummary: ExecutiveSummarySectionData
    investmentCards: InvestmentCardsSectionData
    newsLinks: Optional[List[NewsCardMetadata]] = Field(default=[], description="External news links if found")
