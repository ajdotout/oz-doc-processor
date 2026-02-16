from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# --- System Prompt ---
SYSTEM_PROMPT = """
You are an expert Real Estate Asset Manager. Your goal is to extract the detailed PROPERTY and PHYSICAL ASSET data.

Focus ONLY on the following sections:

### 1. KEY FACTS
- **Goal**: Top-level physical stats.
- **Constraint**: **EXACTLY 4 items**.
- **Typical Items**: Total Units, Net Rentable Area (SF), Year Built, Site Size (Acres), Occupancy %.

### 2. AMENITIES
- **Goal**: Showcase community/property features.
- **Constraint**: **EITHER 4 OR 8 items**.
- **Icons**: Map each amenity to a relevant Lucide icon (e.g. 'Pool', 'Dumbbell', 'Wifi').

### 3. UNIT MIX (Optional)
- **Goal**: Detailed table of unit types.
- **Columns**: Type (e.g. "1 Bed / 1 Bath"), Count, SqFt, Rent ($).
- **Special Features**: If a "Unit Finishes" section exists, extract a summary into `specialFeatures`.

### 4. LOCATION HIGHLIGHTS
- **Goal**: Three cards highlighting the micro-location (e.g. "Walk Score", "Transit Oriented", "University Proximity").
- **Constraint**: **EXACTLY 3 items**.

### 5. DEVELOPMENT TIMELINE/PHASES
- If the project is under construction/multi-phase, extract the timeline status (Completed vs In Progress) and phase breakdown (Phase I units vs Phase II units).
"""

# --- Schema ---

class KeyPropertyFact(BaseModel):
    label: str = Field(..., description="Fact label, e.g. 'Total Units'")
    value: str = Field(..., description="Fact value, e.g. '388'")
    description: str = Field(..., description="Short context")

class KeyFactsSectionData(BaseModel):
    facts: List[KeyPropertyFact] = Field(..., min_length=4, max_length=4, description="Exactly 4 key property facts")

class Amenity(BaseModel):
    name: str
    icon: str = Field(..., description="Lucide icon name, e.g. 'Pool', 'Dumbbell'")

class AmenitiesSectionData(BaseModel):
    amenities: List[Amenity] = Field(..., description="4 or 8 items")

class UnitMixItem(BaseModel):
    type: str = Field(..., description="e.g. 'Studio', '1-Bed'")
    count: int
    sqft: str
    rent: str

class UnitMixSectionData(BaseModel):
    unitMix: List[UnitMixItem]
    specialFeatures: Optional[dict] = Field(None, description="Optional title and description of unit features")

class LocationHighlight(BaseModel):
    title: str
    description: str
    icon: str

class LocationHighlightsSectionData(BaseModel):
    highlights: List[LocationHighlight] = Field(..., min_length=3, max_length=3)

class LocationFeatureSection(BaseModel):
    category: str
    icon: str
    features: List[str]

class LocationFeaturesSectionData(BaseModel):
    featureSections: List[LocationFeatureSection]

class DevelopmentPhase(BaseModel):
    phase: str
    units: int
    sqft: str
    features: str
    timeline: str

class DevelopmentPhasesSectionData(BaseModel):
    phases: List[DevelopmentPhase]

class DevelopmentTimelineItem(BaseModel):
    status: Literal['completed', 'in_progress']
    title: str
    description: str

class DevelopmentTimelineSectionData(BaseModel):
    timeline: List[DevelopmentTimelineItem]

class PropertyExtraction(BaseModel):
    keyFacts: KeyFactsSectionData
    amenities: AmenitiesSectionData
    unitMix: Optional[UnitMixSectionData]
    locationHighlights: Optional[LocationHighlightsSectionData]
    locationFeatures: Optional[LocationFeaturesSectionData]
    phases: Optional[DevelopmentPhasesSectionData]
    timeline: Optional[DevelopmentTimelineSectionData]
