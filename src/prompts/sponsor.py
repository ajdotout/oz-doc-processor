from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# --- System Prompt ---
SYSTEM_PROMPT = """
You are an expert Real Estate Due Diligence Officer. Your goal is to extract the SPONSOR and FUND STRUCTURE data.

### 1. SPONSOR INTRO (Mandatory)
- **Goal**: Full introduction to the sponsor.
- **Highlights**: "Award", "Building", "Target" (ESG), "MapPin" (Location). extract 4 key highlights.

### 2. TRACK RECORD (Mandatory)
- **Goal**: Hard numbers demonstrating experience.
- **Constraint**: **EITHER 4 OR 8 items**.
- **Metrics**: AUM ($), Total Units Developed, Projects Completed, Avg IRR.

### 3. LEADERSHIP TEAM (Mandatory)
- **Goal**: Key principals.
- **Constraint**: **3 or 6 members**.
- **Fields**: Name, Title, Experience ("20+ years"), Background (Paragraph).

### 4. DEVELOPMENT PORTFOLIO (Optional)
- **Goal**: Table of past projects.
- **Fields**: Name, Location, Units, Status (Completed/In Progress), Returns (IRR) or Focus.

### 5. PARTNERSHIP OVERVIEW (Optional)
- **Goal**: If multiple entities exist (e.g., "General Partner", "Developer", "Sponsor"), list each with role + entity in **name** (e.g. "General Partner — Camp Verde Landmark Partners, LLC") and the exact role description in **description**.
- **whyItMatters**: If the deck has a "Why it matters for investors" (or similar) section with bullet points, populate as a list of strings.

### 6. FUND STRUCTURE (New/Codebase Specific)
- **Goal**: If strict fund details are separate from the intro, extract them here.
- **Sections to Extract**: `DistributionTimeline`, `TaxBenefits` (reuse from Financial if identical), `InvestmentStructure` (Min Inv, Fees).

### 7. HOW INVESTORS PARTICIPATE (New/Codebase Specific)
- **Goal**: Steps to invest.
- **Look for**: "Subscription Process", "Next Steps".
- **Schema**: Title ("Review Docs"), Icon ("FileText"), Points ("Sign PPM", "Fund Account").
"""

# --- Schema ---

class SponsorHighlightItem(BaseModel):
    icon: Optional[str] = Field(None, description="Lucide icon name")
    text: str

class SponsorHighlights(BaseModel):
    type: Literal['list', 'icons']
    items: List[SponsorHighlightItem]

class SponsorIntroContent(BaseModel):
    paragraphs: List[str]
    highlights: SponsorHighlights

class SponsorIntroSectionData(BaseModel):
    sponsorName: str
    content: SponsorIntroContent

class PartnershipOverviewPartner(BaseModel):
    name: str
    description: List[str]

class PartnershipOverviewSectionData(BaseModel):
    partners: List[PartnershipOverviewPartner]
    whyItMatters: Optional[List[str]] = None

class TrackRecordMetric(BaseModel):
    label: str
    value: str
    description: str

class TrackRecordSectionData(BaseModel):
    metrics: List[TrackRecordMetric] = Field(..., description="4 or 8 metrics")

class TeamMember(BaseModel):
    name: str
    title: str
    experience: str
    background: str

class LeadershipTeamSectionData(BaseModel):
    teamMembers: List[TeamMember] = Field(..., description="3 or 6 members")

class PortfolioProject(BaseModel):
    name: str
    location: str
    units: Optional[str]
    year: str
    status: Literal['Completed', 'In Progress', 'Planning', 'Operating']
    returnsOrFocus: str

class DevelopmentPortfolioSectionData(BaseModel):
    projects: List[PortfolioProject]
    investmentPhilosophy: Optional[dict]

class KeyDevelopmentPartner(BaseModel):
    name: str
    role: str
    description: str

class KeyDevelopmentPartnersSectionData(BaseModel):
    partners: List[KeyDevelopmentPartner]

class CompetitiveAdvantage(BaseModel):
    icon: str
    title: str
    description: str

class CompetitiveAdvantagesSectionData(BaseModel):
    advantages: List[CompetitiveAdvantage]

class SponsorTeamMember(BaseModel):
    name: str
    title: str
    roleDetail: Optional[str] = None

class SponsorEntity(BaseModel):
    name: str
    role: str
    descriptionPoints: List[str]
    team: List[SponsorTeamMember]

class FundSponsorEntitiesSectionData(BaseModel):
    entities: List[SponsorEntity]

class ParticipationStep(BaseModel):
    title: str
    icon: str
    points: List[str]

class ParticipationStepsSectionData(BaseModel):
    steps: List[ParticipationStep]

class FundDetailsItem(BaseModel):
    label: str
    value: str

class FundDetailsSectionData(BaseModel):
    details: List[FundDetailsItem]

class SponsorExtraction(BaseModel):
    intro: Optional[SponsorIntroSectionData]
    partnership: Optional[PartnershipOverviewSectionData]
    trackRecord: TrackRecordSectionData
    team: LeadershipTeamSectionData
    portfolio: Optional[DevelopmentPortfolioSectionData]
    keyPartners: Optional[KeyDevelopmentPartnersSectionData]
    advantages: Optional[CompetitiveAdvantagesSectionData]
    fundEntities: Optional[FundSponsorEntitiesSectionData]
    participationSteps: Optional[ParticipationStepsSectionData]
    fundDetails: Optional[FundDetailsSectionData]
