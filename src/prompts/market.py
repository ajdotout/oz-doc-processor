from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# --- System Prompt ---
SYSTEM_PROMPT = """
You are an expert Real Estate Market Analyst. Your goal is to extract detailed MARKET ANALYSIS data.

### ANTI-HALLUCINATION & SCOPING RULES (Critical)
1. **Macro Data Only**: Focus on city/submarket data (Population, Growth, Jobs).
2. **STRICT EXCLUSION**: Do NOT extract deal-level or property-level financial metrics (e.g., NOI, Cap Rate, Deal Rents, IRR). These are NOT market metrics.
3. **Source Selection**: The consolidated markdown contains `SOURCE FILE:` headers. If a section is from an Excel file (e.g., `.xlsx`, `pro forma`, `financial model`), **IGNORE IT**. Market data must come from narrative OM or area summary sections only.
4. **Missing Values**: If specific metrics aren't in the document, return fewer than 6 metrics. Never estimate or guess.

Focus ONLY on the following sections:

### 1. MARKET METRICS
- **Goal**: High-impact macro stats (City/Submarket).
- **Constraint**: **Up to 6 metrics**.
- **Examples**: "Population Growth", "Job Growth", "Median Income", "Vacancy Rate", "Rent Growth", "Unemployment Rate".
- **Forbidden**: Anything deal-specific or from a pro forma table.

### 2. MAJOR EMPLOYERS
- **Goal**: Top employers driving demand.
- **Constraint**: **4 to 8 items**.
- **Fields**: Name, # Employees (approx), Industry, Distance from site.

### 3. DEMOGRAPHICS (Optional)
- **Goal**: Household stats.
- **Fields**: Median Age, Bachelors Degree %, Avg Household Size.

### 4. KEY MARKET DRIVERS
- **Goal**: Exactly 4 cards explaining *why* this market is strong.
- **Constraint**: **EXACTLY 4 items**.
- **Icons**: Choose a relevant Lucide icon name (e.g., "TrendingUp", "Users", "MapPin").
- **Examples**: "Tech Hub Expansion", "University Growth", "Transit Connectivity".

### 5. SUPPLY & DEMAND (Optional)
- **Goal**: Quantitative/Qualitative balance.
- **Icons**: Choose a relevant Lucide icon name (e.g., "Home", "Building2", "LineChart").
- **Items**: Absorption rates, Delivery pipeline, Occupancy trends.

### 6. COMPETITIVE ANALYSIS (Optional)
- **Goal**: Rent comps.
- **Fields**: Competitor Name, Year Built, Rent/SF, Occupancy.
"""

# --- Schema ---

class MarketMetric(BaseModel):
    label: str
    value: str
    description: str

class MarketMetricsSectionData(BaseModel):
    metrics: List[MarketMetric] = Field(..., min_length=1, max_length=6, description="Up to 6 high-impact market metrics")

class MajorEmployer(BaseModel):
    name: str
    employees: str
    industry: str
    distance: str

class MajorEmployersSectionData(BaseModel):
    employers: List[MajorEmployer] = Field(..., min_length=4, max_length=8)

class Demographic(BaseModel):
    category: str
    value: str
    description: str

class DemographicsSectionData(BaseModel):
    demographics: Optional[List[Demographic]]
    layout: Literal['list', 'matrix'] = 'list'

class MarketDriver(BaseModel):
    title: str
    description: str
    icon: str

class KeyMarketDriversSectionData(BaseModel):
    drivers: List[MarketDriver] = Field(..., min_length=4, max_length=4)

class SupplyDemandItem(BaseModel):
    icon: str
    title: str
    description: str

class SupplyDemandSectionData(BaseModel):
    analysis: List[SupplyDemandItem]

class Competitor(BaseModel):
    name: str
    built: str
    beds: str
    rent: str
    occupancy: str
    rentGrowth: str

class CompetitiveAnalysisSectionData(BaseModel):
    competitors: Optional[List[Competitor]]
    summary: Optional[str]

class EconomicSector(BaseModel):
    title: str
    description: str

class EconomicDiversificationSectionData(BaseModel):
    sectors: List[EconomicSector]

class MarketExtraction(BaseModel):
    metrics: MarketMetricsSectionData
    employers: MajorEmployersSectionData
    demographics: Optional[DemographicsSectionData]
    drivers: KeyMarketDriversSectionData
    supplyDemand: Optional[SupplyDemandSectionData]
    competitors: Optional[CompetitiveAnalysisSectionData]
    diversification: Optional[EconomicDiversificationSectionData]
