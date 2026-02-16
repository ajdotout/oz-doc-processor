from .base_extractor import BaseExtractor
from ..prompts import overview, financial, property, market, sponsor
from typing import Type
from pydantic import BaseModel

class OverviewAgent(BaseExtractor):
    def get_system_prompt(self) -> str:
        return overview.SYSTEM_PROMPT

    def get_response_model(self) -> Type[BaseModel]:
        return overview.OverviewExtraction

class FinancialAgent(BaseExtractor):
    def get_system_prompt(self) -> str:
        return financial.SYSTEM_PROMPT

    def get_response_model(self) -> Type[BaseModel]:
        return financial.FinancialExtraction

class PropertyAgent(BaseExtractor):
    def get_system_prompt(self) -> str:
        return property.SYSTEM_PROMPT

    def get_response_model(self) -> Type[BaseModel]:
        return property.PropertyExtraction

class MarketAgent(BaseExtractor):
    def get_system_prompt(self) -> str:
        return market.SYSTEM_PROMPT

    def get_response_model(self) -> Type[BaseModel]:
        return market.MarketExtraction

class SponsorAgent(BaseExtractor):
    def get_system_prompt(self) -> str:
        return sponsor.SYSTEM_PROMPT

    def get_response_model(self) -> Type[BaseModel]:
        return sponsor.SponsorExtraction
