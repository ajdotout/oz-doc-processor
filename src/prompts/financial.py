from pydantic import BaseModel, Field
from typing import List, Optional

# --- System Prompt ---
SYSTEM_PROMPT = """
You are an expert Real Estate Financial Analyst. Your goal is to extract the detailed FINANCIAL data/returns from a real estate offering memorandum.

You will be provided with the full text of the document (OCR output). Focus ONLY on the following sections.

### 1. FINANCIAL PROJECTIONS (Compulsory)
- **Goal**: A grid of exactly 6 highest-impact metrics.
- **Constraint**: **EXACTLY 6 items**.
- **Mandatory First 3**:
    1. Label: "10-Yr Equity Multiple" (Value ex: "4.29x")
    2. Label: "Target IRR" (Value ex: "17.7%")
    3. Label: "Preferred Return" (Value ex: "8.0%")
- **Selection**: Choose the remaining 3 to best represent financial strength (e.g., "Stabilized Yield", "Cash-on-Cash", "Total Capital Requirement").

### 2. DISTRIBUTION TIMELINE (Compulsory)
- **Goal**: Outlining expected distribution phases.
- **Format**: Year range (e.g., "Years 1-2") -> Phase Name -> Distribution % -> Description.

### 3. TAX BENEFITS (Compulsory)
- **Goal**: Explain Opportunity Zone (OZ) benefits.
- **Standard Items** (Extract/Verify these):
    1. "Capital Gains Deferral"
    2. "Basis Step-Up"
    3. "Tax-Free Growth"

### 4. INVESTMENT STRUCTURE (Compulsory)
- **Goal**: Key terms list.
- **Items**: Minimum Investment, Asset Type, Hold Period, Distribution Frequency, Sponsor Co-Invest.

### 5. CAPITAL STACK (Optional)
- **Goal**: Sources and Uses of funds.
- **Uses**: Acquisition, Construction, Soft Costs, Reserves.
- **Sources**: Senior Debt, Mezzanine Debt, Sponsor Equity, Investor Equity.
- **Calculations**: Ensure 'Total Project' matches the sum.

### 6. WATERFALL (Optional)
- **Goal**: Explain the split of profits.
- **Tiers**: Preferred Return -> Catch-up -> Carried Interest splits (e.g., 80/20, 70/30).
"""

# --- Schema ---

class Projection(BaseModel):
    label: str = Field(..., description="Metric name. First 3 MUST be '10-Yr Equity Multiple', 'Target IRR', 'Preferred Return'")
    value: str = Field(..., description="Value, e.g. '17.7%'")
    description: str = Field(..., description="Short explanation of the metric")

class ProjectionsSectionData(BaseModel):
    projections: List[Projection] = Field(..., min_length=6, max_length=6, description="Exactly 6 key financial projections.")

class CapitalUseItem(BaseModel):
    use: str
    amount: str
    percentage: str
    description: str

class CapitalSourceItem(BaseModel):
    source: str
    amount: str
    perUnit: str
    percentage: str
    description: str

class CapitalStackSectionData(BaseModel):
    uses: List[CapitalUseItem]
    sources: List[CapitalSourceItem]
    totalProject: str

class WaterfallItem(BaseModel):
    priority: str
    allocation: str
    description: str
    recipient: Optional[str]

class DistributionWaterfallSectionData(BaseModel):
    saleWaterfall: List[WaterfallItem]
    cashFlowDistribution: List[WaterfallItem]
    refinancingWaterfall: Optional[List[WaterfallItem]]

class DistributionPhase(BaseModel):
    year: str
    phase: str
    distribution: str
    description: str

class DistributionTimelineSectionData(BaseModel):
    timeline: List[DistributionPhase]

class TaxBenefit(BaseModel):
    icon: str = Field(..., description="Lucide icon name, e.g. 'Calendar', 'Target', 'DollarSign'")
    title: str
    description: str

class TaxBenefitsSectionData(BaseModel):
    benefits: List[TaxBenefit]

class InvestmentStructureItem(BaseModel):
    label: str
    value: str

class InvestmentStructureSectionData(BaseModel):
    structure: List[InvestmentStructureItem]

class FinancialExtraction(BaseModel):
    projections: ProjectionsSectionData
    capitalStack: Optional[CapitalStackSectionData]
    waterfall: Optional[DistributionWaterfallSectionData]
    timeline: DistributionTimelineSectionData
    taxBenefits: TaxBenefitsSectionData
    structure: InvestmentStructureSectionData
